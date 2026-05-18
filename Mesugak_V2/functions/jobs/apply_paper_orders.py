"""Apply staged Mesugak V2 rebalance orders to the paper account ledger."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

FUNCTIONS_DIR = Path(__file__).resolve().parents[1]
if str(FUNCTIONS_DIR) not in sys.path:
    sys.path.insert(0, str(FUNCTIONS_DIR))

from strategy_engine.ledger import apply_paper_orders, initialize_account
from strategy_engine.repositories import FirestoreStrategyRepository, init_firestore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Apply Mesugak V2 staged orders to the paper ledger")
    parser.add_argument("--market", default="KR")
    parser.add_argument("--allocation-id", default=None)
    parser.add_argument("--cred-path", default=None)
    parser.add_argument("--initial-cash", type=float, default=10_000_000)
    parser.add_argument("--dry-run", action="store_true")
    return parser


def _default_allocation_id(market: str) -> str:
    return f"{market}_{datetime.now().strftime('%Y-%m-%d')}"


def run_with_repo(args: argparse.Namespace, repo: FirestoreStrategyRepository) -> dict:
    market = str(args.market).upper().strip()
    allocation_id = args.allocation_id or _default_allocation_id(market)
    account = repo.fetch_account_snapshot() or initialize_account(args.initial_cash, market)
    applied_ids = set(account.get("appliedAllocationIds", []) or [])
    if allocation_id in applied_ids:
        return {
            "market": market,
            "allocationId": allocation_id,
            "status": "already_applied",
            "orderCount": 0,
            "executedCount": 0,
        }

    orders = repo.fetch_rebalance_orders(market, allocation_id=allocation_id)
    if not orders:
        return {
            "market": market,
            "allocationId": allocation_id,
            "status": "no_orders",
            "orderCount": 0,
            "executedCount": 0,
        }

    previous_positions = repo.fetch_current_positions()
    prices = repo.fetch_latest_prices(market, [str(order.get("code")) for order in orders if order.get("code")])

    result = apply_paper_orders(
        account,
        previous_positions,
        orders,
        prices,
        market=market,
        initial_cash=args.initial_cash,
    )
    result["snapshot"]["appliedAllocationIds"] = sorted(applied_ids | {allocation_id})
    result["snapshot"]["lastAppliedAllocationId"] = allocation_id

    if not args.dry_run:
        repo.save_paper_positions(result["positions"], previous_codes=set(previous_positions))
        repo.append_trade_logs(result["logs"])
        repo.save_account_snapshot(result["snapshot"])
        repo.save_paper_order_application(
            allocation_id,
            {
                "market": market,
                "allocationId": allocation_id,
                "orderCount": len(orders),
                "executedCount": len(result["logs"]),
                "missingPriceCodes": sorted({
                    str(order.get("code"))
                    for order in orders
                    if order.get("side") != "HOLD" and str(order.get("code")) not in prices
                }),
                "snapshot": result["snapshot"],
                "logs": result["logs"],
            },
        )

    return {
        "market": market,
        "allocationId": allocation_id,
        "status": "dry_run" if args.dry_run else "applied",
        "orderCount": len(orders),
        "executedCount": len(result["logs"]),
        "cash": result["snapshot"]["cash"],
        "totalEquity": result["snapshot"]["totalEquity"],
        "holdingCount": result["snapshot"]["holdingCount"],
        "missingPriceCodes": sorted({
            str(order.get("code"))
            for order in orders
            if order.get("side") != "HOLD" and str(order.get("code")) not in prices
        }),
        "logs": result["logs"],
        "snapshot": result["snapshot"],
    }


def run(args: argparse.Namespace) -> dict:
    repo = FirestoreStrategyRepository(init_firestore(args.cred_path))
    return run_with_repo(args, repo)


def main() -> None:
    args = build_parser().parse_args()
    result = run(args)
    print(result)


if __name__ == "__main__":
    main()
