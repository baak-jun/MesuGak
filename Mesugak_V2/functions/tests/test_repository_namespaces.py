from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from strategy_engine.repositories import FirestoreStrategyRepository  # noqa: E402


class FakeSnapshot:
    exists = False

    @staticmethod
    def to_dict():
        return None


class FakeDocument:
    def __init__(self, db, collection_name, document_id):
        self.db = db
        self.collection_name = collection_name
        self.document_id = document_id

    def get(self):
        return FakeSnapshot()

    def set(self, payload, merge=False):
        self.db.writes.append((self.collection_name, self.document_id, payload))

    def delete(self):
        self.db.deletes.append((self.collection_name, self.document_id))


class FakeCollection:
    def __init__(self, db, name):
        self.db = db
        self.name = name

    def document(self, document_id):
        return FakeDocument(self.db, self.name, document_id)

    def stream(self):
        return []

    def add(self, payload):
        self.db.writes.append((self.name, "auto-id", payload))


class FakeDatabase:
    def __init__(self):
        self.collection_names = []
        self.writes = []
        self.deletes = []

    def collection(self, name):
        self.collection_names.append(name)
        return FakeCollection(self, name)


class RepositoryNamespaceTests(unittest.TestCase):
    def test_contest_paper_state_reads_and_writes_are_isolated(self):
        db = FakeDatabase()
        repo = FirestoreStrategyRepository(db, paper_namespace="contest")

        with patch.object(FirestoreStrategyRepository, "_server_timestamp", return_value="timestamp"):
            repo.fetch_current_positions()
            repo.fetch_account_snapshot()
            repo.fetch_intraday_trade_state("KR", "2026-10-01")
            repo.save_intraday_trade_state("KR", "2026-10-01", {})
            repo.save_paper_positions({}, previous_codes=set())
            repo.append_trade_logs([])
            repo.save_account_snapshot({})
            repo.save_intraday_runtime_state({})
            repo.append_intraday_runtime_event({})
            repo.save_private_paper_performance({})
            repo.save_paper_order_application("order", {})

        self.assertEqual(
            set(db.collection_names),
            {
                "contest_bot_portfolio",
                "contest_bot_account_snapshot",
                "contest_intraday_trade_state",
                "contest_bot_trade_logs",
                "contest_paper_trading_runtime",
                "contest_paper_trading_runtime_events",
                "contest_paper_performance_private",
                "contest_paper_order_applications",
            },
        )
        self.assertTrue(db.writes)
        self.assertTrue(all(name.startswith("contest_") for name, _, _ in db.writes))

    def test_default_site_repository_keeps_legacy_collection_names(self):
        db = FakeDatabase()
        repo = FirestoreStrategyRepository(db)

        repo.fetch_current_positions()
        repo.fetch_account_snapshot()
        repo.save_intraday_runtime_state({})

        self.assertEqual(
            db.collection_names,
            ["bot_portfolio", "bot_account_snapshot", "paper_trading_runtime"],
        )

    def test_paper_namespace_rejects_collection_path_characters(self):
        with self.assertRaises(ValueError):
            FirestoreStrategyRepository(FakeDatabase(), paper_namespace="contest/subdir")


if __name__ == "__main__":
    unittest.main()
