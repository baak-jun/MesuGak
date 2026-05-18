"""Backtest entry points for Mesugak V2."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pandas as pd

from .analysis import StockIdentity, analyze_stock, to_summary
from .orders import RebalanceConfig, build_rebalance_orders
from .portfolio import AllocationConfig, build_target_allocations


AnalysisFn = Callable[[pd.DataFrame, StockIdentity], dict | None]


@dataclass(frozen=True)
class BacktestConfig:
    initial_cash: float = 10_000_000
    min_history: int = 120
    max_positions: int = 5
    max_position_weight: float = 0.25
    min_confidence: float = 65.0
    default_cash_target_pct: float = 0.10
    min_weight_delta: float = 0.01


def _prepare_frame(df: pd.DataFrame) -> pd.DataFrame:
    required = {"date", "open", "high", "low", "close"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Backtest data is missing columns: {sorted(missing)}")
    out = df.copy()
    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    out = out.dropna(subset=["date", "open", "high", "low", "close"]).sort_values("date")
    for column in ["open", "high", "low", "close", "volume"]:
        if column in out.columns:
            out[column] = pd.to_numeric(out[column], errors="coerce")
    if "volume" not in out.columns:
        out["volume"] = 0
    return out.dropna(subset=["open", "high", "low", "close"]).reset_index(drop=True)


def _market_value(positions: dict[str, float], prices: dict[str, float]) -> float:
    return sum(float(quantity) * float(prices.get(code, 0.0)) for code, quantity in positions.items())


def _position_payloads(positions: dict[str, float], prices: dict[str, float], names: dict[str, str], account_value: float) -> dict[str, dict]:
    payloads: dict[str, dict] = {}
    for code, quantity in positions.items():
        price = float(prices.get(code, 0.0))
        market_value = float(quantity) * price
        payloads[code] = {
            "code": code,
            "name": names.get(code, code),
            "quantity": quantity,
            "marketValue": market_value,
            "weight": market_value / account_value if account_value > 0 else 0.0,
        }
    return payloads


def run_backtest(
    price_frames: dict[str, pd.DataFrame] | None = None,
    identities: dict[str, StockIdentity] | None = None,
    config: BacktestConfig | None = None,
    analysis_fn: AnalysisFn = analyze_stock,
) -> dict:
    """Run a daily rebalance simulation without lookahead.

    Signals are calculated with data through day N. Trades are executed at day N+1
    close, so the engine never trades on the same bar used for signal generation.
    """

    if not price_frames:
        return {
            "status": "not_run",
            "reason": "price_frames_required",
            "equityCurve": [],
            "trades": [],
            "finalValue": 0.0,
            "returnPct": 0.0,
        }

    cfg = config or BacktestConfig()
    frames = {code: _prepare_frame(df) for code, df in price_frames.items()}
    frames = {code: df for code, df in frames.items() if len(df) >= cfg.min_history + 1}
    if not frames:
        return {
            "status": "not_run",
            "reason": "insufficient_history",
            "equityCurve": [],
            "trades": [],
            "finalValue": float(cfg.initial_cash),
            "returnPct": 0.0,
        }

    max_steps = min(len(df) for df in frames.values())
    cash = float(cfg.initial_cash)
    positions: dict[str, float] = {}
    trades: list[dict] = []
    equity_curve: list[dict] = []
    names = {
        code: (identities or {}).get(code, StockIdentity("BT", code, code)).name
        for code in frames
    }

    for signal_idx in range(cfg.min_history - 1, max_steps - 1):
        signal_date = frames[next(iter(frames))].iloc[signal_idx]["date"].strftime("%Y-%m-%d")
        trade_date = frames[next(iter(frames))].iloc[signal_idx + 1]["date"].strftime("%Y-%m-%d")
        trade_prices = {code: float(df.iloc[signal_idx + 1]["close"]) for code, df in frames.items()}
        account_value = cash + _market_value(positions, trade_prices)

        candidates = []
        for code, df in frames.items():
            identity = (identities or {}).get(code) or StockIdentity("BT", code, code)
            payload = analysis_fn(df.iloc[: signal_idx + 1].copy(), identity)
            if payload:
                candidates.append(to_summary(payload))

        cash_target = max(
            [float(item.get("cashTargetPct") or 0.0) for item in candidates],
            default=cfg.default_cash_target_pct,
        )
        cash_target = max(cash_target, cfg.default_cash_target_pct)
        allocation = build_target_allocations(
            candidates,
            cash_target,
            AllocationConfig(
                max_positions=cfg.max_positions,
                max_position_weight=cfg.max_position_weight,
                min_confidence=cfg.min_confidence,
            ),
        )
        current_payloads = _position_payloads(positions, trade_prices, names, account_value)
        orders = build_rebalance_orders(
            current_payloads,
            allocation,
            account_value,
            RebalanceConfig(min_weight_delta=cfg.min_weight_delta),
        )

        target_by_code = {item["code"]: item for item in allocation.get("positions", [])}
        next_positions: dict[str, float] = {}
        next_cash = account_value
        for code, target in target_by_code.items():
            price = trade_prices.get(code, 0.0)
            if price <= 0:
                continue
            target_value = account_value * float(target.get("targetWeight", 0.0))
            quantity = target_value / price
            next_positions[code] = quantity
            next_cash -= target_value
        positions = next_positions
        cash = next_cash

        for order in orders:
            if order["side"] == "HOLD":
                continue
            trades.append({**order, "signalDate": signal_date, "tradeDate": trade_date})

        final_value = cash + _market_value(positions, trade_prices)
        equity_curve.append(
            {
                "date": trade_date,
                "value": round(final_value, 2),
                "cash": round(cash, 2),
                "positionCount": len(positions),
            }
        )

    final_value = equity_curve[-1]["value"] if equity_curve else float(cfg.initial_cash)
    return {
        "status": "done",
        "initialCash": float(cfg.initial_cash),
        "finalValue": final_value,
        "returnPct": round(((final_value - cfg.initial_cash) / cfg.initial_cash) * 100, 4) if cfg.initial_cash else 0.0,
        "equityCurve": equity_curve,
        "trades": trades,
    }
