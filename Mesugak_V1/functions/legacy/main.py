import time
import datetime
import schedule
import csv
import os
from dotenv import load_dotenv

# 만든 모듈 가져오기
from kis_api import KoreaStockTrader
from analyzer import StockAnalyzer, Config

# ==========================================
# 1. 설정 및 초기화
# ==========================================
load_dotenv()

TRADE_LOG_FILE = "real_trade_history.csv"
DAILY_LOG_FILE = "real_daily_summary.csv"

db = Config.initialize_firebase()
analyzer = StockAnalyzer(db)
trader = KoreaStockTrader(mode='mock')
trader.auth()

print(f"🤖 [시스템 준비] 모드: {trader.get_current_mode().upper()}")

# ==========================================
# 2. 로깅 함수
# ==========================================
def log_trade(type, name, code, price, qty, profit_pct=0):
    file_exists = os.path.isfile(TRADE_LOG_FILE)
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    profit_str = f"{profit_pct:.2f}%" if type == '매도' else ""
    
    with open(TRADE_LOG_FILE, 'a', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['시간', '유형', '종목명', '코드', '단가', '수량', '총액', '수익률'])
        writer.writerow([now, type, name, code, price, qty, price*qty, profit_str])
    print(f"📝 [기록] {name} {type} 저장 완료")

def log_daily_summary():
    balance = trader.get_balance()
    total_eval = 0
    holdings = []
    
    for item in balance:
        code = item['pdno']
        qty = int(item['hldg_qty'])
        curr = trader.get_current_price(code)
        if curr:
            total_eval += curr * qty
            holdings.append(f"{code}({qty}주)")
            
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    file_exists = os.path.isfile(DAILY_LOG_FILE)
    
    with open(DAILY_LOG_FILE, 'a', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['날짜', '총평가금액', '보유종목수', '내역'])
        writer.writerow([today, total_eval, len(balance), " | ".join(holdings)])
    print(f"📝 [마감] 일별 결산 저장 완료")

# ==========================================
# 3. 스케줄링 작업
# ==========================================

def job_night_analysis():
    print("\n🌙 [분석] 데이터 최신화 및 매수 종목 발굴 시작...")
    
    # 1. 전체 DB 업데이트 (History 생성됨)
    analyzer.run_market_analysis("KR") 
    
    print("🔎 [검색] 업데이트된 DB에서 매수 신호 종목 추출 중...")
    
    # 2. 매수각 종목 추출
    docs = db.collection('stock_analysis').where('type', '==', 'buy_signal').stream()
    
    count = 0
    for doc in docs:
        data = doc.to_dict()
        
        # ✅ [수정] data['id'] 대신 doc.id 사용 (버그 해결)
        # doc.id 예시: "KR_005930"
        code_raw = doc.id.split('_')[1] 
        name = data['name']
        
        print(f"  ✨ 매수 대기 등록: {name} ({code_raw})")
        
        db.collection('pending_orders').document(f"KR_{code_raw}").set({
            'code': code_raw,
            'name': name,
            'date': datetime.datetime.now().strftime('%Y-%m-%d'),
            'status': 'ready'
        })
        count += 1
        
    print(f"✅ 분석 및 예약 완료. 총 {count}개 종목 매수 대기.")

def job_morning_buy():
    print("\n🌞 [매수] 장 시작! 예약된 종목 매수 시도...")
    trader.auth()
    
    docs = db.collection('pending_orders').where('status', '==', 'ready').stream()
    budget_per_stock = 200000 
    
    for doc in docs:
        data = doc.to_dict()
        code = data['code']
        name = data['name']
        
        curr_price = trader.get_current_price(code)
        if curr_price and curr_price > 0:
            qty = int(budget_per_stock // curr_price)
            
            if qty > 0:
                print(f"💰 {name} 매수 주문: {curr_price}원 x {qty}주")
                if trader.buy_market_order(code, qty):
                    db.collection('portfolio').document(code).set({
                        'name': name,
                        'buy_price': curr_price,
                        'highest_price': curr_price,
                        'quantity': qty,
                        'buy_at': datetime.datetime.now()
                    })
                    db.collection('pending_orders').document(doc.id).update({'status': 'done'})
                    log_trade("매수", name, code, curr_price, qty)
            else:
                print(f"  Pass: {name} (가격 {curr_price}원이 예산 초과)")
        time.sleep(0.2)

def job_monitoring():
    now = datetime.datetime.now()
    if now.weekday() >= 5 or not (9 <= now.hour < 16): return

    pf_refs = db.collection('portfolio').stream()
    
    for pf in pf_refs:
        data = pf.to_dict()
        code = pf.id
        name = data['name']
        highest = data.get('highest_price', 0)
        buy_price = data.get('buy_price', 0)
        qty = data.get('quantity', 0)
        
        curr = trader.get_current_price(code)
        if not curr: continue
        
        if curr > highest:
            highest = curr
            db.collection('portfolio').document(code).update({'highest_price': highest})
            
        stop_price = highest * 0.982
        
        if curr <= stop_price:
            print(f"\n🚨 {name} 매도 신호! (고점 {highest} -> 현재 {curr})")
            if trader.sell_market_order(code, qty):
                profit = (curr - buy_price) / buy_price * 100
                log_trade("매도", name, code, curr, qty, profit)
                db.collection('portfolio').document(code).delete()
        time.sleep(0.1)

# ==========================================
# 4. 실행
# ==========================================
schedule.every().day.at("23:00").do(job_night_analysis)
schedule.every().day.at("08:55").do(trader.auth)
schedule.every().day.at("09:01").do(job_morning_buy)
schedule.every().day.at("15:40").do(log_daily_summary)
schedule.every(1).minutes.do(job_monitoring)

print("\n⚡ [시스템 시작] 봇을 가동합니다.")
print("⚡ [초기화] 데이터를 최신 상태로 업데이트합니다 (약 10~15분 소요)...")

try:
    job_night_analysis()
except Exception as e:
    print(f"❌ 초기 분석 중 에러 발생 (무시하고 스케줄러 진입): {e}")

print("\n🕒 [대기 모드] 스케줄러가 작동 중입니다...")

while True:
    schedule.run_pending()
    time.sleep(1)