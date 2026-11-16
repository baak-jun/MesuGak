from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from strategy_engine.checkpoints import LocalCheckpointManager, MemoryCheckpointManager
from strategy_engine.market_data import KR_INDEX_NAMES, targets_from_codes, load_market_universe


class MarketDataCheckpointTests(unittest.TestCase):
    def test_universe_keeps_alphanumeric_share_codes_in_both_exchanges(self):
        class Client:
            def latest_stock_rows(self):
                return [
                    {'mrktCtg': 'KOSPI', 'srtnCd': '005930', 'mrktTotAmt': '300'},
                    {'mrktCtg': 'KOSPI', 'srtnCd': '00104K', 'mrktTotAmt': '100'},
                    {'mrktCtg': 'KOSDAQ', 'srtnCd': '000001', 'mrktTotAmt': '200'},
                    {'mrktCtg': 'KONEX', 'srtnCd': '000002', 'mrktTotAmt': '400'},
                    {'mrktCtg': 'KOSPI', 'srtnCd': '../bad', 'mrktTotAmt': '400'},
                ]
        self.assertEqual([row.code for row in load_market_universe('KR', client=Client())], ['005930', '000001', '00104K'])
    def test_targets_from_codes_strips_empty_values(self) -> None:
        targets = targets_from_codes([" 005930 ", "", "NVDA"])

        self.assertEqual([target.code for target in targets], ["005930", "NVDA"])
        self.assertEqual([target.name for target in targets], ["005930", "NVDA"])

    def test_public_index_names_match_api_labels(self) -> None:
        self.assertEqual(KR_INDEX_NAMES, {"KOSPI": "코스피", "KOSDAQ": "코스닥"})

    def test_checkpoint_records_success_and_resumes_done_codes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "checkpoint.json"
            manager = LocalCheckpointManager(path, "KR")
            manager.prepare(total_count=2)
            manager.record_success("005930", {"id": "KR_005930"}, remaining_count=1)

            resumed = LocalCheckpointManager(path, "KR")
            resumed.prepare(total_count=2)

            self.assertEqual(resumed.done_codes(), {"005930"})
            self.assertEqual(resumed.summaries(), [{"id": "KR_005930"}])
            self.assertEqual(resumed.snapshot()["remainingCount"], 1)

    def test_memory_checkpoint_does_not_resume_disk_state(self) -> None:
        manager = MemoryCheckpointManager("KR")
        manager.prepare(total_count=1)
        manager.record_success("005930", {"id": "KR_005930"}, remaining_count=0)

        fresh = MemoryCheckpointManager("KR")
        fresh.prepare(total_count=1)

        self.assertIsNone(fresh.path)
        self.assertEqual(fresh.done_codes(), set())
        self.assertEqual(fresh.summaries(), [])

    def test_successful_retry_removes_previous_failure_from_checkpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = LocalCheckpointManager(Path(tmp) / 'checkpoint.json', 'KR')
            manager.prepare(total_count=1)
            manager.record_failure('005930', 'timeout', remaining_count=0)
            manager.record_success('005930', {'code': '005930'}, remaining_count=0)
            self.assertEqual(manager.snapshot()['failedCodes'], [])


if __name__ == "__main__":
    unittest.main()
