"""Local checkpoint support for resumable analysis jobs."""

from __future__ import annotations

import copy
import datetime as dt
import json
from pathlib import Path
from typing import Any


def today_str() -> str:
    return dt.date.today().isoformat()


def now_iso() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


class LocalCheckpointManager:
    def __init__(self, path: Path, market: str):
        self.path = path
        self.market = market
        self.state = self._load()

    def _default_state(self, previous_meta_doc_count: int = 0) -> dict[str, Any]:
        return {
            "market": self.market,
            "runDate": today_str(),
            "status": "idle",
            "startedAt": now_iso(),
            "updatedAt": now_iso(),
            "finishedAt": None,
            "totalCount": 0,
            "remainingCount": 0,
            "doneCodes": [],
            "failedCodes": [],
            "summaries": [],
            "metaDocCount": previous_meta_doc_count,
        }

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return self._default_state()
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return self._default_state()
        if not isinstance(data, dict):
            return self._default_state()
        return self._normalize(data)

    def _normalize(self, state: dict[str, Any]) -> dict[str, Any]:
        normalized = self._default_state(previous_meta_doc_count=int(state.get("metaDocCount", 0) or 0))
        normalized.update(state)
        for key in ("doneCodes", "failedCodes", "summaries"):
            if not isinstance(normalized.get(key), list):
                normalized[key] = []
        for key in ("totalCount", "remainingCount", "metaDocCount"):
            normalized[key] = int(normalized.get(key, 0) or 0)
        normalized["market"] = self.market
        return normalized

    def _atomic_write(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.path.with_suffix(self.path.suffix + ".tmp")
        temp_path.write_text(json.dumps(self.state, ensure_ascii=False, indent=2), encoding="utf-8")
        temp_path.replace(self.path)

    def reset(self) -> None:
        previous_meta_doc_count = int(self.state.get("metaDocCount", 0) or 0)
        self.state = self._default_state(previous_meta_doc_count=previous_meta_doc_count)
        self.state["status"] = "reset"
        self._atomic_write()

    def prepare(self, total_count: int) -> dict[str, Any]:
        if self.state.get("runDate") != today_str() or self.state.get("market") != self.market:
            previous_meta_doc_count = int(self.state.get("metaDocCount", 0) or 0)
            self.state = self._default_state(previous_meta_doc_count=previous_meta_doc_count)
        self.state["status"] = "running"
        self.state["totalCount"] = int(total_count)
        self.state["remainingCount"] = max(0, total_count - len(self.state.get("doneCodes", [])))
        self.state["updatedAt"] = now_iso()
        self._atomic_write()
        return self.snapshot()

    def snapshot(self) -> dict[str, Any]:
        return copy.deepcopy(self.state)

    def done_codes(self) -> set[str]:
        return {str(code) for code in self.state.get("doneCodes", [])}

    def summaries(self) -> list[dict[str, Any]]:
        return list(self.state.get("summaries", []) or [])

    def record_success(self, code: str, summary: dict[str, Any], remaining_count: int) -> None:
        if code not in self.done_codes():
            self.state["doneCodes"].append(code)
            self.state["summaries"].append(summary)
        self.state["remainingCount"] = int(remaining_count)
        self.state["updatedAt"] = now_iso()
        self._atomic_write()

    def record_failure(self, code: str, reason: str, remaining_count: int) -> None:
        existing = {str(item.get("code")) for item in self.state.get("failedCodes", []) if isinstance(item, dict)}
        if code not in existing:
            self.state["failedCodes"].append({"code": code, "reason": reason})
        self.state["remainingCount"] = int(remaining_count)
        self.state["updatedAt"] = now_iso()
        self._atomic_write()

    def update_meta_doc_count(self, count: int) -> None:
        self.state["metaDocCount"] = int(count)
        self.state["updatedAt"] = now_iso()
        self._atomic_write()

    def mark_done(self) -> None:
        self.state["status"] = "done"
        self.state["remainingCount"] = 0
        self.state["updatedAt"] = now_iso()
        self.state["finishedAt"] = now_iso()
        self._atomic_write()

    def mark_interrupted(self) -> None:
        self.state["status"] = "interrupted"
        self.state["updatedAt"] = now_iso()
        self._atomic_write()


def resolve_checkpoint_path(market: str, explicit_dir: str | None = None) -> Path:
    base_dir = Path(explicit_dir).expanduser().resolve() if explicit_dir else Path(__file__).resolve().parents[1] / ".checkpoints"
    return base_dir / f"analyze_market_{market}.json"


class MemoryCheckpointManager:
    """Checkpoint-compatible manager for runs that must not touch disk."""

    def __init__(self, market: str):
        self.market = market
        self.path = None
        self.state = {
            "market": self.market,
            "runDate": today_str(),
            "status": "idle",
            "startedAt": now_iso(),
            "updatedAt": now_iso(),
            "finishedAt": None,
            "totalCount": 0,
            "remainingCount": 0,
            "doneCodes": [],
            "failedCodes": [],
            "summaries": [],
            "metaDocCount": 0,
        }

    def reset(self) -> None:
        self.__init__(self.market)
        self.state["status"] = "reset"

    def prepare(self, total_count: int) -> dict[str, Any]:
        self.state["status"] = "running"
        self.state["totalCount"] = int(total_count)
        self.state["remainingCount"] = int(total_count)
        self.state["updatedAt"] = now_iso()
        return self.snapshot()

    def snapshot(self) -> dict[str, Any]:
        return copy.deepcopy(self.state)

    def done_codes(self) -> set[str]:
        return set()

    def summaries(self) -> list[dict[str, Any]]:
        return list(self.state.get("summaries", []) or [])

    def record_success(self, code: str, summary: dict[str, Any], remaining_count: int) -> None:
        self.state["doneCodes"].append(code)
        self.state["summaries"].append(summary)
        self.state["remainingCount"] = int(remaining_count)
        self.state["updatedAt"] = now_iso()

    def record_failure(self, code: str, reason: str, remaining_count: int) -> None:
        self.state["failedCodes"].append({"code": code, "reason": reason})
        self.state["remainingCount"] = int(remaining_count)
        self.state["updatedAt"] = now_iso()

    def update_meta_doc_count(self, count: int) -> None:
        self.state["metaDocCount"] = int(count)
        self.state["updatedAt"] = now_iso()

    def mark_done(self) -> None:
        self.state["status"] = "done"
        self.state["remainingCount"] = 0
        self.state["updatedAt"] = now_iso()
        self.state["finishedAt"] = now_iso()

    def mark_interrupted(self) -> None:
        self.state["status"] = "interrupted"
        self.state["updatedAt"] = now_iso()
