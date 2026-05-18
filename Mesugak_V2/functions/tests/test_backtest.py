from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from strategy_engine.analysis import StockIdentity  # noqa: E402
from strategy_engine.backtest import BacktestConfig, run_backtest  # noqa: E402


def price_frame(rows: int = 8) -> pd.DataFrame:
    dates = pd.date_range("2026-01-01", periods=rows, freq="D")
    closes = [100 + idx for idx in range(rows)]
    return pd.DataFrame(
        {
            "date": dates,
            "open": closes,
            "high": [close + 1 for close in closes],
            "low": [close - 1 for close in closes],
            "close": closes,
            "volume": [1000] * rows,
        }
    )


class BacktestTests(unittest.TestCase):
    def test_backtest_trades_on_next_day_after_signal(self) -> None:
        seen_lengths = []

        def fake_analysis(df: pd.DataFrame, identity: StockIdentity) -> dict:
            seen_lengths.append(len(df))
            return {
                "id": identity.doc_id,
                "code": identity.code,
                "name": identity.name,
                "market": identity.market,
                "strategyVersion": "V2",
                "status": "BUY_CANDIDATE",
                "type": "buy_signal",
                "currentPrice": float(df.iloc[-1]["close"]),
                "lastDate": df.iloc[-1]["date"].strftime("%Y-%m-%d"),
                "confidenceScore": 90.0,
                "confidenceLabel": "STRONG_BUY",
                "riskState": "NORMAL",
                "riskFlags": [],
                "cashTargetPct": 0.20,
                "stopLoss": 0,
                "signal": {"action": "BUY_CANDIDATE"},
                "indicatorStates": {},
            }

        result = run_backtest(
            {"AAA": price_frame()},
            {"AAA": StockIdentity("BT", "AAA", "Alpha")},
            BacktestConfig(initial_cash=1000, min_history=3, max_positions=1, max_position_weight=0.5),
            analysis_fn=fake_analysis,
        )

        self.assertEqual(result["status"], "done")
        self.assertEqual(seen_lengths[0], 3)
        self.assertEqual(result["trades"][0]["signalDate"], "2026-01-03")
        self.assertEqual(result["trades"][0]["tradeDate"], "2026-01-04")
        self.assertGreater(result["finalValue"], 1000)

    def test_backtest_reports_insufficient_history(self) -> None:
        result = run_backtest(
            {"AAA": price_frame(rows=3)},
            config=BacktestConfig(initial_cash=1000, min_history=5),
        )

        self.assertEqual(result["status"], "not_run")
        self.assertEqual(result["reason"], "insufficient_history")
        self.assertEqual(result["finalValue"], 1000)


if __name__ == "__main__":
    unittest.main()
