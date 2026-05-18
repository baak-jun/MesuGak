from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from strategy_engine.ledger import apply_paper_orders, build_account_snapshot, initialize_account, normalize_account  # noqa: E402


class LedgerTests(unittest.TestCase):
    def test_initialize_account_sets_cash_and_mode(self) -> None:
        account = initialize_account(initial_cash=500000, market="KR")

        self.assertEqual(account["cash"], 500000)
        self.assertEqual(account["initialCash"], 500000)
        self.assertEqual(account["mode"], "paper")
        self.assertEqual(account["source"], "Mesugak_V2")

    def test_buy_order_applies_integer_quantity_and_reduces_cash(self) -> None:
        result = apply_paper_orders(
            initialize_account(initial_cash=1000),
            {},
            [{"code": "AAA", "name": "Alpha", "side": "BUY", "tradeAmount": 450, "reason": "confidence_rebalance"}],
            {"AAA": 100},
            executed_at="2026-01-02T09:00:00",
        )

        self.assertEqual(result["account"]["cash"], 600)
        self.assertEqual(result["positions"]["AAA"]["quantity"], 4)
        self.assertEqual(result["positions"]["AAA"]["buyPrice"], 100)
        self.assertEqual(result["logs"][0]["action"], "BUY")
        self.assertEqual(result["logs"][0]["amount"], 400)

    def test_existing_snapshot_without_cash_does_not_create_extra_cash(self) -> None:
        account = normalize_account({"totalEvalAmt": 1000, "initialCash": 1000}, initial_cash=1000)

        self.assertEqual(account["cash"], 0)

    def test_buy_order_caps_quantity_to_available_cash(self) -> None:
        result = apply_paper_orders(
            initialize_account(initial_cash=250),
            {},
            [{"code": "AAA", "side": "BUY", "tradeAmount": 1000}],
            {"AAA": 100},
        )

        self.assertEqual(result["account"]["cash"], 50)
        self.assertEqual(result["positions"]["AAA"]["quantity"], 2)
        self.assertGreaterEqual(result["account"]["cash"], 0)

    def test_buy_existing_position_updates_average_price(self) -> None:
        result = apply_paper_orders(
            initialize_account(initial_cash=1000),
            {"AAA": {"code": "AAA", "name": "Alpha", "quantity": 2, "buyPrice": 100, "lastPrice": 100}},
            [{"code": "AAA", "name": "Alpha", "side": "BUY", "tradeAmount": 300}],
            {"AAA": 150},
        )

        self.assertEqual(result["positions"]["AAA"]["quantity"], 4)
        self.assertEqual(result["positions"]["AAA"]["buyPrice"], 125)
        self.assertEqual(result["account"]["cash"], 700)

    def test_sell_order_realizes_pnl_and_keeps_remaining_position(self) -> None:
        result = apply_paper_orders(
            initialize_account(initial_cash=0),
            {"AAA": {"code": "AAA", "name": "Alpha", "quantity": 10, "buyPrice": 100, "lastPrice": 100}},
            [{"code": "AAA", "name": "Alpha", "side": "SELL", "tradeAmount": 450, "targetWeight": 0.5}],
            {"AAA": 150},
        )

        self.assertEqual(result["positions"]["AAA"]["quantity"], 7)
        self.assertEqual(result["account"]["cash"], 450)
        self.assertEqual(result["account"]["realizedPnl"], 150)
        self.assertEqual(result["logs"][0]["action"], "SELL")
        self.assertEqual(result["logs"][0]["pnlPct"], 50)

    def test_sell_with_zero_target_weight_sells_all(self) -> None:
        result = apply_paper_orders(
            initialize_account(initial_cash=0),
            {"AAA": {"code": "AAA", "quantity": 3, "buyPrice": 100, "lastPrice": 100}},
            [{"code": "AAA", "side": "SELL", "tradeAmount": 1, "targetWeight": 0}],
            {"AAA": 120},
        )

        self.assertNotIn("AAA", result["positions"])
        self.assertEqual(result["account"]["cash"], 360)
        self.assertEqual(result["account"]["realizedPnl"], 60)

    def test_hold_order_is_ignored(self) -> None:
        result = apply_paper_orders(
            initialize_account(initial_cash=1000),
            {},
            [{"code": "AAA", "side": "HOLD", "tradeAmount": 500}],
            {"AAA": 100},
        )

        self.assertEqual(result["positions"], {})
        self.assertEqual(result["logs"], [])
        self.assertEqual(result["account"]["cash"], 1000)

    def test_account_snapshot_calculates_unrealized_pnl_and_return(self) -> None:
        snapshot = build_account_snapshot(
            {"market": "KR", "mode": "paper", "source": "Mesugak_V2", "cash": 200, "initialCash": 1000, "realizedPnl": 30},
            {"AAA": {"code": "AAA", "name": "Alpha", "quantity": 5, "buyPrice": 100, "lastPrice": 100}},
            {"AAA": 120},
            updated_at="2026-01-02T09:00:00",
        )

        self.assertEqual(snapshot["cash"], 200)
        self.assertEqual(snapshot["totalEvalAmt"], 600)
        self.assertEqual(snapshot["totalBuyAmt"], 500)
        self.assertEqual(snapshot["unrealizedPnl"], 100)
        self.assertEqual(snapshot["totalPnl"], 130)
        self.assertEqual(snapshot["totalEquity"], 800)
        self.assertEqual(snapshot["returnPct"], -20)
        self.assertEqual(snapshot["holdings"][0]["pnlPct"], 20)


if __name__ == "__main__":
    unittest.main()
