"""Crash-safe local order state for the school-server paper trader."""

from __future__ import annotations

import json
import os
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class OrderStateStore:
    """A tiny SQLite WAL ledger used before and after every broker call.

    Firestore remains the reporting surface.  SQLite is the local source of
    truth needed to make a process restart or a lost HTTP response safe.
    """

    def __init__(self, path: str | Path):
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path, timeout=30)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA synchronous=NORMAL")
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                signal_id TEXT PRIMARY KEY,
                session_date TEXT NOT NULL,
                code TEXT NOT NULL,
                side TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                limit_price REAL NOT NULL DEFAULT 0,
                reason TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL,
                broker_order_no TEXT NOT NULL DEFAULT '',
                filled_quantity INTEGER NOT NULL DEFAULT 0,
                average_fill_price REAL NOT NULL DEFAULT 0,
                payload_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        self.connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_orders_broker_order_no
            ON orders(broker_order_no)
            """
        )
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS runtime_state (
                key TEXT PRIMARY KEY,
                value_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS email_outbox (
                event_key TEXT PRIMARY KEY, subject TEXT NOT NULL, body TEXT NOT NULL,
                created_at TEXT NOT NULL, sent_at TEXT, attempts INTEGER NOT NULL DEFAULT 0,
                next_attempt_at REAL NOT NULL DEFAULT 0, last_error TEXT NOT NULL DEFAULT ''
            )
        """)
        self.connection.commit()
        try:
            self.path.chmod(0o600)
        except OSError:
            pass

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "OrderStateStore":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def reserve_signal(
        self,
        signal_id: str,
        *,
        session_date: str,
        code: str,
        side: str,
        quantity: int,
        limit_price: float = 0.0,
        reason: str = "",
        payload: dict[str, Any] | None = None,
    ) -> bool:
        """Atomically reserve a signal; false means it was already seen."""
        now = _now()
        cursor = self.connection.execute(
            """
            INSERT OR IGNORE INTO orders(
                signal_id, session_date, code, side, quantity, limit_price,
                reason, status, payload_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'RESERVED', ?, ?, ?)
            """,
            (
                str(signal_id),
                str(session_date),
                str(code),
                str(side).upper(),
                int(quantity),
                float(limit_price or 0),
                str(reason or ""),
                json.dumps(payload or {}, ensure_ascii=False, default=str),
                now,
                now,
            ),
        )
        self.connection.commit()
        return cursor.rowcount == 1

    def update(self, signal_id: str, *, status: str, commit: bool = True, **fields: Any) -> None:
        allowed = {
            "broker_order_no": "broker_order_no",
            "filled_quantity": "filled_quantity",
            "average_fill_price": "average_fill_price",
            "quantity": "quantity",
            "limit_price": "limit_price",
            "reason": "reason",
        }
        assignments: list[str] = ["status = ?", "updated_at = ?"]
        values: list[Any] = [str(status).upper(), _now()]
        for key, column in allowed.items():
            if key in fields:
                assignments.append(f"{column} = ?")
                values.append(fields[key])
        if "payload" in fields:
            assignments.append("payload_json = ?")
            values.append(json.dumps(fields["payload"] or {}, ensure_ascii=False, default=str))
        values.append(str(signal_id))
        self.connection.execute(
            f"UPDATE orders SET {', '.join(assignments)} WHERE signal_id = ?",
            values,
        )
        if commit:
            self.connection.commit()

    def get(self, signal_id: str) -> dict[str, Any] | None:
        row = self.connection.execute("SELECT * FROM orders WHERE signal_id = ?", (str(signal_id),)).fetchone()
        return self._row(row) if row else None

    def by_broker_order(self, broker_order_no: str) -> dict[str, Any] | None:
        row = self.connection.execute(
            "SELECT * FROM orders WHERE broker_order_no = ? ORDER BY created_at DESC LIMIT 1",
            (str(broker_order_no),),
        ).fetchone()
        return self._row(row) if row else None

    def pending(self) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            "SELECT * FROM orders WHERE status IN ('RESERVED', 'SUBMITTED', 'ACCEPTED', 'PARTIALLY_FILLED', 'UNKNOWN') ORDER BY created_at"
        ).fetchall()
        return [self._row(row) for row in rows]

    def set_runtime(self, key: str, payload: dict[str, Any]) -> None:
        self.connection.execute(
            """
            INSERT INTO runtime_state(key, value_json, updated_at) VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json, updated_at=excluded.updated_at
            """,
            (str(key), json.dumps(payload, ensure_ascii=False, default=str), _now()),
        )
        self.connection.commit()

    def get_runtime(self, key: str) -> dict[str, Any] | None:
        row = self.connection.execute("SELECT value_json FROM runtime_state WHERE key = ?", (str(key),)).fetchone()
        if not row:
            return None
        try:
            value = json.loads(row["value_json"])
        except (TypeError, json.JSONDecodeError):
            return None
        return value if isinstance(value, dict) else None

    def queue_email(self, event_key: str, subject: str, body: str) -> bool:
        cursor = self.connection.execute(
            'INSERT OR IGNORE INTO email_outbox(event_key, subject, body, created_at) VALUES (?, ?, ?, ?)',
            (event_key, subject, body, _now()),
        )
        self.connection.commit()
        return cursor.rowcount == 1

    def pending_emails(self, *, limit: int = 10, now: float | None = None) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            'SELECT * FROM email_outbox WHERE sent_at IS NULL AND next_attempt_at <= ? ORDER BY created_at, rowid LIMIT ?',
            (time.time() if now is None else now, max(1, int(limit))),
        ).fetchall()
        return [dict(row) for row in rows]

    def finish_email(self, event_key: str, *, error: str = '') -> None:
        if error:
            row = self.connection.execute('SELECT attempts FROM email_outbox WHERE event_key = ?', (event_key,)).fetchone()
            attempts = int(row[0] if row else 0) + 1
            delay = min(1800, 30 * 2 ** min(attempts - 1, 6))
            self.connection.execute('UPDATE email_outbox SET attempts=?, next_attempt_at=?, last_error=? WHERE event_key=?',
                                    (attempts, time.time() + delay, error, event_key))
        else:
            self.connection.execute('UPDATE email_outbox SET sent_at=?, last_error=? WHERE event_key=?', (_now(), '', event_key))
        self.connection.commit()

    def claim_email(self, event_key: str) -> bool:
        now = time.time()
        cursor = self.connection.execute(
            'UPDATE email_outbox SET next_attempt_at=? WHERE event_key=? AND sent_at IS NULL AND next_attempt_at<=?',
            (now + 120, event_key, now),
        )
        self.connection.commit()
        return cursor.rowcount == 1

    @staticmethod
    def _row(row: sqlite3.Row) -> dict[str, Any]:
        result = dict(row)
        try:
            result["payload"] = json.loads(result.pop("payload_json") or "{}")
        except (TypeError, json.JSONDecodeError):
            result["payload"] = {}
        return result
