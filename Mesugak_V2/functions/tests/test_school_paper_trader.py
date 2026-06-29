from __future__ import annotations

import argparse
import sys
import unittest
from pathlib import Path

FUNCTIONS_DIR = Path(__file__).resolve().parents[1]
JOBS_DIR = FUNCTIONS_DIR / "jobs"
for path in (FUNCTIONS_DIR, JOBS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from school_paper_trader import fetch_live_prices, run  # noqa: E402


class FakeClient:
    def __init__(self, prices: dict[str, float], failures: set[str] | None = None, balance_error: Exception | None = None):
        self.prices = prices
        self.failures = failures or set()
        self.balance_error = balance_error

    def quote(self, code: str) -> float:
        if code in self.failures:
            raise RuntimeError("quote temporarily unavailable")
        return self.prices[code]

    def fetch_balance(self, *, market: str = "KR", initial_cash: float = 0.0):
        if self.balance_error:
            raise self.balance_error
        return (
            {"market": market, "mode": "paper", "source": "KIS_PAPER", "cash": 1000000, "totalEquity": 1000000, "initialCash": initial_cash},
            {},
        )


class FakeRepo:
    def __init__(self):
        self.saved_positions = None
        self.saved_snapshot = None

    def fetch_meta_candidates(self, market: str) -> list[dict]:
        return []

    def fetch_current_positions(self) -> dict[str, dict]:
        return {}

    def fetch_account_snapshot(self) -> dict | None:
        return {"market": "KR", "cash": 1000000, "totalEquity": 1000000, "initialCash": 1000000}

    def save_paper_positions(self, positions, *, previous_codes=None):
        self.saved_positions = positions

    def save_account_snapshot(self, payload):
        self.saved_snapshot = payload


class SchoolPaperTraderTests(unittest.TestCase):
    def test_fetch_live_prices_skips_failed_quote(self) -> None:
        prices, errors = fetch_live_prices(FakeClient({"AAA": 100.0}, {"BAD"}), ["AAA", "BAD"])

        self.assertEqual(prices, {"AAA": 100.0})
        self.assertIn("BAD", errors)
        self.assertIn("quote temporarily unavailable", errors["BAD"])

    def test_run_reports_quote_errors_without_crashing(self) -> None:
        args = argparse.Namespace(
            market="KR",
            initial_cash=1000000,
            buy_score_min=65.0,
            score_exit_threshold=-15.0,
            trailing_stop_pct=0.08,
            position_weight=0.10,
            rotation_score_gap=10.0,
            max_live_candidates=2,
            quote_delay_seconds=0.0,
            quote_retries=0,
            quote_rate_limit_backoff_seconds=0.0,
            execute=False,
            skip_account_sync=False,
            cred_path=None,
        )
        candidates = [
            {"code": "AAA", "name": "Alpha", "confidenceScore": 70, "status": "BUY_CANDIDATE"},
            {"code": "BAD", "name": "Bad", "confidenceScore": 69, "status": "BUY_CANDIDATE"},
        ]

        result = run(args, repo=FakeRepo(), client=FakeClient({"AAA": 100.0}, {"BAD"}), candidates=candidates)

        self.assertEqual(result["status"], "dry_run")
        self.assertEqual(result["prices"], {"AAA": 100.0})
        self.assertIn("BAD", result["quoteErrors"])

    def test_execute_is_blocked_when_account_sync_fails(self) -> None:
        args = argparse.Namespace(
            market="KR",
            initial_cash=1000000,
            buy_score_min=65.0,
            score_exit_threshold=-15.0,
            trailing_stop_pct=0.08,
            position_weight=0.10,
            rotation_score_gap=10.0,
            max_live_candidates=1,
            quote_delay_seconds=0.0,
            quote_retries=0,
            quote_rate_limit_backoff_seconds=0.0,
            execute=True,
            skip_account_sync=False,
            cred_path=None,
        )

        result = run(args, repo=FakeRepo(), client=FakeClient({}, balance_error=RuntimeError("balance unavailable")), candidates=[])

        self.assertEqual(result["status"], "account_sync_failed")
        self.assertEqual(result["executedCount"], 0)
        self.assertIn("balance unavailable", result["accountSyncError"])


if __name__ == "__main__":
    unittest.main()
