import FinanceDataReader as fdr
import pandas as pd
import numpy as np
from tqdm import tqdm
import os

# ==========================================
# 1. 설정
# ==========================================
START_DATE = '2018-01-01'
END_DATE = '2025-12-31'
INITIAL_CAPITAL = 3_000_000
BETTING_RATIO = 0.1
TOP_N = 500

# ==========================================
# 2. 데이터 준비
# ==========================================
def preprocess_data(code):
    try:
        df = fdr.DataReader(code, "2021-01-01", END_DATE)
        if len(df) < 150: return None
        
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['StdDev'] = df['Close'].rolling(window=20).std()
        df['Upper'] = df['MA20'] + (df['StdDev'] * 2)
        df['Lower'] = df['MA20'] - (df['StdDev'] * 2)
        
        mask = df['MA20'] != 0
        df['Bandwidth'] = 0.0
        df.loc[mask, 'Bandwidth'] = (df['Upper'] - df['Lower']) / df['MA20']
        df['MinBW125'] = df['Bandwidth'].rolling(window=125).min()
        
        df = df[df.index >= START_DATE]
        return df
    except:
        return None

print(f"📥 데이터 로딩 중 ({TOP_N}개 종목)...")
stocks = fdr.StockListing('KRX').sort_values('Marcap', ascending=False).head(TOP_N)
stock_pool = {}

for idx, row in tqdm(stocks.iterrows(), total=len(stocks)):
    df = preprocess_data(row['Code'])
    if df is not None and not df.empty:
        stock_pool[row['Code']] = {'name': row['Name'], 'data': df}

# ==========================================
# 3. 시뮬레이션 시작
# ==========================================
print("\n📊 현실적 트레일링 스탑(갭하락 반영) 시뮬레이션...")

sample_code = list(stock_pool.keys())[0]
date_index = stock_pool[sample_code]['data'].index

cash = INITIAL_CAPITAL
portfolio = {} 
trade_records = []
daily_records = []

for today in tqdm(date_index):
    today_str = today.strftime('%Y-%m-%d')
    current_stock_value = 0
    
    # ----------------------------------------
    # [1] 매도 로직 (수정됨)
    # ----------------------------------------
    for code in list(portfolio.keys()):
        info = portfolio[code]
        df = stock_pool[code]['data']
        name = stock_pool[code]['name']
        
        if today not in df.index:
            current_stock_value += info['qty'] * info['highest']
            continue

        row = df.loc[today]
        curr_price = row['Close']
        open_price = row['Open']
        high_price = row['High']
        low_price = row['Low']
        
        # 1. 어제까지의 최고가 기준 손절가 계산
        current_highest = info['highest']
        stop_price = current_highest * 0.982
        
        sell_price = 0
        sell_type = ""
        
        # 🚨 [CASE A] 갭하락 (Gap Down) 체크
        # 장 시작(Open)하자마자 이미 손절가 밑인가?
        if open_price < stop_price:
            sell_price = open_price # 어쩔 수 없이 시가에 매도
            sell_type = "손절(갭하락)"
            
        else:
            # 🚨 [CASE B] 장중 하락 (Intraday Drop)
            # 시가는 괜찮았는데, 장중에 고점 찍고 내려오거나 그냥 내려온 경우
            
            # (1) 오늘 고가가 더 높으면 최고가 갱신 -> 손절가도 따라 올라감
            if high_price > current_highest:
                current_highest = high_price
                stop_price = current_highest * 0.982
                portfolio[code]['highest'] = current_highest # 포트폴리오 업데이트
            
            # (2) 갱신된(혹은 기존) 손절가를 저가가 건드렸나?
            if low_price <= stop_price:
                sell_price = stop_price # 정확히 손절가에 매도 (장중 대응)
                sell_type = "손절(장중이탈)"
                
        # 매도 실행 여부 확인
        if sell_price > 0:
            sell_amt = (sell_price * info['qty']) * 0.9977 # 수수료 적용
            cash += sell_amt
            profit_rate = (sell_price - info['buy_price']) / info['buy_price'] * 100
            
            trade_records.append({
                '날짜': today_str,
                '유형': '매도',
                '사유': sell_type,
                '종목명': name,
                '매수가': int(info['buy_price']),
                '매도가': int(sell_price),
                '수량': info['qty'],
                '수익률': f"{profit_rate:.2f}%"
            })
            del portfolio[code]
        else:
            # 안 팔렸으면 보유 유지
            current_stock_value += curr_price * info['qty']

    # ----------------------------------------
    # [2] 매수 (어제 돌파 -> 오늘 시가)
    # ----------------------------------------
    total_equity = cash + current_stock_value
    available_bet_size = total_equity * BETTING_RATIO
    
    if cash >= available_bet_size:
        for code, item in stock_pool.items():
            if code in portfolio: continue
            
            df = item['data']
            if today not in df.index: continue
            
            try:
                loc = df.index.get_loc(today)
                if loc < 6: continue 
            except:
                continue
                
            yesterday_row = df.iloc[loc-1]
            day_before = df.iloc[loc-2]
            
            recent_squeeze = (df['Bandwidth'].iloc[loc-6:loc-1] <= (df['MinBW125'].iloc[loc-6:loc-1] * 1.15)).any()
            is_expanding = yesterday_row['Bandwidth'] > day_before['Bandwidth']
            is_breakout = yesterday_row['Close'] > yesterday_row['Upper']
            
            if recent_squeeze and is_expanding and is_breakout:
                buy_price = df.iloc[loc]['Open']
                name = item['name']
                
                if buy_price > 0:
                    buy_qty = int(available_bet_size // buy_price)
                    buy_amt = buy_qty * buy_price
                    
                    if buy_qty > 0 and cash >= buy_amt:
                        cash -= buy_amt
                        portfolio[code] = {
                            'qty': buy_qty,
                            'buy_price': buy_price,
                            'highest': buy_price 
                        }
                        trade_records.append({
                            '날짜': today_str,
                            '유형': '매수',
                            '사유': '돌파매수',
                            '종목명': name,
                            '매수가': int(buy_price),
                            '매도가': '',
                            '수량': buy_qty,
                            '수익률': ''
                        })
                        
                        if cash < (total_equity * BETTING_RATIO):
                            break 
                            
    # 일별 기록
    daily_records.append({
        '날짜': today_str,
        '총자산': int(total_equity),
        '현금': int(cash)
    })

# ==========================================
# 4. 파일 저장 및 결과
# ==========================================
print("\n💾 결과 파일 저장 중...")
df_trades = pd.DataFrame(trade_records)
df_trades.to_csv('realistic_backtest_trades.csv', index=False, encoding='utf-8-sig')

df_daily = pd.DataFrame(daily_records)
df_daily.to_csv('realistic_backtest_daily.csv', index=False, encoding='utf-8-sig')

final_return = (df_daily.iloc[-1]['총자산'] - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100

print(f"   -> realistic_backtest_trades.csv")
print(f"   -> realistic_backtest_daily.csv")
print("\n" + "="*50)
print(f"🏆 최종 현실적 수익률: {final_return:.2f}%")
print("="*50)