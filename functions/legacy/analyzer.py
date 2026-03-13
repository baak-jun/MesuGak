import pandas as pd
import FinanceDataReader as fdr
import firebase_admin
from firebase_admin import credentials, firestore
import datetime
import time
import numpy as np

# ==========================================
# 1. 초기 설정
# ==========================================
class Config:
    CRED_PATH = "./serviceAccountKey.json"
    
    @staticmethod
    def initialize_firebase():
        if not firebase_admin._apps:
            cred = credentials.Certificate(Config.CRED_PATH)
            firebase_admin.initialize_app(cred)
        return firestore.client()

# ==========================================
# 2. 분석기 클래스
# ==========================================
class StockAnalyzer:
    def __init__(self, db):
        self.db = db

    def get_stock_data(self, code):
        """주가 데이터 수집 (최근 400일)"""
        try:
            end_date = datetime.datetime.now()
            start_date = end_date - datetime.timedelta(days=400)
            
            df = fdr.DataReader(code, start_date, end_date)
            
            # 데이터 최소 개수 확인
            if df.empty or len(df) < 120: 
                return None
            
            df = df.reset_index()
            df.columns = [c.lower() for c in df.columns]
            
            # 컬럼명 통일
            rename_map = {'index': 'date', 'adj close': 'close'}
            df.rename(columns=rename_map, inplace=True)
            
            if 'date' not in df.columns: return None

            # 숫자형 변환 (Volume 포함)
            cols = ['open', 'high', 'low', 'close', 'volume']
            for c in cols:
                if c in df.columns:
                    df[c] = pd.to_numeric(df[c], errors='coerce')
            
            df = df.dropna()
            
            # 거래량 0인 날도 데이터는 유지하되, 계산 시 주의
            return df
        except Exception as e:
            # print(f"❌ 데이터 수집 실패 ({code}): {e}")
            return None

    def calculate_indicators(self, df):
        """
        지표 계산 및 History 생성 (요청하신 구조 완벽 적용)
        """
        if df is None: return None
        
        # 1. 볼린저 밴드 및 보조지표 계산
        df['MA20'] = df['close'].rolling(window=20).mean()
        df['StdDev'] = df['close'].rolling(window=20).std()
        df['Upper'] = df['MA20'] + (df['StdDev'] * 2)
        df['Lower'] = df['MA20'] - (df['StdDev'] * 2)
        
        # Bandwidth
        # 분모가 0이 되는 경우 방지
        df['MA20'] = df['MA20'].replace(0, np.nan)
        df['Bandwidth'] = (df['Upper'] - df['Lower']) / df['MA20']
        
        # MinBW125 (125일 최저 밴드폭)
        df['MinBW125'] = df['Bandwidth'].rolling(window=125, min_periods=20).min()
        
        # NaN 및 Infinity 처리 (DB 저장 에러 방지)
        df = df.fillna(0)
        df = df.replace([np.inf, -np.inf], 0)
        
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        # 2. 매수/매도 패턴 분석
        status, pattern = "일반 흐름", "normal"
        
        if last.get('volume', 0) == 0:
            status, pattern = "거래정지", "suspended"
        else:
            # 스퀴즈 판단
            if last['MinBW125'] > 0 and last['Bandwidth'] <= (last['MinBW125'] * 1.15):
                status, pattern = "에너지 응축", "squeeze"
                
            # 매수 신호 판단 (5일내 스퀴즈 + 확장 + 상단돌파)
            recent_squeeze = (df['Bandwidth'].iloc[-5:-1] <= (df['MinBW125'].iloc[-5:-1] * 1.15)).any()
            is_expanding = last['Bandwidth'] > prev['Bandwidth']
            is_breakout = last['close'] > last['Upper']
            
            if recent_squeeze and is_expanding and is_breakout:
                status, pattern = "매수 신호", "buy_signal"

        # 3. [중요] History 배열 생성 (요청하신 필드명 준수)
        # 웹사이트 차트용 데이터 (최근 90일)
        recent_df = df.tail(90).copy()
        history_list = []
        
        for idx, row in recent_df.iterrows():
            d_str = row['date'].strftime('%Y-%m-%d')
            
            # %B 계산
            band_diff = row['Upper'] - row['Lower']
            pct_b = (row['close'] - row['Lower']) / band_diff if band_diff > 0 else 0.0
            
            # 모든 숫자는 float()로 감싸서 numpy type 제거
            history_item = {
                "date": d_str,
                "open": float(row['open']),
                "high": float(row['high']),
                "low": float(row['low']),
                "close": float(row['close']),
                "volume": float(row.get('volume', 0)),
                "upper": float(round(row['Upper'], 2)),
                "lower": float(round(row['Lower'], 2)),
                "ma20": float(round(row['MA20'], 2)),
                "bandwidth": float(round(row['Bandwidth'], 4)),
                "percentB": float(round(pct_b, 4))
            }
            history_list.append(history_item)

        # 마지막 날짜 기준 %B
        band_diff_last = last['Upper'] - last['Lower']
        last_pct_b = (last['close'] - last['Lower']) / band_diff_last if band_diff_last > 0 else 0.0

        # 4. 최종 결과 반환
        return {
            "status": str(status),
            "type": str(pattern),
            "currentPrice": float(last['close']),
            "volume": float(last.get('volume', 0)),
            "bandwidth": float(round(last['Bandwidth'], 4)),
            "percentB": float(round(last_pct_b, 4)),
            "lastDate": history_list[-1]['date'] if history_list else "",
            "history": history_list
        }

    def get_target_stocks(self, market="KR"):
        """전 종목 리스트 가져오기 (Marcap 포함)"""
        print(f"📥 [{market}] 전 종목 리스트 다운로드 중...")
        try:
            if market == "KR":
                # KRX 전체 종목, 시가총액(Marcap) 포함
                df = fdr.StockListing('KRX')
                df = df.sort_values('Marcap', ascending=False) # 시총 순 정렬
                
                # 필요한 컬럼만 추출
                # Marcap이 없는 경우 0으로 처리
                if 'Marcap' not in df.columns:
                    df['Marcap'] = 0
                
                return df[['Code', 'Name', 'Marcap']].to_dict('records')
            return []
        except Exception as e:
            print(f"❌ 종목 가져오기 실패: {e}")
            return []

    def run_market_analysis(self, market="KR"):
        """전체 분석 및 DB 저장"""
        targets = self.get_target_stocks(market)
        total_count = len(targets)
        print(f"🔥 [{market}] 총 {total_count}개 종목 분석 시작!\n")
        
        batch = self.db.batch()
        count = 0
        success_count = 0
        
        # 목록 요약 데이터 저장을 위한 리스트
        summary_list = []
        meta_chunk_index = 0
        
        for idx, stock in enumerate(targets):
            code = stock['Code']
            name = stock['Name']
            marcap = float(stock.get('Marcap', 0)) # 시가총액 (float 변환)
            
            # 데이터 가져오기 & 분석
            df = self.get_stock_data(code)
            res = self.calculate_indicators(df)
            
            if res:
                # [요청하신 루트 데이터 구조]
                res['id'] = f"{market}_{code}"  # 예: KR_005930
                res['name'] = name
                res['market'] = market
                res['marcap'] = marcap
                res['updatedAt'] = firestore.SERVER_TIMESTAMP
                
                # DB 저장
                doc_ref = self.db.collection('stock_analysis').document(res['id'])
                batch.set(doc_ref, res)
                
                # [추가] 메타 데이터 수집 (사이드바 목록용)
                summary_item = {
                    'id': res['id'],
                    'name': name,
                    'type': res['type'],
                    'status': res['status'],
                    'currentPrice': res['currentPrice'],
                    'bandwidth': res['bandwidth'],
                    'percentB': res['percentB'],
                    'marcap': marcap,
                    'volume': res['volume'],
                    'market': market
                }
                summary_list.append(summary_item)

                count += 1
                success_count += 1
                
                if res['type'] == 'buy_signal':
                    print(f"  ✨ [매수신호] {name} ({code})")
                
                # 400개마다 커밋 (상세 데이터)
                if count >= 400:
                    batch.commit()
                    print(f"  💾 상세 데이터 중간 저장 완료 ({success_count}/{total_count})")
                    batch = self.db.batch()
                    count = 0
                
                # [수정] 500개마다 메타 데이터 중간 저장 (안정성 강화)
                if len(summary_list) >= 500:
                    doc_name = f"meta_{market}_{meta_chunk_index}"
                    print(f"  📝 목록(meta_data) 중간 저장: {doc_name} ({len(summary_list)}개)")
                    
                    self.db.collection('meta_data').document(doc_name).set({
                        'list': summary_list,
                        'market': market,
                        'updatedAt': firestore.SERVER_TIMESTAMP
                    })
                    
                    summary_list = [] # 리스트 초기화
                    meta_chunk_index += 1

            if (idx + 1) % 100 == 0:
                print(f"  ... {idx + 1}개 완료")
            
            time.sleep(0.01)
            
        if count > 0:
            batch.commit()
            print(f"  💾 상세 데이터 최종 저장 완료.")

        # [수정] 남은 메타 데이터 최종 저장
        if summary_list:
            doc_name = f"meta_{market}_{meta_chunk_index}"
            print(f"  📝 목록(meta_data) 최종 저장: {doc_name} ({len(summary_list)}개)")
            
            self.db.collection('meta_data').document(doc_name).set({
                'list': summary_list,
                'market': market,
                'updatedAt': firestore.SERVER_TIMESTAMP
            })
            
        print(f"\n✅ [{market}] 분석 종료. (총 {success_count}개 데이터 생성)")