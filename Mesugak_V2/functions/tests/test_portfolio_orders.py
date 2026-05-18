import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from strategy_engine.orders import RebalanceConfig, build_rebalance_orders
from strategy_engine.portfolio import AllocationConfig, build_target_allocations


class PortfolioOrderTests(unittest.TestCase):
    def test_target_allocations_respect_cash_limits_and_confidence_filters(self):
        candidates = [
            {"code": "AAA", "name": "Alpha", "confidenceScore": 95},
            {"code": "BBB", "name": "Beta", "confidenceScore": 80},
            {"code": "CCC", "name": "Gamma", "confidenceScore": 75},
            {"code": "DDD", "name": "Delta", "confidenceScore": 64},
            {"code": "EEE", "name": "Exit", "confidenceScore": 99, "signal": {"action": "EXIT"}},
        ]

        allocation = build_target_allocations(
            candidates,
            cash_target_pct=0.30,
            config=AllocationConfig(max_positions=2, max_position_weight=0.35, min_confidence=65),
        )

        self.assertEqual(allocation["cashTargetPct"], 0.30)
        self.assertEqual([item["code"] for item in allocation["positions"]], ["AAA", "BBB"])
        self.assertEqual([item["targetWeight"] for item in allocation["positions"]], [0.35, 0.35])

    def test_target_allocations_redistribute_after_position_cap(self):
        allocation = build_target_allocations(
            [
                {"code": "AAA", "confidenceScore": 100},
                {"code": "BBB", "confidenceScore": 10},
                {"code": "CCC", "confidenceScore": 10},
            ],
            cash_target_pct=0.10,
            config=AllocationConfig(max_positions=3, max_position_weight=0.32, min_confidence=0),
        )

        weights = {item["code"]: item["targetWeight"] for item in allocation["positions"]}
        self.assertEqual(weights, {"AAA": 0.32, "BBB": 0.29, "CCC": 0.29})
        self.assertEqual(allocation["cashTargetPct"], 0.10)

    def test_rebalance_orders_sell_removed_hold_small_delta_and_buy_underweight(self):
        orders = build_rebalance_orders(
            current_positions={
                "AAA": {"name": "Alpha", "weight": 0.251},
                "BBB": {"name": "Beta", "weight": 0.10},
                "OLD": {"name": "Old Holding", "weight": 0.20},
            },
            target_allocation={
                "cashTargetPct": 0.40,
                "positions": [
                    {"code": "AAA", "name": "Alpha", "targetWeight": 0.25},
                    {"code": "BBB", "name": "Beta", "targetWeight": 0.30},
                ],
            },
            account_value=100000,
            config=RebalanceConfig(min_weight_delta=0.01),
        )

        by_code = {order["code"]: order for order in orders}
        self.assertEqual(by_code["OLD"]["side"], "SELL")
        self.assertEqual(by_code["OLD"]["reason"], "removed_from_target_allocation")
        self.assertEqual(by_code["OLD"]["tradeAmount"], 20000)
        self.assertEqual(by_code["AAA"]["side"], "HOLD")
        self.assertEqual(by_code["AAA"]["tradeAmount"], 100)
        self.assertEqual(by_code["BBB"]["side"], "BUY")
        self.assertEqual(by_code["BBB"]["targetAmount"], 30000)
        self.assertEqual(by_code["BBB"]["tradeAmount"], 20000)

    def test_rebalance_orders_can_derive_weight_from_market_value(self):
        orders = build_rebalance_orders(
            current_positions={"AAA": {"marketValue": 20000}},
            target_allocation={"positions": [{"code": "AAA", "targetWeight": 0.15}]},
            account_value=100000,
        )

        self.assertEqual(orders[0]["side"], "SELL")
        self.assertEqual(orders[0]["currentWeight"], 0.20)
        self.assertEqual(orders[0]["tradeAmount"], 5000)


if __name__ == "__main__":
    unittest.main()
