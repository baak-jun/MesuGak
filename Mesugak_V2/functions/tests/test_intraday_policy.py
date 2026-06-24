from __future__ import annotations

import sys
import unittest
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


if __name__ == "__main__":
    unittest.main()
