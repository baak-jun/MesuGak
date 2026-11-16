from __future__ import annotations

import asyncio
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parents[1] / 'jobs')]
from contest_notifications import ContestNotifications
from strategy_engine.order_state import OrderStateStore


class ContestNotificationTests(unittest.TestCase):
    def test_health_incident_sends_once_until_recovery_even_after_restart(self):
        from datetime import datetime, timedelta
        from zoneinfo import ZoneInfo
        now = datetime(2026, 10, 29, 9, tzinfo=ZoneInfo('Asia/Seoul'))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'orders.sqlite3'
            with OrderStateStore(path) as store:
                ContestNotifications(store, enabled=True).health('scan_incomplete', 'timeout', now=now)
            with OrderStateStore(path) as store:
                mail = ContestNotifications(store, enabled=True)
                for minutes in [30, 60, 1440]:
                    mail.health('scan_incomplete', 'still failing', now=now+timedelta(minutes=minutes))
                self.assertEqual(len(store.pending_emails()), 1)
                mail.health('scan_incomplete', None, now=now+timedelta(days=2))
                mail.health('scan_incomplete', None, now=now+timedelta(days=2, minutes=1))
                self.assertEqual(len(store.pending_emails()), 2)
                mail.health('scan_incomplete', 'new incident', now=now+timedelta(days=3))
                self.assertEqual(len(store.pending_emails()), 3)

    def test_surge_exit_email_uses_the_faster_threshold(self):
        with tempfile.TemporaryDirectory() as directory, OrderStateStore(Path(directory)/'orders.db') as store:
            mail=ContestNotifications(store,enabled=True)
            row={'signal_id':'surge','side':'SELL','code':'A','quantity':5,'reason':'monitored_high_partial_exit','payload':{'snapshot':{'entryMode':'surge'}}}
            mail.trade(row,{'price':100},name='A',quantity=5,filled_quantity=5,average_price=100,holding_quantity=5,status='FILLED',notice_key='fill')
            body=store.pending_emails()[0]['body']
            self.assertIn('0.8%',body)
            self.assertNotIn('1.8%',body)

    def test_trade_has_actual_fill_quantity_amount_and_no_duplicate_mail(self):
        with tempfile.TemporaryDirectory() as directory, OrderStateStore(Path(directory) / 'orders.sqlite3') as store:
            mail = ContestNotifications(store, enabled=True)
            row = {'signal_id': 's1', 'side': 'SELL', 'code': '005930', 'quantity': 10, 'broker_order_no': '42', 'reason': 'monitored_high_partial_exit'}
            fill = {'price': 70000}
            for _ in range(2):
                mail.trade(row, fill, name='삼성전자', quantity=5, filled_quantity=5, average_price=70000, holding_quantity=15, status='PARTIALLY_FILLED', notice_key='same-fill')
            items = store.pending_emails()
            self.assertEqual(len(items), 1)
            self.assertIn('삼성전자', items[0]['subject'])
            for text in ['이번 체결 수량: 5주', '체결 단가: 70,000원', '이번 체결 금액: 350,000원', '미체결 수량: 5주', '보유 수량: 15주']:
                self.assertIn(text, items[0]['body'])

    def test_pause_and_resume_each_send_once_and_survive_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'orders.sqlite3'
            with OrderStateStore(path) as store:
                mail = ContestNotifications(store, enabled=True)
                mail.state(True, 'network_error', '연결 오류')
                mail.state(True, 'network_error', '동일 오류')
            with OrderStateStore(path) as store:
                mail = ContestNotifications(store, enabled=True)
                mail.state(True, 'network_error', '재시작 후 같은 오류')
                mail.state(False, 'streaming_execute', '수신 정상')
                mail.state(False, 'streaming_execute')
                self.assertEqual(len(store.pending_emails()), 2)
                self.assertFalse(store.get_runtime('contest_email_state')['paused'])

    def test_failed_smtp_is_saved_for_retry_and_does_not_escape_to_trading(self):
        with tempfile.TemporaryDirectory() as directory, OrderStateStore(Path(directory) / 'orders.sqlite3') as store:
            mail = ContestNotifications(store, enabled=True)
            mail.state(True, 'error')
            with patch('contest_notifications.send_gmail', side_effect=OSError('network')):
                self.assertEqual(asyncio.run(mail.deliver()), 0)
            self.assertEqual(store.pending_emails(), [])
            items = store.pending_emails(now=10**12)
            self.assertEqual(items[0]['attempts'], 1)
            self.assertEqual(items[0]['last_error'], 'OSError')
            store.connection.execute('UPDATE email_outbox SET next_attempt_at=0')
            store.connection.commit()
            with patch('contest_notifications.send_gmail') as sender:
                self.assertEqual(asyncio.run(mail.deliver()), 1)
                self.assertIn('message_id', sender.call_args.kwargs)
            self.assertEqual(store.pending_emails(now=10**12), [])

    def test_two_senders_cannot_claim_the_same_event(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'orders.sqlite3'
            with OrderStateStore(path) as first, OrderStateStore(path) as second:
                first.queue_email('a', 's', 'body')
                self.assertTrue(first.claim_email('a'))
                self.assertFalse(second.claim_email('a'))

    def test_disabled_email_and_secret_redaction(self):
        with tempfile.TemporaryDirectory() as directory, OrderStateStore(Path(directory) / 'orders.sqlite3') as store:
            ContestNotifications(store).state(True, 'error')
            self.assertEqual(store.pending_emails(), [])
            with patch.dict(os.environ, {'KIS_PAPER_APP_SECRET': 'secret-value'}):
                ContestNotifications(store, enabled=True).state(True, 'error', 'detail: secret-value')
            self.assertNotIn('secret-value', store.pending_emails()[0]['body'])
