"""Poll the FSC public API and start the KR pipeline after a new basDt appears."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

FUNCTIONS_DIR = Path(__file__).resolve().parents[1]
if str(FUNCTIONS_DIR) not in sys.path:
    sys.path.insert(0, str(FUNCTIONS_DIR))

from strategy_engine.market_data import PublicDataClient, get_public_data_client


KST = ZoneInfo("Asia/Seoul")
PACIFIC = ZoneInfo("America/Los_Angeles")
DEFAULT_START_HOUR = 13
DEFAULT_END_HOUR = 20
DEFAULT_RETRY_MINUTES = 30


def _now() -> dt.datetime:
    return dt.datetime.now(KST)


def _read_state(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}
    return value if isinstance(value, dict) else {}


def _write_state(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def _parse_date(value: object) -> dt.date | None:
    text = str(value or "").strip()
    for fmt in ("%Y-%m-%d", "%Y%m%d", "%Y/%m/%d"):
        try:
            return dt.datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _parse_time(value: object) -> dt.datetime | None:
    if not value:
        return None
    try:
        parsed = dt.datetime.fromisoformat(str(value))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=KST)
    return parsed.astimezone(KST)


def _in_watch_window(now: dt.datetime, start_hour: int, end_hour: int) -> bool:
    return now.weekday() < 5 and start_hour <= now.hour <= end_hour


def _is_newer_date(latest_date: dt.date, state: dict[str, Any]) -> bool:
    refreshed = _parse_date(state.get("refreshedDate"))
    return refreshed is None or latest_date > refreshed


def _retry_in_cooldown(
    latest_date: dt.date,
    state: dict[str, Any],
    now: dt.datetime,
    retry_minutes: int,
) -> bool:
    if state.get("lastAttemptDate") != latest_date.isoformat():
        return False
    attempted_at = _parse_time(state.get("lastFailureAt") or state.get("lastAttemptAt"))
    if attempted_at is None:
        return False
    return now - attempted_at < dt.timedelta(minutes=max(0, retry_minutes))


def _analysis_budget_available(root: Path, now: dt.datetime) -> bool:
    """Avoid invoking the runner when its local Pacific-day allowance is used.

    The runner's cost guard remains authoritative.  This read-only local
    precheck prevents a predictable cost-blocked invocation (and its alert)
    while the watcher continues cheap public-API polling.
    """
    configured = os.getenv("MESUGAK_COST_STATE_DIR", "").strip()
    state_dir = Path(configured).expanduser() if configured else root / "runtime" / "cost"
    if not state_dir.is_absolute():
        state_dir = root / state_dir
    database = state_dir / "budget.sqlite3"
    if not database.exists():
        return True
    day = now.astimezone(PACIFIC).date().isoformat()
    db = None
    try:
        uri = f"{database.resolve().as_uri()}?mode=ro"
        db = sqlite3.connect(uri, uri=True, timeout=1)
        row = db.execute("SELECT used FROM budget WHERE day=? AND key=?", (day, "analysis")).fetchone()
    except (sqlite3.Error, OSError):
        # Do not turn a local ledger read failure into a false release block;
        # check_cloud_budget.py still fails closed before any Firestore I/O.
        return True
    finally:
        if db is not None:
            db.close()
    return not row or int(row[0]) < 1


def _emit(status: str, **fields: Any) -> None:
    payload = {"status": status, **fields}
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def poll_once(
    *,
    root: Path,
    marker_path: Path,
    runner_path: Path,
    client: PublicDataClient,
    now: dt.datetime,
    start_hour: int = DEFAULT_START_HOUR,
    end_hour: int = DEFAULT_END_HOUR,
    max_age_days: int = 14,
    retry_minutes: int = DEFAULT_RETRY_MINUTES,
    dry_run: bool = False,
) -> int:
    """Run one cheap probe and, only for a new date, the full close pipeline."""
    if not _in_watch_window(now, start_hour, end_hour):
        _emit("outside_watch_window", checkedAt=now.isoformat(timespec="seconds"))
        return 0

    state = _read_state(marker_path)
    try:
        latest_date = client.latest_stock_date(max_age_days=max_age_days, today=now.date())
    except Exception as exc:
        state.update(
            {
                "market": "KR",
                "checkedAt": now.isoformat(timespec="seconds"),
                "status": "poll_failed",
                "error": f"{type(exc).__name__}: {exc}",
            }
        )
        if not dry_run:
            _write_state(marker_path, state)
        _emit("poll_failed", checkedAt=state["checkedAt"], error=state["error"])
        # A transient provider error must not cause a Firebase call.  The
        # health monitor reports a missed publication if the outage persists.
        return 0

    latest_text = latest_date.isoformat()
    state.update(
        {
            "market": "KR",
            "latestAvailableDate": latest_text,
            "checkedAt": now.isoformat(timespec="seconds"),
            "error": None,
        }
    )

    if not _is_newer_date(latest_date, state):
        state["status"] = "unchanged"
        if not dry_run:
            _write_state(marker_path, state)
        _emit("unchanged", latestAvailableDate=latest_text, refreshedDate=state.get("refreshedDate"))
        return 0

    if _retry_in_cooldown(latest_date, state, now, retry_minutes):
        state["status"] = "retry_cooldown"
        if not dry_run:
            _write_state(marker_path, state)
        _emit(
            "retry_cooldown",
            latestAvailableDate=latest_text,
            lastAttemptAt=state.get("lastAttemptAt"),
        )
        return 0

    if not _analysis_budget_available(root, now):
        state.update(
            {
                "status": "cost_cooldown",
                "costQuotaDay": now.astimezone(PACIFIC).date().isoformat(),
            }
        )
        if not dry_run:
            _write_state(marker_path, state)
        _emit(
            "cost_cooldown",
            latestAvailableDate=latest_text,
            costQuotaDay=state["costQuotaDay"],
        )
        return 0

    attempt_at = now.isoformat(timespec="seconds")
    state.update(
        {
            "status": "running",
            "lastAttemptDate": latest_text,
            "lastAttemptAt": attempt_at,
        }
    )
    if not dry_run:
        _write_state(marker_path, state)
        try:
            result = subprocess.run(["bash", str(runner_path)], cwd=str(root), check=False)
            return_code = int(result.returncode)
            error = None if return_code == 0 else f"runner exited with status={return_code}"
        except OSError as exc:
            return_code = 127
            error = f"{type(exc).__name__}: {exc}"
        if return_code == 0:
            state.update(
                {
                    "status": "refreshed",
                    "refreshedDate": latest_text,
                    "refreshedAt": now.isoformat(timespec="seconds"),
                    "lastFailureAt": None,
                    "error": None,
                }
            )
        else:
            state.update({"status": "failed", "lastFailureAt": now.isoformat(timespec="seconds"), "error": error})
        _write_state(marker_path, state)
        _emit("refreshed" if return_code == 0 else "pipeline_failed", latestAvailableDate=latest_text, returnCode=return_code)
        return return_code

    _emit("would_refresh", latestAvailableDate=latest_text, runner=str(runner_path))
    return 0


def build_parser() -> argparse.ArgumentParser:
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description="Watch FSC public data before running the KR close pipeline")
    parser.add_argument("--root", default=str(root))
    parser.add_argument("--runner", default=None, help="Path to run_v2_kr_close.sh")
    parser.add_argument("--marker", default=None, help="Local marker JSON; never stored in Firestore")
    parser.add_argument("--start-hour", type=int, default=DEFAULT_START_HOUR)
    parser.add_argument("--end-hour", type=int, default=DEFAULT_END_HOUR)
    parser.add_argument("--max-age-days", type=int, default=14)
    parser.add_argument("--retry-minutes", type=int, default=DEFAULT_RETRY_MINUTES)
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main() -> int:
    functions_dir = Path(__file__).resolve().parents[1]
    load_dotenv(str(functions_dir / ".env"))
    args = build_parser().parse_args()
    root = Path(args.root).expanduser().resolve()
    runner = Path(args.runner or root / "server_runtime" / "run_v2_kr_close.sh").expanduser().resolve()
    marker = Path(args.marker or root / "runtime" / "watch" / "public_data_KR.json").expanduser().resolve()
    now = _now()
    return poll_once(
        root=root,
        marker_path=marker,
        runner_path=runner,
        client=get_public_data_client(),
        now=now,
        start_hour=args.start_hour,
        end_hour=args.end_hour,
        max_age_days=args.max_age_days,
        retry_minutes=args.retry_minutes,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    raise SystemExit(main())
