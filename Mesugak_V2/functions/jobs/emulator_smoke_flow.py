"""Firestore emulator smoke path for V2 paper order application."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

FUNCTIONS_DIR = Path(__file__).resolve().parents[1]
JOBS_DIR = Path(__file__).resolve().parent
for path in (FUNCTIONS_DIR, JOBS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import apply_paper_orders
from strategy_engine.repositories import FirestoreStrategyRepository, init_firestore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run apply_paper_orders against a local Firestore emulator")
    parser.add_argument("--market", default="KR")
    parser.add_argument("--initial-cash", type=float, default=1_000_000)
    return parser


def _require_emulator() -> None:
    if not os.getenv("FIRESTORE_EMULATOR_HOST"):
        raise RuntimeError("FIRESTORE_EMULATOR_HOST must be set. Start the Firestore emulator before running this command.")


def seed_emulator(repo: FirestoreStrategyRepository, market: str, allocation_id: str) -> None:
    db = repo.db
    stock_id = f"{market}_EMU1"
    db.collection("stock_analysis").document(stock_id).set({
        "id": stock_id,
        "market": market,
        "code": "EMU1",
        "name": "Emulator Smoke",
        "currentPrice": 100,
    })
    db.collection("rebalance_orders").document(f"{allocation_id}_EMU1").set({
        "market": market,
        "allocationId": allocation_id,
        "code": "EMU1",
        "name": "Emulator Smoke",
        "side": "BUY",
        "targetWeight": 0.5,
        "currentWeight": 0,
        "targetAmount": 500000,
        "tradeAmount": 500000,
        "reason": "emulator_smoke",
    })
    db.collection("bot_account_snapshot").document("latest").set({
        "market": market,
        "mode": "paper",
        "source": "emulator_smoke",
        "cash": 1_000_000,
        "initialCash": 1_000_000,
        "realizedPnl": 0,
        "appliedAllocationIds": [],
    })


def run(args: argparse.Namespace) -> dict:
    _require_emulator()
    market = str(args.market).upper().strip()
    allocation_id = f"{market}_EMU_SMOKE_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    repo = FirestoreStrategyRepository(init_firestore(None))
    seed_emulator(repo, market, allocation_id)
    result = apply_paper_orders.run_with_repo(
        SimpleNamespace(
            market=market,
            allocation_id=allocation_id,
            cred_path=None,
            initial_cash=args.initial_cash,
            dry_run=False,
        ),
        repo,
    )
    result["emulatorHost"] = os.getenv("FIRESTORE_EMULATOR_HOST")
    return result


def main() -> None:
    args = build_parser().parse_args()
    result = run(args)
    print(result)
    if result.get("status") != "applied":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
