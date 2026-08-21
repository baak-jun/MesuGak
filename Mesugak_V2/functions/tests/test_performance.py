from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from strategy_engine.performance import build_private_paper_performance, percentage_return  # noqa: E402


class PrivatePaperPerformanceTests(unittest.TestCase):
    def test_return_calculation_uses_shared_baseline(self) -> None:
        self.assertEqual(percentage_return(100.0, 112.5), 12.5)
        self.assertEqual(percentage_return(0.0, 112.5), 0.0)

    def test_snapshot_omits_raw_levels_and_positions(self) -> None:
        snapshot = build_private_paper_performance(
            {
                "market": "KR",
                "initialCash": 100000000,
                "totalEquity": 104000000,
                "totalPnl": 4000000,
                "returnPct": 4.0,
                "holdingCount": 3,
                "holdings": [{"code": "005930"}],
            },
            baseline_date="2026-07-01",
            benchmarks={
                "KOSPI": {"label": "KOSPI", "returnPct": 1.25, "baselineDate": "2026-07-01", "asOfDate": "2026-07-10", "source": "test"},
                "KOSDAQ": {"label": "KOSDAQ", "returnPct": -2.5, "baselineDate": "2026-07-01", "asOfDate": "2026-07-10", "source": "test"},
            },
        )

        # A stale 10M-based return field must not override the KIS 100M account basis.
        self.assertEqual(snapshot["returnPct"], 4.0)
        self.assertEqual(snapshot["totalPnl"], 4000000.0)
        self.assertEqual(snapshot["benchmarks"]["KOSPI"]["gapPctPoints"], 2.75)
        self.assertEqual(snapshot["benchmarks"]["KOSDAQ"]["gapPctPoints"], 6.5)
        self.assertNotIn("holdings", snapshot)
        self.assertNotIn("baselineClose", snapshot["benchmarks"]["KOSPI"])
        self.assertNotIn("lastClose", snapshot["benchmarks"]["KOSPI"])


if __name__ == "__main__":
    unittest.main()