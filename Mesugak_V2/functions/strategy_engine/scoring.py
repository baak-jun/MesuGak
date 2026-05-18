"""Confidence scoring for Mesugak V2."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

SCORING_WEIGHTS = {
    "bollinger": 0.30,
    "maSupport": 0.20,
    "ichimoku": 0.15,
    "rsi": 0.10,
    "valuation": 0.25,
}

NEUTRAL_VALUATION_SCORE = 50.0


@dataclass(frozen=True)
class ScoreResult:
    confidence_score: float
    confidence_label: str
    component_scores: dict[str, float]
    reasons: list[str]
    indicator_states: dict[str, Any] | None = None


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def _num(row: dict[str, Any], key: str, default: float = 0.0) -> float:
    value = row.get(key, default)
    if value is None or pd.isna(value):
        return default
    return float(value)


def _series_num(df: pd.DataFrame, key: str) -> pd.Series:
    if key not in df.columns:
        return pd.Series(dtype="float64")
    return pd.to_numeric(df[key], errors="coerce").dropna()


def classify_bollinger_state(df: pd.DataFrame, lookback: int = 125) -> dict[str, Any]:
    if df.empty:
        return {"state": "NO_DATA", "score": 0.0, "reasons": ["no_data"]}

    last = df.iloc[-1].to_dict()
    prev = df.iloc[-2].to_dict() if len(df) >= 2 else last
    prev2 = df.iloc[-3].to_dict() if len(df) >= 3 else prev
    close = _num(last, "close")
    upper = _num(last, "bb_upper")
    lower = _num(last, "bb_lower")
    mid = _num(last, "bb_mid")
    bandwidth = _num(last, "bb_bandwidth")
    prev_bandwidth = _num(prev, "bb_bandwidth")
    prev2_bandwidth = _num(prev2, "bb_bandwidth")
    percent_b = _num(last, "bb_percent_b")

    recent_bandwidth = _series_num(df.tail(lookback), "bb_bandwidth")
    if recent_bandwidth.empty or bandwidth <= 0:
        return {"state": "NO_DATA", "score": 0.0, "reasons": ["bollinger_no_data"]}

    min_bandwidth = float(recent_bandwidth.min())
    max_bandwidth = float(recent_bandwidth.max())
    bandwidth_range = max(max_bandwidth - min_bandwidth, 0.0)
    percent_bandwidth = (bandwidth - min_bandwidth) / bandwidth_range if bandwidth_range > 0 else 0.0
    squeeze_threshold = min_bandwidth * 1.05
    high_threshold = float(recent_bandwidth.quantile(0.70))
    bandwidth_rank = float((recent_bandwidth <= bandwidth).mean())
    recent_squeeze = bool((_series_num(df.tail(15), "bb_bandwidth") <= squeeze_threshold).any())
    is_squeezed = bandwidth <= squeeze_threshold
    expanding = bandwidth > prev_bandwidth and prev_bandwidth >= prev2_bandwidth
    upper_slope = upper - _num(prev, "bb_upper")
    mid_slope = mid - _num(prev, "bb_mid")
    lower_slope = lower - _num(prev, "bb_lower")
    upper_breakout = upper > 0 and close > upper
    downside_breakdown = lower > 0 and close < lower
    was_recent_upper_breakout = False
    if "close" in df.columns and "bb_upper" in df.columns and len(df) >= 6:
        recent = df.tail(6).iloc[:-1]
        was_recent_upper_breakout = bool((pd.to_numeric(recent["close"], errors="coerce") > pd.to_numeric(recent["bb_upper"], errors="coerce")).any())

    reasons: list[str] = []
    state = "NEUTRAL"
    score = 40.0

    if downside_breakdown and bandwidth > prev_bandwidth:
        state = "DOWNSIDE_EXPANSION"
        score = 5.0
        reasons.extend(["below_lower_band", "downside_band_expansion"])
    elif was_recent_upper_breakout and close < upper and percent_b < 0.75:
        state = "FAILED_RELEASE"
        score = 25.0
        reasons.extend(["failed_upper_band_release", "back_inside_band"])
    elif recent_squeeze and expanding and (upper_breakout or percent_b >= 1.0) and close >= mid:
        state = "SQUEEZE_RELEASE_UP"
        score = 92.0 if upper_breakout else 84.0
        reasons.extend(["recent_squeeze", "bandwidth_expanding", "upper_band_release"])
    elif is_squeezed:
        state = "SQUEEZE"
        score = 52.0
        reasons.extend(["bandwidth_low_percentile", "volatility_compression"])
    elif bandwidth >= high_threshold and (bandwidth <= prev_bandwidth or upper_slope <= 0 or percent_b < 0.70):
        state = "EXPANSION_CURL_NEUTRAL"
        score = 48.0
        reasons.extend(["expanded_band_curling", "neutral_after_expansion"])
    elif percent_b >= 0.80 and upper_slope > 0 and mid_slope >= 0 and close >= mid:
        state = "BAND_RIDE_UP"
        score = 76.0
        reasons.extend(["upper_band_ride", "middle_band_rising"])
    elif 0.50 <= percent_b < 0.80 and mid_slope >= 0:
        state = "HEALTHY_MID_UP"
        score = 64.0
        reasons.extend(["above_middle_band", "middle_band_rising"])

    if lower_slope > 0 and close >= mid and state in {"SQUEEZE_RELEASE_UP", "BAND_RIDE_UP", "HEALTHY_MID_UP"}:
        score += 3.0
        reasons.append("lower_band_support_rising")

    return {
        "state": state,
        "score": round(_clamp(score), 2),
        "reasons": reasons,
        "bandwidth": round(bandwidth, 6),
        "bandwidthRank": round(bandwidth_rank, 4),
        "percentBandwidth": round(percent_bandwidth, 4),
        "squeezeThreshold": round(squeeze_threshold, 6),
        "percentB": round(percent_b, 4),
        "expanding": expanding,
    }


def classify_ma_support_state(df: pd.DataFrame, lookback: int = 60) -> dict[str, Any]:
    if df.empty:
        return {"state": "NO_DATA", "score": 0.0, "reasons": ["no_data"]}

    last = df.iloc[-1].to_dict()
    prev = df.iloc[-2].to_dict() if len(df) >= 2 else last
    close = _num(last, "close")
    prev_close = _num(prev, "close")
    low = _num(last, "low", close)
    open_price = _num(last, "open", close)
    ma20 = _num(last, "ma20")
    ma60 = _num(last, "ma60")
    prev_ma20 = _num(prev, "ma20")
    prev_ma60 = _num(prev, "ma60")

    if ma20 <= 0 or ma60 <= 0:
        return {"state": "NO_DATA", "score": 0.0, "reasons": ["ma_no_data"]}

    ma20_rising = ma20 > prev_ma20
    ma60_rising = ma60 > prev_ma60
    broke_down_20 = prev_close >= prev_ma20 and close < ma20
    broke_down_60 = prev_close >= prev_ma60 and close < ma60
    broke_up_20 = prev_close < prev_ma20 and close >= ma20 and ma20_rising
    broke_up_60 = prev_close < prev_ma60 and close >= ma60 and ma60_rising
    bounce_20 = low <= ma20 * 1.015 and close > ma20 and close >= open_price and ma20_rising
    bounce_60 = low <= ma60 * 1.02 and close > ma60 and close >= open_price and ma60_rising

    ma60_series = _series_num(df.tail(lookback), "ma60")
    close_series = _series_num(df.tail(lookback), "close")
    aligned = pd.concat([close_series, ma60_series], axis=1, join="inner").dropna()
    above_ma60_ratio = float((aligned.iloc[:, 0] >= aligned.iloc[:, 1]).mean()) if not aligned.empty else 0.0

    reasons: list[str] = []
    state = "NEUTRAL"
    score = 35.0

    if broke_down_60:
        state = "MA60_BREAKDOWN"
        score = 0.0
        reasons.append("broke_below_ma60")
    elif broke_down_20:
        state = "MA20_BREAKDOWN"
        score = 12.0 if close >= ma60 else 0.0
        reasons.append("broke_below_ma20")
    elif broke_up_60:
        state = "MA60_BREAKOUT"
        score = 88.0
        reasons.append("reclaimed_ma60")
    elif bounce_60:
        state = "MA60_SUPPORT_BOUNCE"
        score = 84.0
        reasons.append("bounced_from_ma60_support")
    elif broke_up_20:
        state = "MA20_BREAKOUT"
        score = 76.0
        reasons.append("reclaimed_ma20")
    elif bounce_20 and close >= ma60:
        state = "MA20_SUPPORT_BOUNCE"
        score = 72.0
        reasons.append("bounced_from_ma20_support")
    elif above_ma60_ratio >= 0.80 and close >= ma60 and ma60_rising:
        state = "SUSTAINED_ABOVE_MA60"
        score = 70.0
        reasons.append("sustained_above_ma60_quality")
    elif close >= ma20 and close >= ma60 and ma20_rising:
        state = "ABOVE_RISING_SUPPORT"
        score = 62.0
        reasons.append("above_ma20_ma60")

    if ma20 > ma60 and state not in {"MA60_BREAKDOWN", "MA20_BREAKDOWN"}:
        score += 6.0
        reasons.append("ma20_above_ma60")

    return {
        "state": state,
        "score": round(_clamp(score), 2),
        "reasons": reasons,
        "aboveMa60Ratio": round(above_ma60_ratio, 4),
        "ma20Rising": ma20_rising,
        "ma60Rising": ma60_rising,
    }


def score_valuation(fundamentals: dict[str, Any] | None = None) -> dict[str, Any]:
    data = fundamentals or {}
    per = data.get("per")
    pbr = data.get("pbr")
    if per is None and pbr is None:
        return {
            "state": "NO_DATA",
            "score": NEUTRAL_VALUATION_SCORE,
            "reasons": ["valuation_data_missing_neutral"],
        }
    return {
        "state": "UNIMPLEMENTED",
        "score": NEUTRAL_VALUATION_SCORE,
        "reasons": ["valuation_model_pending"],
    }


def score_latest(df: pd.DataFrame, fundamentals: dict[str, Any] | None = None) -> ScoreResult:
    if df.empty:
        return ScoreResult(0.0, "NO_DATA", {}, ["no_data"], {"bollinger": {"state": "NO_DATA"}})

    last: dict[str, Any] = df.iloc[-1].to_dict()
    prev: dict[str, Any] = df.iloc[-2].to_dict() if len(df) >= 2 else last
    close = _num(last, "close")
    reasons: list[str] = []

    ichimoku = 0.0
    cloud_top = max(_num(last, "senkou_a"), _num(last, "senkou_b"))
    if cloud_top > 0 and close > cloud_top:
        ichimoku += 45
        reasons.append("price_above_cloud")
    if _num(last, "tenkan") > _num(last, "kijun"):
        ichimoku += 35
        reasons.append("tenkan_above_kijun")
    if _num(last, "senkou_a") > _num(last, "senkou_b"):
        ichimoku += 20
        reasons.append("bullish_cloud")

    ma_state = classify_ma_support_state(df)
    ma_support = float(ma_state.get("score", 0.0))
    reasons.append(f"ma_state_{ma_state.get('state', 'UNKNOWN').lower()}")
    reasons.extend([f"ma_{reason}" for reason in ma_state.get("reasons", [])])

    bollinger_state = classify_bollinger_state(df)
    bollinger = float(bollinger_state.get("score", 0.0))
    reasons.append(f"bollinger_state_{bollinger_state.get('state', 'UNKNOWN').lower()}")
    reasons.extend([f"bollinger_{reason}" for reason in bollinger_state.get("reasons", [])])

    rsi_score = 0.0
    rsi = _num(last, "rsi")
    prev_rsi = _num(prev, "rsi")
    if 45 <= rsi <= 65:
        rsi_score += 65
        reasons.append("rsi_momentum_zone")
    elif 35 <= rsi < 45:
        rsi_score += 35
        reasons.append("rsi_recovery_zone")
    if rsi > prev_rsi:
        rsi_score += 35
        reasons.append("rsi_rising")

    penalty = 0.0
    if close < _num(last, "bb_lower"):
        penalty += 15
        reasons.append("penalty_below_lower_band")
    if rsi >= 75:
        penalty += 10
        reasons.append("penalty_rsi_overheated")

    valuation_state = score_valuation(fundamentals)
    valuation = float(valuation_state.get("score", NEUTRAL_VALUATION_SCORE))
    reasons.append(f"valuation_state_{valuation_state.get('state', 'UNKNOWN').lower()}")
    reasons.extend([f"valuation_{reason}" for reason in valuation_state.get("reasons", [])])

    component_scores = {
        "ichimoku": _clamp(ichimoku),
        "maSupport": _clamp(ma_support),
        "bollinger": _clamp(bollinger),
        "rsi": _clamp(rsi_score),
        "valuation": _clamp(valuation),
        "penalty": _clamp(penalty),
    }
    confidence = (
        component_scores["bollinger"] * SCORING_WEIGHTS["bollinger"]
        + component_scores["maSupport"] * SCORING_WEIGHTS["maSupport"]
        + component_scores["ichimoku"] * SCORING_WEIGHTS["ichimoku"]
        + component_scores["rsi"] * SCORING_WEIGHTS["rsi"]
        + component_scores["valuation"] * SCORING_WEIGHTS["valuation"]
        - component_scores["penalty"]
    )
    confidence = round(_clamp(confidence), 2)

    bollinger_name = str(bollinger_state.get("state", "UNKNOWN"))
    high_quality_setup = (
        bollinger_name in {"SQUEEZE_RELEASE_UP", "BAND_RIDE_UP"}
        and component_scores["ichimoku"] >= 75
        and component_scores["maSupport"] >= 70
        and 45 <= rsi <= 72
        and component_scores["penalty"] == 0
    )
    clean_buy_setup = (
        bollinger_name not in {"FAILED_RELEASE", "DOWNSIDE_EXPANSION", "EXPANSION_CURL_NEUTRAL", "NO_DATA"}
        and component_scores["ichimoku"] >= 55
        and component_scores["maSupport"] >= 55
        and component_scores["penalty"] < 15
    )

    valuation_has_data = valuation_state.get("state") not in {"NO_DATA", "UNIMPLEMENTED"}
    strong_threshold = 88.0 if valuation_has_data else 78.0
    buy_threshold = 70.0 if valuation_has_data else 62.0

    if confidence >= strong_threshold and high_quality_setup:
        label = "STRONG_BUY"
    elif confidence >= buy_threshold and clean_buy_setup:
        label = "BUY_CANDIDATE"
    elif confidence >= 45:
        label = "WATCH"
    else:
        label = "AVOID"

    return ScoreResult(
        confidence,
        label,
        component_scores,
        reasons,
        {"bollinger": bollinger_state, "maSupport": ma_state, "valuation": valuation_state},
    )
