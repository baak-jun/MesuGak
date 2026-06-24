"""Analyze stocks with the Mesugak V2 strategy engine."""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

FUNCTIONS_DIR = Path(__file__).resolve().parents[1]
if str(FUNCTIONS_DIR) not in sys.path:
    sys.path.insert(0, str(FUNCTIONS_DIR))

from strategy_engine.analysis import StockIdentity, analyze_stock, to_summary
from strategy_engine.checkpoints import LocalCheckpointManager, MemoryCheckpointManager, resolve_checkpoint_path
from strategy_engine.market_data import load_kr_fundamentals_with_fdr, load_market_universe, load_ohlcv_with_fdr, targets_from_codes
from strategy_engine.repositories import FirestoreStrategyRepository, init_firestore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Mesugak V2 stock analysis")
    parser.add_argument("--market", default="KR")
    parser.add_argument("--codes", default=None, help="Comma-separated stock codes. If omitted, loads the full market universe.")
    parser.add_argument("--kr-markets", default="KOSPI,KOSDAQ", help="Comma-separated KR submarkets for universe mode")
    parser.add_argument("--max-stocks", type=int, default=None, help="Limit analysis count per market")
    parser.add_argument("--cred-path", default=None)
    parser.add_argument("--checkpoint-dir", default=None)
    parser.add_argument("--reset-checkpoint", action="store_true")
    parser.add_argument("--meta-chunk-size", type=int, default=400)
    parser.add_argument("--progress-interval", type=int, default=10, help="Print progress every N processed stocks")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def _parse_csv(raw: str | None) -> list[str]:
    return [part.strip() for part in str(raw or "").split(",") if part.strip()]


def _load_targets(args: argparse.Namespace, market: str):
    if args.codes:
        targets = targets_from_codes(_parse_csv(args.codes))
    else:
        targets = load_market_universe(
            market,
            kr_markets=_parse_csv(args.kr_markets) if market == "KR" else None,
            max_stocks=args.max_stocks,
        )
    if args.codes and args.max_stocks is not None and args.max_stocks > 0:
        targets = targets[: args.max_stocks]
    return targets


def _save_meta_chunks(repo: FirestoreStrategyRepository, market: str, summaries: list[dict], chunk_size: int) -> int:
    chunk_count = 0
    for index in range(0, len(summaries), chunk_size):
        repo.save_meta_chunk(market, chunk_count, summaries[index : index + chunk_size])
        chunk_count += 1
    return chunk_count


def _delete_stale_meta_chunks(repo: FirestoreStrategyRepository, market: str, start_index: int, previous_count: int) -> None:
    for index in range(start_index, max(start_index, previous_count)):
        repo.delete_meta_chunk(market, index)


