from __future__ import annotations

import base64
import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from strategy_engine.kis_realtime import (  # noqa: E402
    KISFrameParser,
    NOTICE_COLUMNS,
    TRADE_COLUMNS,
    subscription_message,
    KISWebSocketStream,
    KISSubscriptionLimitError,
)
from jobs.kis_realtime_trader import (  # noqa: E402
    _entry_window_open,
    _virtual_holiday_feed_unavailable,
    load_live_candidates,
    TraderRuntime,
    RealtimeSignalEngine,
    run_live,
)
from strategy_engine.order_state import OrderStateStore
from strategy_engine.kis_paper import KISOrderRejectedError
from strategy_engine.realtime_policy import TradeTick


class KISRealtimeTests(unittest.TestCase):
    def test_disk_cache_load_bypasses_blocked_rest_and_survives_watch_rotation(self):
        import asyncio
        import gzip
        import threading
        from datetime import timedelta
        from strategy_engine.contest_market_data import SOURCE
        day=date(2026,10,16)
        with tempfile.TemporaryDirectory() as directory, OrderStateStore(Path(directory)/'orders.sqlite3') as store:
            rows=[{'date':(day-timedelta(days=i)).isoformat(),'open':100,'high':102,'low':98,'close':101,'volume':1000} for i in range(1,181)]
            (Path(directory)/'KR_A.json.gz').write_bytes(gzip.compress(json.dumps({'source':SOURCE,'cachedFor':day.isoformat(),'history':rows}).encode()))
            engine=RealtimeSignalEngine([{'code':'A'},{'code':'B'}],session_date=day)
            args=SimpleNamespace(history_dir=directory)
            runtime=TraderRuntime(args,None,SimpleNamespace(request_interval=8),engine,store,None,{},day)
            engine.score_provider=runtime.live_score
            started,release=threading.Event(),threading.Event()
            def backfill(*args):
                started.set()
                if not release.wait(3):
                    raise AssertionError('backfill test did not release')
                return runtime.histories['A'].copy()
            async def check():
                runtime.last_watch=['B']
                runtime.queue_histories(['B'])
                try:
                    for _ in range(100):
                        if started.is_set(): break
                        await asyncio.sleep(.005)
                    self.assertTrue(started.is_set())
                    runtime.last_watch=['A']
                    await asyncio.wait_for(runtime.load_watch_histories(['A']),timeout=1)
                    runtime.queue_histories(['A'])
                    self.assertFalse(runtime.history_tasks['B'].cancelled())
                    self.assertTrue(runtime.live_score(TradeTick('A',1,101,1000))['liveScoreReady'])
                    original=runtime.histories['A']
                    runtime.last_watch=[]
                    runtime.queue_histories([])
                    await runtime.load_watch_histories([])
                    self.assertIs(runtime.histories['A'],original)
                    with patch('jobs.kis_realtime_trader.load_cached_score_histories',side_effect=AssertionError('Memory reuse should not reread disk')):
                        await runtime.load_watch_histories(['A'])
                finally:
                    release.set()
                    await asyncio.gather(*list(runtime.history_tasks.values()))
                self.assertIn('B',runtime.histories)
                self.assertEqual(runtime.history_rest_fills,1)
            with patch('jobs.kis_realtime_trader.load_score_history',side_effect=backfill):
                asyncio.run(check())

    def test_observed_scores_keep_their_time_when_off_watch_and_restart(self):
        day=date(2026,10,16)
        engine=RealtimeSignalEngine([{'code':'A','confidenceScore':20}],session_date=day,
                                   score_provider=lambda tick:{'liveScoreReady':True,'liveConfidenceScore':54})
        engine.on_tick(TradeTick('A',12345,100))
        engine.retain_watch([])
        self.assertEqual(engine.live_scores['A'],54)
        self.assertEqual(engine.live_score_times['A'],12345)
        restarted=RealtimeSignalEngine([{'code':'A'}],session_date=day)
        restarted.restore_strategy(engine.strategy_state())
        self.assertEqual(restarted.live_scores['A'],54)
        self.assertEqual(restarted.live_score_times['A'],12345)
        self.assertEqual(restarted.on_tick(TradeTick('A',12346,100)),[])

    def test_cold_kis_history_finishes_before_random_rotation_but_scored_weak_symbols_leave(self):
        import asyncio
        with tempfile.TemporaryDirectory() as directory, OrderStateStore(Path(directory)/'orders.sqlite3') as store:
            path=Path(directory)/'candidates.json'
            rows=[{'code':str(i),'confidenceScore':0} for i in range(8)]
            path.write_text(json.dumps({'market':'KR','summaries':rows}))
            engine=RealtimeSignalEngine(rows,score_provider=lambda tick:{'liveScoreReady':False})
            args=SimpleNamespace(market='KR',max_watch=3,candidate_file=path,execute=False,report_interval=60,entry_close_time='15:15:00')
            runtime=TraderRuntime(args,SimpleNamespace(save_intraday_runtime_state=lambda payload:None),SimpleNamespace(request_interval=2),engine,store,None,{},date(2026,10,15))
            runtime.queue_histories=lambda codes:None
            first=asyncio.run(runtime.refresh_candidates())
            self.assertEqual(asyncio.run(runtime.refresh_candidates()),first)
            engine.live_scores[first[0]]=54
            second=asyncio.run(runtime.refresh_candidates())
            self.assertNotIn(first[0],second)
            self.assertTrue(set(first[1:]).issubset(second))
            self.assertEqual(len(second),3)

    def test_account_failure_recovers_without_waiting_for_periodic_maintenance(self):
        import asyncio
        with tempfile.TemporaryDirectory() as directory, OrderStateStore(Path(directory) / 'orders.sqlite3') as store:
            runtime = TraderRuntime(SimpleNamespace(entry_close_time='23:59:59'), None, SimpleNamespace(request_interval=8), RealtimeSignalEngine([]), store, None, {}, date(2026, 10, 15))
            runtime.pause_entries('account_sync_failed_pause_new_entries', 'temporary balance error')
            async def check():
                stop = asyncio.Event()
                async def sync():
                    stop.set()
                runtime.sync_account = AsyncMock(side_effect=sync)
                runtime.order_check_wakeup.set()
                await asyncio.wait_for(runtime.order_recovery_loop(stop), timeout=1)
                runtime.sync_account.assert_awaited_once()
            with patch('jobs.kis_realtime_trader.time.time', return_value=1792033200):
                asyncio.run(check())
            self.assertTrue(runtime.engine.entry_enabled)
            self.assertEqual(runtime.operational_status, 'streaming_execute')

    def test_buy_and_sell_submit_market_before_any_fallible_cloud_report(self):
        import asyncio
        for side in ['BUY', 'SELL']:
            submitted = []
            class Client:
                def submit_market_order(self, order_side, code, quantity):
                    submitted.append((order_side, code, quantity))
                    return {'output': {'ODNO': '42'}}
                def submit_limit_order(self, *args):
                    raise AssertionError('Contest orders must be market orders')
            class Repo:
                def save_intraday_trade_state(self, *args):
                    self.append_intraday_runtime_event({})
                def append_intraday_runtime_event(self, *args):
                    if not submitted:
                        raise AssertionError('Cloud reporting delayed order submission')
                    raise RuntimeError('reporting unavailable')
            with self.subTest(side=side), tempfile.TemporaryDirectory() as directory, OrderStateStore(Path(directory) / 'orders.sqlite3') as store:
                engine = RealtimeSignalEngine([], {'A': {'quantity': 3, 'buyPrice': 100}} if side == 'SELL' else {})
                runtime = TraderRuntime(SimpleNamespace(execute=True, market='KR'), Repo(), Client(), engine, store, None, {'cash': 1000, 'totalEquity': 1000}, date(2026, 10, 15))
                asyncio.run(runtime.emit_signal({'side': side, 'code': 'A', 'price': 100, 'timestamp': 1}))
                self.assertEqual(submitted[0][:2], (side, 'A'))
                self.assertEqual(store.pending()[0]['status'], 'SUBMITTED')
                self.assertEqual(store.pending()[0]['payload']['orderType'], 'MARKET')
                self.assertTrue(runtime.order_check_wakeup.is_set())

    def test_explicit_market_order_rejection_rearms_buy_and_sell_after_cooldown(self):
        import asyncio
        class Client:
            def submit_market_order(self, *args):
                raise KISOrderRejectedError('명시적 주문 거절')
        for side in ['BUY', 'SELL']:
            with self.subTest(side=side), tempfile.TemporaryDirectory() as directory, OrderStateStore(Path(directory) / 'orders.sqlite3') as store:
                engine = RealtimeSignalEngine([{'code': 'A', 'confidenceScore': 70}], {'A': {'quantity': 3, 'buyPrice': 100}} if side == 'SELL' else {})
                engine.score_provider = lambda tick: {'liveScoreReady': True, 'liveConfidenceScore': 70}
                engine.entry_codes.add('A')
                engine.exit_sent.add('A')
                args = SimpleNamespace(execute=True, market='KR', entry_close_time='23:59:59')
                runtime = TraderRuntime(args, None, Client(), engine, store, None, {'cash': 100000, 'totalEquity': 100000}, date(2026, 10, 15))
                positions = dict(engine.positions)
                with patch('jobs.kis_realtime_trader.sync_kis_account', return_value=({'cash': 100000, 'totalEquity': 100000}, positions, {})), patch('jobs.kis_realtime_trader.time.time', return_value=1792033200):
                    asyncio.run(runtime.emit_signal({'side': side, 'code': 'A', 'price': 100, 'sellFraction': 1.0, 'reason': 'monitored_high_full_exit' if side == 'SELL' else 'live_score_entry', 'timestamp': 1792033200}))
                self.assertFalse(runtime.reconciliation_required)
                self.assertTrue(engine.entry_enabled)
                self.assertFalse(store.pending())
                self.assertEqual(engine.on_tick(TradeTick('A', 1792033201, 95)), [])
                self.assertEqual(engine.on_tick(TradeTick('A', 1792033203, 95))[0]['side'], side)

    def test_normal_account_sync_blocks_signals_until_balance_is_applied(self):
        import asyncio
        engine = RealtimeSignalEngine([{'code': 'A', 'confidenceScore': 70}])
        with tempfile.TemporaryDirectory() as directory, OrderStateStore(Path(directory) / 'orders.sqlite3') as store:
            runtime = TraderRuntime(SimpleNamespace(market='KR'), None, None, engine, store, None, {}, date(2026, 10, 15))
            def balance(*args, **kwargs):
                self.assertTrue(engine.order_sync_in_progress)
                self.assertEqual(engine.on_tick(TradeTick('A', 1, 100)), [])
                return {'cash': 1000}, {}, {}
            with patch('jobs.kis_realtime_trader.sync_kis_account', side_effect=balance):
                asyncio.run(runtime.sync_account())
            self.assertFalse(engine.order_sync_in_progress)
            self.assertEqual(engine.on_tick(TradeTick('A', 2, 100))[0]['side'], 'BUY')

    def test_new_submitted_order_wakes_confirmation_worker_immediately(self):
        import asyncio
        with tempfile.TemporaryDirectory() as directory, OrderStateStore(Path(directory) / 'orders.sqlite3') as store:
            store.reserve_signal('s', session_date='2026-10-15', code='A', side='BUY', quantity=1)
            store.update('s', status='SUBMITTED', broker_order_no='42')
            runtime = TraderRuntime(SimpleNamespace(), None, SimpleNamespace(request_interval=8), RealtimeSignalEngine([]), store, None, {}, date(2026, 10, 15))
            async def check():
                stop = asyncio.Event()
                async def reconcile():
                    stop.set()
                runtime.reconcile_orders = AsyncMock(side_effect=reconcile)
                worker = asyncio.create_task(runtime.order_recovery_loop(stop))
                await asyncio.sleep(0)
                runtime.order_check_wakeup.set()
                await asyncio.wait_for(worker, timeout=1)
                runtime.reconcile_orders.assert_awaited_once()
            asyncio.run(check())

    def test_weak_core_is_replaced_randomly_and_55_explorer_fills_vacancy(self):
        import asyncio
        with tempfile.TemporaryDirectory() as directory, OrderStateStore(Path(directory) / 'orders.sqlite3') as store:
            path = Path(directory) / 'candidates.json'
            rows = [{'code': str(i), 'confidenceScore': score} for i, score in enumerate([60, 55, 54, 53, 52, 51])]
            path.write_text(json.dumps({'market': 'KR', 'summaries': rows}))
            args = SimpleNamespace(market='KR', max_watch=4, candidate_file=path, execute=False, report_interval=60, entry_close_time='15:15:00')
            engine = RealtimeSignalEngine(rows)
            engine.positions = {'5': {'quantity': 1}}
            runtime = TraderRuntime(args, SimpleNamespace(save_intraday_runtime_state=lambda payload: None), SimpleNamespace(request_interval=2.0), engine, store, None, {}, date(2026, 10, 13))
            watch = asyncio.run(runtime.refresh_candidates())
            self.assertEqual(watch[:3], ['5', '0', '1'])
            engine.live_scores.update({'0': 54.99, '1': 54.99, '2': 55})
            watch = asyncio.run(runtime.refresh_candidates())
            self.assertEqual(watch[:2], ['5', '2'])
            self.assertNotIn('0', watch)
            self.assertNotIn('1', watch)
            self.assertEqual(len(watch), 4)
            self.assertEqual(len(runtime.exploration_codes), 2)

    def test_higher_explorer_replaces_lower_core_without_old_daily_score_reentry(self):
        import asyncio
        from strategy_engine.realtime_policy import select_watch_codes
        with tempfile.TemporaryDirectory() as directory, OrderStateStore(Path(directory) / 'orders.sqlite3') as store:
            path = Path(directory) / 'candidates.json'
            rows = [{'code': '000001', 'confidenceScore': 80}, {'code': '000002', 'confidenceScore': 70},
                    {'code': '000003', 'confidenceScore': 50}, {'code': '000004', 'confidenceScore': 40}]
            path.write_text(json.dumps({'market': 'KR', 'summaries': rows}))
            args = SimpleNamespace(market='KR', max_watch=3, candidate_file=path, execute=False, report_interval=60, entry_close_time='15:15:00')
            engine = RealtimeSignalEngine(rows, session_date=date(2026, 10, 12))
            runtime = TraderRuntime(args, SimpleNamespace(save_intraday_runtime_state=lambda payload: None), SimpleNamespace(request_interval=2.0), engine, store, None, {}, date(2026, 10, 12))
            self.assertEqual(asyncio.run(runtime.refresh_candidates())[:2], ['000001', '000002'])
            engine.score_provider = lambda tick: {'liveScoreReady': True, 'liveConfidenceScore': 10 if tick.code == '000001' else 90}
            engine.entry_enabled = False
            engine.on_tick(TradeTick('000001', 1, 100))
            engine.on_tick(TradeTick('000004', 2, 100))
            engine.score_provider = None  # This test needs no history API.
            self.assertEqual(asyncio.run(runtime.refresh_candidates())[:2], ['000004', '000002'])
            engine.retain_watch(['000004', '000002', '000003'])
            self.assertNotIn('000001', engine.latest)
            self.assertEqual(asyncio.run(runtime.refresh_candidates())[:2], ['000004', '000002'])
            restarted = RealtimeSignalEngine(rows, session_date=date(2026, 10, 12))
            restarted.restore_strategy(engine.strategy_state())
            self.assertEqual(select_watch_codes(restarted.ranked_candidates(), [], max_codes=2, exploration_count=0), ['000004', '000002'])

    def test_previous_session_live_rankings_are_not_used_as_todays_scores(self):
        engine = RealtimeSignalEngine([{'code': 'A', 'confidenceScore': 80}], session_date=date(2026, 10, 13))
        engine.restore_strategy({'sessionDate': '2026-10-12', 'liveScores': {'A': 10}})
        self.assertEqual(engine.ranked_candidates()[0]['confidenceScore'], 80)
    def test_untradable_rejection_excludes_only_that_symbol_and_sends_stop_resume(self):
        import asyncio
        with tempfile.TemporaryDirectory() as directory, OrderStateStore(Path(directory) / 'orders.sqlite3') as store:
            class Client:
                def submit_market_order(self, *args):
                    raise RuntimeError('모의투자 주문처리가 안되었습니다(매매불가 종목)')
            args = SimpleNamespace(execute=True, market='KR', initial_cash=100000, entry_close_time='23:59:59')
            engine = RealtimeSignalEngine([{'code': '36328K', 'name': '매매불가종목'}])
            runtime = TraderRuntime(args, None, Client(), engine, store, None, {'cash': 100000, 'totalEquity': 100000}, date(2026, 10, 12))
            runtime.notifications.enabled = True
            with patch('jobs.kis_realtime_trader.sync_kis_account', return_value=({'cash': 100000, 'totalEquity': 100000}, {}, {})), patch('jobs.kis_realtime_trader.time.time', return_value=1791776000):
                asyncio.run(runtime.emit_signal({'side': 'BUY', 'code': '36328K', 'price': 1000, 'timestamp': 1, 'reason': 'live_score_entry'}))
            self.assertTrue(engine.entry_enabled)
            self.assertFalse(runtime.reconciliation_required)
            self.assertIn('36328K', engine.blocked_codes)
            self.assertEqual(store.get_runtime('broker_exclusions')['codes'], ['36328K'])
            self.assertEqual(len(store.pending_emails()), 2)

    def test_ambiguous_network_order_stays_paused_and_does_not_send_a_resume(self):
        import asyncio
        with tempfile.TemporaryDirectory() as directory, OrderStateStore(Path(directory) / 'orders.sqlite3') as store:
            class Client:
                def submit_market_order(self, *args):
                    raise RuntimeError('KIS network error: timeout')
            runtime = TraderRuntime(SimpleNamespace(execute=True, market='KR'), None, Client(), RealtimeSignalEngine([]), store, None, {'cash': 100000, 'totalEquity': 100000}, date(2026, 10, 12))
            runtime.notifications.enabled = True
            asyncio.run(runtime.emit_signal({'side': 'BUY', 'code': 'A', 'price': 1000, 'timestamp': 1}))
            self.assertEqual(store.pending()[0]['status'], 'UNKNOWN')
            self.assertTrue(runtime.reconciliation_required)
            self.assertFalse(runtime.engine.entry_enabled)
            self.assertEqual(len(store.pending_emails()), 1)

    def test_filled_trade_enqueues_one_mail_in_same_ledger_commit(self):
        with tempfile.TemporaryDirectory() as directory, OrderStateStore(Path(directory) / 'orders.sqlite3') as store:
            store.reserve_signal('buy', session_date='2026-10-12', code='A', side='BUY', quantity=2)
            store.update('buy', status='SUBMITTED', broker_order_no='42')
            runtime = TraderRuntime(SimpleNamespace(), None, None, RealtimeSignalEngine([{'code': 'A', 'name': '종목A'}]), store, None, {'cash': 10000}, date(2026, 10, 12))
            runtime.notifications.enabled = True
            fill = {'brokerOrderNo': '42', 'code': 'A', 'quantity': 2, 'price': 1000, 'filled': True, 'noticeTime': '090001'}
            runtime.handle_fill(fill)
            runtime.handle_fill(fill)
            self.assertEqual(store.get('buy')['status'], 'FILLED')
            self.assertEqual(len(store.pending_emails()), 1)
            self.assertIn('이번 체결 금액: 2,000원', store.pending_emails()[0]['body'])

    def test_first_qualified_tick_buys_and_monitoring_high_drives_staged_exits(self):
        row = {'code': 'A', 'confidenceScore': 10, 'status': 'HOLD'}
        engine = RealtimeSignalEngine([row], score_provider=lambda tick: {'liveScoreReady': True, 'liveConfidenceScore': 60.01})
        buy = engine.on_tick(TradeTick('A', 1, 100))
        self.assertEqual([signal['side'] for signal in buy], ['BUY'])
        engine.update_positions({'A': {'quantity': 10, 'buyPrice': 100}})
        half = engine.on_tick(TradeTick('A', 1.01, 98.2))
        self.assertEqual(half[0]['sellFraction'], .5)
        engine.positions['A']['quantity'] = 5
        self.assertEqual(engine.on_tick(TradeTick('A', 1.02, 98.1)), [])
        full = engine.on_tick(TradeTick('A', 1.03, 97))
        self.assertEqual(full[0]['sellFraction'], 1.0)
        self.assertEqual(engine.on_tick(TradeTick('A', 1.04, 96)), [])
        engine.retain_watch([])
        self.assertIn('A', engine.windows)
        self.assertEqual(engine.watch_highs['A'], 100)

    def test_account_sync_and_restart_keep_high_water_mark_and_partial_stage(self):
        engine = RealtimeSignalEngine([], {'A': {'quantity': 10, 'buyPrice': 90}}, session_date=date(2026, 10, 12))
        engine.on_tick(TradeTick('A', 1, 100))
        engine.on_tick(TradeTick('A', 2, 98.2))
        engine.update_positions({'A': {'quantity': 5, 'buyPrice': 90, 'highestPrice': 98.2}})
        self.assertEqual(engine.positions['A']['highestPrice'], 100)
        restarted = RealtimeSignalEngine([], {'A': {'quantity': 5, 'buyPrice': 90}}, session_date=date(2026, 10, 12))
        restarted.restore_strategy(engine.strategy_state())
        self.assertEqual(restarted.on_tick(TradeTick('A', 3, 98)), [])
        self.assertEqual(restarted.on_tick(TradeTick('A', 4, 97))[0]['sellFraction'], 1)

    def test_buy_fill_starts_high_and_partial_fills_keep_only_post_buy_high(self):
        with tempfile.TemporaryDirectory() as directory, OrderStateStore(Path(directory) / 'orders.sqlite3') as store:
            engine = RealtimeSignalEngine([{'code': 'A', 'confidenceScore': 10}])
            engine.entry_enabled = False
            engine.on_tick(TradeTick('A', 1, 200))
            self.assertNotIn('A', engine.watch_highs)
            # Ignore old pre-purchase state left by a previous software version.
            engine.restore_strategy({'sessionDate': engine.session_date.isoformat(), 'watchHighs': {'A': 200}})
            self.assertNotIn('A', engine.watch_highs)
            runtime = TraderRuntime(SimpleNamespace(), None, None, engine, store, None, {'cash': 10000}, engine.session_date)
            store.reserve_signal('buy', session_date=engine.session_date.isoformat(), code='A', side='BUY', quantity=10)
            store.update('buy', status='SUBMITTED', broker_order_no='42')
            fill = {'brokerOrderNo': '42', 'code': 'A', 'quantity': 5, 'price': 100, 'filled': True, 'noticeTime': '090002'}
            runtime.handle_fill(fill)
            self.assertEqual(engine.watch_highs['A'], 100)
            self.assertEqual(engine.on_tick(TradeTick('A', 3, 99)), [])
            engine.on_tick(TradeTick('A', 4, 105))
            runtime.handle_fill({**fill, 'price': 101, 'noticeTime': '090005'})
            self.assertEqual(engine.watch_highs['A'], 105)
            self.assertEqual(engine.on_tick(TradeTick('A', 6, 105 * .982))[0]['sellFraction'], .5)
            store.reserve_signal('sell', session_date=engine.session_date.isoformat(), code='A', side='SELL', quantity=10)
            store.update('sell', status='SUBMITTED', broker_order_no='43')
            runtime.handle_fill({**fill, 'brokerOrderNo': '43', 'quantity': 10, 'price': 103, 'noticeTime': '090007'})
            self.assertNotIn('A', engine.watch_highs)
            store.reserve_signal('rebuy', session_date=engine.session_date.isoformat(), code='A', side='BUY', quantity=1)
            store.update('rebuy', status='SUBMITTED', broker_order_no='44')
            runtime.handle_fill({**fill, 'brokerOrderNo': '44', 'quantity': 1, 'price': 90, 'noticeTime': '090008'})
            self.assertEqual(engine.watch_highs['A'], 90)
            self.assertNotIn('A', engine.partial_exit_sent)

    def test_post_buy_high_and_partial_stage_survive_next_day_restart(self):
        engine = RealtimeSignalEngine([], {'A': {'quantity': 10, 'buyPrice': 90}}, session_date=date(2026, 10, 12))
        engine.on_tick(TradeTick('A', 1, 100))
        engine.on_tick(TradeTick('A', 2, 98.2))
        restarted = RealtimeSignalEngine([], {'A': {'quantity': 5, 'buyPrice': 90}}, session_date=date(2026, 10, 13))
        restarted.restore_strategy(engine.strategy_state())
        self.assertEqual(restarted.on_tick(TradeTick('A', 3, 98)), [])
        self.assertEqual(restarted.on_tick(TradeTick('A', 4, 97))[0]['sellFraction'], 1)

    def test_full_exit_deducts_a_pending_partial_sale_instead_of_overselling(self):
        import asyncio
        with tempfile.TemporaryDirectory() as directory, OrderStateStore(Path(directory) / 'orders.sqlite3') as store:
            store.reserve_signal('half', session_date='2026-10-12', code='A', side='SELL', quantity=5)
            store.update('half', status='SUBMITTED', broker_order_no='42')
            client = SimpleNamespace(submit_market_order=lambda side, code, quantity: {'output': {'ODNO': '43'}})
            engine = RealtimeSignalEngine([], {'A': {'quantity': 10, 'buyPrice': 90}})
            runtime = TraderRuntime(SimpleNamespace(execute=True, market='KR'), None, client, engine, store, None, {}, date(2026, 10, 12))
            asyncio.run(runtime.emit_signal({'side': 'SELL', 'code': 'A', 'sellFraction': 1.0, 'reason': 'monitored_high_full_exit', 'timestamp': 1}))
            full = store.by_broker_order('43')
            self.assertEqual(full['quantity'], 5)
            self.assertEqual(full['status'], 'SUBMITTED')

    def test_fill_before_order_response_is_deferred_and_buy_sell_interleaving_preserves_quantity(self):
        with tempfile.TemporaryDirectory() as directory, OrderStateStore(Path(directory) / 'orders.sqlite3') as store:
            store.reserve_signal('buy', session_date='2026-10-12', code='A', side='BUY', quantity=10)
            engine = RealtimeSignalEngine([])
            runtime = TraderRuntime(SimpleNamespace(), None, None, engine, store, None, {'cash': 10000}, date(2026, 10, 12))
            fill = {'brokerOrderNo': '42', 'code': 'A', 'quantity': 4, 'price': 100, 'filled': True, 'noticeTime': '090001'}
            runtime.handle_fill(fill)
            self.assertEqual(len(runtime.deferred_fills), 1)
            self.assertFalse(runtime.reconciliation_required)
            store.update('buy', status='SUBMITTED', broker_order_no='42')
            runtime.handle_fill(runtime.deferred_fills.popleft())
            store.reserve_signal('sell', session_date='2026-10-12', code='A', side='SELL', quantity=2)
            store.update('sell', status='SUBMITTED', broker_order_no='43')
            runtime.handle_fill({**fill, 'brokerOrderNo': '43', 'quantity': 2, 'noticeTime': '090002'})
            runtime.handle_fill({**fill, 'quantity': 6, 'noticeTime': '090003'})
            self.assertEqual(engine.positions['A']['quantity'], 8)

    def test_entry_window_is_closed_at_and_after_cutoff(self) -> None:
        self.assertTrue(_entry_window_open(100.0, 101.0))
        self.assertFalse(_entry_window_open(101.0, 101.0))
        self.assertFalse(_entry_window_open(102.0, 101.0))

    def test_virtual_holiday_feed_rejection_is_narrowly_recognized(self) -> None:
        class Config:
            base_url = "https://openapivts.koreainvestment.com:29443"

        class Client:
            config = Config()

        self.assertTrue(_virtual_holiday_feed_unavailable(Client(), RuntimeError("EGW02006")))
        self.assertFalse(_virtual_holiday_feed_unavailable(Client(), RuntimeError("timeout")))

    def test_subscription_message_has_paper_header_and_type(self) -> None:
        message = json.loads(subscription_message("approval", "H0STCNT0", "005930", tr_type="2"))
        self.assertEqual(message["header"]["custtype"], "P")
        self.assertEqual(message["header"]["tr_type"], "2")
        self.assertEqual(message["body"]["input"]["tr_key"], "005930")

    def test_parser_maps_trade_and_fill_frames(self) -> None:
        parser = KISFrameParser()
        parser.register("H0STCNT0", "005930")
        values = ["005930", "090000", "1000", "", "", "", "", "", "", "", "1001", "999", "10", "100", "100000", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""]
        message = parser.parse("0|H0STCNT0|001|" + "^".join(values[:len(TRADE_COLUMNS)]))
        tick = parser.trade_tick(message, timestamp=123.0)
        self.assertEqual(tick.code, "005930")
        self.assertEqual(tick.price, 1000)
        self.assertEqual(tick.cumulative_volume, 100)
        self.assertEqual(message["row"][TRADE_COLUMNS[0]], "005930")

        parser.register("H0STCNI9", "HTS")
        notice_values = ["", "", "0001", "", "", "", "", "", "005930", "2", "1000", "090001", "0", "2", "1", "", "2", "", "", "", "", "", "", "", "", ""]
        notice = parser.parse("0|H0STCNI9|001|" + "^".join(notice_values))
        fill = parser.fill_notice(notice)
        self.assertTrue(fill["filled"])
        self.assertEqual(fill["brokerOrderNo"], "0001")
        self.assertEqual(notice["row"][NOTICE_COLUMNS[8]], "005930")

    def test_parser_decrypts_encrypted_payload_with_declared_key_and_iv(self) -> None:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

        parser = KISFrameParser()
        parser.register("H0STCNT0", "005930")
        key, iv = b"1234567890123456", b"abcdefghijklmnop"
        system = {
            "header": {"tr_id": "H0STCNT0", "tr_key": "005930", "encrypt": "Y"},
            "body": {"rt_cd": "0", "output": {"key": key.decode(), "iv": iv.decode()}},
        }
        parser.parse(json.dumps(system))
        plain = "^".join(["005930", "090000", "1000"] + [""] * (len(TRADE_COLUMNS) - 3)).encode()
        padding = 16 - len(plain) % 16
        encryptor = Cipher(algorithms.AES(key), modes.CBC(iv)).encryptor()
        encrypted = encryptor.update(plain + bytes([padding]) * padding) + encryptor.finalize()
        message = parser.parse("1|H0STCNT0|001|" + base64.b64encode(encrypted).decode())
        self.assertEqual(message["row"]["MKSC_SHRN_ISCD"], "005930")

    def test_real_count_header_dispatches_every_record_and_ignores_unsubscribed_codes(self):
        parser = KISFrameParser()
        parser.register("H0STCNT0", "005930")
        parser.register("H0STCNT0", "000660")
        values = []
        for code in ["005930", "000660"]:
            values.extend([code, "090000", "1000"] + [""] * (len(TRADE_COLUMNS) - 3))
        message = parser.parse("0|H0STCNT0|002|" + "^".join(values))
        self.assertEqual([parser.trade_tick(row).code for row in message['messages']], ["005930", "000660"])
        self.assertIsNone(parser.parse("0|H0STCNT0|002|005930^090000^1000"))
        self.assertIsNone(parser.parse("0|H0STCNT0|005930|" + "^".join(values)))

    def test_complete_local_universe_is_used_without_firestone_reads(self):
        class Repo:
            def fetch_meta_candidates(self, market):
                raise AssertionError("The complete local snapshot should avoid capped cloud reads")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'candidates.json'
            rows = [{'code': str(i), 'confidenceScore': i} for i in range(250)]
            path.write_text(json.dumps({'market': 'KR', 'runDate': '2026-10-12', 'summaries': rows}))
            candidates, metadata = load_live_candidates(path, 'KR', Repo())
            self.assertEqual(len(candidates), 250)
            self.assertEqual(metadata['candidateSource'], 'server_full_universe')

    def test_random_slots_visit_the_remaining_universe_without_repeating_a_cycle(self):
        class Repo:
            def save_intraday_runtime_state(self, payload):
                pass
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'candidates.json'
            rows = [{'code': str(i), 'confidenceScore': 100 - i} for i in range(40)]
            path.write_text(json.dumps({'market': 'KR', 'summaries': rows}))
            args = SimpleNamespace(market='KR', max_watch=20, candidate_file=path, execute=False, report_interval=60, entry_close_time='15:15:00')
            with OrderStateStore(Path(directory) / 'orders.sqlite3') as store:
                runtime = TraderRuntime(args, Repo(), SimpleNamespace(request_interval=1.0), RealtimeSignalEngine(rows), store, None, {}, date(2026, 10, 12))
                seen = []
                import asyncio
                for _ in range(11):
                    watch = asyncio.run(runtime.refresh_candidates())
                    self.assertEqual(watch[:18], [str(i) for i in range(18)])
                    self.assertEqual(len(set(watch)), 20)
                    seen.extend(runtime.exploration_codes)
                self.assertEqual(set(seen), {str(i) for i in range(18, 40)})
                self.assertEqual(len(seen), len(set(seen)))
                runtime.reconciliation_required = True
                runtime.engine.entry_enabled = False
                runtime.operational_status = 'stream_error_pause_new_entries'
                asyncio.run(runtime.refresh_candidates())
                self.assertFalse(runtime.engine.entry_enabled)
                self.assertTrue(store.get_runtime('heartbeat')['reconciliationRequired'])

    def test_partial_fills_accumulate_and_duplicate_notices_do_not_double_count(self):
        class Repo:
            def append_intraday_runtime_event(self, payload):
                pass
        with tempfile.TemporaryDirectory() as directory, OrderStateStore(Path(directory) / 'orders.sqlite3') as store:
            store.reserve_signal('s1', session_date='2026-10-12', code='005930', side='BUY', quantity=3)
            store.update('s1', status='SUBMITTED', broker_order_no='42')
            runtime = TraderRuntime(SimpleNamespace(), Repo(), None, RealtimeSignalEngine([]), store, None, {}, date(2026, 10, 12))
            fill = {'brokerOrderNo': '42', 'code': '005930', 'quantity': 1, 'price': 1000, 'filled': True, 'noticeTime': '090001'}
            runtime.handle_fill(fill)
            runtime.handle_fill(fill)
            self.assertEqual(store.get('s1')['status'], 'PARTIALLY_FILLED')
            self.assertEqual(store.get('s1')['filled_quantity'], 1)
            runtime.handle_fill({**fill, 'quantity': 2, 'price': 1100, 'noticeTime': '090002'})
            self.assertEqual(store.get('s1')['status'], 'FILLED')
            self.assertEqual(runtime.engine.positions['005930']['quantity'], 3)
            self.assertAlmostEqual(store.get('s1')['average_fill_price'], 3200 / 3)

    def test_restart_reserves_a_symbol_with_an_existing_unfilled_buy(self):
        class Client:
            def inquire_daily_orders(self, **kwargs):
                return [{'odno': '42', 'tot_ccld_qty': '0'}]
        import asyncio
        with tempfile.TemporaryDirectory() as directory, OrderStateStore(Path(directory) / 'orders.sqlite3') as store:
            store.reserve_signal('s1', session_date='2026-10-12', code='005930', side='BUY', quantity=3)
            store.update('s1', status='SUBMITTED', broker_order_no='42')
            runtime = TraderRuntime(SimpleNamespace(), None, Client(), RealtimeSignalEngine([]), store, None, {}, date(2026, 10, 12))
            runtime.args.market = 'KR'
            with patch('jobs.kis_realtime_trader.sync_kis_account', return_value=({}, {}, {})):
                asyncio.run(runtime.reconcile_startup())
            self.assertIn('005930', runtime.engine.entry_codes)

    def test_prior_day_fills_recover_without_replaying_balance_and_allow_remaining_exit(self):
        import asyncio
        days = []
        class Client:
            def inquire_daily_orders(self, *, order_date, **kwargs):
                days.append(order_date)
                if order_date == date(2026, 10, 14):
                    return [{'odno': '42', 'pdno': 'A', 'tot_ccld_qty': '33', 'tot_ccld_amt': '3300', 'prdt_name': 'A'},
                            {'odno': '43', 'pdno': 'A', 'tot_ccld_qty': '16', 'tot_ccld_amt': '1584'}]
                return [{'odno': '42', 'pdno': 'A', 'tot_ccld_qty': '1', 'tot_ccld_amt': '95'}]
        with tempfile.TemporaryDirectory() as directory, OrderStateStore(Path(directory) / 'orders.sqlite3') as store:
            for sid, day, side, qty, no in [('buy', '2026-10-14', 'BUY', 33, '42'), ('half', '2026-10-14', 'SELL', 16, '43'), ('full', '2026-10-15', 'SELL', 1, '42')]:
                store.reserve_signal(sid, session_date=day, code='A', side=side, quantity=qty)
                store.update(sid, status='UNKNOWN', broker_order_no=no)
            engine = RealtimeSignalEngine([], {'A': {'quantity': 17, 'buyPrice': 100, 'highestPrice': 100}})
            engine.exit_sent.add('A')
            engine.partial_exit_sent.add('A')
            runtime = TraderRuntime(SimpleNamespace(market='KR', execute=False, report_interval=60, entry_close_time='23:59:59', max_watch=39), None, Client(), engine, store, None, {}, date(2026, 10, 15))
            runtime.reconciliation_required = True
            runtime.operational_status = 'startup_order_reconcile_required'
            runtime.notifications.enabled = True
            with patch('jobs.kis_realtime_trader.sync_kis_account', return_value=({'cash': 10000}, {'A': {'quantity': 16, 'buyPrice': 100, 'highestPrice': 100}}, {})), patch('jobs.kis_realtime_trader.time.time', return_value=1792033200):
                asyncio.run(runtime.reconcile_startup())
                asyncio.run(runtime.reconcile_orders())
            self.assertEqual(days, [date(2026, 10, 14), date(2026, 10, 15)])
            self.assertFalse(store.pending())
            self.assertEqual(engine.positions['A']['quantity'], 16)
            self.assertFalse(runtime.reconciliation_required)
            self.assertTrue(engine.entry_enabled)
            self.assertEqual(len([r for r in store.pending_emails() if r['event_key'].startswith('fill:')]), 3)
            self.assertEqual(engine.on_tick(TradeTick('A', 1, 95))[0]['sellFraction'], 1)
            runtime.handle_fill({'brokerOrderNo': '43', 'code': 'A', 'quantity': 16, 'price': 99, 'filled': True, 'noticeTime': '145530'})
            self.assertEqual(engine.positions['A']['quantity'], 16)

    def test_rest_partial_fill_polling_only_notifies_new_quantity_and_ignores_late_notice(self):
        import asyncio
        quantities = iter([2, 3])
        class Client:
            def inquire_daily_orders(self, **kwargs):
                qty = next(quantities)
                return [{'odno': '42', 'pdno': 'A', 'tot_ccld_qty': str(qty), 'tot_ccld_amt': str(qty * 100)}]
        with tempfile.TemporaryDirectory() as directory, OrderStateStore(Path(directory) / 'orders.sqlite3') as store:
            store.reserve_signal('buy', session_date='2026-10-15', code='A', side='BUY', quantity=3)
            store.update('buy', status='SUBMITTED', broker_order_no='42')
            engine = RealtimeSignalEngine([])
            runtime = TraderRuntime(SimpleNamespace(market='KR', execute=False, report_interval=60, max_watch=39), None, Client(), engine, store, None, {}, date(2026, 10, 15))
            runtime.notifications.enabled = True
            with patch('jobs.kis_realtime_trader.sync_kis_account', side_effect=[({}, {'A': {'quantity': 2, 'buyPrice': 100}}, {}), ({}, {'A': {'quantity': 3, 'buyPrice': 100}}, {})]):
                asyncio.run(runtime.reconcile_orders())
                runtime.handle_fill({'brokerOrderNo': '42', 'code': 'A', 'quantity': 1, 'price': 100, 'filled': True})
                self.assertEqual(engine.positions['A']['quantity'], 2)
                asyncio.run(runtime.reconcile_orders())
            self.assertEqual(engine.positions['A']['quantity'], 3)
            self.assertEqual(store.get('buy')['filled_quantity'], 3)
            self.assertEqual(len(store.pending_emails()), 2)
            self.assertFalse(store.pending())

    def test_missing_broker_order_stays_paused_and_is_not_resubmitted(self):
        import asyncio
        class Client:
            def inquire_daily_orders(self, **kwargs):
                return []
        with tempfile.TemporaryDirectory() as directory, OrderStateStore(Path(directory) / 'orders.sqlite3') as store:
            store.reserve_signal('buy', session_date='2026-10-14', code='A', side='BUY', quantity=3)
            store.update('buy', status='SUBMITTED', broker_order_no='42')
            runtime = TraderRuntime(SimpleNamespace(market='KR', execute=False, report_interval=60, max_watch=39), None, Client(), RealtimeSignalEngine([]), store, None, {}, date(2026, 10, 15))
            with patch('jobs.kis_realtime_trader.sync_kis_account', return_value=({}, {}, {})):
                asyncio.run(runtime.reconcile_orders())
            self.assertTrue(runtime.reconciliation_required)
            self.assertFalse(runtime.engine.entry_enabled)
            self.assertEqual(store.get('buy')['status'], 'UNKNOWN')
            self.assertEqual(len(store.pending()), 1)

    def test_notice_arriving_during_rest_balance_sync_does_not_double_holdings(self):
        import asyncio
        class Client:
            def inquire_daily_orders(self, **kwargs):
                runtime.handle_fill({'brokerOrderNo': '42', 'code': 'A', 'quantity': 3, 'price': 100, 'filled': True})
                return [{'odno': '42', 'tot_ccld_qty': '0'}]
        with tempfile.TemporaryDirectory() as directory, OrderStateStore(Path(directory) / 'orders.sqlite3') as store:
            store.reserve_signal('buy', session_date='2026-10-15', code='A', side='BUY', quantity=3)
            store.update('buy', status='SUBMITTED', broker_order_no='42')
            runtime = TraderRuntime(SimpleNamespace(market='KR'), None, Client(), RealtimeSignalEngine([]), store, None, {}, date(2026, 10, 15))
            with patch('jobs.kis_realtime_trader.sync_kis_account', return_value=({}, {'A': {'quantity': 3, 'buyPrice': 100}}, {})):
                asyncio.run(runtime.reconcile_orders())
            self.assertEqual(runtime.engine.positions['A']['quantity'], 3)
            self.assertEqual(store.get('buy')['filled_quantity'], 0)
            self.assertEqual(len(store.pending()), 1)

    def test_expanded_universe_enters_the_random_pool_immediately(self):
        import asyncio
        with tempfile.TemporaryDirectory() as directory, OrderStateStore(Path(directory) / 'orders.sqlite3') as store:
            path = Path(directory) / 'candidates.json'
            rows = [{'code': str(i), 'confidenceScore': 100 - i} for i in range(40)]
            path.write_text(json.dumps({'market': 'KR', 'summaries': rows}))
            args = SimpleNamespace(market='KR', max_watch=20, candidate_file=path, execute=False, report_interval=60, entry_close_time='15:15:00')
            repo = SimpleNamespace(save_intraday_runtime_state=lambda payload: None)
            runtime = TraderRuntime(args, repo, SimpleNamespace(request_interval=2.0), RealtimeSignalEngine(rows), store, None, {}, date(2026, 10, 12))
            asyncio.run(runtime.refresh_candidates())
            self.assertTrue(runtime.exploration_queue)
            rows.extend({'code': str(i), 'confidenceScore': 100 - i} for i in range(40, 100))
            path.write_text(json.dumps({'market': 'KR', 'summaries': rows}))
            with patch('jobs.kis_realtime_trader.random.shuffle', side_effect=lambda codes: codes.sort(key=int, reverse=True)):
                asyncio.run(runtime.refresh_candidates())
            self.assertEqual(runtime.exploration_codes, ['99', '98'])


