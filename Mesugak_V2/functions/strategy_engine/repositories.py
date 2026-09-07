"""Persistence boundaries for Mesugak V2."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Protocol


class StrategyRepository(Protocol):
    def save_stock_analysis(self, doc_id: str, payload: dict) -> None:
        ...

    def save_meta_chunk(self, market: str, index: int, items: list[dict]) -> None:
        ...

    def save_public_meta_chunk(self, market: str, index: int, items: list[dict]) -> None:
        ...

    def save_public_manifest(self, market: str, items: list[dict], chunk_count: int, page_size: int) -> None:
        ...

    def save_private_paper_performance(self, payload: dict) -> None:
        ...

    def fetch_intraday_trade_state(self, market: str, session_date: str) -> dict:
        ...

    def save_intraday_trade_state(self, market: str, session_date: str, payload: dict) -> None:
        ...

    def save_target_allocation(self, allocation_id: str, payload: dict) -> None:
        ...

    def save_rebalance_order(self, order_id: str, payload: dict) -> None:
        ...

    def fetch_pending_paper_refresh_requests(self, limit: int = 5) -> list[dict]:
        ...

    def finish_paper_refresh_request(self, request_id: str, payload: dict) -> None:
        ...


def resolve_cred_path(explicit: str | None = None) -> Path:
    import os

    candidates = [
        explicit,
        os.getenv("BOT_FIREBASE_CRED_PATH"),
        os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH"),
        str(Path(__file__).resolve().parents[2] / "serviceAccountKey.json"),
        str(Path(__file__).resolve().parents[3] / "Mesugak_V1" / "functions" / "serviceAccountKey.json"),
        "./serviceAccountKey.json",
    ]
    checked: list[str] = []
    for raw in candidates:
        if not raw:
            continue
        path = Path(raw).expanduser().resolve()
        checked.append(str(path))
        if path.exists():
            return path
    raise FileNotFoundError("Firebase credential file not found. Checked: " + ", ".join(checked))


def init_firestore(cred_path: str | Path | None = None):
    import os

    import firebase_admin
    from firebase_admin import credentials, firestore

    if not firebase_admin._apps:
        if os.getenv("FIRESTORE_EMULATOR_HOST"):
            firebase_admin.initialize_app(options={"projectId": os.getenv("GCLOUD_PROJECT", "mesugak-v2-emulator")})
        else:
            try:
                resolved = resolve_cred_path(str(cred_path) if cred_path else None)
                firebase_admin.initialize_app(credentials.Certificate(str(resolved)))
            except FileNotFoundError:
                if cred_path:
                    raise
                firebase_admin.initialize_app()
    return firestore.client()


class FirestoreStrategyRepository:
    def __init__(self, db):
        self.db = db

    @staticmethod
    def _server_timestamp():
        from firebase_admin import firestore

        return firestore.SERVER_TIMESTAMP

    @staticmethod
    def _today() -> str:
        return datetime.now().strftime("%Y-%m-%d")

    def save_stock_analysis(self, doc_id: str, payload: dict[str, Any]) -> None:
        data = dict(payload)
        data["updatedAt"] = self._server_timestamp()
        self.db.collection("stock_analysis").document(doc_id).set(data)

    def save_meta_chunk(self, market: str, index: int, items: list[dict[str, Any]]) -> None:
        self.db.collection("meta_data").document(f"meta_v2_{market}_{index}").set(
            {
                "market": market,
                "strategyVersion": "V2",
                "list": items,
                "updatedAt": self._server_timestamp(),
            }
        )

    def delete_meta_chunk(self, market: str, index: int) -> None:
        self.db.collection("meta_data").document(f"meta_v2_{market}_{index}").delete()

    def save_public_meta_chunk(self, market: str, index: int, items: list[dict[str, Any]]) -> None:
        self.db.collection("public_analysis_meta").document(f"public_meta_v2_{market}_{index}").set(
            {
                "market": market,
                "strategyVersion": "V2_PUBLIC",
                "pageIndex": index,
                "pageSize": len(items),
                "list": items,
                "updatedAt": self._server_timestamp(),
            }
        )

    def save_public_manifest(self, market: str, items: list[dict[str, Any]], chunk_count: int, page_size: int) -> None:
        search_index = [
            {
                "code": item.get("code"),
                "name": item.get("name"),
                "page": index // page_size,
            }
            for index, item in enumerate(items)
        ]
        self.db.collection("public_analysis_meta").document(f"public_meta_v2_{market}_manifest").set(
            {
                "market": market,
                "strategyVersion": "V2_PUBLIC_MANIFEST",
                "totalCount": len(items),
                "chunkCount": chunk_count,
                "pageSize": page_size,
                "searchIndex": search_index,
                "updatedAt": self._server_timestamp(),
            }
        )

    def existing_public_chunk_count(self, market: str) -> int:
        prefix = f"public_meta_v2_{market}_"
        count = 0
        for snapshot in self.db.collection("public_analysis_meta").stream():
            suffix = snapshot.id.removeprefix(prefix) if snapshot.id.startswith(prefix) else ""
            if suffix.isdigit():
                count += 1
        return count

    def delete_public_meta_chunk(self, market: str, index: int) -> None:
        self.db.collection("public_analysis_meta").document(f"public_meta_v2_{market}_{index}").delete()

    def fetch_intraday_trade_state(self, market: str, session_date: str) -> dict[str, Any]:
        snapshot = self.db.collection("intraday_trade_state").document(f"{market}_{session_date}").get()
        return snapshot.to_dict() if snapshot.exists else {}

    def save_intraday_trade_state(self, market: str, session_date: str, payload: dict[str, Any]) -> None:
        data = dict(payload)
        data["market"] = market
        data["sessionDate"] = session_date
        data["updatedAt"] = self._server_timestamp()
        self.db.collection("intraday_trade_state").document(f"{market}_{session_date}").set(data, merge=True)

    def save_strategy_run(self, run_id: str, payload: dict[str, Any]) -> None:
        data = dict(payload)
        data["updatedAt"] = self._server_timestamp()
        self.db.collection("strategy_runs").document(run_id).set(data, merge=True)

    def save_strategy_candidate(self, candidate_id: str, payload: dict[str, Any]) -> None:
        data = dict(payload)
        data["updatedAt"] = self._server_timestamp()
        self.db.collection("strategy_candidates").document(candidate_id).set(data)

    def save_target_allocation(self, allocation_id: str, payload: dict[str, Any]) -> None:
        data = dict(payload)
        data["updatedAt"] = self._server_timestamp()
        self.db.collection("target_allocations").document(allocation_id).set(data)

    def save_rebalance_order(self, order_id: str, payload: dict[str, Any]) -> None:
        data = dict(payload)
        data["updatedAt"] = self._server_timestamp()
        self.db.collection("rebalance_orders").document(order_id).set(data)

    def save_risk_state(self, market: str, payload: dict[str, Any]) -> None:
        data = dict(payload)
        data["updatedAt"] = self._server_timestamp()
        self.db.collection("risk_state").document(market).set(data, merge=True)

    def fetch_meta_candidates(self, market: str) -> list[dict[str, Any]]:
        from google.cloud.firestore_v1 import FieldFilter

        docs = self.db.collection("meta_data").where(filter=FieldFilter("market", "==", market)).stream()
        rows: list[dict[str, Any]] = []
        for doc in docs:
            if not doc.id.startswith("meta_v2_"):
                continue
            data = doc.to_dict() or {}
            if data.get("strategyVersion") != "V2":
                continue
            rows.extend(data.get("list", []) or [])
        return rows

    def fetch_current_positions(self, collection_name: str = "bot_portfolio") -> dict[str, dict[str, Any]]:
        positions: dict[str, dict[str, Any]] = {}
        for doc in self.db.collection(collection_name).stream():
            positions[doc.id] = doc.to_dict() or {}
        return positions

    def fetch_account_snapshot(self, collection_name: str = "bot_account_snapshot", doc_id: str = "latest") -> dict[str, Any] | None:
        snap = self.db.collection(collection_name).document(doc_id).get()
        return snap.to_dict() if snap.exists else None

    def fetch_rebalance_orders(self, market: str, allocation_id: str | None = None) -> list[dict[str, Any]]:
        from google.cloud.firestore_v1 import FieldFilter

        query = self.db.collection("rebalance_orders").where(filter=FieldFilter("market", "==", market))
        if allocation_id:
            query = query.where(filter=FieldFilter("allocationId", "==", allocation_id))
        rows: list[dict[str, Any]] = []
        for doc in query.stream():
            rows.append({"id": doc.id, **(doc.to_dict() or {})})
        rows.sort(key=lambda item: (str(item.get("allocationId", "")), str(item.get("code", ""))))
        return rows

    def fetch_latest_prices(self, market: str, codes: list[str]) -> dict[str, float]:
        prices: dict[str, float] = {}
        for code in codes:
            doc_id = f"{market}_{code}"
            snap = self.db.collection("stock_analysis").document(doc_id).get()
            if not snap.exists:
                continue
            data = snap.to_dict() or {}
            price = data.get("currentPrice")
            if price is not None:
                prices[str(code)] = float(price)
        return prices

    def save_paper_positions(
        self,
        positions: dict[str, dict[str, Any]],
        *,
        collection_name: str = "bot_portfolio",
        previous_codes: set[str] | None = None,
    ) -> None:
        collection = self.db.collection(collection_name)
        active_codes = set(positions)
        for code, position in positions.items():
            data = dict(position)
            data["updatedAt"] = self._server_timestamp()
            collection.document(code).set(data, merge=True)
        for code in (previous_codes or set()) - active_codes:
            collection.document(code).delete()

    def append_trade_logs(self, logs: list[dict[str, Any]], collection_name: str = "bot_trade_logs") -> None:
        collection = self.db.collection(collection_name)
        for log in logs:
            data = dict(log)
            data["createdAt"] = self._server_timestamp()
            data["source"] = data.get("source", "Mesugak_V2")
            collection.add(data)

    def save_account_snapshot(
        self,
        payload: dict[str, Any],
        *,
        collection_name: str = "bot_account_snapshot",
        doc_id: str = "latest",
    ) -> None:
        data = dict(payload)
        data["updatedAt"] = self._server_timestamp()
        self.db.collection(collection_name).document(doc_id).set(data, merge=True)

    def save_private_paper_performance(self, payload: dict[str, Any]) -> None:
        """Persist only the administrator-only aggregate benchmark comparison."""
        data = dict(payload)
        data["visibility"] = "admin_only"
        data["updatedAt"] = self._server_timestamp()
        self.db.collection("paper_performance_private").document("latest").set(data, merge=True)
    def fetch_pending_paper_refresh_requests(self, limit: int = 5) -> list[dict[str, Any]]:
        """Return web-requested KIS balance refreshes for the school server.

        These documents are created by an authenticated administrator in the
        frontend. Only the school server processes them; no browser receives
        KIS credentials or calls the brokerage API directly.
        """
        from google.cloud.firestore_v1 import FieldFilter

        safe_limit = max(1, min(int(limit or 5), 20))
        query = (
            self.db.collection("paper_refresh_requests")
            .where(filter=FieldFilter("status", "==", "pending"))
            .limit(safe_limit)
        )
        return [{"id": doc.id, **(doc.to_dict() or {})} for doc in query.stream()]

    def finish_paper_refresh_request(self, request_id: str, payload: dict[str, Any]) -> None:
        """Record only refresh status metadata, not credentials or tokens."""
        data = dict(payload)
        data["updatedAt"] = self._server_timestamp()
        self.db.collection("paper_refresh_requests").document(request_id).set(data, merge=True)

    def save_paper_order_application(self, application_id: str, payload: dict[str, Any]) -> None:
        data = dict(payload)
        data["updatedAt"] = self._server_timestamp()
        self.db.collection("paper_order_applications").document(application_id).set(data, merge=True)
