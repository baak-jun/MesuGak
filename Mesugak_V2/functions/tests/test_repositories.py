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


if __name__ == "__main__":
    unittest.main()
