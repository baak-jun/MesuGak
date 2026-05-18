"""Generate Mesugak V2 paper trading rebalance decisions."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

FUNCTIONS_DIR = Path(__file__).resolve().parents[1]
if str(FUNCTIONS_DIR) not in sys.path:
    sys.path.insert(0, str(FUNCTIONS_DIR))

from strategy_engine.orders import build_rebalance_orders
from strategy_engine.portfolio import AllocationConfig, build_target_allocations
from strategy_engine.repositories import FirestoreStrategyRepository, init_firestore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate Mesugak V2 rebalance decisions")
    parser.add_argument("--market", default="KR")
    parser.add_argument("--cred-path", default=None)
    parser.add_argument("--account-value", type=float, default=10_000_000)
    parser.add_argument("--cash-target-pct", type=float, default=None)
    parser.add_argument("--max-positions", type=int, default=5)
    parser.add_argument("--max-position-weight", type=float, default=0.25)
    parser.add_argument("--min-confidence", type=float, default=65.0)
    parser.add_argument("--dry-run", action="store_true")
    return parser


def _market_cash_target(candidates: list[dict], override: float | None) -> float:
    if override is not None:
        return max(0.0, min(1.0, override))
    defensive = [float(item.get("cashTargetPct") or 0.0) for item in candidates]
    return max(defensive, default=0.1)


def run(args: argparse.Namespace) -> dict:
    market = str(args.market).upper().strip()
    repo = FirestoreStrategyRepository(init_firestore(args.cred_path))
    candidates = repo.fetch_meta_candidates(market)
    current_positions = repo.fetch_current_positions()
    cash_target = _market_cash_target(candidates, args.cash_target_pct)
    allocation_id = f"{market}_{datetime.now().strftime('%Y-%m-%d')}"

    allocation = build_target_allocations(
        candidates,
        cash_target,
        AllocationConfig(
            max_positions=args.max_positions,
            max_position_weight=args.max_position_weight,
            min_confidence=args.min_confidence,
        ),
    )
    orders = build_rebalance_orders(current_positions, allocation, args.account_value)

    if not args.dry_run:
        repo.save_target_allocation(allocation_id, {"market": market, **allocation})
        repo.save_risk_state(market, {"market": market, "cashTargetPct": allocation["cashTargetPct"]})
        for order in orders:
            order_id = f"{allocation_id}_{order['code']}"
            repo.save_rebalance_order(order_id, {"market": market, "allocationId": allocation_id, **order})

    return {
        "allocationId": allocation_id,
        "market": market,
        "cashTargetPct": allocation["cashTargetPct"],
        "positionCount": len(allocation["positions"]),
        "orderCount": len(orders),
        "orders": orders,
    }


def main() -> None:
    args = build_parser().parse_args()
    result = run(args)
    print(result)


if __name__ == "__main__":
    main()
