"""Firebase scheduled entry points for Mesugak V2."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from types import SimpleNamespace

from firebase_functions import scheduler_fn


FUNCTIONS_DIR = Path(__file__).resolve().parent
JOBS_DIR = FUNCTIONS_DIR / "jobs"
for path in (FUNCTIONS_DIR, JOBS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import run_paper_flow


def _bool_env(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _int_env(name: str, default: int | None = None) -> int | None:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


def _float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return float(raw)


@scheduler_fn.on_schedule(schedule="30 8 * * 1-5")
def scheduled_paper_flow(event: scheduler_fn.ScheduledEvent) -> None:
    """Run the V2 paper flow on weekdays at 08:30 UTC, 17:30 Korea time."""

    result = run_paper_flow.run(
        SimpleNamespace(
            market=os.getenv("MESUGAK_MARKET", "KR"),
            codes=os.getenv("MESUGAK_CODES") or None,
            kr_markets=os.getenv("MESUGAK_KR_MARKETS", "KOSPI,KOSDAQ"),
            max_stocks=_int_env("MESUGAK_MAX_STOCKS", 300),
            cred_path=None,
            checkpoint_dir=os.getenv("MESUGAK_CHECKPOINT_DIR") or None,
            reset_checkpoint=_bool_env("MESUGAK_RESET_CHECKPOINT", False),
            meta_chunk_size=_int_env("MESUGAK_META_CHUNK_SIZE", 400),
            progress_interval=_int_env("MESUGAK_PROGRESS_INTERVAL", 25),
            account_value=_float_env("MESUGAK_ACCOUNT_VALUE", 10_000_000),
            initial_cash=_float_env("MESUGAK_INITIAL_CASH", 10_000_000),
            cash_target_pct=None,
            max_positions=_int_env("MESUGAK_MAX_POSITIONS", 5),
            max_position_weight=_float_env("MESUGAK_MAX_POSITION_WEIGHT", 0.25),
            min_confidence=_float_env("MESUGAK_MIN_CONFIDENCE", 65.0),
            allocation_id=None,
            skip_analysis=_bool_env("MESUGAK_SKIP_ANALYSIS", False),
            skip_rebalance=_bool_env("MESUGAK_SKIP_REBALANCE", False),
            skip_apply=_bool_env("MESUGAK_SKIP_APPLY", False),
            dry_run=_bool_env("MESUGAK_DRY_RUN", False),
        )
    )
    print({"eventId": getattr(event, "id", None), "result": result})
