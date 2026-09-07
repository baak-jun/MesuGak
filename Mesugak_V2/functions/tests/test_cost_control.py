import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from strategy_engine.cost_control import latest_storage, reserve_daily
from strategy_engine.storage_policy import compact_analysis, MAX_ANALYSIS_BYTES
import json
import gzip
import base64
from unittest.mock import MagicMock


class CostControlTests(unittest.TestCase):
    def test_backup_roundtrip_preserves_firestore_types(self):
        from google.cloud.firestore_v1.types import Document
        from google.cloud.firestore_v1 import _helpers
        from jobs.maintain_cloud_storage import verified_archive
        snapshot = MagicMock()
        snapshot.reference.path = 'strategy_candidates/example'
        snapshot.update_time = datetime.now(timezone.utc)
        snapshot.to_dict.return_value = {'date': snapshot.update_time, 'n': 123, 'blob': b'bytes', 'history': [1, 2]}
        with tempfile.TemporaryDirectory() as root:
            path = verified_archive(Path(root), [snapshot])
            row = json.loads(gzip.decompress(path.read_bytes()))
            restored = Document.deserialize(base64.b64decode(row['protobuf']))
            self.assertEqual(_helpers.decode_dict(restored.fields, None), snapshot.to_dict())
            self.assertEqual(row['path'], snapshot.reference.path)

    def test_attempts_survive_restart_and_reject_over_budget(self):
        with tempfile.TemporaryDirectory() as root:
            ledger = Path(root) / 'budget.sqlite3'
            reserve_daily(ledger, 'analysis', 1, 1)
            with self.assertRaises(RuntimeError):
                reserve_daily(ledger, 'analysis', 1, 1)

    def test_storage_missing_or_stale_is_not_zero(self):
        now = datetime.now(timezone.utc)
        with self.assertRaises(RuntimeError):
            latest_storage([], now)
        series = [{'points': [{'interval': {'endTime': (now - timedelta(days=2)).isoformat()},
                              'value': {'int64Value': '100'}}]}]
        with self.assertRaises(RuntimeError):
            latest_storage(series, now)

    def test_compaction_preserves_latest_and_does_not_mutate_input(self):
        original = {'confidenceScore': 80, 'history': [{'date': str(i), 'data': 'x' * 1000} for i in range(300)]}
        result = compact_analysis(original)
        self.assertEqual(len(original['history']), 300)
        self.assertEqual(result['history'][-1]['date'], '299')
        self.assertEqual(result['confidenceScore'], 80)
        self.assertLessEqual(len(json.dumps(result, ensure_ascii=False).encode()), MAX_ANALYSIS_BYTES)
        with self.assertRaises(ValueError):
            compact_analysis({'name': 'x' * (MAX_ANALYSIS_BYTES + 1)})
