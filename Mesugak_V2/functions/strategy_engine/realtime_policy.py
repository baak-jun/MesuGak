"""Small, deterministic policy helpers for the KIS intraday paper trader.

The module deliberately contains no broker or Firestore calls.  A quote stream
feeds :class:`RollingQuotes`; the returned snapshots are then passed to the
pure entry/exit predicates below.  That makes the same rules usable by the
live runner and by an offline replay.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import date, datetime
from math import isfinite
from typing import Any, Iterable


def _number(value: Any, default: float = 0.0) -> float:
    try:
        result = float(str(value or "0").replace(",", ""))
    except (TypeError, ValueError):
        return default
    return result if isfinite(result) else default


@dataclass(frozen=True)
class RealtimePolicyConfig:
    daily_score_min: float = 58.0
    partial_drawdown_pct: float = 0.018
    full_drawdown_pct: float = 0.03
    partial_sell_fraction: float = 0.50
    min_price: float = 1_000.0
    min_prior_turnover: float = 5_000_000_000.0
    min_market_cap: float = 50_000_000_000.0
    opening_return_10s: float = 0.008
    opening_trade_value_10s: float = 300_000_000.0
    normal_return_10s: float = 0.004
    normal_return_30s: float = 0.008
    normal_return_60s_min: float = 0.010
    normal_return_60s_max: float = 0.040
    min_trade_value_30s: float = 1_000_000_000.0
    volume_acceleration: float = 2.0
    max_spread_pct: float = 0.003
    max_vwap_extension: float = 0.03
    confirmation_count: int = 2
    confirmation_gap_seconds: float = 3.0
    same_day_stop_loss_pct: float = 0.03
    trailing_stop_pct: float = 0.06
    profit_lock_activate_pct: float = 0.03
    profit_lock_trailing_pct: float = 0.02
    profit_lock_min_pnl_pct: float = 0.005
    momentum_exit_10s: float = -0.008
    position_weight: float = 0.20
    max_positions: int = 5
    rotation_score_gap: float = 10.0
    entry_limit_timeout_seconds: float = 2.0
    max_entry_reprices: int = 1
    evaluation_interval_seconds: float = 0.25


@dataclass(frozen=True)
class TradeTick:
    code: str
    timestamp: float
    price: float
    cumulative_volume: float = 0.0
    ask_price: float = 0.0
    bid_price: float = 0.0
    ask_quantity: float = 0.0
    bid_quantity: float = 0.0
    day_open: float = 0.0
    day_high: float = 0.0
    day_low: float = 0.0


@dataclass(frozen=True)
class QuotePoint:
    timestamp: float
    price: float
    volume: float
    trade_value: float
    ask_price: float
    bid_price: float
    ask_quantity: float
    bid_quantity: float


class RollingQuotes:
    """Keep a bounded quote history and derive short-window metrics."""

    def __init__(self, *, max_seconds: int = 120, max_points: int = 2_400):
        self.max_seconds = max(30, int(max_seconds))
        self.max_points = max(120, int(max_points))
        self.points: deque[QuotePoint] = deque()
        self._last_cumulative_volume = 0.0
        self._last_timestamp = 0.0

    def add(self, tick: TradeTick) -> QuotePoint | None:
        code = str(tick.code).strip()
        if not code or tick.price <= 0 or tick.timestamp < self._last_timestamp:
            return None
        cumulative = max(0.0, float(tick.cumulative_volume or 0.0))
        if cumulative and self._last_cumulative_volume:
            volume = max(0.0, cumulative - self._last_cumulative_volume)
        else:
            # A new subscription starts mid-session; its day total is a baseline, not a fresh trade.
            volume = 0.0
        point = QuotePoint(
            timestamp=float(tick.timestamp),
            price=float(tick.price),
            volume=volume,
            trade_value=volume * float(tick.price),
            ask_price=max(0.0, float(tick.ask_price or 0.0)),
            bid_price=max(0.0, float(tick.bid_price or 0.0)),
            ask_quantity=max(0.0, float(tick.ask_quantity or 0.0)),
            bid_quantity=max(0.0, float(tick.bid_quantity or 0.0)),
        )
        self.points.append(point)
        self._last_timestamp = point.timestamp
        if cumulative:
            self._last_cumulative_volume = cumulative
        cutoff = point.timestamp - self.max_seconds
        while self.points and (self.points[0].timestamp < cutoff or len(self.points) > self.max_points):
            self.points.popleft()
        return point

    def _window(self, seconds: float) -> list[QuotePoint]:
        if not self.points:
            return []
        cutoff = self.points[-1].timestamp - max(0.0, float(seconds))
        return [point for point in self.points if point.timestamp >= cutoff]

    def _return(self, seconds: float) -> float | None:
        points = self._window(seconds)
        if len(points) < 2 or points[0].price <= 0:
            return None
        return points[-1].price / points[0].price - 1.0

    def _value(self, seconds: float) -> float:
        return sum(point.trade_value for point in self._window(seconds))

    def _vwap(self, seconds: float) -> float | None:
        points = self._window(seconds)
        value = sum(point.trade_value for point in points)
        volume = sum(point.volume for point in points)
        if volume <= 0:
            return points[-1].price if points else None
        return value / volume

    def snapshot(self, *, session_started_at: float | None = None) -> dict[str, Any]:
        if not self.points:
            return {"ready": False}
        latest = self.points[-1]
        previous = [point for point in self._window(60.0) if point.timestamp < latest.timestamp]
        previous_values = [point.trade_value for point in previous]
        prior_average = sum(previous_values[-5:]) / len(previous_values[-5:]) if previous_values else 0.0
        current_10_value = self._value(10.0)
        spread = None
        if latest.ask_price > 0 and latest.bid_price > 0 and latest.bid_price <= latest.ask_price:
            spread = (latest.ask_price - latest.bid_price) / latest.bid_price
        elapsed = None
        if session_started_at is not None:
            elapsed = max(0.0, latest.timestamp - float(session_started_at))
        return {
            "ready": True,
            "timestamp": latest.timestamp,
            "price": latest.price,
            "askPrice": latest.ask_price,
            "bidPrice": latest.bid_price,
            "askQuantity": latest.ask_quantity,
            "bidQuantity": latest.bid_quantity,
            "return10s": self._return(10.0),
            "return30s": self._return(30.0),
            "return60s": self._return(60.0),
            "tradeValue10s": current_10_value,
            "tradeValue30s": self._value(30.0),
            "volumeAcceleration": current_10_value / prior_average if prior_average > 0 else None,
            "vwap30s": self._vwap(30.0),
            "vwap60s": self._vwap(60.0),
            "breakout60s": bool(previous and latest.price >= max(point.price for point in previous)),
            "spreadPct": spread,
            "sessionSeconds": elapsed,
        }


def candidate_gate(candidate: dict[str, Any], config: RealtimePolicyConfig) -> tuple[bool, str]:
    score = _number(candidate.get("confidenceScore", candidate.get("score")))
    status = str(candidate.get("status", candidate.get("confidenceLabel", ""))).upper()
    risk_state = str(candidate.get("riskState", "")).upper()
    price = _number(candidate.get("currentPrice"))
    turnover = price * _number(candidate.get("volume"))
    market_cap = _number(candidate.get("marcap"))
    if status not in {"BUY_CANDIDATE", "STRONG_BUY"}:
        return False, "daily_status"
    if score < config.daily_score_min:
        return False, "daily_score"
    if risk_state == "DEFENSIVE":
        return False, "defensive_risk"
    if price < config.min_price:
        return False, "price_floor"
    if turnover < config.min_prior_turnover:
        return False, "turnover_floor"
    if market_cap < config.min_market_cap:
        return False, "market_cap_floor"
    return True, "daily_gate"


def entry_signal(
    candidate: dict[str, Any],
    snapshot: dict[str, Any],
    config: RealtimePolicyConfig | None = None,
) -> tuple[bool, str]:
    cfg = config or RealtimePolicyConfig()
    if not snapshot.get("ready") or _number(snapshot.get("price")) <= 0:
        return False, "quote_not_ready"
    if snapshot.get("liveScoreReady") is False:
        return False, "live_score_not_ready"
    score = _number(snapshot.get("liveConfidenceScore", candidate.get("confidenceScore")))
    if score < cfg.daily_score_min:
        return False, "score_threshold"
    return True, "live_score_entry"


def drawdown_exit(
    price: float, monitored_high: float, partial_done: bool,
    config: RealtimePolicyConfig | None = None,
) -> tuple[str, float] | None:
    """Trim once at 1.8%; at 3% sell all remaining, including a price gap."""
    cfg = config or RealtimePolicyConfig()
    if price <= 0 or monitored_high <= 0:
        return None
    if price <= monitored_high * (1.0 - cfg.full_drawdown_pct):
        return "monitored_high_full_exit", 1.0
    if not partial_done and price <= monitored_high * (1.0 - cfg.partial_drawdown_pct):
        return "monitored_high_partial_exit", cfg.partial_sell_fraction
    return None


class ConfirmationTracker:
    """Require consecutive positive evaluations without retaining tick data."""

    def __init__(self):
        self._state: dict[str, tuple[float, int]] = {}

    def confirm(self, code: str, eligible: bool, timestamp: float, config: RealtimePolicyConfig | None = None) -> bool:
        cfg = config or RealtimePolicyConfig()
        code = str(code)
        if not eligible:
            self._state.pop(code, None)
            return False
        previous = self._state.get(code)
        if previous and timestamp - previous[0] <= cfg.confirmation_gap_seconds:
            count = previous[1] + 1
        else:
            count = 1
        self._state[code] = (timestamp, count)
        return count >= max(1, cfg.confirmation_count)

    def clear(self, code: str) -> None:
        self._state.pop(str(code), None)


def _bought_today(position: dict[str, Any], session_date: date) -> bool:
    raw = position.get("boughtAt")
    if not raw:
        return False
    if isinstance(raw, datetime):
        return raw.date() == session_date
    return str(raw)[:10] == session_date.isoformat()


def exit_reason(
    position: dict[str, Any],
    snapshot: dict[str, Any],
    config: RealtimePolicyConfig | None = None,
    *,
    session_date: date | None = None,
) -> str | None:
    cfg = config or RealtimePolicyConfig()
    if not snapshot.get("ready"):
        return None
    price = _number(snapshot.get("price"))
    buy_price = _number(position.get("buyPrice"))
    high = max(_number(position.get("highestPrice")), price)
    if price <= 0 or buy_price <= 0:
        return None
    if session_date and _bought_today(position, session_date) and price <= buy_price * (1.0 - cfg.same_day_stop_loss_pct):
        return "same_day_stop_loss"
    if price <= high * (1.0 - cfg.trailing_stop_pct):
        return "trailing_stop"
    activated = high >= buy_price * (1.0 + cfg.profit_lock_activate_pct)
    profitable = price >= buy_price * (1.0 + cfg.profit_lock_min_pnl_pct)
    if activated and profitable and price <= high * (1.0 - cfg.profit_lock_trailing_pct):
        return "profit_lock_trailing_stop"
    if _number(snapshot.get("return10s")) <= cfg.momentum_exit_10s and _number(snapshot.get("vwap30s")) > 0 and price < _number(snapshot.get("vwap30s")):
        return "momentum_reversal"
    return None


def should_hold_overnight(position: dict[str, Any], candidate: dict[str, Any], snapshot: dict[str, Any]) -> bool:
    """Keep only profitable, above-VWAP positions with a positive short trend."""
    price = _number(snapshot.get("price"))
    buy_price = _number(position.get("buyPrice"))
    vwap = _number(snapshot.get("vwap60s"))
    score = _number(candidate.get("confidenceScore", candidate.get("score")))
    status = str(candidate.get("status", candidate.get("confidenceLabel", ""))).upper()
    return bool(
        price > buy_price > 0
        and vwap > 0
        and price >= vwap
        and _number(snapshot.get("return30s")) >= 0
        and score >= 60
        and status in {"BUY_CANDIDATE", "STRONG_BUY"}
    )


def select_watch_codes(
    candidates: Iterable[dict[str, Any]],
    held_codes: Iterable[str],
    *,
    max_codes: int = 20,
    exploration_codes: Iterable[str] = (),
    exploration_count: int = 2,
    minimum_score: float | None = None,
) -> list[str]:
    """Keep holdings, reserve exploration slots, then select the highest scores."""
    by_code = {str(item.get("code")): item for item in candidates if item.get("code")}
    limit = max(1, int(max_codes))
    ordered = list(dict.fromkeys(str(code) for code in held_codes if code))
    if len(ordered) > limit:
        raise ValueError("Watch capacity is smaller than the protected holding/order set")
    explore = min(max(0, int(exploration_count)), limit - len(ordered))
    scored = sorted(by_code.values(), key=lambda item: (-_number(item.get("confidenceScore")), -_number(item.get("marcap")), str(item["code"])))
    for item in scored:
        if len(ordered) >= limit - explore:
            break
        if minimum_score is not None and _number(item.get("confidenceScore")) < minimum_score:
            continue
        code = str(item["code"])
        if code not in ordered:
            ordered.append(code)
    for code in exploration_codes:
        if len(ordered) >= limit:
            break
        if str(code) in by_code and str(code) not in ordered:
            ordered.append(str(code))
    for item in scored:
        if len(ordered) >= limit:
            break
        if minimum_score is not None and _number(item.get("confidenceScore")) < minimum_score:
            continue
        if str(item["code"]) not in ordered:
            ordered.append(str(item["code"]))
    return ordered
