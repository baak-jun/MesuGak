"""Local smoke test for the V2 operator flow without Firestore writes."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

FUNCTIONS_DIR = Path(__file__).resolve().parents[1]
if str(FUNCTIONS_DIR) not in sys.path:
    sys.path.insert(0, str(FUNCTIONS_DIR))

from strategy_engine.analysis import StockIdentity, analyze_stock, to_summary
from strategy_engine.ledger import apply_paper_orders, initialize_account
from strategy_engine.orders import build_rebalance_orders
from strategy_engine.portfolio import AllocationConfig, build_target_allocations


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a Firestore-free V2 smoke test")
    parser.add_argument("--market", default="KR")
    parser.add_argument("--initial-cash", type=float, default=1_000_000)
    parser.add_argument("--max-positions", type=int, default=2)
    parser.add_argument("--min-confidence", type=float, default=0.0)
    return parser


def synthetic_ohlcv(rows: int = 180, start: float = 100.0, slope: float = 0.45) -> pd.DataFrame:
    dates = pd.date_range("2026-01-01", periods=rows, freq="D")
    closes = [start + idx * slope for idx in range(rows)]
    return pd.DataFrame(
        {
            "date": dates,
            "open": [close - 0.4 for close in closes],
            "high": [close + 1.2 for close in closes],
            "low": [close - 1.2 for close in closes],
            "close": closes,
            "volume": [100000 + idx * 1000 for idx in range(rows)],
        }
    )


def run(args: argparse.Namespace) -> dict:
    market = str(args.market).upper().strip()
    identities = [
        StockIdentity(market=market, code="SMOKE1", name="Smoke Alpha", marcap=1000),
        StockIdentity(market=market, code="SMOKE2", name="Smoke Beta", marcap=800),
    ]
    frames = {
        "SMOKE1": synthetic_ohlcv(start=100, slope=0.55),
        "SMOKE2": synthetic_ohlcv(start=80, slope=0.25),
    }

    payloads = []
    for identity in identities:
        payload = analyze_stock(frames[identity.code], identity)
        if payload:
            payloads.append(payload)

    summaries = [to_summary(payload) for payload in payloads]
    cash_target = max([float(item.get("cashTargetPct") or 0.1) for item in summaries], default=0.1)
    allocation = build_target_allocations(
        summaries,
        cash_target,
        AllocationConfig(
            max_positions=args.max_positions,
            max_position_weight=0.50,
            min_confidence=args.min_confidence,
        ),
    )
    orders = build_rebalance_orders({}, allocation, args.initial_cash)
    prices = {payload["code"]: float(payload["currentPrice"]) for payload in payloads}
    ledger = apply_paper_orders(
        initialize_account(args.initial_cash, market),
        {},
        orders,
        prices,
        market=market,
        initial_cash=args.initial_cash,
        executed_at="2026-01-01T09:00:00",
    )

    ok = bool(payloads) and bool(allocation["positions"]) and bool(ledger["snapshot"])
    return {
        "status": "ok" if ok else "failed",
        "market": market,
        "analysisCount": len(payloads),
        "positionCount": len(allocation["positions"]),
        "orderCount": len(orders),
        "executedCount": len(ledger["logs"]),
        "cash": ledger["snapshot"]["cash"],
        "totalEquity": ledger["snapshot"]["totalEquity"],
        "returnPct": ledger["snapshot"]["returnPct"],
        "positions": allocation["positions"],
        "logs": ledger["logs"],
    }


def main() -> None:
    args = build_parser().parse_args()
    result = run(args)
    print(result)
    if result["status"] != "ok":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
