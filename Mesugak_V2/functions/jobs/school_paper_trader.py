"""School-server poller: saved V2 scores + KIS paper quotes + paper ledger."""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime, time as clock_time
from pathlib import Path
from zoneinfo import ZoneInfo

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    def load_dotenv(path: str | None = None) -> bool:
        """Small fallback for servers that have not installed python-dotenv yet."""
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

from strategy_engine.intraday_policy import IntradayPolicyConfig, build_intraday_orders
from strategy_engine.kis_paper import KISPaperClient, KISPaperConfig
from strategy_engine.ledger import apply_paper_orders, initialize_account
from strategy_engine.repositories import FirestoreStrategyRepository, init_firestore


KST = ZoneInfo("Asia/Seoul")


def load_server_env() -> None:
    """Read functions/.env regardless of cron's working directory."""
    load_dotenv(os.getenv("MESUGAK_ENV_FILE") or str(FUNCTIONS_DIR / ".env"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run one school-server KIS paper-trading poll")
    parser.add_argument("--market", default=os.getenv("MESUGAK_MARKET", "KR"))
    parser.add_argument("--initial-cash", type=float, default=float(os.getenv("MESUGAK_INITIAL_CASH", "10000000")))
    parser.add_argument("--buy-score-min", type=float, default=float(os.getenv("MESUGAK_BUY_SCORE_MIN", "65")))
    parser.add_argument("--score-exit-threshold", type=float, default=float(os.getenv("MESUGAK_SCORE_EXIT_THRESHOLD", "-15")))
    parser.add_argument("--trailing-stop-pct", type=float, default=float(os.getenv("MESUGAK_TRAILING_STOP_PCT", "0.08")))
    parser.add_argument("--position-weight", type=float, default=float(os.getenv("MESUGAK_POSITION_WEIGHT", "0.10")))
    parser.add_argument("--rotation-score-gap", type=float, default=float(os.getenv("MESUGAK_ROTATION_SCORE_GAP", "10")))
    parser.add_argument("--max-live-candidates", type=int, default=int(os.getenv("MESUGAK_MAX_LIVE_CANDIDATES", "20")))
    parser.add_argument("--poll-interval-seconds", type=int, default=int(os.getenv("MESUGAK_POLL_INTERVAL_SECONDS", "30")))
    parser.add_argument("--loop", action="store_true", help="Poll only during the Korean regular session, then exit")
    parser.add_argument("--start-time", default=os.getenv("MESUGAK_MARKET_START_TIME", "09:00"))
    parser.add_argument("--end-time", default=os.getenv("MESUGAK_MARKET_END_TIME", "15:35"))
    parser.add_argument("--execute", action="store_true", help="Submit KIS virtual orders; otherwise only report proposed orders")
    parser.add_argument("--cred-path", default=None)
    return parser


def run(args: argparse.Namespace, *, repo: FirestoreStrategyRepository | None = None, client: KISPaperClient | None = None, candidates: list[dict] | None = None) -> dict:
    market = str(args.market).upper()
    repo = repo or FirestoreStrategyRepository(init_firestore(args.cred_path))
    client = client or KISPaperClient(KISPaperConfig.from_env())
    candidates = candidates if candidates is not None else repo.fetch_meta_candidates(market)
    positions = repo.fetch_current_positions()
    account = repo.fetch_account_snapshot() or initialize_account(args.initial_cash, market)
    ranked = sorted((item for item in candidates if item.get("code")), key=lambda item: float(item.get("confidenceScore", 0) or 0), reverse=True)
    live_candidates = ranked[: max(1, args.max_live_candidates)]
    codes = sorted({str(item.get("code")) for item in live_candidates} | set(positions))
    prices = {code: client.quote(code) for code in codes}
    equity = float(account.get("totalEquity", account.get("cash", args.initial_cash)) or args.initial_cash)
    policy = IntradayPolicyConfig(args.buy_score_min, args.score_exit_threshold, args.trailing_stop_pct, args.position_weight, args.rotation_score_gap)
    orders = build_intraday_orders(candidates, positions, equity, float(account.get("cash", 0) or 0), prices, policy)
    if not args.execute:
        return {"status": "dry_run", "market": market, "orderCount": len(orders), "orders": orders, "prices": prices}
    result = apply_paper_orders(account, positions, orders, prices, market=market, initial_cash=args.initial_cash)
    for log in result["logs"]:
        broker_response = client.submit_market_order(str(log["action"]), str(log["code"]), int(log["quantity"]))
        log["brokerOrderNo"] = broker_response.get("output", {}).get("ODNO")
    repo.save_paper_positions(result["positions"], previous_codes=set(positions))
    repo.append_trade_logs(result["logs"])
    repo.save_account_snapshot(result["snapshot"])
    return {"status": "applied", "market": market, "orderCount": len(orders), "executedCount": len(result["logs"]), "orders": orders}


def _parse_time(raw: str) -> clock_time:
    return clock_time.fromisoformat(raw)


def run_loop(args: argparse.Namespace) -> None:
    load_server_env()
    repo = FirestoreStrategyRepository(init_firestore(args.cred_path))
    client = KISPaperClient(KISPaperConfig.from_env())
    candidates = repo.fetch_meta_candidates(str(args.market).upper())
    start, end = _parse_time(args.start_time), _parse_time(args.end_time)
    interval = max(5, int(args.poll_interval_seconds))
    now = datetime.now(KST)
    if now.weekday() >= 5 or not client.is_trading_day(now.date()):
        print({"status": "market_closed", "date": now.date().isoformat()})
        return
    while True:
        now = datetime.now(KST)
        if now.weekday() >= 5:
            print({"status": "market_closed_weekend"})
            return
        if now.time() > end:
            print({"status": "market_session_complete", "at": now.isoformat()})
            return
        if now.time() >= start:
            try:
                print(run(args, repo=repo, client=client, candidates=candidates))
            except Exception as exc:
                print({"status": "poll_error", "type": type(exc).__name__, "message": str(exc)})
        time.sleep(interval)


if __name__ == "__main__":
    load_server_env()
    arguments = build_parser().parse_args()
    if arguments.loop:
        run_loop(arguments)
    else:
        print(run(arguments))
