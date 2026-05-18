"""Pure indicator calculations for Mesugak V2."""

from __future__ import annotations

import numpy as np
import pandas as pd


def _validated_numeric_copy(df: pd.DataFrame, required_columns: tuple[str, ...]) -> pd.DataFrame:
    missing = [column for column in required_columns if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required OHLC columns: {', '.join(missing)}")

    out = df.copy()
    for column in required_columns:
        out[column] = pd.to_numeric(out[column], errors="coerce")
    return out


def _safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    return numerator.div(denominator.where(denominator != 0))


def add_moving_averages(df: pd.DataFrame, windows: tuple[int, ...] = (5, 20, 60, 120)) -> pd.DataFrame:
    out = _validated_numeric_copy(df, ("close",))
    for window in windows:
        if window <= 0:
            raise ValueError("Moving average windows must be positive integers")
        out[f"ma{window}"] = out["close"].rolling(window=window, min_periods=window).mean()
    return out


def add_bollinger_bands(df: pd.DataFrame, window: int = 20, deviations: float = 2.0) -> pd.DataFrame:
    if window <= 0:
        raise ValueError("Bollinger window must be a positive integer")

    out = _validated_numeric_copy(df, ("close",))
    mid = out["close"].rolling(window=window, min_periods=window).mean()
    std = out["close"].rolling(window=window, min_periods=window).std()
    width = std * deviations * 2
    out["bb_mid"] = mid
    out["bb_upper"] = mid + (std * deviations)
    out["bb_lower"] = mid - (std * deviations)
    out["bb_bandwidth"] = _safe_divide(width, mid)
    out["bb_percent_b"] = _safe_divide(out["close"] - out["bb_lower"], width)
    return out


def add_rsi(df: pd.DataFrame, period: int = 14, signal_period: int = 9) -> pd.DataFrame:
    if period <= 0:
        raise ValueError("RSI period must be a positive integer")
    if signal_period <= 0:
        raise ValueError("RSI signal period must be a positive integer")

    out = _validated_numeric_copy(df, ("close",))
    delta = out["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = _safe_divide(avg_gain, avg_loss)
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.mask((avg_loss == 0) & (avg_gain > 0), 100.0)
    rsi = rsi.mask((avg_loss == 0) & (avg_gain == 0), 50.0)
    rsi = rsi.mask((avg_gain == 0) & (avg_loss > 0), 0.0)
    out["rsi"] = rsi.replace([np.inf, -np.inf], np.nan)
    out["rsi_signal"] = out["rsi"].rolling(window=signal_period, min_periods=signal_period).mean()
    return out


def add_ichimoku(df: pd.DataFrame) -> pd.DataFrame:
    out = _validated_numeric_copy(df, ("high", "low", "close"))
    high_9 = out["high"].rolling(window=9, min_periods=9).max()
    low_9 = out["low"].rolling(window=9, min_periods=9).min()
    high_26 = out["high"].rolling(window=26, min_periods=26).max()
    low_26 = out["low"].rolling(window=26, min_periods=26).min()
    high_52 = out["high"].rolling(window=52, min_periods=52).max()
    low_52 = out["low"].rolling(window=52, min_periods=52).min()

    out["tenkan"] = (high_9 + low_9) / 2
    out["kijun"] = (high_26 + low_26) / 2
    out["senkou_a"] = ((out["tenkan"] + out["kijun"]) / 2).shift(26)
    out["senkou_b"] = ((high_52 + low_52) / 2).shift(26)
    out["chikou"] = out["close"].shift(-26)
    return out


def add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = add_moving_averages(df)
    out = add_bollinger_bands(out)
    out = add_rsi(out)
    out = add_ichimoku(out)
    return out
