from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

import pandas as pd

FUNCTIONS_DIR = Path(__file__).resolve().parents[1]
if str(FUNCTIONS_DIR) not in sys.path:
    sys.path.insert(0, str(FUNCTIONS_DIR))

from strategy_engine.indicators import (  # noqa: E402
    add_all_indicators,
    add_bollinger_bands,
    add_ichimoku,
    add_moving_averages,
    add_rsi,
)


def deterministic_ohlc(rows: int = 160) -> pd.DataFrame:
    index = pd.date_range("2025-01-01", periods=rows, freq="D")
    close = pd.Series([100 + i + ((i % 7) - 3) * 0.4 for i in range(rows)], index=index)
    high = close + pd.Series([2.0 + (i % 5) * 0.3 for i in range(rows)], index=index)
    low = close - pd.Series([1.5 + (i % 4) * 0.2 for i in range(rows)], index=index)
    open_ = close - 0.25
    volume = pd.Series([10_000 + i * 11 for i in range(rows)], index=index)
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "volume": volume})


def assert_series_equal_exact(actual: pd.Series, expected: pd.Series) -> None:
    pd.testing.assert_series_equal(actual, expected, check_names=False, rtol=0, atol=0)


class IndicatorTests(unittest.TestCase):
    def test_moving_averages_match_rolling_means_for_default_windows(self) -> None:
        df = deterministic_ohlc()

        result = add_moving_averages(df)

        for window in (5, 20, 60, 120):
            expected = df["close"].rolling(window=window, min_periods=window).mean()
            assert_series_equal_exact(result[f"ma{window}"], expected)
            self.assertEqual(result[f"ma{window}"].iloc[window - 2 : window].isna().tolist(), [True, False])

    def test_bollinger_bands_match_rolling_mean_std_and_safe_ratios(self) -> None:
        df = deterministic_ohlc()

        result = add_bollinger_bands(df)

        mid = df["close"].rolling(window=20, min_periods=20).mean()
        std = df["close"].rolling(window=20, min_periods=20).std()
        upper = mid + (std * 2.0)
        lower = mid - (std * 2.0)
        width = std * 4.0

        assert_series_equal_exact(result["bb_mid"], mid)
        assert_series_equal_exact(result["bb_upper"], upper)
        assert_series_equal_exact(result["bb_lower"], lower)
        pd.testing.assert_series_equal(result["bb_bandwidth"], width / mid, check_names=False)
        pd.testing.assert_series_equal(result["bb_percent_b"], (df["close"] - lower) / width, check_names=False)

        flat = pd.DataFrame({"close": [10.0] * 25})
        flat_result = add_bollinger_bands(flat)
        self.assertTrue(math.isnan(flat_result["bb_percent_b"].iloc[-1]))

    def test_rsi_and_signal_match_wilder_ewm_formula(self) -> None:
        df = deterministic_ohlc()

        result = add_rsi(df)

        delta = df["close"].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
        avg_loss = loss.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
        rs = avg_gain / avg_loss.where(avg_loss != 0)
        rsi = 100 - (100 / (1 + rs))
        rsi = rsi.mask((avg_loss == 0) & (avg_gain > 0), 100.0)
        rsi = rsi.mask((avg_loss == 0) & (avg_gain == 0), 50.0)
        rsi = rsi.mask((avg_gain == 0) & (avg_loss > 0), 0.0)
        rsi_signal = rsi.rolling(window=9, min_periods=9).mean()

        pd.testing.assert_series_equal(result["rsi"], rsi, check_names=False)
        pd.testing.assert_series_equal(result["rsi_signal"], rsi_signal, check_names=False)

        rising = pd.DataFrame({"close": range(1, 30)})
        self.assertEqual(add_rsi(rising)["rsi"].iloc[-1], 100.0)

        flat = pd.DataFrame({"close": [7.0] * 30})
        self.assertEqual(add_rsi(flat)["rsi"].iloc[-1], 50.0)

    def test_ichimoku_lines_match_lookback_and_shift_rules(self) -> None:
        df = deterministic_ohlc()

        result = add_ichimoku(df)

        high_9 = df["high"].rolling(window=9, min_periods=9).max()
        low_9 = df["low"].rolling(window=9, min_periods=9).min()
        high_26 = df["high"].rolling(window=26, min_periods=26).max()
        low_26 = df["low"].rolling(window=26, min_periods=26).min()
        high_52 = df["high"].rolling(window=52, min_periods=52).max()
        low_52 = df["low"].rolling(window=52, min_periods=52).min()

        tenkan = (high_9 + low_9) / 2
        kijun = (high_26 + low_26) / 2
        senkou_a = ((tenkan + kijun) / 2).shift(26)
        senkou_b = ((high_52 + low_52) / 2).shift(26)
        chikou = df["close"].shift(-26)

        assert_series_equal_exact(result["tenkan"], tenkan)
        assert_series_equal_exact(result["kijun"], kijun)
        assert_series_equal_exact(result["senkou_a"], senkou_a)
        assert_series_equal_exact(result["senkou_b"], senkou_b)
        assert_series_equal_exact(result["chikou"], chikou)

    def test_add_all_indicators_preserves_source_columns_and_adds_expected_outputs(self) -> None:
        df = deterministic_ohlc()
        original = df.copy(deep=True)

        result = add_all_indicators(df)

        expected_columns = {
            "open",
            "high",
            "low",
            "close",
            "volume",
            "ma5",
            "ma20",
            "ma60",
            "ma120",
            "bb_mid",
            "bb_upper",
            "bb_lower",
            "bb_bandwidth",
            "bb_percent_b",
            "rsi",
            "rsi_signal",
            "tenkan",
            "kijun",
            "senkou_a",
            "senkou_b",
            "chikou",
        }
        self.assertTrue(expected_columns.issubset(result.columns))
        pd.testing.assert_frame_equal(df, original)

    def test_indicator_functions_raise_clear_error_for_missing_columns(self) -> None:
        with self.assertRaisesRegex(ValueError, "close"):
            add_moving_averages(pd.DataFrame({"high": [1.0]}))

        with self.assertRaisesRegex(ValueError, "high"):
            add_ichimoku(pd.DataFrame({"close": [1.0], "low": [1.0]}))


if __name__ == "__main__":
    unittest.main()
