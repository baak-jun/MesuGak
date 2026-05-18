"""Risk state and stop-loss rules for Mesugak V2."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class RiskResult:
    risk_state: str
    cash_target_pct: float
    stop_loss: float | None
    risk_flags: list[str]


def _num(row, key: str, default: float = 0.0) -> float:
    value = row.get(key, default)
    if value is None or pd.isna(value):
        return default
    return float(value)


def evaluate_risk(df: pd.DataFrame) -> RiskResult:
    if df.empty:
        return RiskResult("NO_DATA", 1.0, None, ["no_data"])

    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) >= 2 else last
    close = _num(last, "close")
    flags: list[str] = []
    cash_target = 0.1

    bb_lower = _num(last, "bb_lower")
    if bb_lower > 0 and close < bb_lower:
        flags.append("below_bollinger_lower")
        cash_target += 0.25

    bandwidth = _num(last, "bb_bandwidth")
    prev_bandwidth = _num(prev, "bb_bandwidth")
    ma20 = _num(last, "ma20")
    prev_ma20 = _num(prev, "ma20")
    if bandwidth > prev_bandwidth and ma20 < prev_ma20:
        flags.append("downside_band_expansion")
        cash_target += 0.25

    rsi = _num(last, "rsi")
    if rsi and rsi < 40:
        flags.append("rsi_breakdown")
        cash_target += 0.15

    cloud_bottom = min(_num(last, "senkou_a"), _num(last, "senkou_b"))
    if cloud_bottom > 0 and close < cloud_bottom:
        flags.append("below_ichimoku_cloud")
        cash_target += 0.15

    recent_high = df["high"].tail(20).max() if "high" in df.columns and len(df) >= 20 else None
    if recent_high is not None and not pd.isna(recent_high):
        failed_breakout_level = float(recent_high) * 0.985
        if close < failed_breakout_level and _num(prev, "close") >= failed_breakout_level:
            flags.append("failed_box_breakout")
            cash_target += 0.15

    support_candidates = [
        _num(last, "ma20"),
        _num(last, "ma60"),
        _num(last, "kijun"),
        bb_lower,
    ]
    support = max([value for value in support_candidates if value > 0 and value < close], default=0)
    stop_loss = round(support * 0.985, 2) if support > 0 else None

    if cash_target >= 0.55:
        state = "DEFENSIVE"
    elif flags:
        state = "CAUTION"
    else:
        state = "NORMAL"

    return RiskResult(state, min(round(cash_target, 2), 1.0), stop_loss, flags)
