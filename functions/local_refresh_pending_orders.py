import argparse
import datetime as dt
import os
from pathlib import Path
from typing import Optional

import firebase_admin
from dotenv import load_dotenv
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1 import FieldFilter

try:
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover
    ZoneInfo = None


load_dotenv()
load_dotenv(Path(__file__).with_name(".env"))


def resolve_cred_path(explicit: Optional[str] = None) -> Path:
    candidates = [
        explicit,
        os.getenv("BOT_FIREBASE_CRED_PATH"),
        os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH"),
        "./serviceAccountKey.json",
        str(Path(__file__).with_name("serviceAccountKey.json")),
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


def kst_today() -> str:
    if ZoneInfo is None:
        return dt.datetime.now().strftime("%Y-%m-%d")
    return dt.datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d")


def run_refresh(db, market: str, dry_run: bool = False):
    date = kst_today()
    signals = (
        db.collection("stock_analysis")
        .where(filter=FieldFilter("type", "==", "buy_signal"))
        .where(filter=FieldFilter("market", "==", market))
        .stream()
    )

    docs = list(signals)
    if not docs:
        print(f"[LOCAL_REFRESH] no buy_signal docs for market={market}")
        return

    batch = db.batch()
    op_count = 0
    upserted = 0

    for doc in docs:
        data = doc.to_dict() or {}
        stock_id = data.get("id", doc.id)
        code = stock_id.split("_", 1)[1] if "_" in stock_id else stock_id
        if not code:
            continue

        payload = {
            "code": code,
            "name": data.get("name", code),
            "market": market,
            "status": "ready",
            "signalType": "buy_signal",
            "sourceAnalysisId": doc.id,
            "date": date,
            "updatedAt": firestore.SERVER_TIMESTAMP,
        }

        if dry_run:
            upserted += 1
            continue

        ref = db.collection("pending_orders").document(f"{market}_{code}")
        batch.set(ref, payload, merge=True)
        op_count += 1
        upserted += 1

        if op_count >= 450:
            batch.commit()
            batch = db.batch()
            op_count = 0

    if not dry_run and op_count > 0:
        batch.commit()

    mode = "DRY_RUN" if dry_run else "APPLIED"
    print(
        f"[LOCAL_REFRESH][{mode}] market={market} sourceSignals={len(docs)} upserted={upserted} date={date}"
    )


def build_parser():
    p = argparse.ArgumentParser(
        description="Local fallback: refresh pending_orders from stock_analysis buy_signal docs"
    )
    p.add_argument("--market", default=os.getenv("BOT_MARKET", "KR"))
    p.add_argument("--cred-path", default=None, help="Service account json path")
    p.add_argument("--dry-run", action="store_true", help="Read only; do not write to Firestore")
    return p


def main():
    args = build_parser().parse_args()
    cred_path = resolve_cred_path(args.cred_path)
    db = init_firestore(cred_path)
    run_refresh(db, market=args.market, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
