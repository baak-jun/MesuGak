"""Shared persistent operator exclusions for analysis and contest monitoring."""

from __future__ import annotations

import json
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

DEFAULT_UNTRADABLE_PATH = Path(__file__).resolve().parents[2] / 'runtime/checkpoints/untradable_KR.json'


def _read(path: str | Path) -> dict:
    path = Path(path)
    if not path.exists():
        return {'market': 'KR', 'codes': []}
    payload = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(payload, dict) or not isinstance(payload.get('codes'), list):
        raise ValueError('Invalid persistent exclusion registry')
    for code in payload['codes']:
        if not isinstance(code, str) or len(code) != 6 or not code.isascii() or not code.isalnum():
            raise ValueError('Invalid excluded stock code')
    return payload


def _write(path: str | Path, payload: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, prefix=path.name + '.', suffix='.tmp', encoding='utf-8', delete=False) as output:
        json.dump(payload, output, ensure_ascii=False, default=str)
        temporary = Path(output.name)
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def load_untradable_codes(path: str | Path = DEFAULT_UNTRADABLE_PATH) -> set[str]:
    return set(_read(path)['codes'])


def record_untradable(path: str | Path, code: str, reason: str) -> None:
    if len(code) != 6 or not code.isascii() or not code.isalnum():
        raise ValueError('Invalid excluded stock code')
    payload = _read(path)
    payload['codes'] = sorted(set(payload['codes']) | {code})
    payload.setdefault('reasons', {})[code] = reason
    payload['updatedAt'] = datetime.now(ZoneInfo('Asia/Seoul')).isoformat(timespec='seconds')
    _write(path, payload)


def prune_candidate_snapshot(path: str | Path, excluded: set[str]) -> int:
    path = Path(path)
    if not path.exists():
        return 0
    payload = json.loads(path.read_text(encoding='utf-8'))
    rows = payload.get('summaries', [])
    if isinstance(rows, dict):
        kept = {key: row for key, row in rows.items() if str(row.get('code')) not in excluded}
    else:
        kept = [row for row in rows if str(row.get('code')) not in excluded]
    removed = len(rows) - len(kept)
    payload.update(summaries=kept, excludedCodes=sorted(excluded), excludedCount=len(excluded), eligibleCount=len(kept))
    _write(path, payload)
    return removed
