"""All-day KIS paper WebSocket trader with a deterministic replay path.

The default mode is dry-run.  The live process only evaluates daily V2
candidates, consumes a bounded KIS subscription set, and writes a compact
runtime heartbeat.  A separate ``--execute`` opt-in is required before any
KIS order endpoint is called.
"""

from __future__ import annotations

import argparse
import asyncio
import gzip
import json
import math
import os
import random
import sys
import time
from collections import deque
from contextlib import contextmanager
from dataclasses import dataclass, replace, asdict
from datetime import date, datetime, time as clock_time, timedelta
from pathlib import Path
from typing import Any, Callable, Iterable
from zoneinfo import ZoneInfo

FUNCTIONS_DIR = Path(__file__).resolve().parents[1]
if str(FUNCTIONS_DIR) not in sys.path:
    sys.path.insert(0, str(FUNCTIONS_DIR))
JOBS_DIR = FUNCTIONS_DIR / "jobs"
if str(JOBS_DIR) not in sys.path:
    sys.path.insert(0, str(JOBS_DIR))

from school_paper_trader import load_server_env, sync_kis_account  # noqa: E402
from strategy_engine.kis_paper import KISPaperClient, KISPaperConfig, KISOrderRejectedError  # noqa: E402
from strategy_engine.kis_realtime import KISFrameParser, KISWebSocketStream, KISSubscriptionLimitError  # noqa: E402
from strategy_engine.order_state import OrderStateStore  # noqa: E402
from strategy_engine.realtime_policy import (  # noqa: E402
    RealtimePolicyConfig,
    RollingQuotes,
    TradeTick,
    entry_signal,
    drawdown_exit,
    select_watch_codes,
)
from strategy_engine.repositories import FirestoreStrategyRepository, init_firestore  # noqa: E402
from strategy_engine.contest_repository import ContestRepository, require_isolated_dry_run
from strategy_engine.realtime_scoring import valid_history, score_live_history  # noqa: E402
from strategy_engine.contest_market_data import SOURCE as CONTEST_DATA_SOURCE, load_kis_candles, load_cached_score_histories
from contest_notifications import ContestNotifications, clean_detail  # noqa: E402
from strategy_engine.untradable import DEFAULT_UNTRADABLE_PATH, load_untradable_codes, record_untradable, prune_candidate_snapshot  # noqa: E402
from strategy_engine.contest_momentum import MomentumConfig, MomentumWindow, momentum_entry, select_volume_watch


KST = ZoneInfo("Asia/Seoul")


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    return default if value is None else value.strip().lower() in {"1", "true", "yes", "on"}


def _number(value: Any, default: float = 0.0) -> float:
    try:
        result = float(str(value or "0").replace(",", ""))
    except (TypeError, ValueError):
        return default
    return result if math.isfinite(result) else default


def _order_number(payload: dict[str, Any]) -> str:
    for key in ("ODNO", "odno", "ODER_NO", "orderNo", "brokerOrderNo"):
        value = payload.get(key)
        if value:
            return str(value)
    return ""


def _parse_clock(value: str) -> clock_time:
    raw = str(value or "").strip()
    parts = raw.split(":")
    if len(parts) not in {2, 3}:
        raise ValueError(f"Invalid clock time: {value}")
    hour, minute = int(parts[0]), int(parts[1])
    second = int(parts[2]) if len(parts) == 3 else 0
    return clock_time(hour, minute, second)


def _session_timestamp(day: date, value: clock_time) -> float:
    return datetime.combine(day, value, tzinfo=KST).timestamp()


def _entry_window_open(now: float, entry_close_at: float) -> bool:
    return now < entry_close_at


def _timestamp(value: Any, *, fallback: float | None = None) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    raw = str(value or "").strip()
    if not raw:
        return float(fallback if fallback is not None else time.time())
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return float(fallback if fallback is not None else time.time())
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=KST)
    return parsed.timestamp()


def _ranking_code(row: dict[str, Any]) -> str:
    for key in ("mksc_shrn_iscd", "stck_shrn_iscd", "MKSC_SHRN_ISCD", "code", "pdno"):
        value = row.get(key)
        if value:
            return str(value).strip()
    return ""


def _candidate_code(candidate: dict[str, Any]) -> str:
    return str(candidate.get("code") or candidate.get("stck_shrn_iscd") or "").strip()


def _virtual_holiday_feed_unavailable(client: KISPaperClient, error: Exception) -> bool:
    """Recognize KIS's known mock-account holiday-feed rejection.

    The virtual endpoint currently rejects the otherwise common CTCA0903R
    holiday TR with EGW02006.  A weekday fallback keeps the paper runner
    usable while the exchange itself remains the final order gate; all other
    calendar/network failures stay fail-closed below.
    """
    base_url = str(getattr(getattr(client, "config", None), "base_url", ""))
    message = str(error)
    return "openapivts.koreainvestment.com" in base_url and "EGW02006" in message


