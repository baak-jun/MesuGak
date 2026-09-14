from __future__ import annotations

import sys
import unittest
from datetime import date
from pathlib import Path

FUNCTIONS_DIR = Path(__file__).resolve().parents[1]
if str(FUNCTIONS_DIR) not in sys.path:
    sys.path.insert(0, str(FUNCTIONS_DIR))

from strategy_engine.intraday_policy import IntradayPolicyConfig, build_intraday_orders  # noqa: E402


class IntradayPolicyTests(unittest.TestCase):
    def test_negative_score_and_trailing_stop_exit_positions(self) -> None:
        positions = {
            "BAD": {"code": "BAD", "name": "Bad", "quantity": 10, "buyPrice": 100, "highestPrice": 120},
            "STOP": {"code": "STOP", "name": "Stop", "quantity": 10, "buyPrice": 100, "highestPrice": 120},
        }
        candidates = [{"code": "BAD", "confidenceScore": -20}, {"code": "STOP", "confidenceScore": 50}]
        orders = build_intraday_orders(candidates, positions, 10_000, 1_000, {"BAD": 110, "STOP": 108})
        self.assertEqual({order["reason"] for order in orders if order["side"] == "SELL"}, {"negative_score_exit", "trailing_stop"})

    def test_higher_scored_candidate_rotates_profitable_weakest_position(self) -> None:
        positions = {"OLD": {"code": "OLD", "quantity": 10, "buyPrice": 100, "highestPrice": 105}}
        candidates = [{"code": "OLD", "confidenceScore": 60}, {"code": "NEW", "confidenceScore": 75, "status": "BUY_CANDIDATE"}]
        orders = build_intraday_orders(candidates, positions, 10_000, 0, {"OLD": 105, "NEW": 100})
        self.assertEqual([(order["side"], order["code"]) for order in orders], [("SELL", "OLD"), ("BUY", "NEW")])

    def test_profitable_portfolio_trims_each_position_when_no_single_exit_is_allowed(self) -> None:
        positions = {
            "A": {"code": "A", "quantity": 10, "buyPrice": 100, "highestPrice": 110},
            "B": {"code": "B", "quantity": 10, "buyPrice": 100, "highestPrice": 110},
        }
        candidates = [{"code": "A", "confidenceScore": 70}, {"code": "B", "confidenceScore": 72}, {"code": "NEW", "confidenceScore": 85, "status": "BUY_CANDIDATE"}]
        orders = build_intraday_orders(candidates, positions, 2_000, 0, {"A": 110, "B": 110, "NEW": 100}, IntradayPolicyConfig(rotation_score_gap=10))
        trims = [order for order in orders if order["reason"] == "proportional_profit_take"]
        self.assertEqual(len(trims), 2)
        self.assertTrue(any(order["side"] == "BUY" and order["code"] == "NEW" for order in orders))


    def test_same_day_exit_lock_blocks_reentry(self) -> None:
        candidates = [{"code": "LOCKED", "confidenceScore": 90, "status": "BUY_CANDIDATE"}]
        orders = build_intraday_orders(candidates, {}, 10_000, 10_000, {"LOCKED": 100}, entry_blocked_codes={"LOCKED"})
        self.assertEqual(orders, [])

    def test_profit_lock_exits_after_small_gain_retraces_from_high(self) -> None:
        positions = {"GAIN": {"code": "GAIN", "name": "Gain", "quantity": 10, "buyPrice": 100, "highestPrice": 105}}
        candidates = [{"code": "GAIN", "confidenceScore": 70}]
        config = IntradayPolicyConfig(profit_lock_activate_pct=0.03, profit_lock_trailing_pct=0.02, profit_lock_min_pnl_pct=0.005)
        orders = build_intraday_orders(candidates, positions, 10_000, 0, {"GAIN": 102.5}, config)
        self.assertEqual([(order["side"], order["reason"]) for order in orders], [("SELL", "profit_lock_trailing_stop")])
    def test_same_day_stop_loss_exits_only_the_position_opened_today(self) -> None:
        positions = {
            "TODAY": {"code": "TODAY", "name": "Today", "quantity": 10, "buyPrice": 100, "highestPrice": 100, "boughtAt": "2026-07-14T09:01:00+09:00"},
            "OLDER": {"code": "OLDER", "name": "Older", "quantity": 10, "buyPrice": 100, "highestPrice": 100, "boughtAt": "2026-07-13T09:01:00+09:00"},
        }
        candidates = [{"code": "TODAY", "confidenceScore": 70}, {"code": "OLDER", "confidenceScore": 70}]

        orders = build_intraday_orders(
            candidates,
            positions,
            10_000,
            0,
            {"TODAY": 97, "OLDER": 97},
            session_date=date(2026, 7, 14),
        )

        self.assertEqual([(order["side"], order["code"], order["reason"]) for order in orders], [("SELL", "TODAY", "same_day_stop_loss")])
if __name__ == "__main__":
    unittest.main()
