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

from school_paper_trader import choose_live_candidates, fetch_live_prices, process_paper_refresh_requests, run  # noqa: E402


class FakeClient:
    def __init__(self, prices: dict[str, float], failures: set[str] | None = None, balance_error: Exception | None = None):
        self.prices = prices
        self.failures = failures or set()
        self.balance_error = balance_error
        self.quote_calls: list[str] = []

    def quote(self, code: str) -> float:
        self.quote_calls.append(code)
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
        self.refresh_requests = []
        self.finished_refresh_requests = []

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

    def fetch_pending_paper_refresh_requests(self, limit=5):
        return self.refresh_requests[:limit]

    def finish_paper_refresh_request(self, request_id, payload):
        self.finished_refresh_requests.append((request_id, payload))


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
            max_live_scan_candidates=4,
            live_watch_min_score=45.0,
            live_drop_penalty_per_pct=4.0,
            live_rise_bonus_per_pct=1.0,
            live_rise_bonus_max=8.0,
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

    def test_choose_live_candidates_replaces_weakened_candidate(self) -> None:
        args = argparse.Namespace(
            max_live_candidates=1,
            max_live_scan_candidates=3,
            live_watch_min_score=45.0,
            live_drop_penalty_per_pct=4.0,
            live_rise_bonus_per_pct=1.0,
            live_rise_bonus_max=8.0,
            quote_delay_seconds=0.0,
            quote_retries=0,
            quote_rate_limit_backoff_seconds=0.0,
            buy_score_min=65.0,
        )
        candidates = [
            {"code": "AAA", "name": "Alpha", "confidenceScore": 70, "status": "BUY_CANDIDATE", "currentPrice": 100},
            {"code": "BBB", "name": "Beta", "confidenceScore": 60, "status": "WATCH", "currentPrice": 100},
        ]

        selected, prices, errors, telemetry = choose_live_candidates(
            candidates,
            {},
            FakeClient({"AAA": 80.0, "BBB": 101.0}),
            args,
        )

        self.assertEqual([item["code"] for item in selected], ["BBB"])
        self.assertEqual(errors, {})
        self.assertEqual(prices["AAA"], 80.0)
        self.assertEqual(telemetry["liveRejected"], 1)

    def test_choose_live_candidates_checks_held_position_before_candidates(self) -> None:
        args = argparse.Namespace(
            max_live_candidates=1,
            max_live_scan_candidates=2,
            live_watch_min_score=45.0,
            live_drop_penalty_per_pct=4.0,
            live_rise_bonus_per_pct=1.0,
            live_rise_bonus_max=8.0,
            quote_delay_seconds=0.0,
            quote_retries=0,
            quote_rate_limit_backoff_seconds=0.0,
            buy_score_min=65.0,
        )
        client = FakeClient({"HELD": 100.0, "AAA": 100.0, "BBB": 100.0})

        choose_live_candidates(
            [
                {"code": "AAA", "confidenceScore": 80, "status": "BUY_CANDIDATE"},
                {"code": "BBB", "confidenceScore": 70, "status": "BUY_CANDIDATE"},
            ],
            {"HELD": {"code": "HELD", "quantity": 1, "buyPrice": 100}},
            client,
            args,
        )

        self.assertEqual(client.quote_calls, ["HELD", "AAA", "BBB"])
    def test_process_refresh_requests_syncs_account_without_orders(self) -> None:
        repo = FakeRepo()
        repo.refresh_requests = [{"id": "refresh-1", "market": "KR"}]

        result = process_paper_refresh_requests(
            repo,
            FakeClient({}),
            market="KR",
            initial_cash=1000000,
        )

        self.assertEqual(result["completed"], 1)
        self.assertEqual(result["failed"], 0)
        self.assertIsNotNone(repo.saved_snapshot)
        self.assertEqual(repo.finished_refresh_requests[0][0], "refresh-1")
        self.assertEqual(repo.finished_refresh_requests[0][1]["status"], "completed")

    def test_process_refresh_requests_records_sync_failure(self) -> None:
        repo = FakeRepo()
        repo.refresh_requests = [{"id": "refresh-fail", "market": "KR"}]

        result = process_paper_refresh_requests(
            repo,
            FakeClient({}, balance_error=RuntimeError("balance unavailable")),
            market="KR",
            initial_cash=1000000,
        )

        self.assertEqual(result["completed"], 0)
        self.assertEqual(result["failed"], 1)
        self.assertEqual(repo.finished_refresh_requests[0][1]["status"], "failed")
        self.assertEqual(repo.finished_refresh_requests[0][1]["errorCode"], "RuntimeError")

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
            max_live_scan_candidates=3,
            live_watch_min_score=45.0,
            live_drop_penalty_per_pct=4.0,
            live_rise_bonus_per_pct=1.0,
            live_rise_bonus_max=8.0,
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
