import sys,tempfile,unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
sys.path[:0]=[str(Path(__file__).resolve().parents[1]),str(Path(__file__).resolve().parents[1]/'jobs')]
from jobs.contest_daily_report import build_report,format_report,queue_report,score_views
from strategy_engine.order_state import OrderStateStore
from strategy_engine.contest_market_data import SOURCE

class ContestDailyReportTests(unittest.TestCase):
    def test_whole_universe_and_random_watch_scores_are_distinct(self):
        snapshot={'summaries':[{'code':'A','name':'A','confidenceScore':80,'lastDate':'2026-10-14'}, {'code':'B','confidenceScore':40}, {'code':'C','confidenceScore':0,'scorePending':True}]}
        h={'sessionDate':'2026-10-15','watchCodes':['B','C'],'explorationCodes':['B','C']}
        strategy={'sessionDate':'2026-10-15','liveScoreDataSource':SOURCE,'liveScores':{'A':70,'B':35}}
        report=score_views(snapshot,h,strategy,'2026-10-15')
        self.assertEqual(report['topAnalysis'][0]['score'],80)
        self.assertEqual(report['topWatched'],[{'code':'B','name':'B','score':35.0,'kind':'랜덤'}])
        self.assertEqual(report['randomCount'],2)
        self.assertEqual(report['watchedAbove60'],0)
        self.assertEqual(report['scoredCount'],2)

    def test_daily_mail_dedup_missing_baseline_and_failure_does_not_consume_success(self):
        now=datetime(2026,10,15,15,40,tzinfo=ZoneInfo('Asia/Seoul'))
        account={'cash':990,'totalEquity':990,'initialCash':1000,'totalPnl':-10,'returnPct':-1,'holdings':[]}
        orders=[{'ord_dt':'20261015','odno':'1','pdno':'A','prdt_name':'A','sll_buy_dvsn_cd':'01','tot_ccld_qty':'2','tot_ccld_amt':'200','ord_tmd':'110000'}]*2
        report=build_report(now,account,orders,{}, {},{},[])
        self.assertIsNone(report['dailyPnl'])
        self.assertEqual(len(report['trades']),1)
        self.assertIn('보유 없음',format_report(report))
        with tempfile.TemporaryDirectory() as root,OrderStateStore(Path(root)/'orders.sqlite3') as store:
            failed=build_report(now,None,[],{},{},{},[],errors=['API error'])
            self.assertTrue(queue_report(store,failed))
            self.assertTrue(queue_report(store,report))
            self.assertFalse(queue_report(store,report))
            self.assertEqual(len(store.pending_emails()),2)
        previous={'date':'2026-10-14','account':{'totalEquity':995}}
        self.assertEqual(build_report(now,account,[],{},{},{},[],previous)['dailyPnl'],-5)
