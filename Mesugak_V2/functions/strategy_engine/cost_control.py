"""Fail-closed scheduler guard. Monitoring is delayed, not a billing hard cap."""
import json
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]


def reserve_daily(path, key, amount, ceiling):
    """Reserve before I/O; failed attempts still consume the local allowance."""
    if amount < 0 or ceiling < 0:
        raise ValueError('Invalid allowance')
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    day = datetime.now(ZoneInfo('America/Los_Angeles')).date().isoformat()
    with closing(sqlite3.connect(path, timeout=30)) as db, db:
        db.execute('CREATE TABLE IF NOT EXISTS budget (day TEXT, key TEXT, used INTEGER, PRIMARY KEY(day,key))')
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT used FROM budget WHERE day=? AND key=?', (day, key)).fetchone()
        used = row[0] if row else 0
        if used + amount > ceiling:
            raise RuntimeError(f'Daily {key} allowance exhausted')
        db.execute('INSERT OR REPLACE INTO budget VALUES(?,?,?)', (day, key, used + amount))
        db.execute('DELETE FROM budget WHERE day < ?', ((datetime.now(timezone.utc) - timedelta(days=35)).date().isoformat(),))


def latest_storage(series, now):
    if not series:
        raise RuntimeError('Storage metric is missing')
    total = 0
    for entry in series:
        points = entry.get('points', [])
        if not points:
            raise RuntimeError('Storage metric has no samples')
        point = max(points, key=lambda p: p['interval']['endTime'])
        timestamp = datetime.fromisoformat(point['interval']['endTime'].replace('Z', '+00:00'))
        if now - timestamp > timedelta(hours=26):
            raise RuntimeError('Storage metric is stale')
        value = int(point['value']['int64Value'])
        if value < 0:
            raise RuntimeError('Invalid storage metric')
        total += value
    return total


def check_cloud_budget(*, storage_required=True, planned_reads=0, planned_writes=0, planned_deletes=0):
    from google.oauth2 import service_account
    from google.auth.transport.requests import AuthorizedSession
    from .repositories import resolve_cred_path
    credentials = service_account.Credentials.from_service_account_file(
        str(resolve_cred_path()), scopes=['https://www.googleapis.com/auth/monitoring.read'])
    session = AuthorizedSession(credentials)
    now = datetime.now(timezone.utc)
    endpoint = f'https://monitoring.googleapis.com/v3/projects/{credentials.project_id}/timeSeries'

    def query(metric, start):
        params = {'filter': f'metric.type="firestore.googleapis.com/{metric}"',
                  'interval.startTime': start.isoformat(), 'interval.endTime': now.isoformat(), 'pageSize': 100000}
        response = session.get(endpoint, params=params, timeout=30)
        if response.status_code != 200:
            raise RuntimeError(f'Monitoring unavailable (HTTP {response.status_code}); cloud job blocked')
        body = response.json()
        if body.get('nextPageToken'):
            raise RuntimeError('Incomplete monitoring response')
        return body.get('timeSeries', [])

    result = {'checkedAt': now.isoformat(), 'limitBytes': 700 * 1024**2}
    if storage_required:
        storage = latest_storage(query('storage/data_and_index_storage_bytes', now - timedelta(hours=26)), now)
        result['storageBytes'] = storage
        if storage > result['limitBytes']:
            raise RuntimeError(f'Storage {storage} bytes exceeds 700 MiB; cloud job blocked')
    # Rolling 24 hours is deliberately more conservative than the daily quota window.
    planned = {'read': planned_reads, 'write': planned_writes, 'delete': planned_deletes}
    for name, ceiling in [('read', 30000), ('write', 12000), ('delete', 12000)]:
        series = query(f'document/{name}_ops_count', now - timedelta(hours=24))
        count = sum(int(p['value']['int64Value']) for s in series for p in s.get('points', []))
        result[name] = count
        if planned[name] < 0 or count + planned[name] > ceiling:
            raise RuntimeError(f'Observed {name} operations ({count}) plus planned ({planned[name]}) exceed safety threshold {ceiling}')
    return result


def scheduler_guard(kind):
    state = Path(os.getenv('MESUGAK_COST_STATE_DIR', str(ROOT / 'runtime' / 'cost')))
    state.mkdir(parents=True, exist_ok=True)
    try:
        result = check_cloud_budget()
        reserve_daily(state / 'budget.sqlite3', kind, 1, 1 if kind == 'analysis' else 48)
    except Exception as exc:
        (state / 'status.json').write_text(json.dumps({'blocked': True, 'reason': str(exc),
            'checkedAt': datetime.now(timezone.utc).isoformat()}), encoding='utf-8')
        raise
    (state / 'status.json').write_text(json.dumps({'blocked': False, **result}), encoding='utf-8')
    return result
