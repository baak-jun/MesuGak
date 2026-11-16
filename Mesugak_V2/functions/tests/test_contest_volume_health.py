import asyncio
import json
import sys
import tempfile
import unittest
from datetime import datetime, date, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from zoneinfo import ZoneInfo
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'jobs'))
from strategy_engine.contest_momentum import MomentumConfig, MomentumWindow, momentum_entry, select_volume_watch
from strategy_engine.realtime_policy import TradeTick
from strategy_engine.contest_health import assess_contest_health
from strategy_engine.order_state import OrderStateStore
from strategy_engine.kis_realtime import KISFrameParser
from jobs.kis_realtime_trader import RealtimeSignalEngine, TraderRuntime
from contest_notifications import ContestNotifications


def rising_ticks():
    for second in range(361):
        volume=1_000_000+min(second,300)*10+max(0,second-300)*20
        price=100+max(0,second-300)/60
        yield TradeTick('A',second,price,volume,price+.1,price-.1)


class ContestVolumeHealthTests(unittest.TestCase):
    def test_six_minute_warmup_disjoint_volume_windows_and_bounded_memory(self):
        w=MomentumWindow()
        for tick in rising_ticks():
            w.add(tick)
            if tick.timestamp<360: self.assertFalse(w.snapshot()['surgeReady'])
        s=w.snapshot()
        self.assertEqual(s['surgeRecentVolume'],1200)
        self.assertEqual(s['surgeBaselineVolumePerMinute'],600)
        self.assertEqual(s['surgeVolumeRatio'],2)
        self.assertTrue(momentum_entry({**s,'spreadPct':.002},MomentumConfig()))
        self.assertFalse(momentum_entry({**s,'spreadPct':.02},MomentumConfig()))
        self.assertLessEqual(len(w.points),361)
        for _ in range(1000): w.add(tick)
        self.assertLessEqual(len(w.points),361)

    def test_quote_gap_or_volume_reset_restarts_warmup(self):
        for reset in [TradeTick('A',400,102,2_000_000),TradeTick('A',361,102,1)]:
            w=MomentumWindow()
            for tick in rising_ticks(): w.add(tick)
            w.add(reset)
            self.assertFalse(w.snapshot()['surgeReady'])

    def test_low_score_surge_enters_and_uses_faster_post_purchase_exits(self):
        engine=RealtimeSignalEngine([{'code':'A','confidenceScore':40}],momentum_config=MomentumConfig(),
             score_provider=lambda tick:{'liveScoreReady':True,'liveConfidenceScore':40})
        signals=[]
        for tick in rising_ticks(): signals.extend(engine.on_tick(tick))
        self.assertEqual(len(signals),1)
        self.assertEqual(signals[0]['reason'],'volume_surge_entry')
        engine.update_positions({'A':{'quantity':10,'buyPrice':100}})
        self.assertEqual(engine.on_tick(TradeTick('A',361,99.2))[0]['sellFraction'],.5)
        self.assertEqual(engine.on_tick(TradeTick('A',362,98.5))[0]['sellFraction'],1)
        restored=RealtimeSignalEngine([],{'A':{'quantity':5,'buyPrice':100}},momentum_config=MomentumConfig())
        restored.restore_strategy(engine.strategy_state())
        self.assertEqual(restored.entry_modes['A'],'surge')

    def test_unknown_score_and_mid_band_cannot_become_low_score_entry(self):
        for score in [None,50,57.99]:
            engine=RealtimeSignalEngine([{'code':'A','confidenceScore':0}],momentum_config=MomentumConfig(),
                score_provider=lambda tick:{'liveScoreReady':score is not None,'liveConfidenceScore':score})
            self.assertFalse([s for t in rising_ticks() for s in engine.on_tick(t)])

    def test_volume_selection_protects_holdings_and_does_not_filter_low_score(self):
        rows=[{'mksc_shrn_iscd':'A','acml_vol':'1000'},{'mksc_shrn_iscd':'B','acml_vol':'4000'},{'mksc_shrn_iscd':'X','acml_vol':'9999'}]
        self.assertEqual(select_volume_watch(rows,['H'],{'A','B'},3),['H','B','A'])
        with self.assertRaises(ValueError): select_volume_watch(rows,['H','J'],{'A'},1)

    def test_live_volume_refresh_uses_provider_and_keeps_protected_positions(self):
        with tempfile.TemporaryDirectory() as d, OrderStateStore(Path(d)/'orders.db') as store:
            p=Path(d)/'candidates.json';p.write_text(json.dumps({'market':'KR','summaries':[{'code':'A','confidenceScore':5},{'code':'B','confidenceScore':90}]}))
            args=SimpleNamespace(watch_mode='volume',market='KR',candidate_file=p,max_watch=2,execute=False,report_interval=60)
            client=SimpleNamespace(request_interval=2,volume_rank=lambda **kw:[{'mksc_shrn_iscd':'A','acml_vol':'2000'},{'mksc_shrn_iscd':'B','acml_vol':'1000'}])
            engine=RealtimeSignalEngine([],{'H':{'quantity':1,'buyPrice':100}})
            runtime=TraderRuntime(args,None,client,engine,store,None,{},date(2026,10,21))
            self.assertEqual(asyncio.run(runtime.refresh_candidates()),['H','A'])
            self.assertEqual(store.get_runtime('heartbeat')['watchRankingBasis'],'cumulative_volume')

    def test_health_distinguishes_incomplete_scan_and_stale_scoring(self):
        now=datetime(2026,10,21,10,tzinfo=ZoneInfo('Asia/Seoul'))
        scan={'runDate':'2026-10-21','status':'interrupted','successCount':1969,'totalCount':2753,'remainingCount':755,'failedCodes':[{'code':'A'}]}
        h={'sessionDate':'2026-10-21','checkedAt':now.isoformat(),'watchCodes':['A'], 'watchStartedAt':{'A':now.timestamp()-1300},'lastTicks':{'A':now.timestamp()},'scoreObservedAt':{'A':now.timestamp()-1200}}
        checks,issues=assess_contest_health(scan,h,now)
        self.assertIn('scan_incomplete',issues);self.assertNotIn('scan_failures',issues)
        self.assertIn('score_stale',issues);self.assertNotIn('heartbeat_stale',issues)
        h['checkedAt']=(now-timedelta(minutes=3)).isoformat()
        self.assertIn('heartbeat_stale',assess_contest_health(scan,h,now)[1])

    def test_health_email_dedup_and_recovery(self):
        with tempfile.TemporaryDirectory() as d, OrderStateStore(Path(d)/'orders.db') as store:
            mail=ContestNotifications(store,enabled=True)
            mail.health('scan','missing');mail.health('scan','still missing');mail.health('scan',None);mail.health('scan',None)
            self.assertEqual(len(store.pending_emails()),2)

    def test_exchange_event_timestamp_is_not_the_receive_time(self):
        tick=KISFrameParser.trade_tick({'kind':'trade','row':{'MKSC_SHRN_ISCD':'A','STCK_PRPR':'100','BSOP_DATE':'20261021','STCK_CNTG_HOUR':'100000'}})
        self.assertEqual(tick.timestamp,datetime(2026,10,21,10,tzinfo=ZoneInfo('Asia/Seoul')).timestamp())
        self.assertIsNone(KISFrameParser.trade_tick({'kind':'trade','row':{'MKSC_SHRN_ISCD':'A','STCK_PRPR':'100'}}))

    def test_stale_score_cache_does_not_become_a_fresh_entry(self):
        with tempfile.TemporaryDirectory() as d, OrderStateStore(Path(d)/'orders.db') as store:
            runtime=TraderRuntime(SimpleNamespace(),None,None,RealtimeSignalEngine([]),store,None,{},date(2026,10,21))
            runtime.async_scoring=True
            runtime.score_cache['A']={'liveScoreReady':True,'liveConfidenceScore':80,'liveScoreObservedAt':100}
            self.assertFalse(runtime.live_score(TradeTick('A',104,100))['liveScoreReady'])
            self.assertTrue(runtime.live_score(TradeTick('A',102,100))['liveScoreReady'])


if __name__=='__main__': unittest.main()
