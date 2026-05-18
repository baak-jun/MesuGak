from __future__ import annotations

import argparse
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "jobs"))

from smoke_test_flow import run  # noqa: E402


class SmokeTestFlowTests(unittest.TestCase):
    def test_smoke_test_flow_runs_without_firestore(self) -> None:
        result = run(argparse.Namespace(market="KR", initial_cash=1_000_000, max_positions=2, min_confidence=0.0))

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["analysisCount"], 2)
        self.assertGreaterEqual(result["positionCount"], 1)
        self.assertGreaterEqual(result["orderCount"], 1)
        self.assertIn("totalEquity", result)


if __name__ == "__main__":
    unittest.main()
