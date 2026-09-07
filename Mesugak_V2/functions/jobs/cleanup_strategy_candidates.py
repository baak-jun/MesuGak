"""Utility job to clean up legacy strategy_candidates documents from Firestore.

In older versions, every daily scan wrote 2,500 full documents into
`strategy_candidates/{runId}_{id}`, accumulating over 85,000 documents (~6GB)
and incurring Firebase storage overage charges.

This script deletes those documents in 400-item batches.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

FUNCTIONS_DIR = Path(__file__).resolve().parents[1]
if str(FUNCTIONS_DIR) not in sys.path:
    sys.path.insert(0, str(FUNCTIONS_DIR))

from strategy_engine.repositories import init_firestore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Delete orphaned strategy_candidates documents")
    parser.add_argument("--batch-size", type=int, default=50, help="Number of documents to delete per batch (default: 50)")
    parser.add_argument("--max-delete", type=int, default=0, help="Stop after deleting this many documents (0 = all)")
    parser.add_argument("--cred-path", default=None, help="Path to service account credentials JSON")
    return parser


def run(args: argparse.Namespace) -> int:
    db = init_firestore(args.cred_path)
    collection = db.collection("strategy_candidates")
    batch_size = max(1, min(500, int(args.batch_size)))
    deleted_total = 0

    print(f"[cleanup] Starting deletion of 'strategy_candidates' (batch size: {batch_size})...", flush=True)

    while True:
        limit = batch_size
        if args.max_delete > 0:
            remaining = args.max_delete - deleted_total
            if remaining <= 0:
                break
            limit = min(batch_size, remaining)

        # select([]) retrieves only document IDs/references without heavy fields
        docs = list(collection.select([]).limit(limit).stream())
        if not docs:
            break

        try:
            batch = db.batch()
            for doc in docs:
                batch.delete(doc.reference)
            batch.commit()

            deleted_total += len(docs)
            if deleted_total % 250 == 0 or len(docs) < limit:
                print(f"[cleanup] Deleted {deleted_total} documents...", flush=True)
            time.sleep(0.05)
        except Exception as exc:
            if "Transaction too big" in str(exc) or "INVALID_ARGUMENT" in str(exc):
                if batch_size > 10:
                    batch_size = max(10, batch_size // 2)
                    print(f"[cleanup] Batch size exceeded Firestore 10MB limit. Auto-reduced batch size to {batch_size}. Retrying...", flush=True)
                    continue
            raise

    print(f"[cleanup] Done. Total 'strategy_candidates' documents deleted: {deleted_total}", flush=True)
    return deleted_total


def main() -> None:
    args = build_parser().parse_args()
    run(args)


if __name__ == "__main__":
    main()
