from __future__ import annotations

import datetime as dt
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "jobs"))

from monitor_school_server import KST, find_health_issue, mark_success  # noqa: E402


class SchoolServerMonitorTests(unittest.TestCase):
    def test_success_from_friday_is_current_during_weekend(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            mark_success(root, "KR", dt.datetime(2026, 8, 28, 20, 0, tzinfo=KST))

            issue, _ = find_health_issue(
                root, "KR", dt.datetime(2026, 8, 30, 23, 40, tzinfo=KST), "23:30", 90
            )

            self.assertIsNone(issue)

    def test_stale_running_checkpoint_is_reported_first(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            checkpoint = root / "runtime" / "checkpoints" / "analyze_market_KR.json"
            checkpoint.parent.mkdir(parents=True)
            checkpoint.write_text(
                json.dumps({"status": "running", "updatedAt": "2026-08-31T18:00:00+09:00"}),
                encoding="utf-8",
            )

            issue, _ = find_health_issue(
                root, "KR", dt.datetime(2026, 8, 31, 20, 0, tzinfo=KST), "23:30", 90
            )

            self.assertEqual(issue, "checkpoint_stalled")

    def test_previous_business_day_missing_is_reported_after_deadline(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            mark_success(root, "KR", dt.datetime(2026, 8, 28, 20, 0, tzinfo=KST))

            issue, _ = find_health_issue(
                root, "KR", dt.datetime(2026, 8, 31, 23, 40, tzinfo=KST), "23:30", 90
            )

            self.assertEqual(issue, "publication_stale")


if __name__ == "__main__":
    unittest.main()
