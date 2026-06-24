"""Confidence scoring for Mesugak V2."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

SCORING_WEIGHTS = {
    "bollinger": 0.25,
    "maSupport": 0.20,
    "ichimoku": 0.20,
    "rsi": 0.10,
    "valuation": 0.15,
    "volume": 0.10,
}


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


def classify_bollinger_state(df: pd.DataFrame, lookback: int = 25) -> dict[str, Any]:
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
    score = 0.0

    if downside_breakdown and bandwidth > prev_bandwidth:
        state = "DOWNSIDE_EXPANSION"
        score = -45.0
        reasons.extend(["below_lower_band", "downside_band_expansion"])
    elif was_recent_upper_breakout and close < upper and percent_b < 0.75:
        state = "FAILED_RELEASE"
        score = -25.0
        reasons.extend(["failed_upper_band_release", "back_inside_band"])
    elif recent_squeeze and expanding and upper_breakout and close >= mid:
        state = "SQUEEZE_RELEASE_UP"
        score = 90.0
        reasons.extend(["recent_squeeze", "bandwidth_expanding", "upper_band_release"])
    elif is_squeezed:
        state = "SQUEEZE"
        score = 35.0
        reasons.extend(["bandwidth_low_percentile", "volatility_compression"])
    elif bandwidth >= high_threshold and (bandwidth <= prev_bandwidth or upper_slope <= 0 or percent_b < 0.70):
        state = "EXPANSION_CURL_NEUTRAL"
        reasons.extend(["expanded_band_curling", "no_bollinger_signal"])

    return {
        "state": state,
        "score": round(_clamp(score, -100.0, 100.0), 2),
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
    bb_lower = _num(last, "bb_lower")
    prev_bb_lower = _num(prev, "bb_lower")
    ma60 = _num(last, "ma60")
    prev_ma20 = _num(prev, "ma20")
    prev_ma60 = _num(prev, "ma60")

    if bb_lower <= 0 or ma60 <= 0:
        return {"state": "NO_DATA", "score": 0.0, "reasons": ["ma_no_data"]}

    ma60_rising = ma60 > prev_ma60
    lower_above_ma60 = bb_lower > ma60
    crossed_above_ma60 = prev_bb_lower <= prev_ma60 and lower_above_ma60
    crossed_below_ma60 = prev_bb_lower >= prev_ma60 and bb_lower < ma60

    reasons: list[str] = []
    state = "NEUTRAL"
    score = 0.0

    if crossed_above_ma60:
        state = "LOWER_BAND_CROSS_ABOVE_MA60"
        score = 90.0
        reasons.append("bollinger_lower_crossed_above_ma60")
    elif lower_above_ma60:
        state = "LOWER_BAND_ABOVE_MA60"
        score = 70.0
        reasons.append("bollinger_lower_above_ma60")
    elif crossed_below_ma60:
        state = "LOWER_BAND_CROSS_BELOW_MA60"
        score = -35.0
        reasons.append("bollinger_lower_crossed_below_ma60")

    return {
        "state": state,
        "score": round(_clamp(score, -100.0, 100.0), 2),
        "reasons": reasons,
        "lowerBandAboveMa60": lower_above_ma60,
        "ma60Rising": ma60_rising,
    }


def score_valuation(fundamentals: dict[str, Any] | None = None) -> dict[str, Any]:
    data = fundamentals or {}
    per = _num(data, "per", float("nan"))
    pbr = _num(data, "pbr", float("nan"))
    roe = _num(data, "roe", float("nan"))
    debt_ratio = _num(data, "debtRatio", float("nan"))
    operating_profit_growth = _num(data, "operatingProfitGrowth", float("nan"))
    if all(pd.isna(value) for value in (per, pbr, roe, debt_ratio, operating_profit_growth)):
        return {
            "state": "NO_DATA",
            "score": 0.0,
            "reasons": ["valuation_data_missing"],
        }

    score = 0.0
    reasons: list[str] = []
    if not pd.isna(per):
        if per <= 0:
            score -= 35
            reasons.append("negative_or_zero_earnings")
        elif per <= 10:
            score += 25
            reasons.append("low_per")
        elif per <= 20:
            score += 15
            reasons.append("reasonable_per")
        elif per <= 35:
            score += 5
            reasons.append("elevated_but_positive_per")
        elif per > 50:
            score -= 15
            reasons.append("high_per")
    if not pd.isna(pbr):
        if 0 < pbr <= 1.5:
            score += 15
            reasons.append("low_pbr")
        elif pbr <= 3:
            score += 7
            reasons.append("reasonable_pbr")
        elif pbr > 5:
            score -= 10
            reasons.append("high_pbr")
    if not pd.isna(roe):
        if roe >= 15:
            score += 25
            reasons.append("high_roe")
        elif roe >= 8:
            score += 12
            reasons.append("positive_roe")
        elif roe < 0:
            score -= 25
            reasons.append("negative_roe")
    if not pd.isna(debt_ratio):
        if debt_ratio <= 100:
            score += 10
            reasons.append("manageable_debt")
        elif debt_ratio > 200:
            score -= 15
            reasons.append("high_debt")
    if not pd.isna(operating_profit_growth):
        if operating_profit_growth >= 10:
            score += 10
            reasons.append("operating_profit_growing")
        elif operating_profit_growth <= -10:
            score -= 10
            reasons.append("operating_profit_shrinking")
    return {
        "state": "VALUED",
        "score": round(_clamp(score, -100.0, 100.0), 2),
        "reasons": reasons,
    }


def classify_ichimoku_state(df: pd.DataFrame) -> dict[str, Any]:
    if len(df) < 27:
        return {"state": "NO_DATA", "score": 0.0, "reasons": ["ichimoku_no_data"]}
    last, prev = df.iloc[-1].to_dict(), df.iloc[-2].to_dict()
    close = _num(last, "close")
    cloud_top = max(_num(last, "senkou_a"), _num(last, "senkou_b"))
    cloud_bottom = min(_num(last, "senkou_a"), _num(last, "senkou_b"))
    leading_a, leading_b = _num(last, "senkou_a_leading"), _num(last, "senkou_b_leading")
    past_close = _num(df.iloc[-27].to_dict(), "close")
    if cloud_top <= 0 or leading_a <= 0 or past_close <= 0:
        return {"state": "NO_DATA", "score": 0.0, "reasons": ["ichimoku_no_data"]}
    score, reasons = 0.0, []
    if close > cloud_top:
        score += 35; reasons.append("price_above_cloud")
    elif close < cloud_bottom:
        score -= 35; reasons.append("price_below_cloud")
    if _num(last, "tenkan") > _num(last, "kijun"):
        score += 25; reasons.append("tenkan_above_kijun")
    elif _num(last, "tenkan") < _num(last, "kijun"):
        score -= 25; reasons.append("tenkan_below_kijun")
    if leading_a > leading_b:
        score += 15; reasons.append("bullish_forward_cloud")
    elif leading_a < leading_b:
        score -= 15; reasons.append("bearish_forward_cloud")
    if close > past_close:
        score += 15; reasons.append("chikou_confirmed")
    elif close < past_close:
        score -= 15; reasons.append("chikou_below_past_price")
    return {"state": "BULLISH" if score > 0 else "BEARISH" if score < 0 else "NEUTRAL", "score": _clamp(score, -100, 100), "reasons": reasons}


def classify_rsi_state(df: pd.DataFrame) -> dict[str, Any]:
    if len(df) < 3:
        return {"state": "NO_DATA", "score": 0.0, "reasons": ["rsi_no_data"]}
    last, prev = df.iloc[-1].to_dict(), df.iloc[-2].to_dict()
    rsi, prev_rsi, signal = _num(last, "rsi"), _num(prev, "rsi"), _num(last, "rsi_signal")
    if rsi <= 0 or signal <= 0:
        return {"state": "NO_DATA", "score": 0.0, "reasons": ["rsi_no_data"]}
    score, reasons = 0.0, []
    if prev_rsi < 50 <= rsi and rsi > signal:
        score += 55; reasons.append("rsi_crossed_above_50_with_signal")
    elif prev_rsi <= 30 < rsi and rsi > signal:
        score += 35; reasons.append("rsi_oversold_recovery")
    if rsi < 45 and rsi < signal and rsi < prev_rsi:
        score -= 35; reasons.append("rsi_breakdown")
    if len(df) >= 30:
        recent = df.tail(10)
        earlier = df.iloc[-30:-10]
        if _num(last, "close") >= _series_num(recent, "close").max() * 0.98 and rsi < _series_num(earlier, "rsi").max() - 5:
            score -= 30; reasons.append("bearish_rsi_divergence")
    return {"state": "BULLISH" if score > 0 else "BEARISH" if score < 0 else "NEUTRAL", "score": _clamp(score, -100, 100), "reasons": reasons}


def classify_volume_state(df: pd.DataFrame, bollinger_state: dict[str, Any]) -> dict[str, Any]:
    if len(df) < 21:
        return {"state": "NO_DATA", "score": 0.0, "reasons": ["volume_no_data"]}
    last = df.iloc[-1].to_dict()
    relative_volume = _num(last, "relative_volume")
    prior_high = _series_num(df.iloc[-21:-1], "high").max()
    close = _num(last, "close")
    if relative_volume <= 0 or pd.isna(prior_high):
        return {"state": "NO_DATA", "score": 0.0, "reasons": ["volume_no_data"]}
    if close > prior_high and relative_volume >= 1.5:
        return {"state": "BREAKOUT_CONFIRMED", "score": 55.0, "reasons": ["price_breakout_with_relative_volume"]}
    if bollinger_state.get("state") == "SQUEEZE_RELEASE_UP" and relative_volume < 1.0:
        return {"state": "SQUEEZE_RELEASE_WEAK_VOLUME", "score": -20.0, "reasons": ["squeeze_release_lacks_volume"]}
    return {"state": "NEUTRAL", "score": 0.0, "reasons": ["no_volume_setup"], "relativeVolume": round(relative_volume, 4)}


def score_latest(df: pd.DataFrame, fundamentals: dict[str, Any] | None = None) -> ScoreResult:
    if df.empty:
        return ScoreResult(0.0, "NO_DATA", {}, ["no_data"], {"bollinger": {"state": "NO_DATA"}})

    last: dict[str, Any] = df.iloc[-1].to_dict()
    prev: dict[str, Any] = df.iloc[-2].to_dict() if len(df) >= 2 else last
    close = _num(last, "close")
    reasons: list[str] = []

    ichimoku_state = classify_ichimoku_state(df)
    ichimoku = float(ichimoku_state["score"])
    reasons.extend([f"ichimoku_{reason}" for reason in ichimoku_state["reasons"]])

    ma_state = classify_ma_support_state(df)
    ma_support = float(ma_state.get("score", 0.0))
    reasons.append(f"ma_state_{ma_state.get('state', 'UNKNOWN').lower()}")
    reasons.extend([f"ma_{reason}" for reason in ma_state.get("reasons", [])])

    bollinger_state = classify_bollinger_state(df)
    bollinger = float(bollinger_state.get("score", 0.0))
    reasons.append(f"bollinger_state_{bollinger_state.get('state', 'UNKNOWN').lower()}")
    reasons.extend([f"bollinger_{reason}" for reason in bollinger_state.get("reasons", [])])

    rsi_state = classify_rsi_state(df)
    rsi_score = float(rsi_state["score"])
    reasons.extend([f"rsi_{reason}" for reason in rsi_state["reasons"]])
    volume_state = classify_volume_state(df, bollinger_state)
    volume_score = float(volume_state["score"])
    reasons.extend([f"volume_{reason}" for reason in volume_state["reasons"]])

    penalty = 0.0
    if close < _num(last, "bb_lower"):
        penalty += 15
        reasons.append("penalty_below_lower_band")

    valuation_state = score_valuation(fundamentals)
    valuation = float(valuation_state.get("score", 0.0))
    reasons.append(f"valuation_state_{valuation_state.get('state', 'UNKNOWN').lower()}")
    reasons.extend([f"valuation_{reason}" for reason in valuation_state.get("reasons", [])])

    component_scores = {
        "ichimoku": _clamp(ichimoku, -100.0, 100.0),
        "maSupport": _clamp(ma_support, -100.0, 100.0),
        "bollinger": _clamp(bollinger, -100.0, 100.0),
        "rsi": _clamp(rsi_score, -100.0, 100.0),
        "valuation": _clamp(valuation, -100.0, 100.0),
        "volume": _clamp(volume_score, -100.0, 100.0),
        "penalty": _clamp(penalty),
    }
    confidence = (
        component_scores["bollinger"] * SCORING_WEIGHTS["bollinger"]
        + component_scores["maSupport"] * SCORING_WEIGHTS["maSupport"]
        + component_scores["ichimoku"] * SCORING_WEIGHTS["ichimoku"]
        + component_scores["rsi"] * SCORING_WEIGHTS["rsi"]
        + component_scores["valuation"] * SCORING_WEIGHTS["valuation"]
        + component_scores["volume"] * SCORING_WEIGHTS["volume"]
        - component_scores["penalty"]
    )
    confidence = round(_clamp(confidence), 2)

    bollinger_name = str(bollinger_state.get("state", "UNKNOWN"))
    high_quality_setup = (
        bollinger_name == "SQUEEZE_RELEASE_UP"
        and component_scores["ichimoku"] >= 75
        and component_scores["maSupport"] >= 70
        and component_scores["rsi"] > 0
        and component_scores["volume"] > 0
        and component_scores["penalty"] == 0
    )
    clean_buy_setup = (
        bollinger_name in {"SQUEEZE", "SQUEEZE_RELEASE_UP"}
        and component_scores["ichimoku"] > 0
        and component_scores["maSupport"] >= 55
        and component_scores["penalty"] < 15
    )

    valuation_has_data = valuation_state.get("state") == "VALUED"
    strong_threshold = 78.0 if valuation_has_data else 68.0
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
        {"bollinger": bollinger_state, "maSupport": ma_state, "ichimoku": ichimoku_state, "rsi": rsi_state, "volume": volume_state, "valuation": valuation_state},
    )
