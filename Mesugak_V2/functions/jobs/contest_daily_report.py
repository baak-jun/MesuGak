"""End-of-day private account email; no orders or public cloud writes."""
import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
FUNCTIONS=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(FUNCTIONS),str(FUNCTIONS/'jobs')]
from school_paper_trader import load_server_env
from contest_notifications import ContestNotifications, clean_detail
from strategy_engine.kis_paper import KISPaperClient,KISPaperConfig
from strategy_engine.order_state import OrderStateStore
from strategy_engine.contest_market_data import SOURCE,atomic_json
KST=ZoneInfo('Asia/Seoul')

def score_views(snapshot, heartbeat, strategy, day):
    rows=[r for r in snapshot.get('summaries',[]) if not r.get('scorePending') and not r.get('scoreUnavailable')]
    names={r['code']:r.get('name',r['code']) for r in snapshot.get('summaries',[])}
    live=strategy.get('liveScores',{}) if strategy.get('sessionDate')==day and strategy.get('liveScoreDataSource')==SOURCE else {}
    current=heartbeat.get('watchCodes',[]) if heartbeat.get('sessionDate')==day else []
    explorers=set(heartbeat.get('explorationCodes',[]))
    ranked=[{'code':c,'name':names.get(c,c),'score':float(live[c]),'kind':'랜덤' if c in explorers else '고정/보호'} for c in current if c in live]
    ranked.sort(key=lambda r:(-r['score'],r['code']))
    daily=sorted(rows,key=lambda r:(-float(r.get('confidenceScore',0)),r['code']))
    return {'source':snapshot.get('source','unknown'),'scanStatus':snapshot.get('scanStatus'),
            'runDate':snapshot.get('runDate'),'scoredCount':len(rows),'targetCount':snapshot.get('targetCount'),
            'pendingCount':sum(bool(r.get('scorePending')) for r in snapshot.get('summaries',[])),
            'unavailableCount':sum(bool(r.get('scoreUnavailable')) for r in snapshot.get('summaries',[])),
            'dataDates':sorted({str(r.get('lastDate')) for r in rows if r.get('lastDate')}),
            'watchedCount':len(current),'coreCount':len(set(current)-explorers),'randomCount':len(set(current)&explorers),
            'observedCount':len(live),'watchedScoredCount':len(ranked),'watchedAbove60':sum(r['score']>60 for r in ranked),
            'topWatched':ranked[:10], 'topAnalysis':[{'code':r['code'],'name':r.get('name',r['code']), 'score':r.get('confidenceScore'),'asOf':r.get('lastDate'),'zeroVolume':not r.get('volume')} for r in daily[:10]]}

def build_report(now, account, orders, heartbeat, strategy, snapshot, pending, previous=None, errors=()):
    day=now.date().isoformat()
    fields=['cash','initialCash','totalEvalAmt','totalEquity','realizedPnl','unrealizedPnl','totalPnl','returnPct','holdingCount']
    clean_account={key:account.get(key) for key in fields} if account else None
    holdings=[{key:r.get(key) for key in ['code','name','quantity','buyPrice','price','evalAmt','pnl','pnlPct']} for r in (account or {}).get('holdings',[])]
    unique={(str(r.get('ord_dt','')),str(r.get('odno',''))):r for r in orders}
    trades=[]
    for r in unique.values():
        qty=int(float(r.get('tot_ccld_qty') or 0))
        if not qty:
            continue
        amount=float(r.get('tot_ccld_amt') or 0)
        avg=amount/qty if amount else float(r.get('avg_prvs') or 0)
        trades.append({'code':r.get('pdno'),'name':r.get('prdt_name',r.get('pdno')),'side':'매수' if r.get('sll_buy_dvsn_cd')=='02' else '매도','quantity':qty,'price':avg,'amount':amount or qty*avg,'time':r.get('ord_tmd'),'orderType':r.get('ord_dvsn_name','')})
    baseline=(previous or {}).get('account') or {}
    daily_pnl=float(account['totalEquity'])-float(baseline['totalEquity']) if account and account.get('totalEquity') is not None and baseline.get('totalEquity') is not None else None
    return {'date':day,'checkedAt':now.isoformat(timespec='seconds'),'complete':not errors,'errors':list(errors),
            'account':clean_account,'holdings':holdings,'trades':trades,'previousReportDate':(previous or {}).get('date'), 'dailyPnl':daily_pnl,
            'pendingOrders':[{k:r.get(k) for k in ['code','side','quantity','filled_quantity','status']} for r in pending],
            'runtime':{k:heartbeat.get(k) for k in ['checkedAt','sessionDate','status','error','entryEnabled','reconciliationRequired','buyScoreThreshold']},
            'scores':score_views(snapshot,heartbeat,strategy,day)}

