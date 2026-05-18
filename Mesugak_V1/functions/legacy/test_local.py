import time
import datetime
import pandas as pd
import FinanceDataReader as fdr
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

# ==========================================
# 1. Firebase 인증 및 초기화
# ==========================================
# 같은 폴더에 serviceAccountKey.json 파일이 있어야 합니다.
cred_path = "./serviceAccountKey.json"

try:
    cred = credentials.Certificate(cred_path)
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
    print("✅ Firebase 인증 성공")
except Exception as e:
    print(f"❌ Firebase 인증 실패: {e}")
    print("폴더에 'serviceAccountKey.json' 파일이 있는지 확인해주세요.")
    exit()

db = firestore.client()

# ==========================================
# 2. 데이터 수집 함수 (FDR)
# ==========================================
def get_stock_data_fdr(code):
    """
    최근 90일치 데이터를 저장하기 위해 여유 있게 200일치 데이터를 가져옵니다.
    """
    today = datetime.datetime.now()
    start_date = today - datetime.timedelta(days=200)
    
    try:
        # FDR로 데이터 수집
        df = fdr.DataReader(code, start_date)
        
        # 데이터가 너무 적으면 분석 불가 (최소 60일 이상 권장)
        if df.empty or len(df) < 60:
            return None
            
        # 인덱스(Date)를 컬럼으로 변환 및 소문자 통일
        df = df.reset_index()
        df.rename(columns={
            'Date': 'date', 'Open': 'open', 'High': 'high', 
            'Low': 'low', 'Close': 'close', 'Volume': 'volume'
        }, inplace=True)
        
        return df
    except Exception as e:
        print(f"Error fetching {code}: {e}")
        return None

# ==========================================
# 3. 볼린저 밴드 분석 및 데이터 가공
# ==========================================
def analyze_bollinger(df):
    if df is None: return None
    
    # --- [A] 기술적 지표 계산 ---
    df['MA20'] = df['close'].rolling(window=20).mean() # 중심선 (이동평균)
    df['StdDev'] = df['close'].rolling(window=20).std()
    df['Upper'] = df['MA20'] + (df['StdDev'] * 2)
    df['Lower'] = df['MA20'] - (df['StdDev'] * 2)
    
    # 밴드폭 (Bandwidth)
    df['Bandwidth'] = 0.0
    mask = df['MA20'] != 0
    df.loc[mask, 'Bandwidth'] = (df['Upper'] - df['Lower']) / df['MA20']

    # --- [B] 패턴 판별 (최신 데이터 기준) ---
    last = df.iloc[-1]
    prev = df.iloc[-2]
    recent_bw = df['Bandwidth'].iloc[-5:].mean()

    status = "관망"
    pattern_code = "normal"
    
    # 1. 스퀴즈: 밴드폭이 0.12(12%) 미만
    if last['Bandwidth'] < 0.12:
        status = "에너지 응축 (스퀴즈)"
        pattern_code = "squeeze"
        
    # 2. 돌파: 좁은 밴드폭 상태에서 상단 돌파
    if recent_bw < 0.15 and last['close'] > last['Upper']:
        status = "상향 돌파 (강력 매수)"
        pattern_code = "breakout"
        
    # 3. 반전: 하단 밴드 이탈 후 복귀
    if prev['close'] < prev['Lower'] and last['close'] > last['Lower'] and last['close'] > last['open']:
        status = "바닥 반전 (매수 기회)"
        pattern_code = "reversal"

    if pattern_code == "normal":
        status = "일반 흐름"

    # --- [C] 히스토리 데이터 생성 (최근 90일치) ---
    # tail(90)을 사용하여 자동으로 날짜를 슬라이딩
    recent_df = df.tail(90).copy()
    history_data = []

    for index, row in recent_df.iterrows():
        # 날짜 문자열 변환
        d_str = row['date'].strftime('%Y-%m-%d') if hasattr(row['date'], 'strftime') else str(row['date']).split()[0]
        
        # %B 계산
        band_range = row['Upper'] - row['Lower']
        percent_b = (row['close'] - row['Lower']) / band_range if band_range != 0 else 0.0

        history_data.append({
            "date": d_str,
            # [필수] 캔들 차트용 데이터 (시, 고, 저, 종)
            "open": float(row['open']),
            "high": float(row['high']),
            "low": float(row['low']),
            "close": float(row['close']),
            
            # [필수] 볼린저 밴드 및 이동평균선 데이터
            "upper": float(round(row['Upper'], 2)),
            "lower": float(round(row['Lower'], 2)),
            "ma20": float(round(row['MA20'], 2)), # <-- 이게 있어야 노란선이 그려짐
            
            # [보조] 분석용 지표
            "bandwidth": float(round(row['Bandwidth'], 4)),
            "percentB": float(round(percent_b, 4))
        })

    # 최신 날짜
    last_date_str = last['date'].strftime('%Y-%m-%d') if hasattr(last['date'], 'strftime') else str(last['date']).split()[0]

    return {
        "status": status,
        "type": pattern_code,
        "currentPrice": float(last['close']),
        "bandwidth": float(round(last['Bandwidth'], 4)),
        "lastDate": last_date_str,
        "history": history_data
    }

