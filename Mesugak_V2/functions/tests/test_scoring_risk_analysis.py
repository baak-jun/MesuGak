from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd

FUNCTIONS_DIR = Path(__file__).resolve().parents[1]
if str(FUNCTIONS_DIR) not in sys.path:
    sys.path.insert(0, str(FUNCTIONS_DIR))

from strategy_engine.analysis import StockIdentity, analyze_stock, to_summary  # noqa: E402
from strategy_engine.risk import evaluate_risk  # noqa: E402
from strategy_engine.scoring import classify_bollinger_state, classify_ma_support_state, score_latest  # noqa: E402


def scoring_rows(overrides: dict | None = None) -> pd.DataFrame:
    base_prev = {
        "close": 104.0,
        "high": 105.0,
        "low": 103.0,
        "open": 103.5,
        "ma20": 99.0,
        "ma60": 96.0,
        "ma120": 95.0,
        "bb_upper": 110.0,
        "bb_lower": 92.0,
        "bb_bandwidth": 0.16,
        "bb_percent_b": 0.67,
        "rsi": 54.0,
        "tenkan": 101.0,
        "kijun": 100.0,
        "senkou_a": 99.0,
        "senkou_b": 96.0,
    }
    base_last = {
        **base_prev,
        "close": 112.0,
        "high": 113.0,
        "low": 100.5,
        "open": 105.0,
        "ma20": 101.0,
        "ma60": 97.0,
        "bb_bandwidth": 0.19,
        "bb_percent_b": 1.05,
        "rsi": 61.0,
        "tenkan": 104.0,
        "kijun": 102.0,
        "senkou_a": 101.0,
        "senkou_b": 98.0,
    }
    if overrides:
        base_last.update(overrides)
    return pd.DataFrame([base_prev, base_last])


def analysis_ohlcv(rows: int = 160, decline_tail: bool = False) -> pd.DataFrame:
    dates = pd.date_range("2025-01-01", periods=rows, freq="D")
    closes = [100.0 + i * 0.35 for i in range(rows)]
    if decline_tail:
        for idx in range(rows - 10, rows):
            closes[idx] = closes[rows - 11] - (idx - (rows - 10) + 1) * 2.5
    return pd.DataFrame(
        {
            "date": dates,
            "open": [close - 0.5 for close in closes],
            "high": [close + 1.5 for close in closes],
            "low": [close - 1.5 for close in closes],
            "close": closes,
            "volume": [10000 + i for i in range(rows)],
        }
    )


def bollinger_state_rows(state: str) -> pd.DataFrame:
    rows = []
    for idx in range(130):
        close = 100.0 + idx * 0.08
        bandwidth = 0.14
        percent_b = 0.55
        upper = close + 7
        lower = close - 7
        if idx >= 112:
            bandwidth = 0.035
            upper = close + 1.8
            lower = close - 1.8
            percent_b = 0.55
        if state == "release" and idx >= 126:
            bandwidth = 0.035 + (idx - 125) * 0.015
            upper = close - 0.5
            lower = close - 8
            percent_b = 1.08
        if state == "curl" and idx >= 100:
            bandwidth = 0.23 - max(0, idx - 126) * 0.012
            upper = close + max(1, 10 - max(0, idx - 126) * 1.2)
            lower = close - 10
            percent_b = 0.62
        rows.append(
            {
                "close": close,
                "high": close + 1,
                "ma20": close - 1,
                "ma60": close - 2,
                "ma120": close - 3,
                "bb_upper": upper,
                "bb_lower": lower,
                "bb_mid": (upper + lower) / 2,
                "bb_bandwidth": bandwidth,
                "bb_percent_b": percent_b,
                "rsi": 58,
                "tenkan": close - 0.5,
                "kijun": close - 1,
                "senkou_a": close - 2,
                "senkou_b": close - 3,
            }
        )
    return pd.DataFrame(rows)