class WebSocketTests(unittest.IsolatedAsyncioTestCase):
    async def test_after_close_restart_preserves_state_without_broker_or_firestore_calls(self):
        with patch('jobs.kis_realtime_trader.init_firestore', side_effect=AssertionError('No new session after close')):
            result = await run_live(SimpleNamespace(end_time='00:00:00', market='KR'))
        self.assertEqual(result['status'], 'session_closed')

    async def test_pingpong_is_echoed_and_all_trade_records_reach_the_engine(self):
        class Client:
            config = SimpleNamespace(hts_id='HTS')
            def websocket_approval_key(self):
                return 'approval'
            def websocket_url(self):
                return 'ws://example.invalid'
        class Socket:
            def __init__(self, messages):
                self.messages = messages
                self.sent = []
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                pass
            async def send(self, message):
                self.sent.append(message)
            def __aiter__(self):
                async def messages():
                    for message in self.messages:
                        yield message
                return messages()
        ping = json.dumps({'header': {'tr_id': 'PINGPONG'}})
        values = []
        for code in ['005930', '000660']:
            values.extend([code, '090000', '1000'] + [''] * (len(TRADE_COLUMNS) - 3))
        socket = Socket([ping, '0|H0STCNT0|002|' + '^'.join(values)])
        callback = AsyncMock()
        with patch('websockets.connect', return_value=socket), patch('strategy_engine.kis_realtime.asyncio.sleep', new=AsyncMock()):
            await KISWebSocketStream(Client(), ['005930', '000660']).run(callback)
        self.assertEqual(callback.await_count, 2)
        self.assertIn(ping, socket.sent)
        socket = Socket([json.dumps({'header': {'tr_id': 'H0STCNT0', 'tr_key': '005930'}, 'body': {'rt_cd': '1', 'msg1': 'MAX SUBSCRIPTION LIMIT'}})])
        with patch('websockets.connect', return_value=socket), patch('strategy_engine.kis_realtime.asyncio.sleep', new=AsyncMock()):
            with self.assertRaises(KISSubscriptionLimitError):
                await KISWebSocketStream(Client(), ['005930']).run(callback)


if __name__ == "__main__":
    unittest.main()
