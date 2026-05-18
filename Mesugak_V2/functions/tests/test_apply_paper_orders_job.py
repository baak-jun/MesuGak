from __future__ import annotations

import argparse
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "jobs"))

from apply_paper_orders import run_with_repo  # noqa: E402


class FakeRepo:
    def __init__(self, *, account=None, positions=None, orders=None, prices=None):
        self.account = account
        self.positions = positions or {}
        self.orders = orders or []
        self.prices = prices or {}
        self.saved_positions = None
        self.deleted_previous_codes = None
        self.saved_logs = None
        self.saved_snapshot = None
        self.saved_application = None

    def fetch_account_snapshot(self):
        return self.account

    def fetch_rebalance_orders(self, market, allocation_id=None):
        return [
            order for order in self.orders
            if order.get("market") == market and (allocation_id is None or order.get("allocationId") == allocation_id)
        ]

    def fetch_current_positions(self):
        return self.positions

    def fetch_latest_prices(self, market, codes):
        return {code: self.prices[code] for code in codes if code in self.prices}

    def save_paper_positions(self, positions, *, previous_codes=None):
        self.saved_positions = positions
        self.deleted_previous_codes = previous_codes

    def append_trade_logs(self, logs):
        self.saved_logs = logs

    def save_account_snapshot(self, payload):
        self.saved_snapshot = payload

    def save_paper_order_application(self, application_id, payload):
        self.saved_application = {"id": application_id, **payload}


def args(**overrides):
    base = {
        "market": "KR",
        "allocation_id": "KR_2026-01-02",
        "cred_path": None,
        "initial_cash": 1000,
        "dry_run": False,
    }
    base.update(overrides)
    return argparse.Namespace(**base)


class ApplyPaperOrdersJobTests(unittest.TestCase):
    def test_apply_paper_orders_job_writes_positions_logs_and_snapshot(self) -> None:
        repo = FakeRepo(
            account={"market": "KR", "cash": 1000, "initialCash": 1000, "realizedPnl": 0},
            orders=[
                {
                    "market": "KR",
                    "allocationId": "KR_2026-01-02",
                    "code": "AAA",
                    "name": "Alpha",
                    "side": "BUY",
                    "tradeAmount": 500,
                    "reason": "confidence_rebalance",
                }
            ],
            prices={"AAA": 100},
        )

        result = run_with_repo(args(), repo)

        self.assertEqual(result["status"], "applied")
        self.assertEqual(result["executedCount"], 1)
        self.assertEqual(repo.saved_positions["AAA"]["quantity"], 5)
        self.assertEqual(repo.saved_logs[0]["action"], "BUY")
        self.assertEqual(repo.saved_snapshot["cash"], 500)
        self.assertEqual(repo.saved_snapshot["appliedAllocationIds"], ["KR_2026-01-02"])
        self.assertEqual(repo.saved_application["id"], "KR_2026-01-02")
        self.assertEqual(repo.saved_application["executedCount"], 1)

    def test_apply_paper_orders_job_dry_run_does_not_write(self) -> None:
        repo = FakeRepo(
            account={"market": "KR", "cash": 1000, "initialCash": 1000},
            orders=[{"market": "KR", "allocationId": "KR_2026-01-02", "code": "AAA", "side": "BUY", "tradeAmount": 500}],
            prices={"AAA": 100},
        )

        result = run_with_repo(args(dry_run=True), repo)

        self.assertEqual(result["status"], "dry_run")
        self.assertIsNone(repo.saved_positions)
        self.assertIsNone(repo.saved_logs)
        self.assertIsNone(repo.saved_snapshot)
        self.assertIsNone(repo.saved_application)

    def test_apply_paper_orders_job_skips_already_applied_allocation(self) -> None:
        repo = FakeRepo(
            account={"market": "KR", "cash": 1000, "initialCash": 1000, "appliedAllocationIds": ["KR_2026-01-02"]},
            orders=[{"market": "KR", "allocationId": "KR_2026-01-02", "code": "AAA", "side": "BUY", "tradeAmount": 500}],
            prices={"AAA": 100},
        )

        result = run_with_repo(args(), repo)

        self.assertEqual(result["status"], "already_applied")
        self.assertIsNone(repo.saved_positions)


if __name__ == "__main__":
    unittest.main()
