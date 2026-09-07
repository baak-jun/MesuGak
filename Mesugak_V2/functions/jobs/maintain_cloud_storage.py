"""Archive then remove legacy candidates or compact existing analysis documents.

Only these two collections are allowed. Persistent daily allowances include
failed attempts; archives preserve Firestore protobuf field types and are never
deleted automatically. This does not bound requests from other clients.
"""
import argparse
import base64
import gzip
import json
import os
import shutil
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from strategy_engine.repositories import init_firestore
from strategy_engine.cost_control import reserve_daily
from strategy_engine.storage_policy import compact_analysis


def verified_archive(directory, snapshots):
    from google.cloud.firestore_v1 import _helpers
    from google.cloud.firestore_v1.types import Document
    directory.mkdir(parents=True, exist_ok=True)
    os.chmod(directory, 0o700)
    if shutil.disk_usage(directory).free < 1024**3:
        raise RuntimeError('Less than 1 GiB of server disk available; maintenance stopped')
    total = sum(p.stat().st_size for p in directory.glob('*.jsonl.gz'))
    rows = []
    for snapshot in snapshots:
        document = Document(name=snapshot.reference.path, fields=_helpers.encode_dict(snapshot.to_dict()),
                            update_time=snapshot.update_time)
        rows.append(json.dumps({'path': snapshot.reference.path,
            'protobuf': base64.b64encode(Document.serialize(document)).decode('ascii')}))
    content = ('\n'.join(rows) + '\n').encode('utf-8')
    compressed = gzip.compress(content)
    if total + len(compressed) > 2 * 1024**3:
        raise RuntimeError('Archive exceeds 2 GiB; keep archives and stop maintenance')
    path = directory / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + uuid.uuid4().hex + '.jsonl.gz')
    with path.open('xb') as file:
        os.chmod(path, 0o600)
        file.write(compressed)
        file.flush()
        os.fsync(file.fileno())
    if gzip.decompress(path.read_bytes()) != content:
        raise RuntimeError('Archive verification failed; no cloud mutation allowed')
    return path


def run(mode, root, limit, backup_only=False):
    from google.cloud.firestore_v1 import LastUpdateOption
    if not 1 <= limit <= 5000:
        raise ValueError('Maintenance limit must be 1..5000')
    drained = root / 'cost' / 'candidates-drained'
    if mode == 'archive-candidates' and drained.exists() and not backup_only:
        return {'collection': 'strategy_candidates', 'status': 'already-drained'}
    db = init_firestore()
    name = 'strategy_candidates' if mode == 'archive-candidates' else 'stock_analysis'
    processed = changed = 0
    cursor = None
    ledger = root / 'cost' / 'budget.sqlite3'
    while processed < limit:
        size = min(50, limit - processed)
        reserve_daily(ledger, 'maintenance_reads', size, 15000)
        query = db.collection(name).order_by('__name__').limit(size)
        if cursor is not None:
            query = query.start_after(cursor)
        snapshots = list(query.stream())
        if not snapshots:
            if mode == 'archive-candidates' and not backup_only:
                drained.write_text(datetime.now(timezone.utc).isoformat(), encoding='utf-8')
            break
        updates = []
        for snapshot in snapshots:
            original = snapshot.to_dict()
            compact = compact_analysis(original) if mode == 'compact-analysis' else None
            if compact != original:
                updates.append((snapshot, compact))
        if updates:
            archive = verified_archive(root / 'cloud-archives', [s for s, _ in updates])
            if backup_only:
                processed += len(snapshots)
                cursor = snapshots[-1]
                print(json.dumps({'collection': name, 'backedUp': processed, 'archive': archive.name}), flush=True)
                continue
            operation = 'deletes' if mode == 'archive-candidates' else 'writes'
            reserve_daily(ledger, f'maintenance_{operation}', len(updates), 5000)
            batch = db.batch()
            for snapshot, compact in updates:
                option = LastUpdateOption(snapshot.update_time)
                if compact is None:
                    batch.delete(snapshot.reference, option=option)
                else:
                    batch.update(snapshot.reference, {'history': compact.get('history', [])}, option=option)
            batch.commit()
            changed += len(updates)
            print(json.dumps({'collection': name, 'processed': processed + len(snapshots),
                              'changed': changed, 'archive': archive.name}), flush=True)
        processed += len(snapshots)
        cursor = snapshots[-1]
        if len(snapshots) < size:
            if mode == 'archive-candidates' and not backup_only:
                drained.write_text(datetime.now(timezone.utc).isoformat(), encoding='utf-8')
            break
    return {'collection': name, 'processed': processed, 'changed': changed, 'backupOnly': backup_only}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['archive-candidates', 'compact-analysis'], required=True)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2] / 'runtime')
    parser.add_argument('--limit', type=int, default=5000)
    parser.add_argument('--backup-only', action='store_true', help='Verify server archives without any cloud writes/deletes')
    args = parser.parse_args()
    print(run(args.mode, args.root, args.limit, args.backup_only))
