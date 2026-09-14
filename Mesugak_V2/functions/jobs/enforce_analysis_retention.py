"""Keep only the selected KR analysis universe in Firestore.

The job is deliberately fail-closed: it derives the keep set from the same
public-data universe used by the analysis job and issues bounded, conditional
deletes. A local archive is opt-in for exceptional recovery; the scheduled
production path passes ``--skip-archive`` because these inputs are
regenerable from the public API. It never touches users, paper-trading,
orders, or public-feed collections.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from dotenv import load_dotenv

FUNCTIONS_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = FUNCTIONS_DIR.parent
if str(FUNCTIONS_DIR) not in sys.path:
    sys.path.insert(0, str(FUNCTIONS_DIR))

from google.cloud.firestore_v1 import LastUpdateOption

from jobs.maintain_cloud_storage import verified_archive
from strategy_engine.cost_control import check_cloud_budget, reserve_daily
from strategy_engine.market_data import load_market_universe
from strategy_engine.repositories import init_firestore


MAX_RETENTION_STOCKS = 1000
# The reviewed inventory is 4,315 documents; leave a small bounded margin.
MAX_SCAN_DOCUMENTS = 5000
MAX_DELETE_DOCUMENTS = 5000
BATCH_SIZE = 200


def load_server_env() -> None:
    """Load server defaults without printing secret values."""
    load_dotenv(PROJECT_ROOT / ".env.server")
    env_file = os.getenv("MESUGAK_ENV_FILE") or str(FUNCTIONS_DIR / ".env")
    load_dotenv(env_file, override=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bound KR stock_analysis retention")
    parser.add_argument("--market", default="KR")
    parser.add_argument(
        "--max-stocks",
        type=int,
        default=None,
        help="Number of current universe documents to keep (default: MESUGAK_MAX_STOCKS or 1000)",
    )
    parser.add_argument("--cred-path", default=None)
    parser.add_argument("--root", type=Path, default=PROJECT_ROOT / "runtime")
    parser.add_argument("--archive-dir", type=Path, default=None)
    parser.add_argument("--keep-file", type=Path, default=None, help="Selected IDs produced by local ranked analysis")
    parser.add_argument(
        "--skip-archive",
        action="store_true",
        help="Delete regenerable stale analysis without creating a local backup",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser


def resolve_limit(value: int | None) -> int:
    if value is None:
        value = int(os.getenv("MESUGAK_RETENTION_MAX_STOCKS", os.getenv("MESUGAK_MAX_STOCKS", "1000")))
    value = int(value)
    if not 1 <= value <= MAX_RETENTION_STOCKS:
        raise ValueError(f"Retention limit must be between 1 and {MAX_RETENTION_STOCKS}")
    return value


def select_stale_snapshots(
    snapshots: Iterable,
    *,
    market: str,
    keep_ids: set[str],
) -> list:
    """Select only active-market documents outside the keep set."""
    prefix = f"{market}_"
    stale = []
    for snapshot in snapshots:
        data = snapshot.to_dict() or {}
        belongs = data.get("market") == market or snapshot.id.startswith(prefix)
        if belongs and snapshot.id not in keep_ids:
            stale.append(snapshot)
    return stale


def keep_set_hash(keep_ids: set[str]) -> str:
    payload = "\n".join(sorted(keep_ids)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_keep_file(path: Path, market: str, limit: int) -> set[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if str(data.get("market") or "").upper().strip() != market:
        raise ValueError(f"Keep file market does not match {market}: {path}")
    ids = {str(item).strip() for item in data.get("ids") or [] if str(item).strip()}
    if not ids or len(ids) > limit:
        raise ValueError(f"Keep file contains {len(ids)} IDs; expected 1..{limit}")
    if any(not item.startswith(f"{market}_") for item in ids):
        raise ValueError("Keep file contains an ID outside the active market")
    return ids


def _write_marker(root: Path, payload: dict) -> None:
    marker = root / "cost" / "analysis-retention.json"
    marker.parent.mkdir(parents=True, exist_ok=True)
    temporary = marker.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(marker)


def run(args: argparse.Namespace) -> dict:
    market = str(args.market).upper().strip()
    if market != "KR":
        raise ValueError("Retention currently supports KR only")
    limit = resolve_limit(args.max_stocks)
    root = Path(args.root).expanduser().resolve()
    archive_dir = (Path(args.archive_dir) if args.archive_dir else root / "cloud-archives").expanduser().resolve()

    keep_file = Path(args.keep_file).expanduser().resolve() if args.keep_file else None
    if keep_file and keep_file.exists():
        keep_ids = load_keep_file(keep_file, market, limit)
        selection_source = str(keep_file)
    else:
        targets = load_market_universe(
            market,
            kr_markets=[item for item in os.getenv("MESUGAK_KR_MARKETS", "KOSPI,KOSDAQ").split(",") if item.strip()],
            max_stocks=limit,
        )
        keep_ids = {f"{market}_{target.code}" for target in targets}
        if len(keep_ids) != len(targets):
            raise RuntimeError("Public-data universe contains duplicate document IDs")
        selection_source = "market_cap_fallback"

    # Bound the collection scan before the first Firestore stream call.
    check_cloud_budget(storage_required=False, planned_reads=MAX_SCAN_DOCUMENTS)
    ledger = root / "cost" / "budget.sqlite3"
    # A dry-run is an intentional inventory read. Keep it in a separate
    # allowance so the reviewed dry-run + one real cleanup can both run on
    # the same day without making the actual retention job fail closed.
    read_key = "analysis_retention_dry_run_reads" if args.dry_run else "analysis_retention_reads"
    read_ceiling = MAX_SCAN_DOCUMENTS if args.dry_run else 15000
    reserve_daily(ledger, read_key, MAX_SCAN_DOCUMENTS, read_ceiling)
    db = init_firestore(args.cred_path)
    snapshots = list(db.collection("stock_analysis").stream())
    if len(snapshots) > MAX_SCAN_DOCUMENTS:
        raise RuntimeError(f"stock_analysis inventory {len(snapshots)} exceeds reviewed scan limit {MAX_SCAN_DOCUMENTS}")
    stale = select_stale_snapshots(
        snapshots,
        market=market,
        keep_ids=keep_ids,
    )
    market_count = sum(
        1
        for snapshot in snapshots
        if (snapshot.to_dict() or {}).get("market") == market or snapshot.id.startswith(f"{market}_")
    )
    current_ids = {snapshot.id for snapshot in snapshots}
    result = {
        "market": market,
        "keepRequested": limit,
        "keepSetCount": len(keep_ids),
        "keepSetHash": keep_set_hash(keep_ids),
        "selectionSource": selection_source,
        "inventoryCount": len(snapshots),
        "marketInventoryCount": market_count,
        "keepPresentCount": len(keep_ids & current_ids),
        "missingKeepCount": len(keep_ids - current_ids),
        "staleCount": len(stale),
        "dryRun": bool(args.dry_run),
    }
    if len(stale) > MAX_DELETE_DOCUMENTS:
        raise RuntimeError(f"{len(stale)} stale documents exceeds reviewed delete limit {MAX_DELETE_DOCUMENTS}")
    print(json.dumps(result, ensure_ascii=False), flush=True)
    if args.dry_run or not stale:
        return result

    reserve_daily(ledger, "analysis_retention_deletes", len(stale), MAX_DELETE_DOCUMENTS)
    if args.skip_archive:
        archive_path = None
    else:
        archive_path = verified_archive(archive_dir, stale)
    result["archive"] = str(archive_path) if archive_path else None
    # Conditional deletes prevent a concurrent analysis write from being removed.
    deleted = 0
    for start in range(0, len(stale), BATCH_SIZE):
        batch = db.batch()
        chunk = stale[start : start + BATCH_SIZE]
        for snapshot in chunk:
            batch.delete(snapshot.reference, option=LastUpdateOption(snapshot.update_time))
        batch.commit()
        deleted += len(chunk)
        print(json.dumps({"deleted": deleted, "total": len(stale)}), flush=True)

    remaining_market_count = market_count - sum(
        1
        for snapshot in stale
        if (snapshot.to_dict() or {}).get("market") == market or snapshot.id.startswith(f"{market}_")
    )
    if remaining_market_count > limit:
        raise RuntimeError(
            f"Retention verification failed: {remaining_market_count} {market} documents remain; limit={limit}"
        )
    result.update(
        {
            "deletedCount": deleted,
            "remainingMarketCount": remaining_market_count,
            "completedAt": datetime.now(timezone.utc).isoformat(),
        }
    )
    _write_marker(root, result)
    print(json.dumps(result, ensure_ascii=False), flush=True)
    return result


def main() -> None:
    load_server_env()
    args = build_parser().parse_args()
    print(run(args))


if __name__ == "__main__":
    main()
