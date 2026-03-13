import argparse
import datetime as dt
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

import firebase_admin
from dotenv import load_dotenv
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1 import FieldFilter

from local_refresh_pending_orders import run_refresh as refresh_pending_orders


load_dotenv()
load_dotenv(Path(__file__).with_name(".env"))


def resolve_cred_path(explicit: Optional[str] = None) -> Path:
    candidates = [
        explicit,
        os.getenv("BOT_FIREBASE_CRED_PATH"),
        os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH"),
        str(Path(__file__).with_name("serviceAccountKey.json")),
        "./serviceAccountKey.json",
    ]
    checked = []
    for raw in candidates:
        if not raw:
            continue
        p = Path(raw).expanduser().resolve()
        checked.append(str(p))
        if p.exists():
            return p
    raise FileNotFoundError("Firebase credential file not found. Checked: " + ", ".join(checked))


def init_firestore(cred_path: Path):
    if not firebase_admin._apps:
        firebase_admin.initialize_app(credentials.Certificate(str(cred_path)))
    return firestore.client()


def build_analyzer(db):
    legacy_path = Path(__file__).with_name("legacy")
    if not legacy_path.exists():
        raise FileNotFoundError(f"Legacy folder not found: {legacy_path}")
    sys.path.insert(0, str(legacy_path))
    from analyzer import StockAnalyzer  # type: ignore

    return StockAnalyzer(db)


def _extract_code_from_doc_id(doc_id: str, market: str) -> str:
    prefix = f"{market}_"
    if doc_id.startswith(prefix):
        return doc_id[len(prefix) :]
    if "_" in doc_id:
        return doc_id.split("_", 1)[1]
    return doc_id


def load_fallback_targets_from_firestore(db, market: str) -> List[Dict]:
    # Fallback source 1: stock_analysis collection
    q = (
        db.collection("stock_analysis")
        .where(filter=FieldFilter("market", "==", market))
        .stream()
    )
    rows: List[Dict] = []
    seen = set()
    for doc in q:
        data = doc.to_dict() or {}
        sid = data.get("id", doc.id)
        code = _extract_code_from_doc_id(sid, market)
        if not code or code in seen:
            continue
        rows.append(
            {
                "Code": code,
                "Name": data.get("name", code),
                "Marcap": float(data.get("marcap", 0) or 0),
            }
        )
        seen.add(code)

    if rows:
        rows.sort(key=lambda x: float(x.get("Marcap", 0) or 0), reverse=True)
        print(f"[LOCAL_CHART] fallback targets from stock_analysis: {len(rows)}")
        return rows

    # Fallback source 2: meta_data collection
    meta_rows: List[Dict] = []
    meta_seen = set()
    meta_docs = db.collection("meta_data").stream()
    for doc in meta_docs:
        data = doc.to_dict() or {}
        for item in data.get("list", []):
            if item.get("market") != market:
                continue
            sid = item.get("id", "")
            code = _extract_code_from_doc_id(sid, market)
            if not code or code in meta_seen:
                continue
            meta_rows.append(
                {
                    "Code": code,
                    "Name": item.get("name", code),
                    "Marcap": float(item.get("marcap", 0) or 0),
                }
            )
            meta_seen.add(code)

    if meta_rows:
        meta_rows.sort(key=lambda x: float(x.get("Marcap", 0) or 0), reverse=True)
        print(f"[LOCAL_CHART] fallback targets from meta_data: {len(meta_rows)}")
    else:
        print("[LOCAL_CHART] fallback targets not found in Firestore")
    return meta_rows


def run_chart_refresh(db, market: str, max_stocks: Optional[int] = None):
    analyzer = build_analyzer(db)

    original = analyzer.get_target_stocks
    source_targets = original(market)
    if not source_targets:
        source_targets = load_fallback_targets_from_firestore(db, market)

    if max_stocks is not None and max_stocks > 0:
        print(f"[LOCAL_CHART] test mode enabled: max_stocks={max_stocks}")
        source_targets = source_targets[:max_stocks]

    if source_targets:
        analyzer.get_target_stocks = lambda m=market: source_targets  # type: ignore[method-assign]

    started = dt.datetime.now()
    print(f"[LOCAL_CHART] start market={market} at {started.isoformat(timespec='seconds')}")
    analyzer.run_market_analysis(market)
    ended = dt.datetime.now()
    elapsed = (ended - started).total_seconds()
    print(f"[LOCAL_CHART] done market={market} elapsed={elapsed:.1f}s")


def build_parser():
    p = argparse.ArgumentParser(
        description="Manual refresh for chart sources (stock_analysis/meta_data) and optional pending_orders"
    )
    p.add_argument("--market", default=os.getenv("BOT_MARKET", "KR"))
    p.add_argument("--cred-path", default=None, help="Service account json path")
    p.add_argument(
        "--max-stocks",
        type=int,
        default=None,
        help="Optional test mode: analyze only first N stocks",
    )
    p.add_argument(
        "--skip-pending-orders",
        action="store_true",
        help="Skip pending_orders refresh after chart refresh",
    )
    return p


def main():
    args = build_parser().parse_args()
    cred_path = resolve_cred_path(args.cred_path)
    db = init_firestore(cred_path)

    run_chart_refresh(db, market=args.market, max_stocks=args.max_stocks)

    if not args.skip_pending_orders:
        refresh_pending_orders(db, market=args.market, dry_run=False)


if __name__ == "__main__":
    main()
