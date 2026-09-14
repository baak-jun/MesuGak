import sys
import tempfile
import unittest
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from jobs.enforce_analysis_retention import MAX_RETENTION_STOCKS, resolve_limit, select_stale_snapshots
from jobs.analyze_market import MAX_DAILY_STOCKS, _prune_local_payloads, select_top_summaries, validate_stock_limit
from jobs.delete_analysis_market import ANALYSIS_COLLECTIONS, _matches, resolve_collections
from strategy_engine.market_data import MarketTarget


class AnalysisRetentionTests(unittest.TestCase):
    def test_limit_is_bounded(self):
        self.assertEqual(resolve_limit(1000), MAX_RETENTION_STOCKS)
        with self.assertRaises(ValueError):
            resolve_limit(1001)
        self.assertEqual(validate_stock_limit(MAX_DAILY_STOCKS), MAX_DAILY_STOCKS)
        with self.assertRaises(ValueError):
            validate_stock_limit(MAX_DAILY_STOCKS + 1)

    def test_only_market_documents_outside_keep_set_are_stale(self):
        def snap(doc_id, market=None):
            item = MagicMock()
            item.id = doc_id
            item.to_dict.return_value = {"market": market} if market else {}
            return item

        snapshots = [snap("KR_KEEP", "KR"), snap("KR_OLD", "KR"), snap("US_OLD", "US"), snap("misc")]
        stale = select_stale_snapshots(snapshots, market="KR", keep_ids={"KR_KEEP"})
        self.assertEqual([item.id for item in stale], ["KR_OLD"])

    def test_ranked_selection_uses_score_then_market_cap(self):
        rows = [
            {"id": "KR_B", "code": "B", "confidenceScore": 80, "marcap": 100},
            {"id": "KR_A", "code": "A", "confidenceScore": 80, "marcap": 200},
            {"id": "KR_C", "code": "C", "confidenceScore": 70, "marcap": 900},
        ]
        self.assertEqual([row["id"] for row in select_top_summaries(rows, 2)], ["KR_A", "KR_B"])

    def test_retired_market_match_is_exact_prefix_or_field(self):
        item = MagicMock()
        item.id = "US_AAPL"
        item.to_dict.return_value = {"market": "US"}
        self.assertTrue(_matches(item, "US"))
        self.assertFalse(_matches(item, "KR"))

    def test_retired_market_collections_are_fixed_to_analysis_allow_list(self):
        self.assertEqual(resolve_collections(None), ANALYSIS_COLLECTIONS)
        self.assertEqual(resolve_collections("stock_analysis,meta_data,stock_analysis"), ("stock_analysis", "meta_data"))
        with self.assertRaises(ValueError):
            resolve_collections("users")

    def test_local_candidate_payload_pruning_keeps_selected_ids_only(self):
        with tempfile.TemporaryDirectory() as root:
            directory = Path(root)
            (directory / "KR_KEEP.json.gz").write_bytes(b"keep")
            (directory / "KR_DROP.json.gz").write_bytes(b"drop")
            removed = _prune_local_payloads(directory, {"KR_KEEP"})
            self.assertEqual(removed, 1)
            self.assertTrue((directory / "KR_KEEP.json.gz").exists())
            self.assertFalse((directory / "KR_DROP.json.gz").exists())

    def test_local_ranked_run_does_not_initialize_firestore_and_stores_cap(self):
        from jobs import analyze_market

        targets = [
            MarketTarget("000001", "A", 100),
            MarketTarget("000002", "B", 200),
        ]

        def fake_analysis(_df, identity, fundamentals=None, history_limit=130):
            score = 80 if identity.code == "000001" else 90
            return {"id": identity.doc_id, "code": identity.code, "name": identity.name, "market": "KR", "confidenceScore": score, "marcap": identity.marcap}

        def fake_summary(payload):
            return dict(payload)

        with tempfile.TemporaryDirectory() as root, \
             patch.object(analyze_market, "load_market_universe", return_value=targets), \
             patch.object(analyze_market, "load_ohlcv_with_public_data", return_value=object()), \
             patch.object(analyze_market, "analyze_stock", side_effect=fake_analysis), \
             patch.object(analyze_market, "to_summary", side_effect=fake_summary), \
             patch.object(analyze_market, "init_firestore", side_effect=AssertionError("Firestore must stay lazy")):
            args = SimpleNamespace(
                market="KR", codes=None, kr_markets="KOSPI", max_stocks=1, candidate_limit=None,
                analyze_all_local=True, local_payload_dir=str(Path(root) / "payloads"),
                keep_file=str(Path(root) / "keep.json"), cred_path=None,
                checkpoint_dir=str(Path(root) / "checkpoints"), reset_checkpoint=True,
                meta_chunk_size=400, progress_interval=10, history_limit=130,
                retention_days=30, skip_retention_cleanup=True, dry_run=True,
            )
            result = analyze_market.run(args)
        self.assertEqual(result["candidateCount"], 2)
        self.assertEqual(result["storedCount"], 1)
        self.assertEqual(result["selection"], "confidenceScore desc, marcap desc, code asc")


if __name__ == "__main__":
    unittest.main()
