from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from strategy_engine.checkpoints import LocalCheckpointManager, MemoryCheckpointManager
from strategy_engine.market_data import KR_INDEX_NAMES, targets_from_codes


class MarketDataCheckpointTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
