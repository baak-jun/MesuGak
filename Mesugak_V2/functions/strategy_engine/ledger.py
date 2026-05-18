"""Pure paper account ledger logic for Mesugak V2."""

from __future__ import annotations

import datetime as dt
import math
from typing import Any


def today_iso() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def initialize_account(initial_cash: float = 10_000_000, market: str = "KR") -> dict[str, Any]:
    cash = float(initial_cash)
    return {
        "market": market,
        "mode": "paper",
        "source": "Mesugak_V2",
        "initialCash": cash,
        "cash": cash,
        "realizedPnl": 0.0,
    }


def normalize_account(account: dict[str, Any] | None, initial_cash: float = 10_000_000, market: str = "KR") -> dict[str, Any]:
    base = initialize_account(initial_cash=initial_cash, market=market)
    if not account:
        return base
    out = {**base, **account}
    if "cash" in account or "cashAmt" in account:
        cash = account.get("cash", account.get("cashAmt", 0.0))
    elif account.get("totalEquity") is not None and account.get("totalEvalAmt") is not None:
        cash = float(account.get("totalEquity") or 0.0) - float(account.get("totalEvalAmt") or 0.0)
    else:
        cash = 0.0
    out["cash"] = float(cash or 0.0)
    out["initialCash"] = float(out.get("initialCash", initial_cash) or initial_cash)
    out["realizedPnl"] = float(out.get("realizedPnl", 0.0) or 0.0)
    out["market"] = str(out.get("market") or market)
    out["mode"] = str(out.get("mode") or "paper")
    out["source"] = str(out.get("source") or "Mesugak_V2")
    return out


def normalize_position(payload: dict[str, Any], fallback_code: str = "") -> dict[str, Any]:
    code = str(payload.get("code") or payload.get("pdno") or fallback_code)
    quantity = float(payload.get("quantity", payload.get("qty", payload.get("hldg_qty", 0))) or 0.0)
    buy_price = float(payload.get("buyPrice", payload.get("avgPrice", payload.get("pchs_avg_pric", 0))) or 0.0)
    last_price = float(payload.get("lastPrice", payload.get("currentPrice", payload.get("price", buy_price))) or 0.0)
    highest_price = float(payload.get("highestPrice", max(buy_price, last_price)) or 0.0)
    return {
        "code": code,
        "name": payload.get("name") or payload.get("prdt_name") or code,
        "quantity": quantity,
        "buyPrice": buy_price,
        "highestPrice": max(highest_price, last_price, buy_price),
        "lastPrice": last_price,
        "market": payload.get("market"),
        "signalType": payload.get("signalType", "v2_paper"),
        "boughtAt": payload.get("boughtAt"),
    }


def normalize_positions(positions: dict[str, dict[str, Any]] | list[dict[str, Any]] | None) -> dict[str, dict[str, Any]]:
    if not positions:
        return {}
    if isinstance(positions, dict):
        return {
            str(code): normalize_position(position, str(code))
            for code, position in positions.items()
            if normalize_position(position, str(code))["quantity"] > 0
        }
    return {
        normalize_position(position).get("code"): normalize_position(position)
        for position in positions
        if normalize_position(position).get("code") and normalize_position(position)["quantity"] > 0
    }


def _price_for(code: str, order: dict[str, Any], prices: dict[str, float]) -> float:
    return float(order.get("price", order.get("currentPrice", prices.get(code, 0.0))) or 0.0)


def _buy_quantity(cash: float, requested_amount: float, price: float) -> int:
    spendable = min(max(requested_amount, 0.0), max(cash, 0.0))
    if price <= 0 or spendable <= 0:
        return 0
    return int(math.floor(spendable / price))


def _sell_quantity(position: dict[str, Any], requested_amount: float, price: float, sell_all: bool) -> int:
    held = int(math.floor(float(position.get("quantity", 0.0) or 0.0)))
    if held <= 0 or price <= 0:
        return 0
    if sell_all:
        return held
    requested = int(math.floor(max(requested_amount, 0.0) / price))
    return min(held, requested)