class ScoringRiskAnalysisTests(unittest.TestCase):
    def test_score_latest_strong_candidate_and_reasons(self) -> None:
        result = score_latest(scoring_rows())

        self.assertEqual(result.confidence_label, "STRONG_BUY")
        self.assertGreaterEqual(result.confidence_score, 78)
        self.assertIn("price_above_cloud", result.reasons)
        self.assertIn("bollinger_state_squeeze_release_up", result.reasons)
        self.assertIn("penalty", result.component_scores)

    def test_bollinger_state_detects_squeeze_release_up(self) -> None:
        state = classify_bollinger_state(bollinger_state_rows("release"))

        self.assertEqual(state["state"], "SQUEEZE_RELEASE_UP")
        self.assertGreaterEqual(state["score"], 84)
        self.assertIn("recent_squeeze", state["reasons"])

    def test_bollinger_state_detects_expansion_curl_neutral(self) -> None:
        state = classify_bollinger_state(bollinger_state_rows("curl"))

        self.assertEqual(state["state"], "EXPANSION_CURL_NEUTRAL")
        self.assertLessEqual(state["score"], 55)

    def test_score_latest_does_not_buy_expansion_curl(self) -> None:
        result = score_latest(bollinger_state_rows("curl"))

        self.assertEqual(result.indicator_states["bollinger"]["state"], "EXPANSION_CURL_NEUTRAL")
        self.assertNotIn(result.confidence_label, {"STRONG_BUY", "BUY_CANDIDATE"})

    def test_ma_support_rewards_sustained_above_ma60(self) -> None:
        rows = []
        for idx in range(70):
            close = 100 + idx * 0.4
            rows.append(
                {
                    "open": close - 0.2,
                    "low": close - 0.1,
                    "close": close,
                    "ma20": close - 5.0,
                    "ma60": close - 8.0 + idx * 0.02,
                }
            )

        state = classify_ma_support_state(pd.DataFrame(rows))

        self.assertEqual(state["state"], "SUSTAINED_ABOVE_MA60")
        self.assertGreaterEqual(state["score"], 70)

    def test_ma_support_blocks_breakdown_through_ma60(self) -> None:
        df = pd.DataFrame(
            [
                {"open": 103, "low": 101, "close": 103, "ma20": 102, "ma60": 100},
                {"open": 101, "low": 98, "close": 99, "ma20": 102, "ma60": 100},
            ]
        )

        state = classify_ma_support_state(df)

        self.assertEqual(state["state"], "MA60_BREAKDOWN")
        self.assertEqual(state["score"], 0)

    def test_strong_buy_requires_high_quality_bollinger_setup(self) -> None:
        result = score_latest(scoring_rows({"bb_percent_b": 0.62, "close": 106.0, "bb_upper": 112.0}))

        self.assertNotEqual(result.confidence_label, "STRONG_BUY")

    def test_score_latest_penalizes_overheated_breakdown(self) -> None:
        result = score_latest(scoring_rows({"close": 88.0, "bb_lower": 92.0, "rsi": 78.0}))

        self.assertIn("penalty_below_lower_band", result.reasons)
        self.assertIn("penalty_rsi_overheated", result.reasons)
        self.assertLess(result.confidence_score, 62)

    def test_score_latest_tolerates_missing_indicator_values(self) -> None:
        result = score_latest(scoring_rows({"senkou_a": pd.NA, "senkou_b": pd.NA, "rsi": pd.NA}))

        self.assertIsInstance(result.confidence_score, float)

    def test_evaluate_risk_detects_defensive_conditions(self) -> None:
        df = scoring_rows(
            {
                "close": 88.0,
                "bb_lower": 92.0,
                "bb_bandwidth": 0.24,
                "ma20": 98.0,
                "rsi": 34.0,
                "senkou_a": 100.0,
                "senkou_b": 96.0,
            }
        )

        result = evaluate_risk(df)

        self.assertEqual(result.risk_state, "DEFENSIVE")
        self.assertGreaterEqual(result.cash_target_pct, 0.55)
        self.assertIn("below_bollinger_lower", result.risk_flags)
        self.assertIn("downside_band_expansion", result.risk_flags)
        self.assertIn("below_ichimoku_cloud", result.risk_flags)

    def test_analyze_stock_outputs_v1_compatible_summary(self) -> None:
        payload = analyze_stock(
            analysis_ohlcv(),
            StockIdentity(market="KR", code="005930", name="Samsung", marcap=123.0),
        )

        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertEqual(payload["id"], "KR_005930")
        self.assertIn(payload["status"], {"BUY_CANDIDATE", "WATCH", "HOLD", "DEFENSIVE"})
        self.assertIn("history", payload)
        self.assertLessEqual(len(payload["history"]), 160)

        summary = to_summary(payload)
        self.assertNotIn("history", summary)
        self.assertEqual(summary["id"], payload["id"])
        self.assertIn("confidenceScore", summary)
        self.assertIn("indicatorStates", summary)
        self.assertIn("componentScores", summary)
        self.assertIn("sortMetrics", summary)
        self.assertIn("bollinger", summary["sortMetrics"])
        self.assertIn("percentB", summary["sortMetrics"]["bollinger"])

    def test_analyze_stock_rejects_short_history(self) -> None:
        payload = analyze_stock(
            analysis_ohlcv(rows=80),
            StockIdentity(market="KR", code="SHORT", name="Short"),
        )

        self.assertIsNone(payload)


if __name__ == "__main__":
    unittest.main()
