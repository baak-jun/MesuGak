"""Analyze stocks with the Mesugak V2 strategy engine."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

FUNCTIONS_DIR = Path(__file__).resolve().parents[1]
if str(FUNCTIONS_DIR) not in sys.path:
    sys.path.insert(0, str(FUNCTIONS_DIR))

from strategy_engine.analysis import StockIdentity, analyze_stock, to_summary
from strategy_engine.checkpoints import LocalCheckpointManager, MemoryCheckpointManager, resolve_checkpoint_path
from strategy_engine.market_data import load_market_universe, load_ohlcv_with_public_data, targets_from_codes
from strategy_engine.repositories import FirestoreStrategyRepository, init_firestore


MAX_DAILY_STOCKS = 1000
MAX_LOCAL_CANDIDATES = 5000
LOCAL_ANALYSIS_MODE = "local_ranked_v1"


def validate_stock_limit(value: int | None) -> int | None:
    """Validate the optional limit before market-data or Firestore I/O."""
    if value is None:
        return None
    value = int(value)
    if value < 1:
        raise ValueError("--max-stocks must be at least 1")
    if value > MAX_DAILY_STOCKS:
        raise ValueError(
            f"Daily analysis is limited to {MAX_DAILY_STOCKS} stocks; reduce --max-stocks before running"
        )
    return value


def resolve_storage_limit(value: int | None) -> int:
    """Resolve the Firebase persistence cap without widening it implicitly."""
    if value is None:
        value = int(os.getenv("MESUGAK_MAX_STOCKS", str(MAX_DAILY_STOCKS)))
    result = validate_stock_limit(value)
    if result is None:
        return MAX_DAILY_STOCKS
    return result


def _number(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    return result if result == result else default


def analysis_rank_key(summary: dict[str, Any]) -> tuple[float, float, str]:
    """Rank analysis candidates by strategy score, then market cap, then code."""
    return (-_number(summary.get("confidenceScore")), -_number(summary.get("marcap")), str(summary.get("code") or ""))


def select_top_summaries(summaries: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    """Return at most ``limit`` deterministic, score-ranked summaries."""
    unique: dict[str, dict[str, Any]] = {}
    for summary in summaries:
        key = str(summary.get("id") or summary.get("code") or "")
        if key:
            unique[key] = summary
    return sorted(unique.values(), key=analysis_rank_key)[:limit]


def _universe_hash(targets: list[Any]) -> str:
    value = "\n".join(f"{target.code}:{target.name}:{target.marcap}" for target in targets)
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _local_payload_dir(args: argparse.Namespace, market: str) -> Path:
    configured = getattr(args, "local_payload_dir", None)
    if configured:
        return Path(configured).expanduser().resolve() / market
    checkpoint_dir = getattr(args, "checkpoint_dir", None)
    base = Path(checkpoint_dir).expanduser().resolve().parent if checkpoint_dir else FUNCTIONS_DIR.parent / "runtime"
    return base / "local-analysis" / market


def _keep_file_path(args: argparse.Namespace, market: str) -> Path:
    configured = getattr(args, "keep_file", None)
    if configured:
        return Path(configured).expanduser().resolve()
    checkpoint_dir = getattr(args, "checkpoint_dir", None)
    base = Path(checkpoint_dir).expanduser().resolve() if checkpoint_dir else FUNCTIONS_DIR / ".checkpoints"
    return base / f"analysis_keep_{market}.json"


def _write_local_payload(directory: Path, payload: dict[str, Any]) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{payload['id']}.json.gz"
    content = gzip.compress(json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8"))
    if len(content) > 512 * 1024:
        raise ValueError(f"Local analysis payload exceeds 512 KiB: {payload['id']}")
    temporary = path.with_suffix(".tmp")
    temporary.write_bytes(content)
    temporary.replace(path)
    return path


def _read_local_payload(directory: Path, doc_id: str) -> dict[str, Any]:
    path = directory / f"{doc_id}.json.gz"
    if not path.exists():
        raise FileNotFoundError(f"Local analysis payload missing: {path}")
    return json.loads(gzip.decompress(path.read_bytes()).decode("utf-8"))


def _prune_local_payloads(directory: Path, keep_ids: set[str]) -> int:
    """Remove regenerable candidate payloads after a successful Firebase write."""
    keep_names = {f"{doc_id}.json.gz" for doc_id in keep_ids}
    removed = 0
    for path in directory.glob("*.json.gz"):
        if path.name in keep_names:
            continue
        path.unlink()
        removed += 1
    return removed


def _write_keep_file(path: Path, market: str, summaries: list[dict[str, Any]], limit: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "market": market,
        "limit": limit,
        "selection": "confidenceScore desc, marcap desc, code asc",
        "ids": [str(item.get("id")) for item in summaries],
        "updatedAt": datetime.now().isoformat(timespec="seconds"),
    }
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Mesugak V2 stock analysis")
    parser.add_argument("--market", default="KR")
    parser.add_argument("--codes", default=None, help="Comma-separated stock codes. If omitted, loads the full market universe.")
    parser.add_argument("--kr-markets", default="KOSPI,KOSDAQ", help="Comma-separated KR submarkets for universe mode")
    parser.add_argument("--max-stocks", type=int, default=None, help="Maximum number of ranked results stored in Firebase")
    parser.add_argument("--candidate-limit", type=int, default=None, help="Optional limit before local analysis")
    parser.add_argument(
        "--analyze-all-local",
        action="store_true",
        help="Analyse the full public-data universe locally, then persist only the ranked cap",
    )
    parser.add_argument("--local-payload-dir", default=None, help="Directory for server-only compressed analysis payloads")
    parser.add_argument("--keep-file", default=None, help="JSON file containing the selected Firebase document IDs")
    parser.add_argument("--cred-path", default=None)
    parser.add_argument("--checkpoint-dir", default=None)
    parser.add_argument("--reset-checkpoint", action="store_true")
    parser.add_argument("--meta-chunk-size", type=int, default=400)
    parser.add_argument("--progress-interval", type=int, default=10, help="Print progress every N processed stocks")
    parser.add_argument(
        "--retention-days",
        type=int,
        default=int(os.getenv("MESUGAK_RETENTION_DAYS", "30")),
        help="Number of days to keep historical operational data (default: 30)",
    )
    parser.add_argument(
        "--skip-retention-cleanup",
        action="store_true",
        default=os.getenv("MESUGAK_ENABLE_RETENTION_CLEANUP", "false").strip().lower() not in {"1", "true", "yes", "on"},
        help="Skip cleanup of past operational data (enabled only when MESUGAK_ENABLE_RETENTION_CLEANUP is true)",
    )
    parser.add_argument(
        "--history-limit",
        type=int,
        default=int(os.getenv("MESUGAK_HISTORY_LIMIT", "130")),
        help="Trading days of chart history to store per stock (default: 130)",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser


def _parse_csv(raw: str | None) -> list[str]:
    return [part.strip() for part in str(raw or "").split(",") if part.strip()]


def _load_targets(args: argparse.Namespace, market: str):
    candidate_limit = getattr(args, "candidate_limit", None)
    if getattr(args, "analyze_all_local", False):
        candidate_limit = None
    elif candidate_limit is None:
        # Preserve the old direct-call behaviour for paper-flow callers.
        candidate_limit = getattr(args, "max_stocks", None)
    if args.codes:
        targets = targets_from_codes(_parse_csv(args.codes))
    else:
        targets = load_market_universe(
            market,
            kr_markets=_parse_csv(args.kr_markets) if market == "KR" else None,
            max_stocks=candidate_limit,
        )
    if args.codes and candidate_limit is not None and candidate_limit > 0:
        targets = targets[:candidate_limit]
    return targets


def _save_meta_chunks(
    repo: FirestoreStrategyRepository,
    market: str,
    summaries: list[dict],
    chunk_size: int,
    previous_count: int = 0,
) -> int:
    chunks = []
    chunk_count = 0
    for index in range(0, len(summaries), chunk_size):
        chunks.append((chunk_count, summaries[index : index + chunk_size]))
        chunk_count += 1
    if hasattr(repo, "save_meta_chunks_batch"):
        repo.save_meta_chunks_batch(
            market,
            chunks,
            start_delete_index=chunk_count,
            previous_count=previous_count,
        )
    else:
        for chunk_idx, items in chunks:
            repo.save_meta_chunk(market, chunk_idx, items)
        for index in range(chunk_count, max(chunk_count, previous_count)):
            repo.delete_meta_chunk(market, index)
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


def load_server_env() -> None:
    load_dotenv(os.getenv("MESUGAK_ENV_FILE") or str(FUNCTIONS_DIR / ".env"))


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
    if market != "KR":
        raise ValueError("Financial Services Commission public analysis supports KR only")
    storage_limit = resolve_storage_limit(getattr(args, "max_stocks", None))
    local_ranked = bool(getattr(args, "analyze_all_local", False))
    targets = _load_targets(args, market)
    if len(targets) > (MAX_LOCAL_CANDIDATES if local_ranked else MAX_DAILY_STOCKS):
        raise ValueError(
            f"Local candidate analysis is limited to {MAX_LOCAL_CANDIDATES} stocks"
            if local_ranked
            else f"Daily analysis is limited to {MAX_DAILY_STOCKS} stocks; set --max-stocks explicitly before running"
        )
    if not 1 <= getattr(args, 'history_limit', 130) <= 130:
        raise ValueError('Stored chart history must be between 1 and 130 trading days')
    run_id = f"{market}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    repo = None if getattr(args, "dry_run", False) or local_ranked else FirestoreStrategyRepository(init_firestore(args.cred_path))
    checkpoint = (
        LocalCheckpointManager(resolve_checkpoint_path(market, args.checkpoint_dir), market)
        if not getattr(args, "dry_run", False) or getattr(args, "checkpoint_dir", None)
        else MemoryCheckpointManager(market)
    )
    if getattr(args, "reset_checkpoint", False):
        checkpoint.reset()
    analysis_mode = LOCAL_ANALYSIS_MODE if local_ranked else "direct_v1"
    universe_hash = _universe_hash(targets)
    previous_state = checkpoint.snapshot()
    if previous_state.get("analysisMode") != analysis_mode or previous_state.get("universeHash") != universe_hash:
        checkpoint.reset()
    checkpoint.set_metadata(analysisMode=analysis_mode, universeHash=universe_hash)
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
    write_batch_size = 40
    local_payload_dir = _local_payload_dir(args, market) if local_ranked else None
    batch_buffer: list[tuple[str, dict]] = []

    def flush_batch() -> None:
        nonlocal batch_buffer
        if repo and batch_buffer:
            if hasattr(repo, "save_stock_analyses_batch"):
                repo.save_stock_analyses_batch(batch_buffer)
            else:
                for doc_id, item_payload in batch_buffer:
                    repo.save_stock_analysis(doc_id, item_payload)
            batch_buffer = []

    print(
        f"[start] {market} runId={run_id} targets={len(targets)} "
        f"resumeDone={initial_done_count} remaining={len(remaining_targets)} "
        f"storageLimit={storage_limit} localRanked={local_ranked} dryRun={bool(getattr(args, 'dry_run', False))}",
        flush=True,
    )
    try:
        for offset, target in enumerate(remaining_targets):
            remaining_count = len(remaining_targets) - offset - 1
            try:
                df = load_ohlcv_with_public_data(target.code)
                payload = analyze_stock(
                    df,
                    StockIdentity(
                        market=market,
                        code=target.code,
                        name=target.name,
                        marcap=target.marcap,
                    ),
                    fundamentals={},
                    history_limit=getattr(args, "history_limit", 130),
                )
                if not payload:
                    failure = {"code": target.code, "reason": "insufficient_data"}
                    failures.append(failure)
                    checkpoint.record_failure(target.code, failure["reason"], remaining_count)
                    continue
                summary = to_summary(payload)
                summaries.append(summary)
                if local_ranked:
                    _write_local_payload(local_payload_dir, payload)
                elif repo:
                    batch_buffer.append((payload["id"], payload))
                    if len(batch_buffer) >= write_batch_size:
                        flush_batch()
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
        flush_batch()
        selected_summaries = select_top_summaries(summaries, storage_limit) if local_ranked else list(summaries)
        selected_payloads: list[tuple[str, dict[str, Any]]] = []
        if local_ranked:
            if not selected_summaries:
                raise RuntimeError("No successful local analyses are available for Firebase persistence")
            for summary in selected_summaries:
                doc_id = str(summary.get("id") or "")
                selected_payloads.append((doc_id, _read_local_payload(local_payload_dir, doc_id)))
            if not getattr(args, "dry_run", False):
                repo = FirestoreStrategyRepository(init_firestore(args.cred_path))
                for start in range(0, len(selected_payloads), write_batch_size):
                    repo.save_stock_analyses_batch(selected_payloads[start : start + write_batch_size])
            summaries = selected_summaries
        else:
            selected_summaries = summaries
        if repo:
            print(f"[meta] writing {len(summaries)} summaries to meta_data chunks size={args.meta_chunk_size}", flush=True)
            meta_doc_count = _save_meta_chunks(repo, market, summaries, args.meta_chunk_size, previous_count=previous_meta_doc_count)
            checkpoint.update_meta_doc_count(meta_doc_count)
            repo.save_strategy_run(
                run_id,
                {
                    "runId": run_id,
                    "market": market,
                    "status": "done",
                    "targetCount": len(targets),
                    "candidateCount": len(checkpoint.summaries()),
                    "storedCount": len(summaries),
                    "successCount": len(checkpoint.summaries()),
                    "failureCount": len(failures),
                    "failures": failures,
                    "selection": "confidenceScore desc, marcap desc, code asc" if local_ranked else "input_order",
                },
            )
            if local_ranked:
                _write_keep_file(_keep_file_path(args, market), market, summaries, storage_limit)
                pruned = _prune_local_payloads(
                    local_payload_dir,
                    {str(item.get("id")) for item in summaries if item.get("id")},
                )
                print(f"[local] pruned {pruned} regenerable candidate payloads", flush=True)
            if not getattr(args, "skip_retention_cleanup", False) and hasattr(repo, "cleanup_past_data"):
                retention_days = max(1, int(getattr(args, "retention_days", 30) or 30))
                print(f"[retention] cleaning up operational data older than {retention_days} days...", flush=True)
                cleanup_summary = repo.cleanup_past_data(market=market, retention_days=retention_days)
                print(f"[retention] cleanup finished: {cleanup_summary}", flush=True)
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
        try:
            flush_batch()
        except Exception:
            pass
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
        "candidateCount": len(checkpoint.summaries()),
        "storedCount": len(summaries),
        "successCount": len(checkpoint.summaries()),
        "failureCount": len(failures),
        "failures": failures,
        "selection": "confidenceScore desc, marcap desc, code asc" if local_ranked else "input_order",
    }


def main() -> None:
    load_server_env()
    args = build_parser().parse_args()
    result = run(args)
    print(result)


if __name__ == "__main__":
    main()
