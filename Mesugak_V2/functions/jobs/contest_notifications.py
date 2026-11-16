"""Durable event email for the contest bot, using the existing Gmail settings."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

FUNCTIONS_DIR = Path(__file__).resolve().parents[1]
if str(FUNCTIONS_DIR) not in sys.path:
    sys.path.insert(0, str(FUNCTIONS_DIR))

from strategy_engine.order_state import OrderStateStore
from monitor_school_server import send_gmail
from school_paper_trader import load_server_env

KST = ZoneInfo('Asia/Seoul')


def clean_detail(value: object) -> str:
    text = str(value or '')
    for key in ['KIS_PAPER_APP_KEY', 'KIS_PAPER_APP_SECRET', 'KIS_PAPER_CANO', 'KIS_PAPER_HTS_ID', 'MESUGAK_GMAIL_APP_PASSWORD']:
        secret = os.getenv(key, '')
        if secret:
            text = text.replace(secret, '[비공개]')
    return text[:2000]


class ContestNotifications:
    def __init__(self, store: OrderStateStore, *, enabled: bool = False):
        self.store, self.enabled = store, enabled

    def health(self, key: str, detail: str | None, *, now: datetime | None = None) -> None:
        """Independent incidents: a stale scan must not masquerade as an order stop."""
        if not self.enabled:
            return
        now = now or datetime.now(KST)
        state_key = 'contest_health:' + key
        previous = self.store.get_runtime(state_key) or {}
        active = bool(detail)
        if active == bool(previous.get('active')):
            return
        sequence = int(previous.get('sequence', 0)) + 1
        label = '이상 감지' if active else '이상 복구'
        body = f'대회 {label}\n시각: {now.isoformat(timespec="seconds")}\n항목: {key}\n{clean_detail(detail) if active else "해당 점검 조건이 정상 범위로 돌아왔습니다."}'
        self.store.queue_email(f'health:{key}:{sequence}', f'[MesuGak 대회] {label}: {key}', body)
        self.store.set_runtime(state_key, {'active': active, 'sequence': sequence, 'notifiedAt': now.timestamp(), 'detail': clean_detail(detail)})

    def state(self, paused: bool, reason: str, detail: str = '') -> None:
        if not self.enabled:
            return
        previous = self.store.get_runtime('contest_email_state') or {}
        if previous.get('paused', False) == paused:
            return
        sequence = int(previous.get('sequence', 0)) + 1
        full_stop = reason in {'process_exit', 'fatal_process_error', 'configuration_error', 'holiday_check_failed', 'account_sync_failed'}
        kind = ('오류로 자동매매 정지' if full_stop else '오류로 신규 매수 정지') if paused else '자동매매 재개'
        now = datetime.now(KST).isoformat(timespec='seconds')
        body = f'대회 모의매매 {kind}\n시각: {now}\n상태: {reason}\n사유: {clean_detail(detail) or reason}'
        if paused:
            body += ('\n\n자동매매 프로세스가 정상 실행되지 못하고 있습니다. 장중 재시작 예약에서 복구를 시도합니다.' if full_stop else
                     '\n\n신규 매수는 중지하며, 시세를 수신하는 보유 종목의 청산 관리는 계속합니다.')
        self.store.queue_email(f'state:{sequence}:{paused}', f'[MesuGak 대회] {kind}', body)
        self.store.set_runtime('contest_email_state', {'paused': paused, 'sequence': sequence, 'reason': reason, 'detail': clean_detail(detail), 'changedAt': now})

    def trade(self, row: dict, fill: dict, *, name: str, quantity: int, filled_quantity: int,
              average_price: float, holding_quantity: int, status: str, notice_key: str) -> None:
        if not self.enabled:
            return
        side = '매수' if row['side'] == 'BUY' else '매도'
        price = float(fill.get('price') or 0)
        label = '체결 완료' if status == 'FILLED' else '일부 체결'
        snapshot = (row.get('payload') or {}).get('snapshot') or {}
        surge = snapshot.get('entryMode') == 'surge'
        partial, full = ('0.8', '1.5') if surge else ('1.8', '3')
        reason = {'live_score_entry': '실시간 점수 기준 이상', 'volume_surge_entry': '저점수 종목의 가격·거래량 급등 조건 충족',
                  'monitored_high_partial_exit': f'매수 체결 이후 최고가 대비 {partial}% 하락: 50% 매도',
                  'monitored_high_full_exit': f'매수 체결 이후 최고가 대비 {full}% 하락: 남은 수량 전량 매도'}.get(row.get('reason'), row.get('reason') or '')
        body = (f'대회 모의계좌 {side} {label}\n'
                f'시각: {datetime.now(KST).isoformat(timespec="seconds")}\n'
                f'종목: {name} ({row["code"]})\n'
                f'이번 체결 수량: {quantity:,}주\n체결 단가: {price:,.0f}원\n'
                f'이번 체결 금액: {quantity * price:,.0f}원\n'
                f'주문 수량: {int(row["quantity"]):,}주\n누적 체결 수량: {filled_quantity:,}주\n'
                f'평균 체결 단가: {average_price:,.2f}원\n누적 체결 금액: {filled_quantity * average_price:,.0f}원\n'
                f'미체결 수량: {max(0, int(row["quantity"]) - filled_quantity):,}주\n'
                f'체결 반영 후 보유 수량: {holding_quantity:,}주\n'
                f'주문 번호: {row.get("broker_order_no", "")}\n매매 사유: {reason}\n'
                '금액은 수수료·세금 차감 전 체결 금액입니다.')
        if snapshot.get('liveConfidenceScore') is not None:
            body += f'\n판단 시 실시간 점수: {snapshot["liveConfidenceScore"]}'
        if fill.get('reconciled'):
            body += (f'\n\n체결 통보 누락을 증권사 주문 조회로 복구한 알림입니다.'
                     f'\n주문일: {fill.get("orderDate", "")} / 주문 시각: {fill.get("orderTime") or "확인 불가"}'
                     '\n위 알림 시각은 복구 확인 시각이며, 보유 수량은 조회 당시 잔고입니다.')
        key = f'fill:{row["signal_id"]}:{notice_key}'
        self.store.queue_email(key, f'[MesuGak 대회] {side} {label}: {name} {quantity:,}주', body)

    async def deliver(self, *, limit: int = 10) -> int:
        if not self.enabled:
            return 0
        sent = 0
        for item in self.store.pending_emails(limit=limit):
            if not self.store.claim_email(item['event_key']):
                continue
            message_id = '<' + hashlib.sha256(item['event_key'].encode()).hexdigest() + '@mesugak.invalid>'
            try:
                await asyncio.to_thread(send_gmail, item['subject'], item['body'], message_id=message_id)
            except Exception as exc:
                self.store.finish_email(item['event_key'], error=type(exc).__name__)
            else:
                self.store.finish_email(item['event_key'])
                sent += 1
        return sent


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--env-file', default='functions/.env.contest')
    parser.add_argument('--state-path', default='runtime/realtime_order_state.sqlite3')
    parser.add_argument('--process-exit', type=int)
    parser.add_argument('--send-test', action='store_true')
    args = parser.parse_args()
    load_server_env(args.env_file)
    enabled = os.getenv('MESUGAK_CONTEST_EMAIL_ENABLED', 'false').lower() == 'true'
    with OrderStateStore(args.state_path) as store:
        notifications = ContestNotifications(store, enabled=enabled)
        if args.process_exit:
            notifications.state(True, 'process_exit', f'대회 프로세스가 오류 코드 {args.process_exit}로 종료됐습니다. 장중 재시작 예약으로 복구를 시도합니다.')
        if args.send_test and enabled:
            key = 'configuration-test:' + datetime.now(KST).isoformat()
            store.queue_email(key, '[MesuGak 대회] 매매·정지·재개 메일 설정 완료',
                              '대회 모의매매 메일 알림을 활성화했습니다.\n매수·매도 체결 시 종목, 수량, 단가, 금액, 체결 상태를 보내며, 오류로 인한 신규 매수 정지와 정상 재개도 알립니다.')
        count = asyncio.run(notifications.deliver())
        print({'emailEnabled': enabled, 'sentCount': count})


if __name__ == '__main__':
    main()
