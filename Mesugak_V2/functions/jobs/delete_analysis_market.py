"""Explicitly remove a retired market from analysis-only collections.

This is intentionally separate from daily KR retention so a scheduled job can
never delete another market accidentally.  The user-authorized US cleanup can
skip a local backup because those inputs are reproducible from the public
source; the exact market field or document prefix is still verified before any
delete.  Account, order, portfolio, and paper-trading collections are not in
the allow-list and cannot be selected by this job.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

FUNCTIONS_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = FUNCTIONS_DIR.parent
if str(FUNCTIONS_DIR) not in sys.path:
    sys.path.insert(0, str(FUNCTIONS_DIR))

from google.cloud.firestore_v1 import LastUpdateOption

from jobs.maintain_cloud_storage import verified_archive
from strategy_engine.cost_control import check_cloud_budget, reserve_daily
from strategy_engine.repositories import init_firestore


ANALYSIS_COLLECTIONS = (
    "stock_analysis",
    "public_analysis_meta",
    "meta_data",
    "strategy_runs",
)
MAX_SCAN_DOCUMENTS = 5000
MAX_DELETE_DOCUMENTS = 5000
BATCH_SIZE = 200


def load_server_env() -> None:
    load_dotenv(PROJECT_ROOT / ".env.server")
    load_dotenv(os.getenv("MESUGAK_ENV_FILE") or str(FUNCTIONS_DIR / ".env"), override=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Delete one explicitly retired market from stock_analysis")
    parser.add_argument("--market", required=True, help="Retired market code, for example US")
    parser.add_argument("--cred-path", default=None)
    parser.add_argument("--root", type=Path, default=PROJECT_ROOT / "runtime")
    parser.add_argument("--archive-dir", type=Path, default=None)
    parser.add_argument(
        "--collections",
        default=",".join(ANALYSIS_COLLECTIONS),
        help="Comma-separated analysis collections from the fixed allow-list",
    )
    parser.add_argument("--skip-archive", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def _matches(snapshot, market: str) -> bool:
    data = snapshot.to_dict() or {}
    return data.get("market") == market or snapshot.id.startswith(f"{market}_")


def resolve_collections(raw: str | None) -> tuple[str, ...]:
    if raw is None:
        return ANALYSIS_COLLECTIONS
    requested = tuple(item.strip() for item in str(raw or "").split(",") if item.strip())
    if not requested:
        raise ValueError("At least one analysis collection is required")
    unknown = sorted(set(requested) - set(ANALYSIS_COLLECTIONS))
    if unknown:
        raise ValueError(f"Collections are not in the retired-market allow-list: {unknown}")
    return tuple(dict.fromkeys(requested))


def run(args: argparse.Namespace) -> dict:
    market = str(args.market).upper().strip()
    if not market or market == "KR" or not market.isalnum():
        raise ValueError("This job requires a non-KR retired market code")
    root = Path(args.root).expanduser().resolve()
    archive_dir = (Path(args.archive_dir) if args.archive_dir else root / "cloud-archives").expanduser().resolve()
    collections = resolve_collections(getattr(args, "collections", None))
    planned_reads = MAX_SCAN_DOCUMENTS * len(collections)
    check_cloud_budget(storage_required=False, planned_reads=planned_reads)
    ledger = root / "cost" / "budget.sqlite3"
    read_key = "retired_market_dry_run_reads" if args.dry_run else "retired_market_reads"
    reserve_daily(ledger, read_key, planned_reads, planned_reads * 3)
    db = init_firestore(args.cred_path)
    matched_by_collection: dict[str, list] = {}
    inventory_by_collection: dict[str, int] = {}
    for collection in collections:
        snapshots = list(db.collection(collection).stream())
        if len(snapshots) > MAX_SCAN_DOCUMENTS:
            raise RuntimeError(f"{collection} inventory exceeds reviewed limit: {len(snapshots)}")
        inventory_by_collection[collection] = len(snapshots)
        matched_by_collection[collection] = [snapshot for snapshot in snapshots if _matches(snapshot, market)]
    stale = [
        (collection, snapshot)
        for collection in collections
        for snapshot in matched_by_collection[collection]
    ]
    result = {
        "market": market,
        "collections": list(collections),
        "inventoryByCollection": inventory_by_collection,
        "matchedByCollection": {key: len(value) for key, value in matched_by_collection.items()},
        "inventoryCount": sum(inventory_by_collection.values()),
        "matchedCount": len(stale),
        "dryRun": bool(args.dry_run),
        "archiveSkipped": bool(args.skip_archive),
    }
    if len(stale) > MAX_DELETE_DOCUMENTS:
        raise RuntimeError(f"{market} matched {len(stale)} documents; reviewed delete limit is {MAX_DELETE_DOCUMENTS}")
    print(json.dumps(result, ensure_ascii=False), flush=True)
    if args.dry_run or not stale:
        return result
    reserve_daily(ledger, "retired_market_deletes", len(stale), MAX_DELETE_DOCUMENTS)
    if args.skip_archive:
        archive_path = None
    else:
        archive_path = verified_archive(archive_dir, [snapshot for _, snapshot in stale])
    deleted = 0
    for start in range(0, len(stale), BATCH_SIZE):
        batch = db.batch()
        chunk = stale[start : start + BATCH_SIZE]
        for collection, snapshot in chunk:
            batch.delete(snapshot.reference, option=LastUpdateOption(snapshot.update_time))
        batch.commit()
        deleted += len(chunk)
        print(json.dumps({"deleted": deleted, "total": len(stale)}), flush=True)
    remaining_by_collection = {
        collection: sum(1 for snapshot in db.collection(collection).stream() if _matches(snapshot, market))
        for collection in collections
    }
    if any(remaining_by_collection.values()):
        raise RuntimeError(f"Retired-market verification failed: {remaining_by_collection}")
    result.update(
        {
            "deletedCount": deleted,
            "remainingByCollection": remaining_by_collection,
            "archive": str(archive_path) if archive_path else None,
            "completedAt": datetime.now(timezone.utc).isoformat(),
        }
    )
    marker = root / "cost" / f"retired-market-{market}.json"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False), flush=True)
    return result


def main() -> None:
    load_server_env()
    print(run(build_parser().parse_args()))


if __name__ == "__main__":
    main()