# ==========================================
# 4. 배치 실행 로직
# ==========================================
def run_analysis_job(market="KR"):
    print(f"\n🚀 [{market}] 상위 300개 종목 데이터 갱신 시작...")
    print("   (캔들 데이터와 이동평균선을 포함하여 저장합니다)")
    
    target_stocks = []
    
    # 1. 종목 리스트 가져오기
    if market == "KR":
        print("KRX 종목 리스트 다운로드 중...")
        df_list = fdr.StockListing('KRX')
        df_list = df_list.sort_values('Marcap', ascending=False).head(300)
        target_stocks = df_list[['Code', 'Name']].to_dict('records')
        
    elif market == "US":
        print("S&P 500 종목 리스트 다운로드 중...")
        df_list = fdr.StockListing('S&P500')
        target_stocks = df_list.head(300)[['Symbol', 'Name']].to_dict('records')
        for s in target_stocks:
            s['Code'] = s.pop('Symbol')

    total = len(target_stocks)
    print(f"총 {total}개 종목 분석 시작.")
    
    count = 0
    batch = firestore.WriteBatch(db)
    
    for idx, stock in enumerate(target_stocks):
        code = stock['Code']
        name = stock['Name']
        
        # 진행률 표시
        print(f"[{idx+1}/{total}] {name} ({code}) 처리 중...", end="\r")
        
        # 데이터 수집 및 분석
        df = get_stock_data_fdr(code)
        result = analyze_bollinger(df)
        
        if result:
            result['name'] = name
            result['id'] = f"{market}_{code}"
            result['market'] = market
            result['updatedAt'] = firestore.SERVER_TIMESTAMP
            
            doc_ref = db.collection('stock_analysis').document(result['id'])
            batch.set(doc_ref, result)
            
            count += 1
            
            # 400개마다 저장
            if count % 400 == 0:
                batch.commit()
                batch = firestore.WriteBatch(db)
                print(f"\n💾 중간 저장 완료 ({count}개 처리)")

        # FDR 차단 방지용 딜레이
        time.sleep(0.1)

    batch.commit()
    print(f"\n\n✨ [{market}] 완료! 총 {count}개 종목 업데이트 됨.")

# ==========================================
# 5. 메인 실행부
# ==========================================
if __name__ == "__main__":
    while True:
        print("\n" + "="*40)
        print("   📈 주식 데이터 업데이트 (캔들+MA20 포함)")
        print("="*40)
        print("1. 한국 주식 (KR) - 상위 300개")
        print("2. 미국 주식 (US) - 상위 300개")
        print("q. 종료")
        
        choice = input("\n메뉴 선택 >> ")
        
        if choice == '1':
            run_analysis_job("KR")
        elif choice == '2':
            run_analysis_job("US")
        elif choice.lower() == 'q':
            break
        else:
            print("잘못된 입력입니다.")