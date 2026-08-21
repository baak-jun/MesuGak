"""Pure school-server paper-trading policy based on saved daily analysis."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo


KST = ZoneInfo("Asia/Seoul")


@dataclass(frozen=True)
class IntradayPolicyConfig:
    buy_score_min: float = 65.0
    score_exit_threshold: float = -15.0
    trailing_stop_pct: float = 0.08
    position_weight: float = 0.10
    rotation_score_gap: float = 10.0
    profit_lock_activate_pct: float = 0.03
    profit_lock_trailing_pct: float = 0.02
    profit_lock_min_pnl_pct: float = 0.005
    same_day_stop_loss_pct: float = 0.03


def _score(item: dict[str, Any]) -> float:
    return float(item.get("confidenceScore", item.get("score", 0)) or 0)


def _price(position: dict[str, Any], prices: dict[str, float]) -> float:
    return float(prices.get(str(position.get("code")), position.get("lastPrice", 0)) or 0)


def _pnl_pct(position: dict[str, Any], prices: dict[str, float]) -> float:
    buy_price = float(position.get("buyPrice", 0) or 0)
    price = _price(position, prices)
    return (price / buy_price - 1.0) * 100 if buy_price > 0 and price > 0 else -100.0


def _profit_lock_triggered(position: dict[str, Any], price: float, cfg: IntradayPolicyConfig) -> bool:
    """Exit a *remainingly profitable* position after a fast retreat from its high.

    This is not an intraday Bollinger signal: the poller only has a current
    quote, not an intraday candle series. It prevents a realised small gain
    from becoming a large loss while a proper candle-based exit is added later.
    """
    buy_price = float(position.get("buyPrice", 0) or 0)
    highest_price = float(position.get("highestPrice", 0) or 0)
    if buy_price <= 0 or highest_price <= 0 or price <= 0:
        return False
    activated = highest_price >= buy_price * (1.0 + max(0.0, cfg.profit_lock_activate_pct))
    drawdown = price <= highest_price * (1.0 - max(0.0, cfg.profit_lock_trailing_pct))
    still_profitable = price >= buy_price * (1.0 + max(0.0, cfg.profit_lock_min_pnl_pct))
    return activated and drawdown and still_profitable


def _bought_on_session_date(position: dict[str, Any], session_date: date) -> bool:
    """Return whether the persisted position was opened during this KST session."""
    bought_at = position.get("boughtAt")
    if not bought_at:
        return False
    if isinstance(bought_at, datetime):
        stamp = bought_at
    elif isinstance(bought_at, date):
        return bought_at == session_date
    else:
        try:
            stamp = datetime.fromisoformat(str(bought_at).replace("Z", "+00:00"))
        except ValueError:
            return str(bought_at)[:10] == session_date.isoformat()
    if stamp.tzinfo is not None:
        stamp = stamp.astimezone(KST)
    return stamp.date() == session_date


def _same_day_stop_loss_triggered(
    position: dict[str, Any],
    price: float,
    cfg: IntradayPolicyConfig,
    session_date: date,
) -> bool:
    buy_price = float(position.get("buyPrice", 0) or 0)
    if buy_price <= 0 or price <= 0 or not _bought_on_session_date(position, session_date):
        return False
    return price <= buy_price * (1.0 - max(0.0, cfg.same_day_stop_loss_pct))


def update_high_water_marks(positions: dict[str, dict[str, Any]], prices: dict[str, float]) -> dict[str, dict[str, Any]]:
    updated: dict[str, dict[str, Any]] = {}
    for code, position in positions.items():
        copy = dict(position)
        price = _price(copy, prices)
        if price > 0:
            copy["lastPrice"] = price
            copy["highestPrice"] = max(float(copy.get("highestPrice", 0) or 0), price)
        updated[str(code)] = copy
    return updated


def build_intraday_orders(
    candidates: list[dict[str, Any]],
    positions: dict[str, dict[str, Any]],
    account_equity: float,
    cash: float,
    prices: dict[str, float],
    config: IntradayPolicyConfig | None = None,
    *,
    entry_blocked_codes: set[str] | None = None,
    session_date: date | None = None,
) -> list[dict[str, Any]]:
    cfg = config or IntradayPolicyConfig()
    session_day = session_date or datetime.now(KST).date()
    positions = update_high_water_marks(positions, prices)
    blocked_codes = {str(code) for code in (entry_blocked_codes or set())}
    candidate_by_code = {str(item.get("code")): item for item in candidates if item.get("code")}
    orders: list[dict[str, Any]] = []

    for code, position in positions.items():
        score = _score(candidate_by_code.get(code, {}))
        price = _price(position, prices)
        high = float(position.get("highestPrice", 0) or 0)
        if _same_day_stop_loss_triggered(position, price, cfg, session_day):
            orders.append({"side": "SELL", "code": code, "name": position.get("name", code), "targetWeight": 0, "tradeAmount": 0, "reason": "same_day_stop_loss"})
        elif score <= cfg.score_exit_threshold:
            orders.append({"side": "SELL", "code": code, "name": position.get("name", code), "targetWeight": 0, "tradeAmount": 0, "reason": "negative_score_exit"})
        elif price > 0 and high > 0 and price <= high * (1.0 - cfg.trailing_stop_pct):
            orders.append({"side": "SELL", "code": code, "name": position.get("name", code), "targetWeight": 0, "tradeAmount": 0, "reason": "trailing_stop"})
        elif _profit_lock_triggered(position, price, cfg):
            orders.append({"side": "SELL", "code": code, "name": position.get("name", code), "targetWeight": 0, "tradeAmount": 0, "reason": "profit_lock_trailing_stop"})

    exiting = {str(order["code"]) for order in orders}
    available_cash = max(0.0, float(cash)) + sum(
        max(0.0, _price(positions[code], prices) * float(positions[code].get("quantity", 0) or 0))
        for code in exiting
    )
    target_amount = max(0.0, float(account_equity) * cfg.position_weight)
    eligible = [
        item for item in candidates
        if str(item.get("code")) not in positions
        and str(item.get("code")) not in blocked_codes
        and _score(item) >= cfg.buy_score_min
        and str(item.get("status", item.get("confidenceLabel", ""))).upper() not in {"DEFENSIVE", "AVOID"}
    ]
    eligible.sort(key=_score, reverse=True)

    for candidate in eligible:
        code = str(candidate["code"])
        if available_cash < target_amount:
            held = [p for key, p in positions.items() if key not in exiting]
            if not held:
                continue
            weakest = min(held, key=lambda p: _score(candidate_by_code.get(str(p.get("code")), {})))
            weakest_code = str(weakest.get("code"))
            weakest_score = _score(candidate_by_code.get(weakest_code, {}))
            if _score(candidate) < weakest_score + cfg.rotation_score_gap:
                continue
            if weakest_score <= cfg.score_exit_threshold:
                orders.append({"side": "SELL", "code": weakest_code, "name": weakest.get("name", weakest_code), "targetWeight": 0, "tradeAmount": 0, "reason": "score_rotation"})
                exiting.add(weakest_code)
                available_cash += _price(weakest, prices) * float(weakest.get("quantity", 0) or 0)
            elif all(_pnl_pct(position, prices) >= 0 for position in held):
                fraction = 1.0 / len(held)
                for position in held:
                    code_to_trim = str(position.get("code"))
                    amount = _price(position, prices) * float(position.get("quantity", 0) or 0) * fraction
                    orders.append({"side": "SELL", "code": code_to_trim, "name": position.get("name", code_to_trim), "targetWeight": fraction, "tradeAmount": amount, "reason": "proportional_profit_take"})
                    available_cash += amount
        if available_cash >= target_amount and prices.get(code, 0) > 0:
            orders.append({"side": "BUY", "code": code, "name": candidate.get("name", code), "targetWeight": cfg.position_weight, "tradeAmount": target_amount, "reason": "daily_score_entry"})
            available_cash -= target_amount
    return orders
