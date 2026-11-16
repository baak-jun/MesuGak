import sqlite3
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from strategy_engine.incident_email_policy import install


class IncidentEmailPolicyTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.addCleanup(self.db.close)
        self.db.execute('CREATE TABLE email_outbox(event_key TEXT PRIMARY KEY,subject TEXT,body TEXT,created_at TEXT,sent_at TEXT,next_attempt_at REAL DEFAULT 0,last_error TEXT DEFAULT "")')
        install(self.db)
        self.now=datetime(2026,10,29,1,tzinfo=timezone.utc)

    def queue(self,key,seconds=0,recovery=False):
        self.db.execute('INSERT INTO email_outbox(event_key,subject,body,created_at) VALUES (?,?,?,?)',
            (key,'이상 복구' if recovery else '이상 감지','detail',(self.now+timedelta(seconds=seconds)).isoformat()))

    def eligible(self,seconds):
        return [r[0] for r in self.db.execute('SELECT event_key FROM email_outbox WHERE sent_at IS NULL AND next_attempt_at<=?',(self.now.timestamp()+seconds,))]

    def test_threshold_exactly_twenty_minutes_and_no_reminders(self):
        self.queue('health:network:1')
        self.assertEqual(self.eligible(1199),[])
        self.assertEqual(self.eligible(1200),['health:network:1'])
        self.queue('health:network:2',3600)
        self.assertEqual(self.eligible(3600),['health:network:1'])

    def test_short_incident_suppresses_both_messages(self):
        self.queue('health:network:1')
        self.queue('health:network:2',1199,True)
        self.assertEqual(self.eligible(100000),[])

    def test_recovery_only_after_alert_was_actually_sent(self):
        self.queue('health:network:1')
        self.db.execute("UPDATE email_outbox SET sent_at=? WHERE event_key='health:network:1'",((self.now+timedelta(seconds=1200)).isoformat(),))
        self.queue('health:network:2',1201,True)
        self.assertEqual(self.eligible(1201),['health:network:2'])
        self.queue('health:network:3',1202,True)
        self.assertEqual(self.eligible(1202),['health:network:2'])

    def test_recovered_before_smtp_succeeded_cancels_late_error_and_recovery(self):
        self.queue('health:network:1')
        self.queue('health:network:2',1800,True)
        self.assertEqual(self.eligible(100000),[])

    def test_pause_resume_and_next_incident(self):
        self.queue('state:1:True')
        self.queue('state:2:False',10,True)
        self.assertEqual(self.eligible(100000),[])
        self.queue('state:3:True',20)
        self.assertEqual(self.eligible(1219),[])
        self.assertEqual(self.eligible(1220),['state:3:True'])

    def test_score_delay_is_not_applied_twice(self):
        self.queue('health:score_stale:1')
        self.assertEqual(self.eligible(0),['health:score_stale:1'])

    def test_scan_threshold_clear_is_silent_and_allows_new_incident(self):
        self.queue('health:scan_failures:1')
        self.db.execute("UPDATE email_outbox SET sent_at='sent' WHERE event_key='health:scan_failures:1'")
        self.queue('health:scan_failures:2',1201,True)
        self.assertEqual(self.eligible(100000),[])
        self.queue('health:scan_failures:3',1300)
        self.assertEqual(self.eligible(2499),[])
        self.assertEqual(self.eligible(2500),['health:scan_failures:3'])

    def test_daily_summary_and_trade_rules_are_not_changed(self):
        self.queue('daily-summary:2026-10-29')
        self.assertEqual(self.eligible(0),['daily-summary:2026-10-29'])

    def test_independent_error_types_have_independent_timers(self):
        self.queue('health:network:1')
        self.queue('health:scan_incomplete:1',100)
        self.assertEqual(self.eligible(1200),['health:network:1'])
        self.queue('health:network:2',1199,True)
        self.assertEqual(self.eligible(1300),['health:scan_incomplete:1'])
