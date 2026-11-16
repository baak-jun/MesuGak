"""Private contest candles. Never publishes KIS prices to the public site."""
import gzip
import json
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
import pandas as pd
from .realtime_scoring import valid_history

SOURCE = 'KIS_PAPER_DAILY_PLUS_WS'

def load_cached_score_history(directory: Path, code: str, session_date: date) -> pd.DataFrame:
    """Read completed KIS candles locally; this path never calls the broker."""
    path = Path(directory) / f'KR_{code}.json.gz'
    cached = json.loads(gzip.decompress(path.read_bytes()))
    if cached.get('source') != SOURCE:
        raise ValueError('Not a KIS candle cache')
    frame = valid_history(cached.get('history', []), session_date)
    previous_weekday = session_date - timedelta(days=1)
    while previous_weekday.weekday() >= 5:
        previous_weekday -= timedelta(days=1)
    if cached.get('cachedFor') != session_date.isoformat() and frame.iloc[-1]['date'].date() < previous_weekday:
        raise ValueError('KIS completed history needs a daily refresh')
    return frame


def load_cached_score_histories(directory: Path, codes, session_date: date) -> tuple[dict, dict]:
    """Batch disk reads separately from slow REST backfills."""
    histories, missing = {}, {}
    for code in codes:
        try:
            histories[code] = load_cached_score_history(directory, code, session_date)
        except (OSError, ValueError, EOFError, TypeError, KeyError) as exc:
            missing[code] = type(exc).__name__
    return histories, missing


def atomic_json(path: Path, payload: dict, *, compressed: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(payload, ensure_ascii=False, default=str).encode('utf-8')
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(gzip.compress(data) if compressed else data)
    temporary.chmod(0o600)
    temporary.replace(path)

def load_kis_candles(client, directory: Path, code: str, session_date: date, *, refresh: bool = False) -> pd.DataFrame:
    path = Path(directory) / f'KR_{code}.json.gz'
    cached = {}
    try:
        cached = json.loads(gzip.decompress(path.read_bytes()))
    except (OSError, ValueError, EOFError):
        pass
    rows = cached.get('history', []) if cached.get('source') == SOURCE else []
    if cached.get('cachedFor') == session_date.isoformat() and rows and not refresh:
        valid_history(rows, session_date)
        return pd.DataFrame(rows).assign(date=lambda frame: pd.to_datetime(frame['date']))
    latest = client.daily_candles(code, session_date)
    if not latest:
        raise ValueError('KIS returned no daily candles')
    old = {str(row['date'])[:10]: row for row in rows}
    if any(str(row['date'])[:10] < session_date.isoformat() and str(row['date'])[:10] != cached.get('cachedFor') and str(row['date'])[:10] in old and abs(float(row['close'])-float(old[str(row['date'])[:10]]['close'])) > .01 for row in latest):
        rows = []  # Refresh older adjusted candles after a split/correction.
    merged = {str(row['date'])[:10]: row for row in rows}
    merged.update({str(row['date'])[:10]: row for row in latest})
    completed_count = sum(key < session_date.isoformat() for key in merged)
    if completed_count < 120:
        end = date.fromisoformat(min(str(row['date'])[:10] for row in latest)) - timedelta(days=1)
        older = client.daily_candles(code, end)
        for row in older:
            merged.setdefault(str(row['date'])[:10], row)
    # KIS alone supplies every candle, including prior-day gaps and corporate actions.
    frame = valid_history(list(merged.values()), session_date + timedelta(days=1), minimum_rows=0)
    checked = datetime.now(ZoneInfo('Asia/Seoul')).isoformat(timespec='seconds')
    atomic_json(path, {'source':SOURCE, 'cachedFor':session_date.isoformat(), 'fetchedAt':checked,
                      'history':frame.assign(date=lambda f:f['date'].dt.strftime('%Y-%m-%d')).to_dict('records')}, compressed=True)
    # Keep valid short history too: repeating the same request cannot create older bars.
    valid_history(frame.to_dict('records'), session_date)
    return frame