def load_live_candidates(path: str | Path, market: str, repo) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Use the complete atomic server snapshot instead of the capped public feed."""
    candidate_path = Path(path).expanduser()
    if not candidate_path.exists():
        return repo.fetch_meta_candidates(market), {"candidateSource": "firestore_fallback"}
    payload = json.loads(candidate_path.read_text(encoding="utf-8"))
    if payload.get("market") != market:
        raise ValueError("Realtime candidate snapshot market mismatch")
    rows = payload.get("summaries") or []
    if isinstance(rows, dict):
        rows = list(rows.values())
    if not rows or any(not isinstance(row, dict) or not row.get("code") for row in rows):
        raise ValueError("Realtime candidate snapshot has no valid scored universe")
    return rows, {"candidateSource": "server_full_universe", "analysisRunDate": payload.get("runDate"), "analysisTargetCount": payload.get("targetCount"), "analysisFailureCount": payload.get("failureCount", 0),
                  "analysisScanStatus":payload.get('scanStatus'), "analysisReadyCount":sum(not r.get('scorePending') and not r.get('scoreUnavailable') for r in rows),
                  "analysisPendingCount":sum(bool(r.get('scorePending')) for r in rows), "analysisUpdatedAt":payload.get('updatedAt')}


def load_score_history(directory: Path, code: str, session_date: date, client):
    """Use complete KIS history; the live quote path performs no REST requests."""
    frame = load_kis_candles(client, directory, code, session_date)
    return valid_history(frame.to_dict('records'), session_date)


class RealtimeSignalEngine:
    """Stateful adapter around the pure realtime policy functions."""

    def __init__(
        self,
        candidates: Iterable[dict[str, Any]],
        positions: dict[str, dict[str, Any]] | None = None,
        *,
        config: RealtimePolicyConfig | None = None,
        session_date: date | None = None,
        session_started_at: float | None = None,
        blocked_codes: Iterable[str] = (),
        score_provider: Callable[[TradeTick], dict[str, Any]] | None = None,
        momentum_config: MomentumConfig | None = None,
    ):
        self.config = config or RealtimePolicyConfig()
        self.momentum_config = momentum_config or MomentumConfig(enabled=False)
        self.momentum_windows: dict[str, MomentumWindow] = {}
        self.entry_modes: dict[str, str] = {}
        self.session_date = session_date or datetime.now(KST).date()
        self.session_started_at = session_started_at
        self.candidates: dict[str, dict[str, Any]] = {}
        self.windows: dict[str, RollingQuotes] = {}
        self.latest: dict[str, dict[str, Any]] = {}
        self.live_scores: dict[str, float] = {}
        self.live_score_times: dict[str, float] = {}
        self.last_evaluated: dict[str, float] = {}
        self.score_provider = score_provider
        self.watch_highs: dict[str, float] = {}
        self.partial_exit_sent: set[str] = set()
        self.positions: dict[str, dict[str, Any]] = dict(positions or {})
        self.blocked_codes = {str(code) for code in blocked_codes if code}
        self.exit_sent: set[str] = set()
        self.entry_codes: set[str] = set()
        self.entry_enabled = True
        self.order_sync_in_progress = False
        self.order_retry_after: dict[str, float] = {}
        self.order_rejection_counts: dict[str, int] = {}
        self.signal_count = 0
        self.update_candidates(candidates)

    def update_candidates(self, candidates: Iterable[dict[str, Any]]) -> None:
        self.candidates = {
            _candidate_code(item): dict(item)
            for item in candidates
            if _candidate_code(item)
        }
        for code in set(self.live_scores) - set(self.candidates):
            self.live_scores.pop(code, None)
            self.live_score_times.pop(code, None)

    def ranked_candidates(self) -> list[dict[str, Any]]:
        return [{**row, 'confidenceScore': self.live_scores.get(code, row.get('confidenceScore'))}
                for code, row in self.candidates.items()]

    def update_positions(self, positions: dict[str, dict[str, Any]]) -> None:
        previous = self.positions
        self.positions = {str(code): dict(position) for code, position in positions.items()}
        for code, position in self.positions.items():
            position['highestPrice'] = max(_number(position.get('buyPrice')), _number(position.get('highestPrice')), _number(previous.get(code, {}).get('highestPrice')), self.watch_highs.get(code, 0.0) if code in previous else 0.0)
            self.watch_highs[code] = position['highestPrice']
        for code in set(self.watch_highs) - set(self.positions):
            self.watch_highs.pop(code, None)
        self.partial_exit_sent.intersection_update(self.positions)
        self.entry_codes.difference_update(self.positions)

    def retain_watch(self, codes: Iterable[str]) -> None:
        active = set(codes) | set(self.positions) | self.entry_codes
        for mapping in [self.windows, self.latest, self.last_evaluated, self.watch_highs, self.momentum_windows]:
            for code in set(mapping) - active:
                mapping.pop(code, None)

    def strategy_state(self) -> dict[str, Any]:
        return {"sessionDate": self.session_date.isoformat(), "highWatermarkBasis": "after_first_buy_fill", "watchHighs": self.watch_highs,
                "blockedEntryCodes": sorted(self.blocked_codes),
                "partialExitCodes": sorted(self.partial_exit_sent), "exitSentCodes": sorted(self.exit_sent), "entryModes":dict(self.entry_modes),
                "liveScores": dict(self.live_scores), "liveScoreObservedAt":dict(self.live_score_times), "liveScoreDataSource":CONTEST_DATA_SOURCE, "orderRetryAfter": dict(self.order_retry_after), "orderRejectionCounts": dict(self.order_rejection_counts)}

    def restore_strategy(self, state: dict[str, Any]) -> None:
        self.entry_modes.update(state.get('entryModes') or {})
        self.partial_exit_sent.update(str(code) for code in state.get('partialExitCodes', []) if str(code) in self.positions)
        if state.get('highWatermarkBasis') == 'after_first_buy_fill':
            self.watch_highs.update({str(code): _number(high) for code, high in state.get('watchHighs', {}).items() if str(code) in self.positions})
        if state.get('sessionDate') == self.session_date.isoformat():
            self.blocked_codes.update(str(code) for code in state.get('blockedEntryCodes', []))
            self.order_retry_after.update({str(code): _number(value) for code, value in state.get('orderRetryAfter', {}).items()})
            self.order_rejection_counts.update({str(code): int(value) for code, value in state.get('orderRejectionCounts', {}).items()})
            if state.get('liveScoreDataSource') == CONTEST_DATA_SOURCE:
                self.live_scores.update({str(code): _number(score) for code, score in state.get('liveScores', {}).items() if str(code) in self.candidates})
                self.live_score_times.update({str(code): _number(stamp) for code, stamp in state.get('liveScoreObservedAt', {}).items() if str(code) in self.candidates})
            self.exit_sent.update(str(code) for code in state.get('exitSentCodes', []))

    def on_tick(self, tick: TradeTick, *, update_window: bool = True) -> list[dict[str, Any]]:
        window = self.windows.setdefault(str(tick.code), RollingQuotes())
        if update_window and window.add(tick) is None:
            return []
        momentum = self.momentum_windows.setdefault(str(tick.code), MomentumWindow())
        if update_window:
            momentum.add(tick)
        self.last_evaluated[str(tick.code)] = tick.timestamp
        snapshot = window.snapshot(session_started_at=self.session_started_at)
        snapshot.update(momentum.snapshot())
        code = str(tick.code)
        self.latest[code] = snapshot
        position = self.positions.get(code)
        if position and _number(position.get("quantity")) > 0:
            self.watch_highs[code] = max(self.watch_highs.get(code, 0.0), tick.price, _number(position.get('buyPrice')), _number(position.get('highestPrice')))
            position["highestPrice"] = self.watch_highs[code]
            snapshot['monitoredHigh'] = self.watch_highs[code]
            snapshot['drawdownPct'] = (1.0 - tick.price / self.watch_highs[code]) * 100.0
            if self.order_sync_in_progress or tick.timestamp < self.order_retry_after.get(code, 0.0):
                return []
            exit_config = self.config
            if self.entry_modes.get(code) == 'surge':
                exit_config = replace(self.config, partial_drawdown_pct=self.momentum_config.partial_drawdown, full_drawdown_pct=self.momentum_config.full_drawdown)
            snapshot['entryMode'] = self.entry_modes.get(code, 'score')
            decision = drawdown_exit(tick.price, self.watch_highs[code], code in self.partial_exit_sent, exit_config)
            if decision and code not in self.exit_sent:
                reason, fraction = decision
                if fraction >= 1.0:
                    self.exit_sent.add(code)
                else:
                    self.partial_exit_sent.add(code)
                self.blocked_codes.add(code)
                signal = self._signal("SELL", code, reason, snapshot)
                signal['sellFraction'] = fraction
                return [signal]
            return []
        if self.score_provider is not None:
            snapshot.update(self.score_provider(tick))
        if snapshot.get('liveScoreReady'):
            self.live_scores[code] = _number(snapshot.get('liveConfidenceScore'))
            self.live_score_times[code] = snapshot.get('liveScoreObservedAt', tick.timestamp)
        if self.order_sync_in_progress or tick.timestamp < self.order_retry_after.get(code, 0.0) or not self.entry_enabled or code in self.blocked_codes or code in self.positions or code in self.entry_codes:
            return []
        if len(self.positions) + len(self.entry_codes) >= max(1, self.config.max_positions):
            return []
        candidate = self.candidates.get(code)
        if not candidate:
            return []
        eligible, reason = entry_signal(candidate, snapshot, self.config)
        if not eligible and snapshot.get('liveScoreReady') and _number(snapshot.get('liveConfidenceScore')) < self.momentum_config.score_ceiling and momentum_entry(snapshot, self.momentum_config):
            eligible, reason = True, 'volume_surge_entry'
        if not eligible:
            return []
        self.entry_modes[code] = 'surge' if reason == 'volume_surge_entry' else 'score'
        snapshot['entryMode'] = self.entry_modes[code]
        self.entry_codes.add(code)
        return [self._signal("BUY", code, reason, snapshot, candidate)]

    def _signal(
        self,
        side: str,
        code: str,
        reason: str,
        snapshot: dict[str, Any],
        candidate: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.signal_count += 1
        return {
            "side": side,
            "code": str(code),
            "reason": str(reason),
            "timestamp": _number(snapshot.get("timestamp"), time.time()),
            "price": _number(snapshot.get("price")),
            "askPrice": _number(snapshot.get("askPrice")),
            "bidPrice": _number(snapshot.get("bidPrice")),
            "snapshot": dict(snapshot),
            "candidate": dict(candidate or self.candidates.get(str(code), {})),
        }


class OneSecondBarRecorder:
    """Optional gzip JSONL recorder; disabled unless ``--record-dir`` is set."""

    def __init__(self, directory: str | Path | None, session_date: date):
        self.directory = Path(directory).expanduser() if directory else None
        self.session_date = session_date
        self.current: dict[tuple[str, int], dict[str, Any]] = {}
        self.last_cumulative_volume: dict[str, float] = {}
        if self.directory:
            self.directory.mkdir(parents=True, exist_ok=True)

    def add(self, tick: TradeTick) -> None:
        if not self.directory:
            return
        second = int(tick.timestamp)
        key = (str(tick.code), second)
        bar = self.current.get(key)
        if bar is None:
            bar = {
                "timestamp": second,
                "code": str(tick.code),
                "open": tick.price,
                "high": tick.price,
                "low": tick.price,
                "close": tick.price,
                "volume": 0.0,
                "tradeValue": 0.0,
            }
            self.current[key] = bar
        bar["high"] = max(float(bar["high"]), tick.price)
        bar["low"] = min(float(bar["low"]), tick.price)
        bar["close"] = tick.price
        if tick.cumulative_volume:
            previous = self.last_cumulative_volume.get(str(tick.code), tick.cumulative_volume)
            delta = tick.cumulative_volume - previous if tick.cumulative_volume >= previous else tick.cumulative_volume
            self.last_cumulative_volume[str(tick.code)] = tick.cumulative_volume
            bar["volume"] = float(bar["volume"]) + max(0.0, delta)
        bar["tradeValue"] = float(bar["volume"]) * float(bar["close"])
        self._flush_before(second - 1)

    def _flush_before(self, cutoff: int) -> None:
        if not self.directory:
            return
        ready = [key for key in self.current if key[1] <= cutoff]
        if not ready:
            return
        path = self.directory / f"realtime_{self.session_date.isoformat()}.jsonl.gz"
        with gzip.open(path, "at", encoding="utf-8") as handle:
            for key in sorted(ready, key=lambda item: (item[1], item[0])):
                handle.write(json.dumps(self.current.pop(key), ensure_ascii=False) + "\n")

    def close(self) -> None:
        if self.current:
            self._flush_before(2**63 - 1)


def _read_json_rows(path: str | Path) -> list[dict[str, Any]]:
    target = Path(path).expanduser()
    opener = gzip.open if target.suffix == ".gz" else open
    rows: list[dict[str, Any]] = []
    with opener(target, "rt", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            value = json.loads(line)
            if isinstance(value, dict):
                rows.append(value)
    return rows


def _tick_from_row(row: dict[str, Any], fallback_timestamp: float | None = None) -> TradeTick | None:
    code = str(row.get("code") or row.get("MKSC_SHRN_ISCD") or row.get("symbol") or "").strip()
    price = _number(row.get("price") or row.get("STCK_PRPR") or row.get("close"))
    if not code or price <= 0:
        return None
    return TradeTick(
        code=code,
        timestamp=_timestamp(row.get("timestamp") or row.get("time"), fallback=fallback_timestamp),
        price=price,
        cumulative_volume=_number(row.get("cumulativeVolume") or row.get("cumulative_volume") or row.get("ACML_VOL") or row.get("volume")),
        ask_price=_number(row.get("askPrice") or row.get("ask_price") or row.get("ASKP1")),
        bid_price=_number(row.get("bidPrice") or row.get("bid_price") or row.get("BIDP1")),
        ask_quantity=_number(row.get("askQuantity") or row.get("ASKP_RSQN1")),
        bid_quantity=_number(row.get("bidQuantity") or row.get("BIDP_RSQN1")),
    )


def _candidate_rows(path: str | Path | None, events: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    if path:
        value = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
        return value if isinstance(value, list) else list(value.get("candidates", []))
    latest: dict[str, dict[str, Any]] = {}
    for row in events:
        candidate = row.get("candidate")
        if isinstance(candidate, dict) and _candidate_code(candidate):
            latest[_candidate_code(candidate)] = candidate
    return list(latest.values())


def replay_events(
    events: Iterable[dict[str, Any]],
    candidates: Iterable[dict[str, Any]],
    *,
    positions: dict[str, dict[str, Any]] | None = None,
    config: RealtimePolicyConfig | None = None,
) -> dict[str, Any]:
    """Run the exact stream policy offline without credentials or Firestore."""
    rows = list(events)
    if not rows:
        return {"eventCount": 0, "signals": [], "lastSnapshots": {}}
    first_tick = next((_tick_from_row(row) for row in rows), None)
    if first_tick is None:
        return {"eventCount": len(rows), "signals": [], "lastSnapshots": {}}
    day = datetime.fromtimestamp(first_tick.timestamp, KST).date()
    engine = RealtimeSignalEngine(
        candidates,
        positions,
        config=config,
        session_date=day,
        session_started_at=_session_timestamp(day, clock_time(9, 0)),
    )
    signals: list[dict[str, Any]] = []
    for row in rows:
        tick = _tick_from_row(row)
        if tick:
            signals.extend(engine.on_tick(tick))
    return {
        "eventCount": len(rows),
        "tickCount": sum(1 for row in rows if _tick_from_row(row)),
        "signals": signals,
        "lastSnapshots": engine.latest,
    }


@dataclass
class TraderRuntime:
    args: argparse.Namespace
    repo: FirestoreStrategyRepository
    client: KISPaperClient
    engine: RealtimeSignalEngine
    store: OrderStateStore
    recorder: OneSecondBarRecorder
    account: dict[str, Any]
    session_date: date
    last_report: float = 0.0
    last_account_sync: float = 0.0
    last_watch: list[str] | None = None
    operational_status: str = "starting"
    reconciliation_required: bool = False
    emitted_signals: deque[dict[str, Any]] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        self.emitted_signals = deque(maxlen=50)
        self.exploration_queue: deque[str] = deque()
        self.exploration_pool: set[str] = set()
        self.exploration_codes: list[str] = []
        self.watch_started_at: dict[str, float] = {}
        self.candidate_metadata: dict[str, Any] = {}
        self.received_tick_count = 0
        self.last_tick_at: float | None = None
        self.watch_cycle = 0
        self.histories: dict[str, Any] = {}
        self.history_errors: dict[str, str] = {}
        self.history_tasks: dict[str, asyncio.Task] = {}
        self.history_semaphore = asyncio.Semaphore(1)
        self.history_retry_after: dict[str, float] = {}
        self.history_cache_misses: dict[str, str] = {}
        self.history_cache_load_seconds = 0.0
        self.history_rest_fills = 0
        self.volume_rank_observed_at = 0.0
        self.volume_rank_rows: list[dict] = []
        self.score_cache: dict[str, dict] = {}
        self.score_queue: dict[str, TradeTick] = {}
        self.score_requested_at: dict[str, float] = {}
        self.last_received_ticks: dict[str, TradeTick] = {}
        self.async_scoring = False
        self.report_task = None
        self.report_error = None
        self.stale_tick_count = 0
        self.history_client = KISPaperClient(self.client.config) if isinstance(self.client, KISPaperClient) else None
        self.discovery_client = KISPaperClient(self.client.config) if isinstance(self.client, KISPaperClient) else self.client
        self.order_tasks: set[asyncio.Task] = set()
        self.deferred_fills: deque[dict[str, Any]] = deque()
        self.last_strategy_save = 0.0
        self.last_error = ''
        self.account_sync_lock = asyncio.Lock()
        self.account_operation_count = 0
        self.order_check_wakeup = asyncio.Event()
        self.untradable_file = Path(getattr(self.args, 'untradable_file', self.store.path.parent / 'untradable_KR.json'))
        self.notifications = ContestNotifications(self.store, enabled=bool(getattr(self.args, 'execute', False)) and _env_bool('MESUGAK_CONTEST_EMAIL_ENABLED', False))
        previous = self.store.get_runtime('heartbeat') or {}
        if previous.get('sessionDate') == self.session_date.isoformat() and previous.get('reconciliationRequired'):
            failure = self.store.connection.execute("SELECT reason FROM orders WHERE status IN ('FAILED','UNKNOWN') ORDER BY created_at DESC LIMIT 1").fetchone()
            self.notifications.state(True, previous.get('status') or 'previous_pause', str(failure[0]) if failure else '메일 활성화 시 기존 신규 매수 정지 상태를 확인했습니다.')

    def pause_entries(self, status: str, detail: str = '', *, reconcile: bool = False) -> None:
        self.operational_status = status
        self.engine.entry_enabled = False
        self.reconciliation_required = self.reconciliation_required or reconcile
        self.last_error = clean_detail(detail) or status
        self.notifications.state(True, status, self.last_error)

    def resume_entries(self, status: str, detail: str = '') -> None:
        if self.reconciliation_required:
            return
        self.operational_status = status
        self.engine.entry_enabled = _entry_window_open(time.time(), _session_timestamp(self.session_date, _parse_clock(self.args.entry_close_time)))
        self.last_error = ''
        if self.engine.entry_enabled:
            self.notifications.state(False, status, detail or '시세 연결과 계좌·주문 상태가 정상으로 확인되어 신규 매수를 재개합니다.')

    async def mail_loop(self, stop: asyncio.Event) -> None:
        while not stop.is_set():
            await self.notifications.deliver()
            try:
                await asyncio.wait_for(stop.wait(), timeout=2.0)
            except asyncio.TimeoutError:
                pass

    async def order_recovery_loop(self, stop: asyncio.Event) -> None:
        failures = 0
        while not stop.is_set():
            delay = min(30.0, max(2.0, self.client.request_interval) * 2 ** min(failures, 4))
            try:
                await asyncio.wait_for(self.order_check_wakeup.wait(), timeout=delay)
            except asyncio.TimeoutError:
                pass
            self.order_check_wakeup.clear()
            pending = self.store.pending()
            if not pending:
                if self.operational_status == 'account_sync_failed_pause_new_entries' and not self.order_tasks:
                    try:
                        await self.sync_account()
                        self.resume_entries('streaming_execute', '잔고 조회 재시도가 성공해 신규 매수를 재개합니다.')
                        failures = 0
                    except Exception as exc:
                        failures += 1
                        self.pause_entries('account_sync_failed_pause_new_entries', str(exc))
                continue
            if any(row['status'] == 'RESERVED' for row in pending):
                continue
            try:
                await self.reconcile_orders()
                failures = failures + 1 if self.reconciliation_required else 0
            except Exception as exc:
                failures += 1
                self.pause_entries('order_poll_reconcile_failed', str(exc), reconcile=True)

    def live_score(self, tick: TradeTick) -> dict[str, Any]:
        if self.async_scoring:
            cached = self.score_cache.get(tick.code, {})
            if 0 <= tick.timestamp - cached.get('liveScoreObservedAt', 0) <= 3:
                return cached
            return {'liveScoreReady':False}
        history = self.histories.get(tick.code)
        if history is None:
            return {"liveScoreReady": False}
        return score_live_history(history, tick, self.session_date)

    def dispatch_signals(self, signals):
        self.save_strategy(force=bool(signals))
        for signal in signals:
            task = asyncio.create_task(self.emit_signal(signal))
            self.order_tasks.add(task)
            task.add_done_callback(self.order_tasks.discard)

    async def score_loop(self, stop: asyncio.Event) -> None:
        """One coalescing worker; expensive pandas work never blocks exit ticks."""
        while not stop.is_set():
            if not self.score_queue:
                await asyncio.sleep(.05)
                continue
            code = next(iter(self.score_queue))
            tick = self.score_queue.pop(code)
            history = self.histories.get(code)
            if history is None or code not in (self.last_watch or []):
                continue
            self.score_requested_at[code] = tick.timestamp
            try:
                score = await asyncio.to_thread(score_live_history, history, tick, self.session_date)
                score['liveScoreObservedAt'] = tick.timestamp
                self.score_cache[code] = score
                if self.history_errors.get(code, '').startswith('score_error:'):
                    self.history_errors.pop(code, None)
                latest = self.last_received_ticks.get(code)
                if latest and code in (self.last_watch or []) and 0 <= time.time()-latest.timestamp <= 10:
                    self.dispatch_signals(self.engine.on_tick(latest, update_window=False))
            except Exception as exc:
                self.history_errors[code] = 'score_error:' + type(exc).__name__

    async def load_watch_histories(self, codes: Iterable[str]) -> None:
        """Prepare disk hits before subscription; REST misses cannot block hits."""
        if self.engine.score_provider is None or not getattr(self.args, 'history_dir', None):
            return
        codes = list(dict.fromkeys(codes))
        missing = [code for code in codes if code not in self.histories]
        started = time.monotonic()
        if missing:
            loaded, errors = await asyncio.to_thread(load_cached_score_histories, Path(self.args.history_dir), missing, self.session_date)
            self.histories.update(loaded)
            for code in loaded:
                self.history_errors.pop(code, None)
                self.history_retry_after.pop(code, None)
            self.history_cache_misses.update(errors)
        self.history_cache_load_seconds = time.monotonic() - started
        for code in codes:
            if code in self.histories:
                self.history_cache_misses.pop(code, None)
        eligible = set(self.engine.candidates) | set(self.engine.positions) | set(codes)
        for code in set(self.histories) - eligible:
            self.histories.pop(code, None)

    async def prepare_history(self, code: str) -> None:
        try:
            async with self.history_semaphore:
                if code in self.histories or code not in set(self.last_watch or []) | set(self.engine.positions):
                    return
                history = await asyncio.to_thread(load_score_history, Path(self.args.history_dir), code, self.session_date, self.history_client)
            if code in self.engine.candidates or code in self.engine.positions:
                self.histories[code] = history
                self.history_errors.pop(code, None)
                self.history_cache_misses.pop(code, None)
                self.history_retry_after.pop(code, None)
                self.history_rest_fills += 1
        except Exception as exc:
            self.history_errors[code] = f'completed_history_unavailable:{type(exc).__name__}'
            self.history_retry_after[code] = time.time() + 300.0
        finally:
            self.history_tasks.pop(code, None)

    def queue_histories(self, codes: Iterable[str]) -> None:
        if self.engine.score_provider is None or not getattr(self.args, 'history_dir', None):
            return
        # Canceling to_thread leaves REST threads running and can exhaust the
        # shared executor needed by orders. Let one backfill finish on rotation.
        for code in codes:
            if code not in self.histories and code not in self.history_tasks and time.time() >= self.history_retry_after.get(code, 0):
                self.history_tasks[code] = asyncio.create_task(self.prepare_history(code))

    def save_strategy(self, *, force: bool = False) -> None:
        now = time.monotonic()
        if force or now - self.last_strategy_save >= 1.0:
            self.store.set_runtime('strategy', self.engine.strategy_state())
            self.last_strategy_save = now

    async def on_message(self, message: dict[str, Any]) -> None:
        if message.get("kind") == "trade":
            tick = KISFrameParser.trade_tick(message)
            if tick is None:
                return
            if self.async_scoring and self.last_watch is not None and tick.code not in self.last_watch and tick.code not in self.engine.positions:
                return
            if not -2 <= time.time() - tick.timestamp <= 10:
                self.stale_tick_count += 1
                return
            self.received_tick_count += 1
            self.last_tick_at = tick.timestamp
            self.last_received_ticks[tick.code] = tick
            if self.async_scoring and tick.code not in self.engine.positions and tick.timestamp-self.score_requested_at.get(tick.code,0) >= 1:
                self.score_queue[tick.code] = tick
            if self.operational_status in {'stream_error_pause_new_entries', 'subscription_limit_reduced'}:
                self.resume_entries('streaming_execute', '실제 시세 수신이 다시 확인되어 거래 판단을 재개합니다.')
            elif self.engine.entry_enabled and not self.reconciliation_required:
                self.notifications.state(False, 'streaming_execute', '실제 시세 수신과 시작 시 계좌·주문 확인을 마쳤습니다.')
            self.recorder.add(tick)
            signals = self.engine.on_tick(tick)
            self.dispatch_signals(signals)
            return
        if message.get("kind") == "fill_notice":
            fill = KISFrameParser.fill_notice(message)
            if fill:
                self.handle_fill(fill)

    async def emit_signal(self, signal: dict[str, Any]) -> None:
        self.emitted_signals.append({key: value for key, value in signal.items() if key not in {"snapshot", "candidate"}})
        side = str(signal.get("side")).upper()
        code = str(signal.get("code"))
        position = self.engine.positions.get(code, {})
        if side == "SELL":
            held = int(_number(position.get("quantity")))
            pending_quantity = sum(max(0, int(row['quantity']) - int(row.get('filled_quantity') or 0)) for row in self.store.pending() if row['code'] == code and row['side'] == 'SELL')
            fraction = _number(signal.get('sellFraction'), 1.0)
            requested = held if fraction >= 1.0 else max(1, int(held * fraction))
            quantity = min(max(0, held - pending_quantity), requested)
            unit_price = 0.0
        else:
            ask = _number(signal.get("askPrice")) or _number(signal.get("price"))
            equity = _number(self.account.get("totalEquity") or self.account.get("cash"))
            reserved_cash = sum(max(0, int(row['quantity']) - int(row.get('filled_quantity') or 0)) * _number(row.get('limit_price')) for row in self.store.pending() if row['side'] == 'BUY')
            cash = max(0.0, _number(self.account.get("cash")) - reserved_cash)
            budget = min(cash * 0.995, equity * self.engine.config.position_weight) if equity > 0 else cash * 0.995
            quantity = int(budget // ask) if ask > 0 else 0
            unit_price = ask
        if quantity <= 0:
            if side == "BUY":
                self.engine.entry_codes.discard(code)
            return
        signal_id = f"{self.session_date.isoformat()}:{side}:{code}:{int(_number(signal.get('timestamp'), time.time()) * 1000)}:{signal.get('reason', '')}"
        reserved = self.store.reserve_signal(
            signal_id,
            session_date=self.session_date.isoformat(),
            code=code,
            side=side,
            quantity=quantity,
            limit_price=unit_price,
            reason=str(signal.get("reason") or ""),
            payload={"candidate": signal.get("candidate", {}), "snapshot": signal.get("snapshot", {}), "sellFraction": signal.get('sellFraction', 1.0)},
        )
        if not reserved:
            return
        if not self.args.execute:
            self.store.update(signal_id, status="DRY_RUN")
            return
        try:
            response = await asyncio.to_thread(self.client.submit_market_order, side, code, quantity)
            output = response.get("output") or {}
            order_no = _order_number(output if isinstance(output, dict) else {})
            order_branch = str((output or {}).get("KRX_FWDG_ORD_ORGNO") or (output or {}).get("ord_gno_brno") or "06010") if isinstance(output, dict) else "06010"
            original_payload = self.store.get(signal_id).get('payload') or {}
            self.store.update(signal_id, status="SUBMITTED" if order_no else "UNKNOWN", broker_order_no=order_no, payload={**original_payload, "response": output, "orderBranch": order_branch, "orderType": "MARKET"})
            self.engine.order_retry_after.pop(code, None)
            self.engine.order_rejection_counts.pop(code, None)
            self.order_check_wakeup.set()
            deferred = list(self.deferred_fills)
            self.deferred_fills.clear()
            for fill in deferred:
                self.handle_fill(fill)
            if not order_no:
                self.pause_entries('order_reconcile_required', '주문 응답에 주문 번호가 없어 중복 주문 방지를 위해 확인이 필요합니다.', reconcile=True)
            if side == "SELL" and hasattr(self.repo, "save_intraday_trade_state"):
                await asyncio.to_thread(self.repo.save_intraday_trade_state, self.args.market, self.session_date.isoformat(),
                                        {"blockedEntryCodes": sorted(self.engine.blocked_codes), "lastExitSignal": {"code": code, "reason": signal.get("reason")}})
            if hasattr(self.repo, "append_intraday_runtime_event"):
                await asyncio.to_thread(self.repo.append_intraday_runtime_event, {"type": "order_submitted", "signalId": signal_id, "side": side, "code": code, "quantity": quantity, "orderNo": order_no, "reason": signal.get("reason")})
        except Exception as exc:  # noqa: BLE001 - preserve the signal and pause via runtime status.
            if (self.store.get(signal_id) or {}).get('broker_order_no'):
                # A reporting failure must not relabel an accepted broker order as failed.
                self.operational_status = 'reporting_error_after_order'
                return
            detail = f'{code} {side} {quantity:,}주 주문 실패: {exc}'
            untradable = side == 'BUY' and '매매불가종목' in str(exc).replace(' ', '')
            explicit_rejection = isinstance(exc, KISOrderRejectedError) or untradable
            self.store.update(signal_id, status="FAILED" if explicit_rejection else "UNKNOWN", reason=f"{type(exc).__name__}: {exc}")
            self.pause_entries('order_failed_pause_new_entries', detail, reconcile=not explicit_rejection)
            self.order_check_wakeup.set()
            if untradable:
                self.engine.blocked_codes.add(code)
                self.engine.entry_codes.discard(code)
                exclusion = self.store.get_runtime('broker_exclusions') or {}
                codes = set(exclusion.get('codes', [])) if exclusion.get('sessionDate') == self.session_date.isoformat() else set()
                codes.add(code)
                self.store.set_runtime('broker_exclusions', {'sessionDate': self.session_date.isoformat(), 'codes': sorted(codes)})
                record_untradable(self.untradable_file, code, '모의투자 매매불가 종목')
                if getattr(self.args, 'candidate_file', None):
                    prune_candidate_snapshot(self.args.candidate_file, load_untradable_codes(self.untradable_file))
                try:
                    await self.sync_account()
                    self.resume_entries('streaming_execute', f'모의 매매불가 종목 {code}를 오늘 매수 대상에서 제외하고 잔고를 확인해 재개했습니다.')
                except Exception as sync_error:
                    self.pause_entries('account_sync_failed_pause_new_entries', str(sync_error))
                    self.order_check_wakeup.set()
            elif explicit_rejection:
                failures = self.engine.order_rejection_counts.get(code, 0) + 1
                self.engine.order_rejection_counts[code] = failures
                self.engine.order_retry_after[code] = time.time() + min(30, 2 ** min(failures, 5))
                if side == 'BUY':
                    self.engine.entry_codes.discard(code)
                elif signal.get('reason') == 'monitored_high_partial_exit':
                    self.engine.partial_exit_sent.discard(code)
                else:
                    self.engine.exit_sent.discard(code)
                self.save_strategy(force=True)
                try:
                    await self.sync_account()
                    self.resume_entries('streaming_execute', '증권사의 명시적 주문 거절과 잔고를 확인했습니다. 재시도 대기 후 최신 시세·조건으로 다시 판단합니다.')
                except Exception as sync_error:
                    self.pause_entries('account_sync_failed_pause_new_entries', str(sync_error))
                    self.order_check_wakeup.set()
            if hasattr(self.repo, "append_intraday_runtime_event"):
                self.repo.append_intraday_runtime_event({"type": "order_error", "signalId": signal_id, "code": code, "error": f"{type(exc).__name__}: {exc}"})

    def handle_fill(self, fill: dict[str, Any]) -> None:
        if self.engine.order_sync_in_progress:
            self.deferred_fills.append(dict(fill))
            return
        row = self.store.by_broker_order(str(fill.get("brokerOrderNo")))
        if not row:
            if len(self.deferred_fills) < 50 and any(item['status'] == 'RESERVED' for item in self.store.pending()):
                self.deferred_fills.append(dict(fill))
                return
            self.pause_entries('unmatched_fill_reconcile_required', '수신된 체결 통보의 주문 번호를 로컬 주문 기록과 연결하지 못했습니다.', reconcile=True)
            return
        if (row.get('payload') or {}).get('restRecovered'):
            # After cumulative REST recovery, an old incremental notice is ambiguous.
            # Continue confirming this order with cumulative broker quantities.
            return
        quantity = int(fill.get("quantity") or 0)
        payload = dict(row.get('payload') or {})
        notice_key = f"{fill.get('noticeTime')}:{quantity}:{fill.get('price')}:{fill.get('filled')}:{fill.get('rejected')}"
        seen = payload.get('fillNoticeKeys', [])
        if notice_key in seen:
            return
        payload['fillNoticeKeys'] = [*seen, notice_key][-100:]
        filled_quantity = int(row.get('filled_quantity') or 0)
        average_price = _number(row.get('average_fill_price'))
        if fill.get("rejected"):
            status = "REJECTED"
            self.pause_entries('order_rejected_pause_new_entries', f'{row["code"]} {row["side"]} 주문이 체결 통보에서 거절됐습니다.', reconcile=True)
        elif fill.get("filled"):
            quantity = min(quantity, max(0, int(row['quantity']) - filled_quantity))
            if quantity <= 0:
                return
            average_price = (average_price * filled_quantity + _number(fill.get('price')) * quantity) / (filled_quantity + quantity)
            filled_quantity += quantity
            status = "FILLED" if filled_quantity >= int(row['quantity']) else "PARTIALLY_FILLED"
        elif fill.get("accepted"):
            status = "ACCEPTED"
        else:
            status = "PARTIALLY_FILLED"
        self.store.update(row["signal_id"], status=status, commit=False, filled_quantity=filled_quantity, average_fill_price=average_price, payload=payload)
        code = str(fill.get("code"))
        if fill.get('filled') and quantity > 0:
            if row["side"] == "BUY":
                previous = self.engine.positions.get(code, {})
                previous_quantity = int(previous.get('quantity') or 0)
                holding_quantity = previous_quantity + quantity
                holding_average = (_number(previous.get('buyPrice')) * previous_quantity + _number(fill.get('price')) * quantity) / holding_quantity
                high = _number(fill.get('price'))
                if previous_quantity:
                    high = max(high, self.engine.watch_highs.get(code, 0.0), _number(previous.get('highestPrice')))
                self.engine.watch_highs[code] = high
                self.engine.positions[code] = {"code": code, "quantity": holding_quantity, "buyPrice": holding_average, "highestPrice": high, "boughtAt": previous.get('boughtAt') or datetime.now(KST).isoformat(timespec="seconds")}
                if not previous_quantity:
                    self.engine.exit_sent.discard(code)
                    self.engine.partial_exit_sent.discard(code)
                self.account['cash'] = max(0.0, _number(self.account.get('cash')) - _number(fill.get('price')) * quantity)
                if status == 'FILLED':
                    self.engine.entry_codes.discard(code)
            elif row["side"] == "SELL":
                position = self.engine.positions.get(code, {})
                remaining = max(0, int(position.get('quantity', 0)) - quantity)
                if remaining:
                    position['quantity'] = remaining
                else:
                    self.engine.positions.pop(code, None)
                    self.engine.watch_highs.pop(code, None)
                    self.engine.partial_exit_sent.discard(code)
                self.engine.blocked_codes.add(code)
                self.engine.entry_codes.discard(code)
            name = str(self.engine.candidates.get(code, {}).get('name') or code)
            self.notifications.trade(row, fill, name=name, quantity=quantity, filled_quantity=filled_quantity,
                                     average_price=average_price, holding_quantity=int(self.engine.positions.get(code, {}).get('quantity', 0)), status=status, notice_key=notice_key)
            self.save_strategy(force=True)
            if hasattr(self.repo, 'save_paper_positions'):
                self.repo.save_paper_positions({code: self.engine.positions[code]} if code in self.engine.positions else {}, previous_codes={code})
        self.store.connection.commit()
        if hasattr(self.repo, "append_intraday_runtime_event"):
            self.repo.append_intraday_runtime_event({"type": "fill_notice", "signalId": row["signal_id"], "code": code, "side": row["side"], "status": status, "quantity": quantity, "price": fill.get("price")})

    async def reconcile_startup(self) -> None:
        """Reconcile local pending rows before allowing a new entry."""
        excluded = self.store.get_runtime('broker_exclusions') or {}
        codes = set(excluded.get('codes', [])) | load_untradable_codes(self.untradable_file)
        for failed in self.store.connection.execute("SELECT code, reason FROM orders WHERE status='FAILED' AND side='BUY'"):
            if '매매불가종목' in failed['reason'].replace(' ', ''):
                codes.add(failed['code'])
        for code in codes - load_untradable_codes(self.untradable_file):
            record_untradable(self.untradable_file, code, '모의투자 매매불가 종목')
        self.engine.blocked_codes.update(codes)
        self.store.set_runtime('broker_exclusions', {'sessionDate': self.session_date.isoformat(), 'codes': sorted(codes)})
        await self.reconcile_orders()

    @contextmanager
    def account_operation(self):
        self.account_operation_count += 1
        self.engine.order_sync_in_progress = True
        try:
            yield
        finally:
            self.account_operation_count -= 1
            self.engine.order_sync_in_progress = self.account_operation_count > 0
            if not self.engine.order_sync_in_progress:
                deferred = list(self.deferred_fills)
                self.deferred_fills.clear()
                for fill in deferred:
                    self.handle_fill(fill)

    async def sync_account(self) -> None:
        with self.account_operation():
            async with self.account_sync_lock:
                account, positions, _ = await asyncio.to_thread(sync_kis_account, self.repo, self.client, market=self.args.market, initial_cash=getattr(self.args, 'initial_cash', 0))
                self.account = account
                self.engine.update_positions(positions)
                self.last_account_sync = time.time()

    async def reconcile_orders(self) -> None:
        pending_rows = self.store.pending()
        if not pending_rows or any(row['status'] == 'RESERVED' for row in pending_rows):
            if pending_rows:
                self.pause_entries('startup_order_reconcile_required', '주문 번호 없는 요청을 확인해야 합니다.', reconcile=True)
            return
        with self.account_operation():
            for row in pending_rows:
                row['payload'] = {**(row.get('payload') or {}), 'restRecovered': True}
                self.store.update(row['signal_id'], status=row['status'], payload=row['payload'])
            await self._reconcile_orders(pending_rows)

    async def _reconcile_orders(self, pending_rows: list[dict]) -> None:
        by_order = {}
        for day in sorted({str(row['session_date']) for row in pending_rows}):
            rows = await asyncio.to_thread(self.client.inquire_daily_orders, order_date=date.fromisoformat(day), pending_only=False)
            by_order.update({(day, _order_number(row)): row for row in rows if _order_number(row)})
        updates = []
        uncertain = False
        for pending in pending_rows:
            order_no = str(pending.get("broker_order_no") or "")
            if not order_no:
                self.store.update(pending["signal_id"], status="UNKNOWN", reason="startup_missing_broker_order")
                uncertain = True
                continue
            row = by_order.get((str(pending['session_date']), order_no))
            if row is None:
                self.store.update(pending["signal_id"], status="UNKNOWN", reason="startup_broker_order_not_found")
                uncertain = True
                continue
            filled = int(_number(row.get("tot_ccld_qty") or row.get("cntg_qty") or row.get("filledQuantity")))
            requested = int(pending.get("quantity") or 0)
            if (row.get('pdno') and str(row['pdno']) != str(pending['code'])) or not int(pending.get('filled_quantity') or 0) <= filled <= requested:
                raise RuntimeError('Broker order identity or cumulative fill quantity mismatch')
            if requested > 0 and filled >= requested:
                status = "FILLED"
            elif str(row.get('cncl_yn') or '').upper() == 'Y' or (_number(row.get('cncl_cfrm_qty')) >= requested - filled > 0 and str(row.get('rmn_qty')) == '0'):
                status = 'CANCELLED'
            elif _number(row.get('rjct_qty')) >= requested > 0:
                status = 'REJECTED'
            else:
                status = "PARTIALLY_FILLED" if filled else "ACCEPTED"
            average = _number(row.get('tot_ccld_amt')) / filled if filled and _number(row.get('tot_ccld_amt')) > 0 else _number(row.get("avg_prvs") or row.get("avgFillPrice") or row.get("ord_unpr"))
            if filled and average <= 0:
                raise RuntimeError('Broker fill has no valid execution amount')
            updates.append((pending, row, status, filled, average))
        # Balance already includes these fills. Never replay them into holdings.
        await self.sync_account()
        recovered_sells = set()
        for pending, row, status, filled, average in updates:
            previous_filled = int(pending.get('filled_quantity') or 0)
            delta = filled - previous_filled
            payload = dict(pending.get('payload') or {})
            if delta:
                payload['restRecovered'] = True
                delta_price = (filled * average - previous_filled * _number(pending.get('average_fill_price'))) / delta
                fill = {'price': delta_price, 'reconciled': True, 'orderDate': pending['session_date'], 'orderTime': row.get('ord_tmd')}
                self.notifications.trade(pending, fill, name=str(row.get('prdt_name') or pending['code']), quantity=delta, filled_quantity=filled, average_price=average,
                                         holding_quantity=int(_number(self.engine.positions.get(pending['code'], {}).get('quantity'))), status=status, notice_key=f'broker-cumulative:{filled}')
            self.store.update(pending['signal_id'], status=status, commit=False, filled_quantity=filled, average_fill_price=average, payload=payload)
            if pending['side'] == 'SELL' and status in {'FILLED', 'CANCELLED', 'REJECTED'}:
                recovered_sells.add(pending['code'])
        self.store.connection.commit()
        remaining = self.store.pending()
        pending_sells = {row['code'] for row in remaining if row['side'] == 'SELL'}
        self.engine.exit_sent.difference_update(recovered_sells - pending_sells)
        self.engine.entry_codes = {row['code'] for row in remaining if row['side'] == 'BUY'}
        self.save_strategy(force=True)
        if uncertain:
            self.pause_entries('startup_order_reconcile_required', '미체결·결과 불명 주문을 시작 시 확인하지 못했습니다.', reconcile=True)
            if hasattr(self.repo, "append_intraday_runtime_event"):
                self.repo.append_intraday_runtime_event({"type": "startup_order_reconcile_required"})
        elif self.reconciliation_required and self.operational_status in {'startup_order_reconcile_required', 'startup_order_reconcile_failed', 'order_reconcile_required', 'order_poll_reconcile_failed'}:
            self.reconciliation_required = False
            self.resume_entries('streaming_execute', '주문일별 증권사 체결·잔고 대조가 완료되어 신규 매수를 재개합니다.')
        elif not self.reconciliation_required and self.operational_status == 'reporting_error_after_order':
            self.resume_entries('streaming_execute', '주문 접수 후 보고 오류가 있었으나 증권사 체결·잔고 대조가 완료됐습니다.')

    async def refresh_candidates(self) -> list[str]:
        if getattr(self.args, 'watch_mode', 'score') == 'volume':
            return await self.refresh_volume_candidates()
        recovering_stream = self.operational_status in {"stream_error_pause_new_entries", "subscription_limit_reduced"}
        candidates, self.candidate_metadata = await asyncio.to_thread(load_live_candidates, self.args.candidate_file, self.args.market, self.repo)
        exclusions = self.store.get_runtime('broker_exclusions') or {}
        excluded_codes = set(exclusions.get('codes', [])) | load_untradable_codes(self.untradable_file)
        self.engine.blocked_codes.update(excluded_codes)
        candidates = [row for row in candidates if (str(row['code']) not in excluded_codes and not row.get('scoreUnavailable')) or str(row['code']) in self.engine.positions]
        self.engine.update_candidates(candidates)
        candidates = self.engine.ranked_candidates()
        protected = list(dict.fromkeys([*self.engine.positions, *(row['code'] for row in self.store.pending())]))
        explore_count = min(math.ceil(self.args.max_watch * 0.10), max(0, self.args.max_watch - len(protected)))
        core_candidates = [row for row in candidates if str(row['code']) not in self.history_errors or str(row['code']) in protected]
        core = select_watch_codes(core_candidates, protected, max_codes=max(len(protected), self.args.max_watch - explore_count, 1), exploration_count=0, minimum_score=55.0)
        pool = {_candidate_code(row) for row in candidates} - set(core)
        now=time.time()
        history_wait=min(300.0,max(120.0,self.args.max_watch*self.client.request_interval*4))
        warming = [code for code in (self.last_watch or []) if self.engine.score_provider is not None and code in pool
                   and code not in self.engine.live_scores and code not in self.history_errors
                   and now-self.watch_started_at.get(code,now)<history_wait][:max(0,self.args.max_watch-len(core))]
        pool -= set(warming)
        # A discarded weak symbol must not immediately occupy its replacement slot.
        discarded = {code for code in (self.last_watch or []) if code not in protected and self.engine.live_scores.get(code, 55.0) < 55.0}
        pool -= discarded
        explore_count = max(0, self.args.max_watch - len(core) - len(warming))
        self.exploration_queue = deque(code for code in self.exploration_queue if code in pool)
        new_codes = pool - self.exploration_pool
        self.exploration_pool = pool
        if new_codes:
            expanded_queue = [*self.exploration_queue, *new_codes]
            random.shuffle(expanded_queue)
            self.exploration_queue = deque(expanded_queue)
        if len(self.exploration_queue) < explore_count:
            remaining = list(pool - set(self.exploration_queue))
            random.shuffle(remaining)
            self.exploration_queue.extend(remaining)
        watch = [*core, *warming, *list(self.exploration_queue)[:explore_count]]
        self.exploration_codes = [code for code in watch if code not in core]
        for code in self.exploration_codes:
            if code in self.exploration_queue:
                self.exploration_queue.remove(code)
        self.watch_cycle += 1
        self.engine.retain_watch(watch)
        self.last_watch = watch
        history_codes = [code for code in watch if code not in excluded_codes]
        await self.load_watch_histories(history_codes)
        self.queue_histories(history_codes)
        self.watch_started_at={code:self.watch_started_at.get(code,now) for code in watch}
        if recovering_stream and self.args.execute and not self.order_tasks:
            if self.store.pending():
                await self.reconcile_orders()
            else:
                await self.sync_account()
        if self.operational_status in {"watch_refresh_failed_pause_new_entries", "watch_discovery_failed", "stream_error_pause_new_entries", "subscription_limit_reduced"}:
            if self.operational_status not in {'stream_error_pause_new_entries', 'subscription_limit_reduced'}:
                self.resume_entries('recovered_watch_refresh')
        self._save_report(force=True)
        return watch

    async def refresh_volume_candidates(self) -> list[str]:
        candidates, self.candidate_metadata = await asyncio.to_thread(load_live_candidates, self.args.candidate_file, self.args.market, self.repo)
        excluded = load_untradable_codes(self.untradable_file) | set((self.store.get_runtime('broker_exclusions') or {}).get('codes', []))
        self.engine.blocked_codes.update(excluded)
        protected = list(dict.fromkeys([*self.engine.positions, *(r['code'] for r in self.store.pending()), *sorted(self.engine.entry_codes)]))
        candidates = [r for r in candidates if (r['code'] not in excluded and not r.get('scoreUnavailable')) or r['code'] in protected]
        self.engine.update_candidates(candidates)
        # KIS returns up to 30 per market. Explicitly report this coverage.
        rows = []
        for market in ['0001', '1001']:
            rows.extend(await asyncio.to_thread(self.discovery_client.volume_rank, market_code=market))
        by_code = {_ranking_code(r):r for r in rows if _ranking_code(r)}
        eligible = set(self.engine.candidates) - excluded
        watch = select_volume_watch(by_code.values(), protected, eligible, self.args.max_watch)
        if not any(c in eligible for c in watch):
            raise ValueError('No tradable symbols in the provider volume ranking')
        now = time.time()
        self.volume_rank_observed_at = now
        self.volume_rank_rows = list(by_code.values())
        self.watch_cycle += 1
        self.exploration_codes = []
        self.engine.retain_watch(watch)
        self.last_watch = watch
        self.watch_started_at = {c:self.watch_started_at.get(c,now) for c in watch}
        for mapping in [self.score_cache,self.score_queue,self.score_requested_at,self.last_received_ticks]:
            for c in set(mapping)-set(watch): mapping.pop(c,None)
        await self.load_watch_histories([c for c in watch if c not in excluded])
        self.queue_histories([c for c in watch if c not in excluded])
        if self.operational_status in {'watch_refresh_failed_pause_new_entries','watch_discovery_failed','recovered_watch_refresh'}:
            self.resume_entries('streaming_execute' if self.args.execute else 'streaming_dry_run')
        self._save_report(force=True)
        return watch

    def _save_report(self, *, force: bool = False) -> None:
        now = time.time()
        if not force and now - self.last_report < max(10.0, float(self.args.report_interval)):
            return
        self.last_report = now
        payload = {
            "source": "MesuGak_V2",
            "mode": "kis_realtime_paper",
            "status": self.operational_status,
            "market": self.args.market,
            "sessionDate": self.session_date.isoformat(),
            "dryRun": not self.args.execute,
            "watchCount": len(self.last_watch or []),
            "candidateCount": len(self.engine.candidates),
            **self.candidate_metadata,
            "maxWatch": self.args.max_watch,
            "explorationCodes": list(self.exploration_codes),
            "coreWatchCount": len(self.last_watch or []) - len(self.exploration_codes),
            "coreMinimumScore": None if getattr(self.args,'watch_mode','score') == 'volume' else 55.0,
            "watchMode": getattr(self.args,'watch_mode','score'),
            "watchStartedAt": dict(self.watch_started_at),
            "volumeRankObservedAt": self.volume_rank_observed_at,
            "volumeRankCoverage": "KIS top30 per KOSPI/KOSDAQ, eligible union sorted by cumulative volume",
            "volumeRankCount": len(self.volume_rank_rows),
            "momentumPolicy": asdict(self.engine.momentum_config),
            "momentumReadyCodes": [c for c,s in self.engine.latest.items() if s.get('surgeReady')],
            "heldCodes": list(self.engine.positions),
            "scoreObservedAt": {c:self.engine.live_score_times.get(c) for c in (self.last_watch or [])},
            "freshScoreCount": sum(now-self.engine.live_score_times.get(c,0)<=30 for c in (self.last_watch or [])),
            "freshTickCount": sum(now-s.get('timestamp',0)<=30 for c,s in self.engine.latest.items() if c in (self.last_watch or [])),
            "staleTickRejectedCount": self.stale_tick_count,
            "reportError": self.report_error,
            "watchCycle": self.watch_cycle,
            "receivedTickCount": self.received_tick_count,
            "lastTickAt": self.last_tick_at,
            "entryEnabled": self.engine.entry_enabled,
            "buyScoreThreshold": self.engine.config.daily_score_min,
            "buyScoreComparison": "greater_or_equal",
            "entryRule": "live_score_or_low_score_volume_surge",
            "orderType": "MARKET",
            "orderConfirmation": "immediate_on_submission_with_rate_limited_retry",
            "partialDrawdownPct": self.engine.config.partial_drawdown_pct * 100,
            "partialSellFraction": self.engine.config.partial_sell_fraction,
            "fullDrawdownPct": self.engine.config.full_drawdown_pct * 100,
            "scoreBasis": "daily_indicators_with_live_candle",
            "historicalDataSource": CONTEST_DATA_SOURCE,
            "scoreHistoryReadyCount": len(set(self.last_watch or []) & set(self.histories)),
            "historyMemoryCount": len(self.histories),
            "historyLoadPendingCount": sum(not task.done() for task in self.history_tasks.values()),
            "watchHistoryMissingCodes": [code for code in (self.last_watch or []) if code not in self.histories],
            "historyCacheLoadSeconds": round(self.history_cache_load_seconds, 4),
            "historyRestFillCount": self.history_rest_fills,
            "historyPolicy": "disk_cache_before_subscribe_keep_completed_candles",
            "observedScoreCount": len(self.engine.live_scores),
            "observedScoreTop": [{"code":code, "name":self.engine.candidates.get(code, {}).get('name', code), "score":score,
                                  "observedAt":self.engine.live_score_times.get(code), "watched":code in (self.last_watch or [])}
                                 for code,score in sorted(self.engine.live_scores.items(), key=lambda row:-row[1])[:10]],
            "watchRankingBasis": "cumulative_volume" if getattr(self.args,'watch_mode','score') == 'volume' else "last_observed_live_score_else_daily",
            "scoreHistoryErrors": {code:error for code,error in self.history_errors.items() if code in (self.last_watch or [])},
            "reconciliationRequired": self.reconciliation_required,
            "restRequestIntervalSeconds": self.client.request_interval,
            "error": self.last_error or None,
            "emailNotificationsEnabled": self.notifications.enabled,
            "watchCodes": list(self.last_watch or []),
            "holdingCount": len(self.engine.positions),
            "pendingOrderCount": len(self.store.pending()),
            "signalCount": self.engine.signal_count,
            "lastTicks": {code: snapshot.get("timestamp") for code, snapshot in self.engine.latest.items()},
            "lastPrices": {code: snapshot.get("price") for code, snapshot in self.engine.latest.items()},
            "lastScores": {code: snapshot.get("liveConfidenceScore") for code, snapshot in self.engine.latest.items() if snapshot.get('liveScoreReady')},
            "monitoredHighs": dict(self.engine.watch_highs),
            "highWatermarkBasis": "after_first_buy_fill",
            "partialExitCodes": sorted(self.engine.partial_exit_sent),
            "lastSignals": list(self.emitted_signals),
            "checkedAt": datetime.now(KST).isoformat(timespec="seconds"),
        }
        self.store.set_runtime("heartbeat", payload)
        if hasattr(self.repo, 'save_intraday_runtime_state') and (self.report_task is None or self.report_task.done()):
            async def publish():
                try:
                    await asyncio.to_thread(self.repo.save_intraday_runtime_state, payload)
                    self.report_error = None
                except Exception as exc:
                    self.report_error = type(exc).__name__
            try:
                self.report_task = asyncio.get_running_loop().create_task(publish())
            except RuntimeError:
                pass  # Synchronous offline probes already have the local heartbeat.

    async def maintenance(self, stop: asyncio.Event, entry_close_at: float) -> None:
        while not stop.is_set():
            await asyncio.sleep(10.0)
            now = time.time()
            if now >= entry_close_at and self.engine.entry_enabled:
                self.engine.entry_enabled = False
            if self.args.execute and not self.order_tasks and not self.store.pending() and now - self.last_account_sync >= max(60.0, float(self.args.account_sync_interval)):
                try:
                    await self.sync_account()
                    if self.operational_status == "account_sync_failed_pause_new_entries":
                        self.resume_entries('streaming_execute', '계좌 잔고 동기화가 정상으로 복구되어 거래를 재개합니다.')
                except Exception as exc:  # noqa: BLE001 - do not place new entries on uncertain state.
                    self.pause_entries('account_sync_failed_pause_new_entries', str(exc))
                    if hasattr(self.repo, "append_intraday_runtime_event"):
                        self.repo.append_intraday_runtime_event({"type": "account_sync_error", "error": f"{type(exc).__name__}: {exc}"})
            self._save_report()


async def _run_live(args: argparse.Namespace) -> dict[str, Any]:
    session_date = datetime.now(KST).date()
    if time.time() >= _session_timestamp(session_date, _parse_clock(args.end_time)):
        # The 15:35 restart must preserve the completed session's counters and ledger.
        return {"status": "session_closed", "market": args.market, "sessionDate": session_date.isoformat()}
    if not args.execute:
        require_isolated_dry_run(args.state_path)
    repo = ContestRepository(args.state_path, lambda: FirestoreStrategyRepository(init_firestore(args.cred_path), paper_namespace="contest"))
    client = KISPaperClient(KISPaperConfig.from_env())
    if args.execute and not client.config.hts_id:
        payload = {"status": "configuration_error", "market": args.market, "error": "KIS_PAPER_HTS_ID is required for --execute"}
        repo.save_intraday_runtime_state({"source": "MesuGak_V2", "mode": "kis_realtime_paper", **payload})
        return payload
    try:
        trading_day = await asyncio.to_thread(client.is_trading_day, session_date)
    except Exception as exc:  # fail closed: a calendar outage must not become a trade.
        if _virtual_holiday_feed_unavailable(client, exc):
            trading_day = session_date.weekday() < 5
            warning = {
                "type": "holiday_feed_unavailable_weekday_fallback",
                "date": session_date.isoformat(),
                "error": f"{type(exc).__name__}: {exc}",
            }
            if hasattr(repo, "append_intraday_runtime_event"):
                repo.append_intraday_runtime_event(warning)
        else:
            payload = {"status": "holiday_check_failed", "error": f"{type(exc).__name__}: {exc}"}
            if hasattr(repo, "save_intraday_runtime_state"):
                repo.save_intraday_runtime_state({"source": "MesuGak_V2", "mode": "kis_realtime_paper", **payload})
            return payload
    if not trading_day:
        payload = {"status": "not_trading_day", "market": args.market, "sessionDate": session_date.isoformat()}
        if hasattr(repo, "save_intraday_runtime_state"):
            repo.save_intraday_runtime_state({"source": "MesuGak_V2", "mode": "kis_realtime_paper", **payload})
        return payload

    args.max_watch = min(39 if args.execute else 40, max(1, args.max_watch))
    candidates, candidate_metadata = await asyncio.to_thread(load_live_candidates, args.candidate_file, args.market, repo)
    positions = await asyncio.to_thread(repo.fetch_current_positions)
    account = await asyncio.to_thread(repo.fetch_account_snapshot) or {"cash": args.initial_cash, "totalEquity": args.initial_cash}
    if args.execute:
        try:
            account, positions, _ = await asyncio.to_thread(sync_kis_account, repo, client, market=args.market, initial_cash=args.initial_cash)
        except Exception as exc:
            payload = {"status": "account_sync_failed", "market": args.market, "error": f"{type(exc).__name__}: {exc}"}
            repo.save_intraday_runtime_state({"source": "MesuGak_V2", "mode": "kis_realtime_paper", **payload})
            return payload

    state = await asyncio.to_thread(repo.fetch_intraday_trade_state, args.market, session_date.isoformat())
    blocked = state.get("blockedEntryCodes", []) if isinstance(state, dict) else []
    start_time = _parse_clock(args.start_time)
    end_time = _parse_clock(args.end_time)
    entry_close = _parse_clock(args.entry_close_time)
    engine = RealtimeSignalEngine(
        candidates,
        positions,
        config=RealtimePolicyConfig(
            daily_score_min=args.daily_score_min,
            position_weight=args.position_weight,
            max_positions=args.max_positions,
            trailing_stop_pct=args.trailing_stop_pct,
            same_day_stop_loss_pct=args.same_day_stop_loss_pct,
            partial_drawdown_pct=args.partial_drawdown_pct,
            full_drawdown_pct=args.full_drawdown_pct,
            partial_sell_fraction=args.partial_sell_fraction,
        ),
        session_date=session_date,
        session_started_at=_session_timestamp(session_date, start_time),
        blocked_codes=blocked,
        momentum_config=MomentumConfig(enabled=getattr(args,'momentum_enabled',False)),
    )
    engine.entry_enabled = _entry_window_open(
        time.time(), _session_timestamp(session_date, entry_close)
    )
    store = OrderStateStore(args.state_path)
    recorder = OneSecondBarRecorder(args.record_dir, session_date)
    runtime = TraderRuntime(args, repo, client, engine, store, recorder, account, session_date)
    engine.score_provider = runtime.live_score
    runtime.async_scoring = True
    saved_strategy = store.get_runtime('strategy') or {}
    if 'liveScores' not in saved_strategy:
        previous_report = store.get_runtime('heartbeat') or {}
        if previous_report.get('sessionDate') == session_date.isoformat():
            saved_strategy['liveScores'] = previous_report.get('lastScores', {})
    engine.restore_strategy(saved_strategy)
    runtime.candidate_metadata = candidate_metadata
    if args.execute:
        runtime.last_account_sync = time.time()
        try:
            await runtime.reconcile_startup()
        except Exception as exc:  # fail closed when the local ledger cannot be reconciled.
            runtime.pause_entries('startup_order_reconcile_failed', str(exc), reconcile=True)
            repo.append_intraday_runtime_event({"type": "startup_order_reconcile_error", "error": f"{type(exc).__name__}: {exc}"})
    stop = asyncio.Event()
    close_at = _session_timestamp(session_date, end_time)
    entry_close_at = _session_timestamp(session_date, entry_close)
    maintenance_task = asyncio.create_task(runtime.maintenance(stop, entry_close_at))
    mail_task = asyncio.create_task(runtime.mail_loop(stop))
    recovery_task = asyncio.create_task(runtime.order_recovery_loop(stop)) if args.execute else None
    score_task = asyncio.create_task(runtime.score_loop(stop))

    async def refresh() -> list[str]:
        try:
            return await runtime.refresh_candidates()
        except Exception as exc:  # retain the old set; a discovery outage is not a buy signal.
            runtime.pause_entries('watch_refresh_failed_pause_new_entries', str(exc))
            if hasattr(repo, "append_intraday_runtime_event"):
                repo.append_intraday_runtime_event({"type": "watch_refresh_error", "error": f"{type(exc).__name__}: {exc}"})
            return runtime.last_watch or []

    try:
        while time.time() < close_at:
            now = time.time()
            if now < _session_timestamp(session_date, start_time):
                await asyncio.sleep(min(30.0, _session_timestamp(session_date, start_time) - now))
                continue
            if runtime.last_watch is None:
                try:
                    runtime.last_watch = await runtime.refresh_candidates()
                except Exception as exc:
                    runtime.pause_entries('watch_discovery_failed', str(exc))
                    repo.append_intraday_runtime_event({"type": "watch_discovery_error", "error": f"{type(exc).__name__}: {exc}"})
                    await asyncio.sleep(min(args.reconnect_seconds, max(1.0, close_at - time.time())))
                    continue
            stream = KISWebSocketStream(client, runtime.last_watch, include_fill_notice=args.execute)
            try:
                if engine.entry_enabled and not runtime.reconciliation_required:
                    runtime.operational_status = "streaming_dry_run" if not args.execute else "streaming_execute"
                timeout = max(1.0, close_at - time.time())
                await asyncio.wait_for(stream.run(runtime.on_message, refresh=refresh, refresh_seconds=args.discovery_interval), timeout=timeout)
            except asyncio.TimeoutError:
                break
            except asyncio.CancelledError:
                raise
            except KISSubscriptionLimitError as exc:
                protected_count = len(set(runtime.engine.positions) | {row['code'] for row in runtime.store.pending()})
                args.max_watch = max(protected_count, 1, args.max_watch // 2)
                runtime.pause_entries('subscription_limit_reduced', str(exc))
                runtime.last_watch = None
                repo.append_intraday_runtime_event({"type": "subscription_limit_reduced", "maxWatch": args.max_watch, "error": str(exc)})
                await asyncio.sleep(min(10.0, max(1.0, close_at - time.time())))
            except Exception as exc:  # reconnect with new approval key after a bounded backoff.
                runtime.pause_entries('stream_error_pause_new_entries', str(exc))
                runtime.last_watch = None
                repo.append_intraday_runtime_event({"type": "stream_error", "error": f"{type(exc).__name__}: {exc}"})
                await asyncio.sleep(min(args.reconnect_seconds, max(1.0, close_at - time.time())))
            else:
                # A clean remote close is still a reconnect boundary; avoid a
                # tight reconnect loop when the provider closes idle sockets.
                if time.time() < close_at:
                    runtime.pause_entries('stream_error_pause_new_entries', '시세 연결이 종료돼 자동 재연결을 시도합니다.')
                await asyncio.sleep(min(args.reconnect_seconds, max(1.0, close_at - time.time())))
    finally:
        stop.set()
        maintenance_task.cancel()
        score_task.cancel()
        await asyncio.gather(score_task, return_exceptions=True)
        if recovery_task is not None:
            recovery_task.cancel()
            await asyncio.gather(recovery_task, return_exceptions=True)
        try:
            await maintenance_task
        except asyncio.CancelledError:
            pass
        runtime.recorder.close()
        for task in runtime.history_tasks.values():
            task.cancel()
        if runtime.order_tasks:
            await asyncio.gather(*runtime.order_tasks, return_exceptions=True)
        await mail_task
        runtime.save_strategy(force=True)
        runtime.operational_status = "session_complete"
        runtime._save_report(force=True)
        store.close()
    return {"status": "completed", "market": args.market, "sessionDate": session_date.isoformat(), "signals": engine.signal_count, "receivedTickCount": runtime.received_tick_count, "watchCycle": runtime.watch_cycle, "watchCount": len(runtime.last_watch or []), "coreWatchCount": len(runtime.last_watch or []) - len(runtime.exploration_codes), "explorationCodes": runtime.exploration_codes}


async def run_live(args: argparse.Namespace) -> dict[str, Any]:
    try:
        result = await _run_live(args)
    except Exception as exc:
        if getattr(args, 'execute', False) and _env_bool('MESUGAK_CONTEST_EMAIL_ENABLED', False):
            with OrderStateStore(args.state_path) as store:
                notifications = ContestNotifications(store, enabled=True)
                notifications.state(True, 'fatal_process_error', clean_detail(exc))
                await notifications.deliver()
        raise
    if result.get('status') in {'configuration_error', 'holiday_check_failed', 'account_sync_failed'} and getattr(args, 'execute', False) and _env_bool('MESUGAK_CONTEST_EMAIL_ENABLED', False):
        with OrderStateStore(args.state_path) as store:
            notifications = ContestNotifications(store, enabled=True)
            notifications.state(True, result['status'], result.get('error', ''))
            await notifications.deliver()
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the KIS realtime paper-trading contest loop")
    parser.add_argument("--market", default=os.getenv("MESUGAK_MARKET", "KR"))
    parser.add_argument("--initial-cash", type=float, default=float(os.getenv("MESUGAK_INITIAL_CASH", "100000000")))
    parser.add_argument("--daily-score-min", type=float, default=float(os.getenv("MESUGAK_REALTIME_BUY_SCORE_MIN", os.getenv("MESUGAK_BUY_SCORE_MIN", "58"))))
    parser.add_argument('--watch-mode', choices=['volume','score'], default=os.getenv('MESUGAK_REALTIME_WATCH_MODE','volume'))
    parser.add_argument('--momentum-enabled', action=argparse.BooleanOptionalAction, default=_env_bool('MESUGAK_REALTIME_MOMENTUM_ENABLED', True))
    parser.add_argument("--partial-drawdown-pct", type=float, default=float(os.getenv("MESUGAK_REALTIME_PARTIAL_DRAWDOWN_PCT", "0.018")))
    parser.add_argument("--full-drawdown-pct", type=float, default=float(os.getenv("MESUGAK_REALTIME_FULL_DRAWDOWN_PCT", "0.03")))
    parser.add_argument("--partial-sell-fraction", type=float, default=float(os.getenv("MESUGAK_REALTIME_PARTIAL_SELL_FRACTION", "0.50")))
    parser.add_argument("--history-dir", default=os.getenv("MESUGAK_REALTIME_HISTORY_DIR", "runtime/kis-history"))
    parser.add_argument("--position-weight", type=float, default=float(os.getenv("MESUGAK_POSITION_WEIGHT", "0.20")))
    parser.add_argument("--max-positions", type=int, default=int(os.getenv("MESUGAK_MAX_POSITIONS", "5")))
    parser.add_argument("--trailing-stop-pct", type=float, default=float(os.getenv("MESUGAK_TRAILING_STOP_PCT", "0.06")))
    parser.add_argument("--same-day-stop-loss-pct", type=float, default=float(os.getenv("MESUGAK_SAME_DAY_STOP_LOSS_PCT", "0.03")))
    parser.add_argument("--max-watch", type=int, default=int(os.getenv("MESUGAK_REALTIME_MAX_WATCH", "39")))
    parser.add_argument("--candidate-file", default=os.getenv("MESUGAK_REALTIME_CANDIDATE_FILE", "runtime/checkpoints/contest_candidates_KR.json"))
    parser.add_argument('--untradable-file', default=os.getenv('MESUGAK_UNTRADABLE_FILE', str(DEFAULT_UNTRADABLE_PATH)))
    parser.add_argument("--discovery-interval", type=float, default=float(os.getenv("MESUGAK_REALTIME_DISCOVERY_SECONDS", "60")))
    parser.add_argument("--report-interval", type=float, default=float(os.getenv("MESUGAK_REALTIME_REPORT_SECONDS", "60")))
    parser.add_argument("--account-sync-interval", type=float, default=float(os.getenv("MESUGAK_REALTIME_ACCOUNT_SYNC_SECONDS", "300")))
    parser.add_argument("--reconnect-seconds", type=float, default=float(os.getenv("MESUGAK_REALTIME_RECONNECT_SECONDS", "10")))
    parser.add_argument("--start-time", default=os.getenv("MESUGAK_MARKET_START_TIME", "09:00:00"))
    parser.add_argument("--entry-close-time", default=os.getenv("MESUGAK_REALTIME_ENTRY_CLOSE_TIME", "15:15:00"))
    parser.add_argument("--end-time", default=os.getenv("MESUGAK_MARKET_END_TIME", "15:35:00"))
    parser.add_argument("--loop", action=argparse.BooleanOptionalAction, default=_env_bool("MESUGAK_REALTIME_LOOP", True), help="Keep the stream open through the regular session")
    parser.add_argument("--execute", action="store_true", help="Submit KIS virtual orders; default is dry-run")
    parser.add_argument("--env-file", default=None, help="Contest environment file")
    parser.add_argument("--cred-path", default=None)
    parser.add_argument("--state-path", default=os.getenv("MESUGAK_REALTIME_STATE_PATH", "runtime/realtime_order_state.sqlite3"))
    parser.add_argument("--record-dir", default=os.getenv("MESUGAK_REALTIME_RECORD_DIR", ""))
    parser.add_argument("--replay", default=None, help="Replay JSONL/JSONL.GZ ticks instead of connecting to KIS")
    parser.add_argument("--candidates", default=None, help="JSON candidate list for --replay")
    return parser


def main(argv: list[str] | None = None) -> int:
    preliminary = argparse.ArgumentParser(add_help=False)
    preliminary.add_argument("--env-file", default=None)
    pre_args, _ = preliminary.parse_known_args(argv)
    load_server_env(pre_args.env_file)
    args = build_parser().parse_args(argv)
    if args.replay:
        events = _read_json_rows(args.replay)
        candidates = _candidate_rows(args.candidates, events)
        print(json.dumps(replay_events(events, candidates), ensure_ascii=False, indent=2, default=str))
        return 0
    if not args.loop:
        # A non-loop invocation remains bounded to one discovery/connection
        # interval, useful for supervised smoke checks.
        args.end_time = (datetime.now(KST) + timedelta(seconds=max(30.0, args.discovery_interval))).strftime("%H:%M:%S")
    result = asyncio.run(run_live(args))
    print(json.dumps(result, ensure_ascii=False, default=str))
    return 0 if result.get("status") in {"completed", "not_trading_day"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
