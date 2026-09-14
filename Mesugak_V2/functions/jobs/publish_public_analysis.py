"""Publish price-free V2 analysis summaries for the public research screen."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

FUNCTIONS_DIR = Path(__file__).resolve().parents[1]
if str(FUNCTIONS_DIR) not in sys.path:
    sys.path.insert(0, str(FUNCTIONS_DIR))

from strategy_engine.analysis import to_public_summary
from strategy_engine.repositories import FirestoreStrategyRepository, init_firestore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Publish price-free Mesugak V2 public analysis")
    parser.add_argument("--market", default="KR")
    parser.add_argument("--cred-path", default=None)
    parser.add_argument("--meta-chunk-size", type=int, default=30)
    return parser


def _private_chunks(repo: FirestoreStrategyRepository, market: str) -> list[list[dict]]:
    chunks: list[tuple[int, list[dict]]] = []
    prefix = f"meta_v2_{market}_"
    for snapshot in repo.db.collection("meta_data").stream():
        if not snapshot.id.startswith(prefix):
            continue
        data = snapshot.to_dict() or {}
        if data.get("strategyVersion") != "V2" or data.get("market") != market:
            continue
        try:
            index = int(snapshot.id.removeprefix(prefix))
        except ValueError:
            continue
        chunks.append((index, list(data.get("list") or [])))
    return [items for _, items in sorted(chunks)]


def _existing_public_chunk_count(repo: FirestoreStrategyRepository, market: str) -> int:
    if hasattr(repo, "existing_public_chunk_count"):
        return repo.existing_public_chunk_count(market)
    manifest_doc = repo.db.collection("public_analysis_meta").document(f"public_meta_v2_{market}_manifest").get()
    if manifest_doc.exists:
        count = manifest_doc.to_dict().get("chunkCount")
        if count is not None:
            return int(count)
    prefix = f"public_meta_v2_{market}_"
    return sum(
        1
        for snapshot in repo.db.collection("public_analysis_meta").stream()
        if snapshot.id.startswith(prefix) and snapshot.id.removeprefix(prefix).isdigit()
    )


def run(args: argparse.Namespace, repo: FirestoreStrategyRepository | None = None) -> dict:
    market = str(args.market).upper().strip()
    if market != "KR":
        raise ValueError("Financial Services Commission public analysis supports KR only")
    repo = repo or FirestoreStrategyRepository(init_firestore(args.cred_path))
    source_chunks = _private_chunks(repo, market)
    if not source_chunks:
        raise RuntimeError(f"No V2 private metadata chunks found for market={market}")

    public_rows = sorted(
        (to_public_summary(item) for chunk in source_chunks for item in chunk),
        key=lambda item: (-float(item.get("confidenceScore") or 0), str(item.get("name") or "")),
    )
    chunk_size = max(1, int(args.meta_chunk_size or 30))
    previous_count = _existing_public_chunk_count(repo, market)
    chunks = []
    written = 0
    for index in range(0, len(public_rows), chunk_size):
        chunks.append((written, public_rows[index : index + chunk_size]))
        written += 1

    if hasattr(repo, "save_public_analysis_batch"):
        repo.save_public_analysis_batch(
            market=market,
            chunks=chunks,
            manifest_items=public_rows,
            chunk_count=written,
            page_size=chunk_size,
            start_delete_index=written,
            previous_count=previous_count,
        )
    else:
        for chunk_idx, chunk_items in chunks:
            repo.save_public_meta_chunk(market, chunk_idx, chunk_items)
        for index in range(written, max(written, previous_count)):
            repo.delete_public_meta_chunk(market, index)
        repo.save_public_manifest(market, public_rows, written, chunk_size)

    return {"market": market, "publicRowCount": len(public_rows), "chunkCount": written}


def main() -> None:
    result = run(build_parser().parse_args())
    print(result)


if __name__ == "__main__":
    main()