def format_report(r):
    lines=[f'MesuGak 대회 모의매매 마감 요약 — {r["date"]}',f'조회 시각: {r["checkedAt"]}']
    account=r.get('account')
    if account:
        lines+=['','[계좌·포트폴리오]']
        for key,label in [('initialCash','초기 자금'),('cash','보유 현금'),('totalEvalAmt','보유 주식 평가액'),('totalEquity','총자산'),('totalPnl','초기 자금 대비 누적 손익'),('unrealizedPnl','보유 주식 평가손익')]:
            value=account.get(key)
            lines.append(f'{label}: {value:,.0f}원' if value is not None else f'{label}: 조회 불가')
        lines.append(f'누적 수익률: {float(account.get("returnPct") or 0):.4f}%')
        lines.append(f'전회 마감 보고 대비 손익: {r["dailyPnl"]:,.0f}원 ({r["previousReportDate"]} 대비)' if r.get('dailyPnl') is not None else '전회 마감 보고 대비 손익: 비교 기록 없음 — 누적 손익과 구분')
    else:
        lines+=['','계좌 조회 실패: 현재 잔고·손익을 확인하지 못했습니다.']
    lines+=['','[보유 종목]']
    for h in r['holdings']:
        lines.append(f'{h["name"]}({h["code"]}) {float(h["quantity"] or 0):g}주 / 평균 매입 {float(h["buyPrice"] or 0):,.2f}원 / 현재가 {float(h["price"] or 0):,.0f}원 / 평가액 {float(h["evalAmt"] or 0):,.0f}원 / 평가손익 {float(h["pnl"] or 0):,.0f}원 ({float(h["pnlPct"] or 0):.2f}%)')
    if not r['holdings']:
        lines.append('보유 없음' if account else '계좌 조회 실패로 확인 불가')
    lines+=['','[당일 증권사 확인 체결 — 수수료·세금 차감 전]']
    for t in sorted(r['trades'],key=lambda x:x.get('time') or ''):
        lines.append(f'{t["time"]} {t["name"]}({t["code"]}) {t["side"]} {t["quantity"]}주 / 평균 {t["price"]:,.2f}원 / 금액 {t["amount"]:,.0f}원 / {t["orderType"]}')
    if not r['trades']:
        lines.append('확인된 체결 없음 — 조회 오류 여부는 아래 상태 참조')
    lines+=['','[미확인·미체결 및 운영 상태]',f'로컬 미확인·미체결 주문: {len(r["pendingOrders"])}건']
    for p in r['pendingOrders']:
        lines.append(f'{p["code"]} {p["side"]} {p["filled_quantity"]}/{p["quantity"]}주, {p["status"]}')
    lines.append(str(r['runtime']))
    scores=r['scores']
    lines+=['','[전체 검사 — 현재 감시와 구분]',f'출처: {scores["source"]}, 검사 상태: {scores["scanStatus"]}, 실행일: {scores["runDate"]}', f'점수 산출: {scores["scoredCount"]}/{scores["targetCount"]}, 조회 대기: {scores["pendingCount"]}, 계산 불가: {scores["unavailableCount"]}, 일봉 기준일: {", ".join(scores["dataDates"]) or "확인 불가"}']
    for row in scores['topAnalysis']:
        lines.append(f'{row["name"]}({row["code"]}) {row["score"]}점 / {row["asOf"]}' + (' / 거래량 0: 유의' if row['zeroVolume'] else ''))
    lines+=['','[감시·랜덤 탐색 — 오늘 마지막 관측 실시간 점수]',f'고정/보호 {scores["coreCount"]}개, 랜덤 {scores["randomCount"]}개 / 감시 {scores["watchedCount"]}개 중 점수 확인 {scores["watchedScoredCount"]}개 / 60점 초과 {scores["watchedAbove60"]}개']
    for row in scores['topWatched']:
        lines.append(f'{row["kind"]}: {row["name"]}({row["code"]}) {row["score"]:.2f}점')
    if r['errors']:
        lines+=['','[조회 오류 — 누락 정보는 정상 조회 후 재발송]']+list(r['errors'])
    return '\n'.join(lines)