def _format_duration(seconds: float) -> str:
    seconds = max(0, int(seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes:02d}m {secs:02d}s"
    if minutes:
        return f"{minutes}m {secs:02d}s"
    return f"{secs}s"


def _print_progress(
    *,
    market: str,
    processed: int,
    total: int,
    success: int,
    failure: int,
    skipped: int,
    started_at: float,
    current_code: str = "",
    current_name: str = "",
    force: bool = False,
) -> None:
    if total <= 0:
        total = 1
    elapsed = max(0.001, time.monotonic() - started_at)
    rate = processed / elapsed
    remaining = max(0, total - processed)
    eta = remaining / rate if rate > 0 else 0
    percent = min(100.0, processed / total * 100)
    label = f"{current_code} {current_name}".strip()
    suffix = f" last={label}" if label else ""
    prefix = "[done]" if force and processed >= total else "[progress]"
    print(
        f"{prefix} {market} {processed}/{total} ({percent:5.1f}%) "
        f"success={success} failed={failure} skipped={skipped} "
        f"rate={rate:.2f}/s elapsed={_format_duration(elapsed)} eta={_format_duration(eta)}{suffix}",
        flush=True,
    )


def run(args: argparse.Namespace) -> dict:
    market = str(args.market).upper().strip()
    targets = _load_targets(args, market)
    run_id = f"{market}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    repo = None if args.dry_run else FirestoreStrategyRepository(init_firestore(args.cred_path))
    checkpoint = (
        LocalCheckpointManager(resolve_checkpoint_path(market, args.checkpoint_dir), market)
        if not args.dry_run or args.checkpoint_dir
        else MemoryCheckpointManager(market)
    )
    if args.reset_checkpoint:
        checkpoint.reset()
    checkpoint_state = checkpoint.prepare(total_count=len(targets))
    previous_meta_doc_count = int(checkpoint_state.get("metaDocCount", 0) or 0)
    done_codes = checkpoint.done_codes()
    remaining_targets = [target for target in targets if target.code not in done_codes]

    summaries = checkpoint.summaries()
    failures = checkpoint.snapshot().get("failedCodes", [])
    initial_done_count = len(done_codes)
    initial_failure_count = len(failures)
    processed_count = initial_done_count
    skipped_count = initial_done_count
    started_at = time.monotonic()
    progress_interval = max(1, int(args.progress_interval or 10))
    print(
        f"[start] {market} runId={run_id} targets={len(targets)} "
        f"resumeDone={initial_done_count} remaining={len(remaining_targets)} dryRun={bool(args.dry_run)}",
        flush=True,
    )
    try:
        for offset, target in enumerate(remaining_targets):
            remaining_count = len(remaining_targets) - offset - 1
            try:
                df = load_ohlcv_with_fdr(target.code)
                fundamentals = {}
                if market == "KR":
                    try:
                        fundamentals = load_kr_fundamentals_with_fdr(target.code)
                    except Exception as exc:
                        print(f"[fundamentals] {target.code} unavailable: {type(exc).__name__}: {exc}", flush=True)
                payload = analyze_stock(
                    df,
                    StockIdentity(
                        market=market,
                        code=target.code,
                        name=target.name,
                        marcap=target.marcap,
                    ),
                    fundamentals=fundamentals,
                )
                if not payload:
                    failure = {"code": target.code, "reason": "insufficient_data"}
                    failures.append(failure)
                    checkpoint.record_failure(target.code, failure["reason"], remaining_count)
                    continue
                summary = to_summary(payload)
                summaries.append(summary)
                if repo:
                    repo.save_stock_analysis(payload["id"], payload)
                    repo.save_strategy_candidate(f"{run_id}_{payload['id']}", payload)
                checkpoint.record_success(target.code, summary, remaining_count)
            except Exception as exc:
                failure = {"code": target.code, "reason": f"{type(exc).__name__}: {exc}"}
                failures.append(failure)
                checkpoint.record_failure(target.code, failure["reason"], remaining_count)
            finally:
                if remaining_count >= 0:
                    processed_count = initial_done_count + offset + 1
                    if processed_count % progress_interval == 0 or remaining_count == 0:
                        _print_progress(
                            market=market,
                            processed=processed_count,
                            total=len(targets),
                            success=len(summaries),
                            failure=len(failures),
                            skipped=skipped_count,
                            started_at=started_at,
                            current_code=target.code,
                            current_name=target.name,
                        )

        if repo:
            print(f"[meta] writing {len(summaries)} summaries to meta_data chunks size={args.meta_chunk_size}", flush=True)
            meta_doc_count = _save_meta_chunks(repo, market, summaries, args.meta_chunk_size)
            _delete_stale_meta_chunks(repo, market, meta_doc_count, previous_meta_doc_count)
            checkpoint.update_meta_doc_count(meta_doc_count)
            repo.save_strategy_run(
                run_id,
                {
                    "runId": run_id,
                    "market": market,
                    "status": "done",
                    "targetCount": len(targets),
                    "successCount": len(summaries),
                    "failureCount": len(failures),
                    "failures": failures,
                },
            )
        checkpoint.mark_done()
        _print_progress(
            market=market,
            processed=len(targets),
            total=len(targets),
            success=len(summaries),
            failure=len(failures),
            skipped=skipped_count,
            started_at=started_at,
            force=True,
        )
    except Exception:
        checkpoint.mark_interrupted()
        checkpoint_label = str(checkpoint.path) if checkpoint.path else "disabled"
        print(
            f"[interrupted] {market} processed={processed_count}/{len(targets)} "
            f"success={len(summaries)} failed={len(failures)} "
            f"checkpoint={checkpoint_label}",
            flush=True,
        )
        raise

    return {
        "runId": run_id,
        "market": market,
        "targetCount": len(targets),
        "successCount": len(summaries),
        "failureCount": len(failures),
        "failures": failures,
    }


def main() -> None:
    args = build_parser().parse_args()
    result = run(args)
    print(result)


if __name__ == "__main__":
    main()
