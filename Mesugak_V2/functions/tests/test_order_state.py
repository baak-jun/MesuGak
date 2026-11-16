from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from strategy_engine.order_state import OrderStateStore  # noqa: E402


class OrderStateTests(unittest.TestCase):
    def test_signal_reservation_is_idempotent_and_recoverable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "orders.sqlite3"
            with OrderStateStore(path) as store:
                self.assertTrue(store.reserve_signal("s1", session_date="2026-09-23", code="005930", side="BUY", quantity=2, limit_price=1000, payload={"repriceCount": 0}))
                self.assertFalse(store.reserve_signal("s1", session_date="2026-09-23", code="005930", side="BUY", quantity=2))
                store.update("s1", status="SUBMITTED", broker_order_no="42", payload={"repriceCount": 0})
                self.assertEqual(store.by_broker_order("42")["signal_id"], "s1")
                self.assertEqual(store.pending()[0]["status"], "SUBMITTED")
                store.update("s1", status="ACCEPTED")
                self.assertEqual(store.pending()[0]["status"], "ACCEPTED")
                store.update("s1", status="UNKNOWN")
                self.assertEqual(store.pending()[0]["status"], "UNKNOWN")
                store.set_runtime("heartbeat", {"status": "ok"})
                self.assertEqual(store.get_runtime("heartbeat")["status"], "ok")
            self.assertTrue(path.exists())


if __name__ == "__main__":
    unittest.main()
