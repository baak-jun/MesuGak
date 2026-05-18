"""Rebalance order generation for Mesugak V2."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RebalanceConfig:
    min_weight_delta: float = 0.01
    min_trade_amount: float = 0.0


def _current_weight(position: dict, account_value: float) -> float:
    if "weight" in position:
        return float(position.get("weight") or 0)
    position_value = float(position.get("marketValue", position.get("value", 0)) or 0)
    if account_value <= 0:
        return 0.0
    return position_value / account_value


def _side_for_delta(diff: float, trade_amount: float, config: RebalanceConfig) -> str:
    if abs(diff) < config.min_weight_delta or trade_amount < config.min_trade_amount:
        return "HOLD"
    return "BUY" if diff > 0 else "SELL"


def build_rebalance_orders(
    current_positions: dict[str, dict],
    target_allocation: dict,
    account_value: float,
    config: RebalanceConfig | None = None,
) -> list[dict]:
    cfg = config or RebalanceConfig()
    targets = {str(item["code"]): item for item in target_allocation.get("positions", []) if item.get("code")}
    orders: list[dict] = []

    for code, position in current_positions.items():
        if code not in targets:
            current_weight = _current_weight(position, account_value)
            orders.append({
                "code": code,
                "name": position.get("name"),
                "side": "SELL",
                "targetWeight": 0,
                "currentWeight": current_weight,
                "targetAmount": 0,
                "tradeAmount": round(account_value * current_weight, 2),
                "reason": "removed_from_target_allocation",
            })

    for code, target in targets.items():
        current_weight = _current_weight(current_positions.get(code, {}), account_value)
        target_weight = float(target.get("targetWeight", 0))
        diff = target_weight - current_weight
        target_amount = round(account_value * target_weight, 2)
        trade_amount = round(abs(account_value * diff), 2)
        side = _side_for_delta(diff, trade_amount, cfg)
        orders.append({
            "code": code,
            "name": target.get("name"),
            "side": side,
            "targetWeight": target_weight,
            "currentWeight": current_weight,
            "targetAmount": target_amount,
            "tradeAmount": trade_amount,
            "reason": "confidence_rebalance",
        })

    return orders
