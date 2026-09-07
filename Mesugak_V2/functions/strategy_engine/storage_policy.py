"""Bound Firestore chart payloads without changing analysis calculations."""
import json
import gzip
import os
import re
from pathlib import Path

MAX_ANALYSIS_BYTES = 64 * 1024


def archive_latest_analysis(doc_id, payload):
    directory = os.getenv('MESUGAK_ANALYSIS_ARCHIVE_DIR')
    if not directory:
        return
    if not re.fullmatch(r'[A-Z]{2}_[A-Za-z0-9.-]{1,32}', doc_id):
        raise ValueError('Invalid analysis archive id')
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=True)
    os.chmod(root, 0o700)
    path = root / f'{doc_id}.json.gz'
    if not path.exists() and sum(1 for _ in root.glob('*.json.gz')) >= 5000:
        raise RuntimeError('Local analysis archive reached 5000 documents')
    content = gzip.compress(json.dumps(payload, ensure_ascii=False, default=str).encode('utf-8'))
    if len(content) > 512 * 1024:
        raise RuntimeError('Local analysis archive document exceeds 512 KiB')
    temporary = path.with_suffix('.tmp')
    with temporary.open('wb') as file:
        os.chmod(temporary, 0o600)
        file.write(content)
        file.flush()
        os.fsync(file.fileno())
    temporary.replace(path)


def compact_analysis(payload):
    data = dict(payload)
    history = list(data.get('history') or [])[-130:]
    if 'history' in data:
        data['history'] = history
    # Keep recent rows for the administrator chart. All indicators are calculated
    # from the full input series before this persistence-only truncation.
    while history and len(json.dumps(data, ensure_ascii=False, default=str).encode('utf-8')) > MAX_ANALYSIS_BYTES:
        history = history[1:]
        data['history'] = history
    if len(json.dumps(data, ensure_ascii=False, default=str).encode('utf-8')) > MAX_ANALYSIS_BYTES:
        raise ValueError('Analysis metadata exceeds the 64 KiB storage budget')
    return data
