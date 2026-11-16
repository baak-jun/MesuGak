import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from strategy_engine.contest_repository import ContestRepository, require_isolated_dry_run
from strategy_engine.order_state import OrderStateStore


class ContestRepositoryTests(unittest.TestCase):
    def test_dry_run_cannot_touch_live_order_ledger(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'orders.db'
            require_isolated_dry_run(path)
            with OrderStateStore(path) as store:
                require_isolated_dry_run(path)
                store.connection.execute("INSERT INTO orders(signal_id,session_date,code,side,quantity,status,created_at,updated_at) VALUES ('a','2026-10-29','A','BUY',1,'FILLED','now','now')")
                store.connection.commit()
                with self.assertRaises(RuntimeError):require_isolated_dry_run(path)
                self.assertEqual(store.connection.execute('SELECT count(*) FROM orders').fetchone()[0],1)

    def test_restart_preserves_same_day_entry_blocks_and_post_buy_highs(self):
        from datetime import date
        sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'jobs'))
        from kis_realtime_trader import RealtimeSignalEngine
        day=date(2026,10,29)
        engine=RealtimeSignalEngine([],{'A':{'quantity':2,'buyPrice':100}},session_date=day,blocked_codes=['B'])
        engine.watch_highs['A']=125
        engine.partial_exit_sent.add('A')
        saved=engine.strategy_state()
        restored=RealtimeSignalEngine([],{'A':{'quantity':2,'buyPrice':100}},session_date=day)
        restored.restore_strategy(saved)
        self.assertEqual(restored.watch_highs['A'],125)
        self.assertIn('A',restored.partial_exit_sent)
        self.assertIn('B',restored.blocked_codes)
        tomorrow=RealtimeSignalEngine([],{},session_date=date(2026,10,30))
        tomorrow.restore_strategy(saved)
        self.assertNotIn('B',tomorrow.blocked_codes)

    def test_cloud_outage_cannot_break_local_account_state_or_restart(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'orders.db'
            cloud=Mock(side_effect=OSError('offline'))
            repo=ContestRepository(path,cloud)
            repo.save_paper_positions({'A':{'quantity':5,'highestPrice':120},'B':{'quantity':3}})
            repo.save_paper_positions({'A':{'quantity':2,'highestPrice':120}},previous_codes={'A'})
            repo.save_account_snapshot({'cash':123})
            repo.save_intraday_trade_state('KR','2026-10-29',{'blockedEntryCodes':['C']})
            repo.append_intraday_runtime_event({'type':'filled'})
            cloud.assert_not_called()
            repo.save_intraday_runtime_state({'sessionDate':'2026-10-29'})
            repo.publisher.join(timeout=5)
            self.assertFalse(repo.publisher.is_alive())
            restored=ContestRepository(path)
            self.assertEqual(restored.fetch_current_positions()['A']['quantity'],2)
            self.assertIn('B',restored.fetch_current_positions())
            self.assertEqual(restored.fetch_account_snapshot()['cash'],123)
            self.assertEqual(restored.fetch_intraday_trade_state('KR','2026-10-29')['blockedEntryCodes'],['C'])
            self.assertEqual(restored._read('cloud_status')['status'],'unavailable')
            repo.save_paper_positions({},previous_codes={'A'})
            self.assertNotIn('A',restored.fetch_current_positions())

    def test_cloud_is_bounded_and_cannot_read_account_back_into_trading(self):
        with tempfile.TemporaryDirectory() as d:
            cloud=Mock();repo=ContestRepository(Path(d)/'orders.db',lambda:cloud)
            repo.save_paper_positions({'A':{'quantity':2}})
            repo.save_intraday_runtime_state({'status':'ok'})
            repo.publisher.join(timeout=5)
            cloud.fetch_current_positions.assert_not_called()
            cloud.fetch_account_snapshot.assert_not_called()
            self.assertEqual(repo._read('cloud_status')['status'],'ok')
            for call in cloud._paper_collection.return_value.document.return_value.set.call_args_list:
                self.assertEqual(call.kwargs,{'timeout':5,'retry':None})

    def test_full_balance_replaces_closed_positions_and_keeps_other_updates(self):
        with tempfile.TemporaryDirectory() as d:
            repo=ContestRepository(Path(d)/'orders.db')
            repo.save_paper_positions({'A':{'quantity':1},'B':{'quantity':2}})
            repo.save_paper_positions({'B':{'quantity':3}},previous_codes={'A','B'})
            self.assertEqual(repo.fetch_current_positions(),{'B':{'quantity':3}})
