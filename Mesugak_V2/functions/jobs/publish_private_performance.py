"""Publish an administrator-only KIS paper-account benchmark comparison."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import date
from pathlib import Path
from typing import Any, Callable

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    def load_dotenv(path: str | None = None) -> bool:
        env_path = Path(path or ".env")
        if not env_path.exists():
            return False
        for raw in env_path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
        return True


FUNCTIONS_DIR = Path(__file__).resolve().parents[1]
if str(FUNCTIONS_DIR) not in sys.path:
    sys.path.insert(0, str(FUNCTIONS_DIR))

from strategy_engine.market_data import load_kr_benchmark_return
from strategy_engine.performance import build_private_paper_performance
from strategy_engine.repositories import FirestoreStrategyRepository, init_firestore


BENCHMARKS = ("KOSPI", "KOSDAQ")


def load_server_env() -> None:
    load_dotenv(os.getenv("MESUGAK_ENV_FILE") or str(FUNCTIONS_DIR / ".env"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Publish private KIS paper performance comparison")
    parser.add_argument("--market", default=os.getenv("MESUGAK_MARKET", "KR"))
    parser.add_argument("--baseline-date", default=os.getenv("MESUGAK_PERFORMANCE_BASELINE_DATE", ""))
    parser.add_argument("--cred-path", default=None)
    return parser


def _baseline_date(value: str) -> date | None:
    try:
        return date.fromisoformat(str(value).strip())
    except ValueError:
        return None


def run(
    args: argparse.Namespace,
    *,
    repo: FirestoreStrategyRepository | None = None,
    benchmark_loader: Callable[[str, date], dict[str, Any]] = load_kr_benchmark_return,
) -> dict[str, Any]:
    market = str(args.market or "KR").upper().strip()
    if market != "KR":
        return {"status": "skipped", "reason": "unsupported_market", "market": market}

    baseline = _baseline_date(args.baseline_date)
    if baseline is None:
        return {
            "status": "skipped",
            "reason": "baseline_date_not_configured",
            "market": market,
            "hint": "Set MESUGAK_PERFORMANCE_BASELINE_DATE=YYYY-MM-DD in the school-server functions/.env.",
        }

    repo = repo or FirestoreStrategyRepository(init_firestore(args.cred_path))
    account = repo.fetch_account_snapshot()
    if not account:
        return {"status": "skipped", "reason": "account_snapshot_missing", "market": market}
    if str(account.get("market") or market).upper() != market:
        return {"status": "skipped", "reason": "account_market_mismatch", "market": market}

    benchmarks: dict[str, dict[str, Any]] = {}
    errors: dict[str, str] = {}
    for label in BENCHMARKS:
        try:
            benchmarks[label] = benchmark_loader(label, baseline)
        except Exception as exc:  # noqa: BLE001 - one unavailable index must not hide account performance.
            errors[label] = f"{type(exc).__name__}: {exc}"

    payload = build_private_paper_performance(
        account,
        baseline_date=baseline.isoformat(),
        benchmarks=benchmarks,
    )
    payload["benchmarkStatus"] = "complete" if len(benchmarks) == len(BENCHMARKS) else "partial"
    payload["benchmarkErrors"] = errors
    repo.save_private_paper_performance(payload)
    return {
        "status": "published",
        "market": market,
        "baselineDate": baseline.isoformat(),
        "benchmarkCount": len(benchmarks),
        "benchmarkErrors": errors,
    }


def main() -> None:
    load_server_env()
    print(run(build_parser().parse_args()))


if __name__ == "__main__":
    main()