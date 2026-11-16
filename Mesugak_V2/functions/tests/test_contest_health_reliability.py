import json,os,sys,tempfile,unittest
from datetime import datetime,timedelta
from pathlib import Path
from unittest.mock import patch,AsyncMock
from zoneinfo import ZoneInfo
sys.path[:0]=[str(Path(__file__).resolve().parents[1]),str(Path(__file__).resolve().parents[1]/'jobs')]
from strategy_engine.contest_health import assess_contest_health
from strategy_engine.order_state import OrderStateStore
from jobs.contest_health_monitor import check


class HealthReliabilityTests(unittest.TestCase):
    def setUp(self):
        self.now=datetime(2026,10,22,10,tzinfo=ZoneInfo('Asia/Seoul'))
        self.scan={'runDate':'2026-10-22','status':'running','remainingCount':0,'updatedAt':self.now.isoformat(),
                   'failedCodes':[{'code':'X','category':'insufficient_history','availableCandles':20,'requiredCandles':120}]}
        self.h={'sessionDate':'2026-10-22','checkedAt':self.now.isoformat(),'watchCodes':['A','B'],'watchStartedAt':{'A':0,'B':0},
                'lastTicks':{'A':self.now.timestamp(),'B':self.now.timestamp()-150},'scoreObservedAt':{'A':self.now.timestamp()},'heldCodes':[]}

    def test_short_history_and_active_retry_are_not_runtime_outages(self):
        issues=assess_contest_health(self.scan,self.h,self.now)[1]
        self.assertNotIn('scan_incomplete',issues)
        self.assertNotIn('scan_failures',issues)
        self.assertNotIn('quote_stale',issues)
        self.assertNotIn('quote_idle',issues)
        self.scan['failedCodes'].append({'code':'Y','category':'error','detail':'timeout'})
        self.assertNotIn('scan_failures',assess_contest_health(self.scan,self.h,self.now)[1])

    def test_calculation_email_threshold_is_strictly_above_100(self):
        self.scan['failedCodes']=[{'code':str(i),'category':'insufficient_history'} for i in range(100)]
        self.assertNotIn('scan_failures',assess_contest_health(self.scan,self.h,self.now)[1])
        self.scan['failedCodes'].append({'code':'101','category':'error'})
        self.assertIn('scan_failures',assess_contest_health(self.scan,self.h,self.now)[1])

    def test_held_quotes_and_whole_feed_keep_immediate_alerts(self):
        self.h['heldCodes']=['B']
        self.assertIn('held_quote_stale',assess_contest_health(self.scan,self.h,self.now)[1])
        self.h['lastTicks']['A']=self.now.timestamp()-150
        self.assertIn('quote_stale',assess_contest_health(self.scan,self.h,self.now)[1])

    def test_fresh_new_subscription_is_not_a_whole_feed_outage(self):
        self.h['watchStartedAt']['A']=self.now.timestamp()-30
        self.assertNotIn('quote_stale',assess_contest_health(self.scan,self.h,self.now)[1])

    def test_score_delay_boundary_and_new_watch_grace(self):
        self.h['scoreObservedAt']['A']=self.now.timestamp()-1199
        self.assertNotIn('score_stale',assess_contest_health(self.scan,self.h,self.now)[1])
        self.h['scoreObservedAt']['A']=self.now.timestamp()-1200
        self.assertIn('score_stale',assess_contest_health(self.scan,self.h,self.now)[1])
        self.h['watchStartedAt']['A']=self.now.timestamp()-1199
        self.assertNotIn('score_stale',assess_contest_health(self.scan,self.h,self.now)[1])

    def test_known_short_history_is_not_a_runtime_stall(self):
        self.h['scoreObservedAt']['A']=0
        self.h['watchHistoryMissingCodes']=['A']
        self.h['scoreHistoryErrors']={'A':'completed_history_unavailable:InsufficientHistoryError'}
        issues=assess_contest_health(self.scan,self.h,self.now)[1]
        self.assertNotIn('score_stale',issues)
        self.assertNotIn('history_missing',issues)

    def test_only_twenty_minute_score_incident_gets_recovery_mail(self):
        with tempfile.TemporaryDirectory() as d, patch.dict(os.environ,{'MESUGAK_CONTEST_EMAIL_ENABLED':'true'}),patch('jobs.contest_health_monitor.ContestNotifications.deliver',new_callable=AsyncMock,return_value=0):
            root=Path(d);(root/'runtime').mkdir()
            (root/'runtime/contest-kis-scan.json').write_text(json.dumps(self.scan))
            path=root/'runtime/realtime_order_state.sqlite3'
            with OrderStateStore(path) as store:
                store.set_runtime('contest_health:score_stale',{'active':True,'sequence':8,'notifiedAt':self.now.timestamp()})
            def run(age):
                self.h['scoreObservedAt']['A']=self.now.timestamp()-age
                with OrderStateStore(path) as store:store.set_runtime('heartbeat',self.h)
                check(root,self.now)
                with OrderStateStore(path) as store:
                    return [r for r in store.pending_emails() if r['event_key'].startswith('health:score_stale:')]
            self.assertEqual(len(run(1199)),0)
            self.assertEqual(len(run(0)),0)
            self.assertEqual(len(run(1200)),1)
            self.assertEqual(len(run(1201)),1)
            self.assertEqual(len(run(0)),2)
            self.assertEqual(len(run(0)),2)

    def test_nonheld_idle_needs_two_checks_and_small_short_history_sends_no_notice(self):
        with tempfile.TemporaryDirectory() as d, patch.dict(os.environ,{'MESUGAK_CONTEST_EMAIL_ENABLED':'true'}),patch('jobs.contest_health_monitor.ContestNotifications.deliver',new_callable=AsyncMock,return_value=0):
            root=Path(d);(root/'runtime').mkdir()
            self.scan['status']='done_with_errors'
            (root/'runtime/contest-kis-scan.json').write_text(json.dumps(self.scan))
            self.h['lastTicks']['B']=self.now.timestamp()-400
            def run(now):
                self.h['checkedAt']=now.isoformat();self.h['lastTicks']['A']=now.timestamp();self.h['scoreObservedAt']['A']=now.timestamp()
                with OrderStateStore(root/'runtime/realtime_order_state.sqlite3') as store:store.set_runtime('heartbeat',self.h)
                return check(root,now)
            self.assertNotIn('quote_idle',run(self.now)['issues'])
            self.assertIn('quote_idle',run(self.now+timedelta(minutes=2))['issues'])
            self.h['lastTicks']['B']=(self.now+timedelta(minutes=4)).timestamp()
            self.assertIn('quote_idle',run(self.now+timedelta(minutes=4))['issues'])
            self.h['lastTicks']['B']=(self.now+timedelta(minutes=6)).timestamp()
            self.assertNotIn('quote_idle',run(self.now+timedelta(minutes=6))['issues'])
            with OrderStateStore(root/'runtime/realtime_order_state.sqlite3') as store:
                rows=store.pending_emails()
                self.assertEqual(sum(r['event_key'].startswith('data-availability:') for r in rows),0)
                self.assertEqual(sum(r['event_key'].startswith('health:quote_idle:') for r in rows),2)