def queue_report(store, report):
    key='daily-summary:'+report['date']+('' if report['complete'] else ':error')
    return store.queue_email(key, f'[MesuGak 대회] {report["date"]} '+('마감 계좌·포트폴리오 요약' if report['complete'] else '마감 보고 조회 오류'), format_report(report))

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',default=str(FUNCTIONS.parent))
    parser.add_argument('--env-file',default='functions/.env.contest')
    parser.add_argument('--preview',action='store_true')
    args=parser.parse_args()
    load_server_env(args.env_file)
    root=Path(args.root).resolve()
    now=datetime.now(KST)
    day=now.date().isoformat()
    enabled=os.getenv('MESUGAK_CONTEST_EMAIL_ENABLED','false').lower()=='true'
    with OrderStateStore(root/'runtime/realtime_order_state.sqlite3') as store:
        mail=ContestNotifications(store,enabled=enabled)
        existing=store.connection.execute('SELECT sent_at FROM email_outbox WHERE event_key=?',('daily-summary:'+day,)).fetchone()
        if existing and not args.preview:
            count=asyncio.run(mail.deliver())
            print(json.dumps({'date':day,'status':'already_queued','deliveredCount':count}))
            return
        errors=[]
        client=KISPaperClient(KISPaperConfig.from_env())
        account=None
        orders=[]
        try:
            account,_=client.fetch_balance(initial_cash=float(os.getenv('MESUGAK_INITIAL_CASH','100000000')))
        except Exception as exc:
            errors.append('잔고 조회 실패: '+clean_detail(exc))
        try:
            orders=client.inquire_daily_orders(order_date=now.date())
        except Exception as exc:
            errors.append('당일 주문 조회 실패: '+clean_detail(exc))
        candidate=root/'runtime/checkpoints/contest_candidates_KR.json'
        snapshot=json.loads(candidate.read_text()) if candidate.exists() else {}
        directory=root/'runtime/reports'
        directory.mkdir(parents=True,exist_ok=True)
        directory.chmod(0o700)
        prior_files=sorted(p for p in directory.glob('daily_????-??-??.json') if p.stem[6:]<day)
        previous=json.loads(prior_files[-1].read_text()) if prior_files else None
        report=build_report(now,account,orders,store.get_runtime('heartbeat') or {},store.get_runtime('strategy') or {},snapshot,store.pending(),previous,errors)
        suffix='-preview' if args.preview else ('' if report['complete'] else '-error')
        atomic_json(directory/f'daily_{day}{suffix}.json',report)
        if args.preview:
            print(json.dumps({'preview':True,'report':report},ensure_ascii=False))
            return
        if not enabled:
            raise RuntimeError('Contest email must be enabled before scheduling daily reports')
        queue_report(store,report)
        sent=asyncio.run(mail.deliver())
        print(json.dumps({'date':day,'complete':report['complete'],'deliveredCount':sent}))
        if errors:
            raise SystemExit(1)

if __name__=='__main__':
    main()
