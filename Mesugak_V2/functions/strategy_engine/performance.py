"""Pure helpers for administrator-only paper-performance comparison."""

from __future__ import annotations

from typing import Any


def percentage_return(start_value: float, end_value: float) -> float:
    """Return a percentage change, keeping an unusable baseline safe."""
    start = float(start_value or 0.0)
    end = float(end_value or 0.0)
    return round(((end / start) - 1.0) * 100.0, 4) if start > 0 else 0.0


def build_private_paper_performance(
    account: dict[str, Any],
    *,
    baseline_date: str,
    benchmarks: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Build the safe, administrator-only summary stored in Firestore.

    The result deliberately omits account numbers, holdings, order data, and
    raw index levels.  Benchmark values are cumulative returns against the
    same configured experiment baseline.
    """
    total_equity = float(account.get("totalEquity") or 0.0)
    initial_cash = float(account.get("initialCash") or 0.0)
    # A KIS balance refresh is the single source for the account total. Do not
    # reuse an older derived P&L/return field: a stale initial-cash setting
    # must not turn the private comparison into a misleading return.
    total_pnl = total_equity - initial_cash
    return_pct = percentage_return(initial_cash, total_equity)

    comparison: dict[str, dict[str, Any]] = {}
    for key, benchmark in benchmarks.items():
        benchmark_return = float(benchmark.get("returnPct") or 0.0)
        comparison[str(key).upper()] = {
            "label": str(benchmark.get("label") or key).upper(),
            "returnPct": round(benchmark_return, 4),
            "gapPctPoints": round(return_pct - benchmark_return, 4),
            "baselineDate": str(benchmark.get("baselineDate") or baseline_date),
            "asOfDate": str(benchmark.get("asOfDate") or ""),
            "basis": str(benchmark.get("basis") or "closing_price"),
            "source": str(benchmark.get("source") or ""),
        }

    return {
        "visibility": "admin_only",
        "source": "KIS_PAPER_PRIVATE",
        "market": str(account.get("market") or "KR").upper(),
        "baselineDate": baseline_date,
        "initialCash": round(initial_cash, 2),
        "totalEquity": round(total_equity, 2),
        "totalPnl": round(total_pnl, 2),
        "returnPct": round(return_pct, 4),
        "holdingCount": int(account.get("holdingCount") or 0),
        "benchmarks": comparison,
        "methodology": "Same baseline date; index comparisons use the latest available closing value.",
    }
