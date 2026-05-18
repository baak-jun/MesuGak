"""Run the Mesugak V2 paper-trading operator flow."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from types import SimpleNamespace

FUNCTIONS_DIR = Path(__file__).resolve().parents[1]
JOBS_DIR = Path(__file__).resolve().parent
for path in (FUNCTIONS_DIR, JOBS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import analyze_market
import apply_paper_orders
import rebalance


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run analyze -> rebalance -> apply paper orders")
    parser.add_argument("--market", default="KR")
    parser.add_argument("--codes", default=None)
    parser.add_argument("--kr-markets", default="KOSPI,KOSDAQ")
    parser.add_argument("--max-stocks", type=int, default=None)
    parser.add_argument("--cred-path", default=None)
    parser.add_argument("--checkpoint-dir", default=None)
    parser.add_argument("--reset-checkpoint", action="store_true")
    parser.add_argument("--meta-chunk-size", type=int, default=400)
    parser.add_argument("--progress-interval", type=int, default=25)
    parser.add_argument("--account-value", type=float, default=10_000_000)
    parser.add_argument("--initial-cash", type=float, default=10_000_000)
    parser.add_argument("--cash-target-pct", type=float, default=None)
    parser.add_argument("--max-positions", type=int, default=5)
    parser.add_argument("--max-position-weight", type=float, default=0.25)
    parser.add_argument("--min-confidence", type=float, default=65.0)
    parser.add_argument("--allocation-id", default=None)
    parser.add_argument("--skip-analysis", action="store_true")
    parser.add_argument("--skip-rebalance", action="store_true")
    parser.add_argument("--skip-apply", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def run(args: argparse.Namespace) -> dict:
    market = str(args.market).upper().strip()
    result: dict = {"market": market, "dryRun": bool(args.dry_run)}

    if not args.skip_analysis:
        result["analysis"] = analyze_market.run(
            SimpleNamespace(
                market=market,
                codes=args.codes,
                kr_markets=args.kr_markets,
                max_stocks=args.max_stocks,
                cred_path=args.cred_path,
                checkpoint_dir=args.checkpoint_dir,
                reset_checkpoint=args.reset_checkpoint,
                meta_chunk_size=args.meta_chunk_size,
                progress_interval=args.progress_interval,
                dry_run=args.dry_run,
            )
        )

    if not args.skip_rebalance:
        result["rebalance"] = rebalance.run(
            SimpleNamespace(
                market=market,
                cred_path=args.cred_path,
                account_value=args.account_value,
                cash_target_pct=args.cash_target_pct,
                max_positions=args.max_positions,
                max_position_weight=args.max_position_weight,
                min_confidence=args.min_confidence,
                dry_run=args.dry_run,
            )
        )
        if not args.allocation_id:
            args.allocation_id = result["rebalance"].get("allocationId")

    if not args.skip_apply:
        result["apply"] = apply_paper_orders.run(
            SimpleNamespace(
                market=market,
                allocation_id=args.allocation_id,
                cred_path=args.cred_path,
                initial_cash=args.initial_cash,
                dry_run=args.dry_run,
            )
        )

    return result


def main() -> None:
    args = build_parser().parse_args()
    result = run(args)
    print(result)


if __name__ == "__main__":
    main()
