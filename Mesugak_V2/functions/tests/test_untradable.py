from __future__ import annotations

import asyncio
import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from types import SimpleNamespace

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parents[1] / 'jobs')]
from strategy_engine.untradable import load_untradable_codes, record_untradable, prune_candidate_snapshot
from strategy_engine.order_state import OrderStateStore
from jobs.analyze_market import _load_targets
from jobs.kis_realtime_trader import RealtimeSignalEngine, TraderRuntime


class UntradableTests(unittest.TestCase):
    def test_persistent_codes_filter_analysis_targets_including_explicit_requests(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'excluded.json'
            record_untradable(path, '36328K', '매매불가')
            args = SimpleNamespace(codes='36328K,005930', untradable_file=path)
            self.assertEqual([target.code for target in _load_targets(args, 'KR')], ['005930'])
            self.assertEqual(load_untradable_codes(path), {'36328K'})
            # Registry has no session expiry: a later day still excludes it.
            self.assertNotIn('sessionDate', json.loads(path.read_text(encoding='utf-8')))

    def test_pruning_preserves_original_processing_counts_and_removes_current_results(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'candidates.json'
            path.write_text(json.dumps({'market': 'KR', 'targetCount': 2, 'summaries': [{'code': '36328K'}, {'code': '005930'}]}))
            self.assertEqual(prune_candidate_snapshot(path, {'36328K'}), 1)
            data = json.loads(path.read_text())
            self.assertEqual(data['summaries'], [{'code': '005930'}])
            self.assertEqual(data['targetCount'], 2)
            self.assertEqual(data['eligibleCount'], 1)
            self.assertEqual(prune_candidate_snapshot(path, {'36328K'}), 0)

    def test_excluded_codes_never_enter_watch_or_exploration_on_a_later_day(self):
        with tempfile.TemporaryDirectory() as directory, OrderStateStore(Path(directory) / 'orders.sqlite3') as store:
            path = Path(directory) / 'excluded.json'
            record_untradable(path, '36328K', '매매불가')
            candidates = Path(directory) / 'candidates.json'
            rows = [{'code': '36328K', 'confidenceScore': 99}, {'code': '005930', 'confidenceScore': 80}, {'code': '225570', 'confidenceScore': 70}]
            candidates.write_text(json.dumps({'market': 'KR', 'summaries': rows}))
            args = SimpleNamespace(market='KR', max_watch=2, candidate_file=candidates, untradable_file=path, execute=False, report_interval=60, entry_close_time='15:15:00')
            repo = SimpleNamespace(save_intraday_runtime_state=lambda payload: None)
            runtime = TraderRuntime(args, repo, SimpleNamespace(request_interval=2.0), RealtimeSignalEngine(rows), store, None, {}, date(2026, 10, 13))
            watch = asyncio.run(runtime.refresh_candidates())
            self.assertNotIn('36328K', watch)
            self.assertNotIn('36328K', runtime.engine.candidates)
            self.assertNotIn('36328K', runtime.exploration_pool)
            runtime.engine.update_positions({'36328K': {'quantity': 1, 'buyPrice': 100}})
            watch = asyncio.run(runtime.refresh_candidates())
            self.assertIn('36328K', watch)  # Management only until the holding is closed.

    def test_broken_registry_does_not_silently_reenable_excluded_symbols(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'excluded.json'
            path.write_text('{broken')
            with self.assertRaises(ValueError):
                load_untradable_codes(path)