def apply_paper_orders(
    account: dict[str, Any] | None,
    positions: dict[str, dict[str, Any]] | list[dict[str, Any]] | None,
    orders: list[dict[str, Any]],
    prices: dict[str, float],
    *,
    market: str = "KR",
    initial_cash: float = 10_000_000,
    executed_at: str | None = None,
) -> dict[str, Any]:
    next_account = normalize_account(account, initial_cash=initial_cash, market=market)
    next_positions = normalize_positions(positions)
    logs: list[dict[str, Any]] = []
    timestamp = executed_at or today_iso()

    for order in orders:
        side = str(order.get("side", "HOLD")).upper()
        if side == "HOLD":
            continue
        code = str(order.get("code") or "")
        if not code:
            continue
        price = _price_for(code, order, prices)
        if price <= 0:
            continue

        requested_amount = float(order.get("tradeAmount", 0.0) or 0.0)
        name = order.get("name") or next_positions.get(code, {}).get("name") or code
        if side == "BUY":
            quantity = _buy_quantity(next_account["cash"], requested_amount, price)
            if quantity <= 0:
                continue
            amount = round(quantity * price, 2)
            existing = next_positions.get(code)
            if existing:
                old_qty = float(existing.get("quantity", 0.0) or 0.0)
                old_cost = old_qty * float(existing.get("buyPrice", 0.0) or 0.0)
                new_qty = old_qty + quantity
                existing["quantity"] = new_qty
                existing["buyPrice"] = round((old_cost + amount) / new_qty, 4)
                existing["lastPrice"] = price
                existing["highestPrice"] = max(float(existing.get("highestPrice", 0.0) or 0.0), price)
                existing["updatedAt"] = timestamp
            else:
                next_positions[code] = {
                    "code": code,
                    "name": name,
                    "quantity": float(quantity),
                    "buyPrice": price,
                    "highestPrice": price,
                    "lastPrice": price,
                    "market": market,
                    "signalType": "v2_paper",
                    "boughtAt": timestamp,
                    "updatedAt": timestamp,
                }
            next_account["cash"] = round(next_account["cash"] - amount, 2)
            logs.append({
                "action": "BUY",
                "code": code,
                "name": name,
                "price": price,
                "quantity": quantity,
                "amount": amount,
                "reason": order.get("reason", "paper_rebalance"),
                "market": market,
                "createdAt": timestamp,
            })
        elif side == "SELL":
            position = next_positions.get(code)
            if not position:
                continue
            sell_all = float(order.get("targetWeight", 1.0) or 0.0) <= 0.0
            quantity = _sell_quantity(position, requested_amount, price, sell_all)
            if quantity <= 0:
                continue
            amount = round(quantity * price, 2)
            buy_price = float(position.get("buyPrice", 0.0) or 0.0)
            pnl = round((price - buy_price) * quantity, 2)
            pnl_pct = round(((price - buy_price) / buy_price) * 100, 4) if buy_price > 0 else 0.0
            remaining_qty = float(position.get("quantity", 0.0) or 0.0) - quantity
            if remaining_qty > 0:
                position["quantity"] = remaining_qty
                position["lastPrice"] = price
                position["highestPrice"] = max(float(position.get("highestPrice", 0.0) or 0.0), price)
                position["updatedAt"] = timestamp
            else:
                next_positions.pop(code, None)
            next_account["cash"] = round(next_account["cash"] + amount, 2)
            next_account["realizedPnl"] = round(float(next_account.get("realizedPnl", 0.0) or 0.0) + pnl, 2)
            logs.append({
                "action": "SELL",
                "code": code,
                "name": name,
                "price": price,
                "quantity": quantity,
                "amount": amount,
                "pnl": pnl,
                "pnlPct": pnl_pct,
                "reason": order.get("reason", "paper_rebalance"),
                "market": market,
                "createdAt": timestamp,
            })

    snapshot = build_account_snapshot(next_account, next_positions, prices, market=market, updated_at=timestamp)
    return {
        "account": next_account,
        "positions": next_positions,
        "logs": logs,
        "snapshot": snapshot,
    }


def build_account_snapshot(
    account: dict[str, Any],
    positions: dict[str, dict[str, Any]],
    prices: dict[str, float] | None = None,
    *,
    market: str = "KR",
    updated_at: str | None = None,
) -> dict[str, Any]:
    prices = prices or {}
    holdings = []
    total_eval = 0.0
    total_buy = 0.0
    unrealized_pnl = 0.0
    for code, position in sorted(positions.items()):
        quantity = float(position.get("quantity", 0.0) or 0.0)
        if quantity <= 0:
            continue
        price = float(prices.get(code, position.get("lastPrice", position.get("buyPrice", 0.0))) or 0.0)
        buy_price = float(position.get("buyPrice", 0.0) or 0.0)
        eval_amt = round(quantity * price, 2)
        buy_amt = round(quantity * buy_price, 2)
        pnl = round(eval_amt - buy_amt, 2)
        pnl_pct = round((pnl / buy_amt) * 100, 4) if buy_amt > 0 else 0.0
        total_eval += eval_amt
        total_buy += buy_amt
        unrealized_pnl += pnl
        holdings.append({
            "code": code,
            "name": position.get("name", code),
            "qty": quantity,
            "evalAmt": eval_amt,
            "buyAmt": buy_amt,
            "price": price,
            "buyPrice": buy_price,
            "pnl": pnl,
            "pnlPct": pnl_pct,
        })

    cash = float(account.get("cash", 0.0) or 0.0)
    total_equity = round(cash + total_eval, 2)
    initial_cash = float(account.get("initialCash", total_equity) or total_equity)
    realized_pnl = float(account.get("realizedPnl", 0.0) or 0.0)
    return {
        "mode": account.get("mode", "paper"),
        "source": account.get("source", "Mesugak_V2"),
        "market": account.get("market", market),
        "cash": round(cash, 2),
        "initialCash": round(initial_cash, 2),
        "holdingCount": len(holdings),
        "totalEvalAmt": round(total_eval, 2),
        "totalBuyAmt": round(total_buy, 2),
        "totalEquity": total_equity,
        "realizedPnl": round(realized_pnl, 2),
        "unrealizedPnl": round(unrealized_pnl, 2),
        "totalPnl": round(realized_pnl + unrealized_pnl, 2),
        "returnPct": round(((total_equity - initial_cash) / initial_cash) * 100, 4) if initial_cash > 0 else 0.0,
        "holdings": holdings,
        "updatedAt": updated_at or today_iso(),
    }
