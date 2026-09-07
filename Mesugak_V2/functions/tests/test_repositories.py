import unittest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

FUNCTIONS_DIR = Path(__file__).resolve().parents[1]
if str(FUNCTIONS_DIR) not in sys.path:
    sys.path.insert(0, str(FUNCTIONS_DIR))

from strategy_engine.repositories import FirestoreStrategyRepository


class PublicManifestRepositoryTests(unittest.TestCase):
    def test_search_index_uses_maps_instead_of_nested_arrays(self) -> None:
        db = MagicMock()
        document = db.collection.return_value.document.return_value
        repo = FirestoreStrategyRepository(db)

        with patch.object(repo, "_server_timestamp", return_value="now"):
            repo.save_public_manifest(
                "KR",
                [{"id": "KR_005930", "code": "005930", "name": "Samsung"}],
                chunk_count=1,
                page_size=30,
            )

        payload = document.set.call_args.args[0]
        self.assertEqual(
            payload["searchIndex"],
            [{"code": "005930", "name": "Samsung", "page": 0}],
        )

    def test_save_stock_analyses_batch(self) -> None:
        db = MagicMock()
        batch = db.batch.return_value
        repo = FirestoreStrategyRepository(db)

        with patch.object(repo, "_server_timestamp", return_value="now"):
            repo.save_stock_analyses_batch([
                ("KR_005930", {"code": "005930", "name": "Samsung"}),
                ("KR_000660", {"code": "000660", "name": "SK Hynix"}),
            ])

        self.assertEqual(batch.set.call_count, 2)
        batch.commit.assert_called_once()

    def test_save_meta_chunks_batch(self) -> None:
        db = MagicMock()
        batch = db.batch.return_value
        repo = FirestoreStrategyRepository(db)

        chunks = [(0, [{"code": "005930"}]), (1, [{"code": "000660"}])]
        with patch.object(repo, "_server_timestamp", return_value="now"):
            repo.save_meta_chunks_batch("KR", chunks, start_delete_index=2, previous_count=4)

        self.assertEqual(batch.set.call_count, 2)
        self.assertEqual(batch.delete.call_count, 2)
        batch.commit.assert_called_once()

    def test_save_public_analysis_batch(self) -> None:
        db = MagicMock()
        batch = db.batch.return_value
        repo = FirestoreStrategyRepository(db)

        chunks = [(0, [{"code": "005930", "name": "Samsung"}])]
        manifest_items = [{"code": "005930", "name": "Samsung"}]
        with patch.object(repo, "_server_timestamp", return_value="now"):
            repo.save_public_analysis_batch(
                "KR",
                chunks,
                manifest_items,
                chunk_count=1,
                page_size=30,
                start_delete_index=1,
                previous_count=2,
            )

        # 1 chunk set + 1 manifest set = 2 sets
        self.assertEqual(batch.set.call_count, 2)
        # 1 delete (index 1 to 2)
        self.assertEqual(batch.delete.call_count, 1)
        batch.commit.assert_called_once()

    def test_existing_public_chunk_count_from_manifest(self) -> None:
        db = MagicMock()
        manifest_doc = MagicMock()
        manifest_doc.exists = True
        manifest_doc.to_dict.return_value = {"chunkCount": 42}
        db.collection.return_value.document.return_value.get.return_value = manifest_doc

        repo = FirestoreStrategyRepository(db)
        count = repo.existing_public_chunk_count("KR")
        self.assertEqual(count, 42)
        db.collection.return_value.stream.assert_not_called()

    def test_cleanup_past_data_deletes_expired_documents(self) -> None:
        db = MagicMock()
        batch = db.batch.return_value

        # Mock collection query for target_allocations
        doc_old = MagicMock(id="KR_2020-01-01")
        doc_new = MagicMock(id="KR_2099-01-01")

        collection_mock = MagicMock()
        collection_mock.select.return_value.stream.return_value = [doc_old, doc_new]
        collection_mock.stream.return_value = []
        collection_mock.limit.return_value.stream.return_value = []
        db.collection.return_value = collection_mock

        repo = FirestoreStrategyRepository(db)
        counts = repo.cleanup_past_data(market="KR", retention_days=30)

        # Older doc should be batched for deletion
        self.assertGreaterEqual(counts["target_allocations"], 1)
        batch.delete.assert_any_call(doc_old.reference)


if __name__ == "__main__":
    unittest.main()


