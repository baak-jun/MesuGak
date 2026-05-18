import argparse
import copy
import datetime as dt
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import firebase_admin
from dotenv import load_dotenv
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1 import FieldFilter

try:
    from local_refresh_pending_orders import run_refresh as refresh_pending_orders
except ModuleNotFoundError:
    refresh_pending_orders = None


load_dotenv()
load_dotenv(Path(__file__).with_name(".env"))


CHECKPOINT_DIRNAME = ".checkpoints"


def strtobool_env(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def parse_markets(raw: Optional[str]) -> List[str]:
    if raw is None:
        return ["KR"]
    markets = [part.strip().upper() for part in str(raw).split(",") if part.strip()]
    return markets or ["KR"]


def parse_kr_markets(raw: Optional[str]) -> Optional[List[str]]:
    if raw is None or str(raw).strip() == "":
        return None
    markets = [part.strip().upper() for part in str(raw).split(",") if part.strip()]
    return markets or None


def resolve_market_max_stocks(market: str, cli_value: Optional[int]) -> Optional[int]:
    if cli_value is not None:
        return cli_value

    market_key = f"BOT_MAX_STOCKS_{market.upper()}"
    market_raw = os.getenv(market_key)
    if market_raw is not None and str(market_raw).strip() != "":
        value = int(str(market_raw).strip())
        return None if value <= 0 else value

    common_raw = os.getenv("BOT_MAX_STOCKS", "0")
    value = int(str(common_raw).strip() or "0")
    return None if value <= 0 else value


def today_str() -> str:
    return dt.date.today().isoformat()


def now_iso() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def resolve_checkpoint_path(market: str, explicit_dir: Optional[str] = None) -> Path:
    base_dir = (
        Path(explicit_dir).expanduser().resolve()
        if explicit_dir
        else Path(__file__).resolve().parent / CHECKPOINT_DIRNAME
    )
    return base_dir / f"chart_refresh_{market}.json"


class LocalCheckpointManager:
    def __init__(self, path: Path, market: str):
        self.path = path
        self.market = market
        self.state = self._load()

    def _default_state(self, previous_meta_doc_count: int = 0) -> Dict[str, Any]:
        return {
            "market": self.market,
            "run_date": today_str(),
            "status": "idle",
            "started_at": now_iso(),
            "updated_at": now_iso(),
            "finished_at": None,
            "total_count": 0,
            "remaining_count": 0,
            "done_codes": [],
            "processed_codes": [],
            "failed_codes": [],
            "summary_all": [],
            "meta_doc_count": previous_meta_doc_count,
        }

    def _load(self) -> Dict[str, Any]:
        if not self.path.exists():
            return self._default_state()
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return self._default_state()
            return self._normalize(data)
        except Exception:
            return self._default_state()

    def _normalize(self, state: Dict[str, Any]) -> Dict[str, Any]:
        previous_meta_doc_count = int(state.get("meta_doc_count", 0) or 0)
        normalized = self._default_state(previous_meta_doc_count=previous_meta_doc_count)
        normalized.update(state)

        for key in ("done_codes", "processed_codes", "failed_codes", "summary_all"):
            value = normalized.get(key, [])
            normalized[key] = value if isinstance(value, list) else []

        normalized["meta_doc_count"] = int(normalized.get("meta_doc_count", 0) or 0)
        normalized["total_count"] = int(normalized.get("total_count", 0) or 0)
        normalized["remaining_count"] = int(normalized.get("remaining_count", 0) or 0)
        normalized["market"] = self.market
        return normalized

    def _atomic_write(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.path.with_suffix(self.path.suffix + ".tmp")
        temp_path.write_text(
            json.dumps(self.state, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temp_path.replace(self.path)

    def snapshot(self) -> Dict[str, Any]:
        return copy.deepcopy(self.state)

    def reset(self):
        previous_meta_doc_count = int(self.state.get("meta_doc_count", 0) or 0)
        self.state = self._default_state(previous_meta_doc_count=previous_meta_doc_count)
        self.state["status"] = "reset"
        self._atomic_write()
        print(f"[LOCAL_CHART] checkpoint reset: {self.path}")

    def has_today_checkpoint(self) -> bool:
        return (
            self.state.get("market") == self.market
            and self.state.get("run_date") == today_str()
        )

    def prepare_for_run(self, total_count: int) -> Dict[str, Any]:
        if not self.has_today_checkpoint():
            previous_meta_doc_count = int(self.state.get("meta_doc_count", 0) or 0)
            self.state = self._default_state(previous_meta_doc_count=previous_meta_doc_count)
            self.state["status"] = "running"
            self.state["started_at"] = now_iso()
            self.state["updated_at"] = now_iso()
            self.state["total_count"] = total_count
            self.state["remaining_count"] = total_count
            self._atomic_write()
            print(f"[LOCAL_CHART] new local checkpoint created: {self.path}")
            return self.snapshot()

        self.state["status"] = "running"
        self.state["updated_at"] = now_iso()
        self.state["total_count"] = total_count
        self.state["remaining_count"] = max(
            0, total_count - len(self.state.get("done_codes", []))
        )
        self._atomic_write()
        print(
            f"[LOCAL_CHART] resume checkpoint found: "
            f"done={len(self.state.get('done_codes', []))}, "
            f"processed={len(self.state.get('processed_codes', []))}, "
            f"failed={len(self.state.get('failed_codes', []))}"
        )
        return self.snapshot()

    def apply_update(self, update: Dict[str, Any]):
        done_codes_to_add = update.get("done_codes_to_add", []) or []
        processed_codes_to_add = update.get("processed_codes_to_add", []) or []
        failed_codes_to_add = update.get("failed_codes_to_add", []) or []
        summary_items_to_add = update.get("summary_items_to_add", []) or []

        if done_codes_to_add:
            existing = set(self.state.get("done_codes", []))
            for code in done_codes_to_add:
                code_str = str(code)
                if code_str not in existing:
                    self.state["done_codes"].append(code_str)
                    existing.add(code_str)

        if processed_codes_to_add:
            existing = set(self.state.get("processed_codes", []))
            for code in processed_codes_to_add:
                code_str = str(code)
                if code_str not in existing:
                    self.state["processed_codes"].append(code_str)
                    existing.add(code_str)

        if failed_codes_to_add:
            existing = set(self.state.get("failed_codes", []))
            for code in failed_codes_to_add:
                code_str = str(code)
                if code_str not in existing:
                    self.state["failed_codes"].append(code_str)
                    existing.add(code_str)

        if summary_items_to_add:
            self.state["summary_all"].extend(summary_items_to_add)

        if "meta_doc_count" in update:
            self.state["meta_doc_count"] = int(update.get("meta_doc_count", 0) or 0)

        if "remaining_count" in update:
            self.state["remaining_count"] = int(update.get("remaining_count", 0) or 0)

        if "status" in update and update["status"]:
            self.state["status"] = str(update["status"])

        self.state["updated_at"] = now_iso()
        self._atomic_write()

    def mark_done(self):
        self.state["status"] = "done"
        self.state["remaining_count"] = 0
        self.state["updated_at"] = now_iso()
        self.state["finished_at"] = now_iso()
        self._atomic_write()
        print(f"[LOCAL_CHART] checkpoint marked done: {self.path}")

    def mark_interrupted(self):
        self.state["status"] = "interrupted"
        self.state["updated_at"] = now_iso()
        self._atomic_write()
        print(f"[LOCAL_CHART] checkpoint marked interrupted: {self.path}")


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


def get_code_from_target(item: Dict[str, Any], market: str) -> Optional[str]:
    code = item.get("Code")
    if code is not None and str(code).strip():
        return str(code).strip()

    sid = item.get("id")
    if sid is not None and str(sid).strip():
        return _extract_code_from_doc_id(str(sid).strip(), market)

    return None


def load_fallback_targets_from_firestore(db, market: str) -> List[Dict]:
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


def run_chart_refresh(
    db,
    market: str,
    max_stocks: Optional[int] = None,
    checkpoint_dir: Optional[str] = None,
    reset_checkpoint: bool = False,
    kr_markets: Optional[List[str]] = None,
):
    analyzer = build_analyzer(db)

    original = analyzer.get_target_stocks
    source_targets = original(market, kr_markets=kr_markets)
    if not source_targets:
        source_targets = load_fallback_targets_from_firestore(db, market)

    if max_stocks is not None and max_stocks > 0:
        print(f"[LOCAL_CHART] test mode enabled: max_stocks={max_stocks}")
        source_targets = source_targets[:max_stocks]

    checkpoint_path = resolve_checkpoint_path(market, checkpoint_dir)
    checkpoint_manager = LocalCheckpointManager(checkpoint_path, market)

    if reset_checkpoint:
        checkpoint_manager.reset()

    checkpoint_state = checkpoint_manager.prepare_for_run(total_count=len(source_targets))
    done_codes: Set[str] = set(checkpoint_state.get("done_codes", []) or [])

    if done_codes:
        filtered_targets = []
        for item in source_targets:
            code = get_code_from_target(item, market)
            if code and code in done_codes:
                continue
            filtered_targets.append(item)

        skipped = len(source_targets) - len(filtered_targets)
        source_targets = filtered_targets
        checkpoint_manager.apply_update({"remaining_count": len(source_targets)})
        print(
            f"[LOCAL_CHART] resume enabled: skipped={skipped}, "
            f"remaining={len(source_targets)}"
        )

    if not source_targets:
        print("[LOCAL_CHART] nothing to process")
        checkpoint_manager.mark_done()
        return

    analyzer.get_target_stocks = lambda m=market, kr_markets=None: source_targets  # type: ignore[method-assign]

    started = dt.datetime.now()
    print(f"[LOCAL_CHART] start market={market} at {started.isoformat(timespec='seconds')}")

    try:
        analyzer.run_market_analysis(
            market=market,
            kr_markets=kr_markets,
            resume_state=checkpoint_manager.snapshot(),
            checkpoint_callback=checkpoint_manager.apply_update,
        )
        checkpoint_manager.mark_done()
    except Exception:
        checkpoint_manager.mark_interrupted()
        raise

    ended = dt.datetime.now()
    elapsed = (ended - started).total_seconds()
    print(f"[LOCAL_CHART] done market={market} elapsed={elapsed:.1f}s")


def build_parser():
    p = argparse.ArgumentParser(
        description="Manual refresh for chart sources (stock_analysis/meta_data) with local resume checkpoint"
    )
    p.add_argument(
        "--market",
        default=os.getenv("BOT_MARKET", "KR"),
        help="Single market or comma-separated markets, e.g. KR or KR,US",
    )
    p.add_argument("--cred-path", default=None, help="Service account json path")
    p.add_argument(
        "--max-stocks",
        type=int,
        default=None,
        help="Optional CLI override: analyze only first N stocks per market",
    )
    p.add_argument(
        "--kr-markets",
        default=os.getenv("BOT_KR_MARKETS") or None,
        help="Comma-separated KR submarkets, e.g. KOSPI,KOSDAQ",
    )
    p.add_argument(
        "--checkpoint-dir",
        default=os.getenv("BOT_CHECKPOINT_DIR") or None,
        help="Directory for local checkpoint files (default: ./.checkpoints)",
    )
    p.add_argument(
        "--reset-checkpoint",
        action="store_true",
        help="Ignore today's checkpoint and start over",
    )
    p.add_argument(
        "--skip-pending-orders",
        action="store_true",
        default=strtobool_env(os.getenv("BOT_SKIP_PENDING_ORDERS", "false")),
        help="Skip pending_orders refresh after chart refresh",
    )
    return p


def main():
    args = build_parser().parse_args()
    cred_path = resolve_cred_path(args.cred_path)
    db = init_firestore(cred_path)

    markets = parse_markets(args.market)
    kr_markets = parse_kr_markets(args.kr_markets)
    print(f"[LOCAL_CHART] target markets: {markets}")
    if kr_markets:
        print(f"[LOCAL_CHART] KR submarkets filter: {kr_markets}")

    for market in markets:
        market_max_stocks = resolve_market_max_stocks(market, args.max_stocks)
        print(f"[LOCAL_CHART] market={market} max_stocks={market_max_stocks or 'ALL'}")

        run_chart_refresh(
            db,
            market=market,
            max_stocks=market_max_stocks,
            checkpoint_dir=args.checkpoint_dir,
            reset_checkpoint=args.reset_checkpoint,
            kr_markets=kr_markets if market == "KR" else None,
        )

        if not args.skip_pending_orders:
            if refresh_pending_orders is None:
                print("[LOCAL_CHART] skip pending_orders: local_refresh_pending_orders.py not found")
            else:
                refresh_pending_orders(db, market=market, dry_run=False)


if __name__ == "__main__":
    main()
