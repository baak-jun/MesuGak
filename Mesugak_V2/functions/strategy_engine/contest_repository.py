"""Local contest state; cloud reporting can fail without blocking broker work."""
import threading
import time
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from .order_state import OrderStateStore


def require_isolated_dry_run(state_path):
    """A missing --execute must never overwrite a live contest strategy."""
    path = Path(state_path).resolve()
    if not path.exists():
        return
    connection = sqlite3.connect(f'{path.as_uri()}?mode=ro', uri=True)
    try:
        if connection.execute('SELECT 1 FROM orders LIMIT 1').fetchone():
            raise RuntimeError('Dry-run requires a separate --state-path; this ledger contains live paper orders')
    finally:
        connection.close()


class ContestRepository:
    def __init__(self, state_path, cloud_factory=None):
        self.path = Path(state_path)
        self.cloud_factory = cloud_factory
        self.publisher = None
        self.last_publish = 0.0
        self.publish_lock = threading.Lock()

    def _read(self, key):
        with OrderStateStore(self.path) as store:
            return store.get_runtime('contest_local:'+key) or {}

    def _write(self, key, payload, *, merge=False, remove=()):
        with OrderStateStore(self.path) as store:
            store.connection.execute('BEGIN IMMEDIATE')
            data = (store.get_runtime('contest_local:'+key) or {}) if merge else {}
            for code in remove:
                data.pop(code, None)
            data.update(payload)
            store.set_runtime('contest_local:'+key, data)

    def fetch_current_positions(self):
        return self._read('positions')

    def fetch_account_snapshot(self):
        return self._read('account')

    def save_paper_positions(self, positions, *, previous_codes=None):
        self._write('positions', positions, merge=True, remove=set(previous_codes or ())-set(positions))

    def save_account_snapshot(self, payload):
        self._write('account', payload)

    def fetch_intraday_trade_state(self, market, session_date):
        return self._read(f'trade:{market}:{session_date}')

    def save_intraday_trade_state(self, market, session_date, payload):
        self._write(f'trade:{market}:{session_date}', payload, merge=True)

    def fetch_meta_candidates(self, market):
        # Do not revive capped/stale cloud candidates when the local file is missing.
        raise RuntimeError('Local contest candidate snapshot is unavailable; scanner must restore it')

    def append_intraday_runtime_event(self, payload):
        # Bounded diagnostic ring. Orders and fills remain in their durable ledger.
        with OrderStateStore(self.path) as store:
            store.connection.execute('BEGIN IMMEDIATE')
            events = (store.get_runtime('contest_local:events') or {}).get('items', [])
            events.append({**payload, 'recordedAt':datetime.now(timezone.utc).isoformat()})
            store.set_runtime('contest_local:events', {'items':events[-200:]})

    def save_intraday_runtime_state(self, payload):
        self._write('report', payload)
        if self.cloud_factory is None:
            return
        with self.publish_lock:
            if time.monotonic()-self.last_publish < 60 or (self.publisher and self.publisher.is_alive()):
                return
            self.last_publish = time.monotonic()
            self.publisher = threading.Thread(target=self._publish, daemon=True, name='contest-cloud-report')
            self.publisher.start()

    def _publish(self):
        try:
            repo = self.cloud_factory()
            # No cloud reads. Each RPC has no retries and a short deadline.
            def put(collection, key, data):
                repo._paper_collection(collection).document(key).set(data, timeout=5, retry=None)
            report = self._read('report')
            put('paper_trading_runtime', 'latest', report)
            put('bot_account_snapshot', 'latest', self._read('account'))
            positions = self._read('positions')
            published = self._read('published_positions').get('codes', [])
            for code, position in positions.items():
                put('bot_portfolio', code, position)
            for code in set(published)-set(positions):
                repo._paper_collection('bot_portfolio').document(code).delete(timeout=5, retry=None)
            self._write('published_positions', {'codes':list(positions)})
            self._write('cloud_status', {'status':'ok', 'checkedAt':datetime.now(timezone.utc).isoformat()})
        except Exception as exc:
            self._write('cloud_status', {'status':'unavailable', 'errorType':type(exc).__name__,
                                        'checkedAt':datetime.now(timezone.utc).isoformat()})
