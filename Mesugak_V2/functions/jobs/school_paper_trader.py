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
    parser.add_argument("--quote-delay-seconds", type=float, default=float(os.getenv("MESUGAK_QUOTE_DELAY_SECONDS", os.getenv("KIS_PAPER_QUOTE_DELAY_SECONDS", "1.1"))))
    parser.add_argument("--quote-retries", type=int, default=int(os.getenv("MESUGAK_QUOTE_RETRIES", "2")))
    parser.add_argument("--quote-rate-limit-backoff-seconds", type=float, default=float(os.getenv("MESUGAK_QUOTE_RATE_LIMIT_BACKOFF_SECONDS", "2.0")))
    parser.add_argument("--poll-interval-seconds", type=int, default=int(os.getenv("MESUGAK_POLL_INTERVAL_SECONDS", "60")))
    parser.add_argument("--loop", action="store_true", help="Poll only during the Korean regular session, then exit")
    parser.add_argument("--start-time", default=os.getenv("MESUGAK_MARKET_START_TIME", "09:00"))
    parser.add_argument("--end-time", default=os.getenv("MESUGAK_MARKET_END_TIME", "15:35"))
    parser.add_argument("--execute", action="store_true", help="Submit KIS virtual orders; otherwise only report proposed orders")
    parser.add_argument("--skip-account-sync", action="store_true", help="Do not sync the KIS paper account before deciding orders")
    parser.add_argument("--cred-path", default=None)
    return parser


def _is_rate_limit_error(exc: Exception) -> bool:
    message = str(exc)
    return "EGW00201" in message or "초당 거래건수" in message


def fetch_live_prices(
    client: KISPaperClient,
    codes: list[str],
    quote_delay_seconds: float = 1.1,
    quote_retries: int = 2,
    rate_limit_backoff_seconds: float = 2.0,
) -> tuple[dict[str, float], dict[str, str]]:
    """Fetch quotes defensively: one bad symbol or rate limit must not stop the trading loop."""
    prices: dict[str, float] = {}
    errors: dict[str, str] = {}
    delay = max(0.0, float(quote_delay_seconds or 0.0))
    retries = max(0, int(quote_retries or 0))
    backoff = max(delay, float(rate_limit_backoff_seconds or 0.0))
    for index, code in enumerate(codes):
        if index > 0 and delay > 0:
            time.sleep(delay)
        for attempt in range(retries + 1):
            try:
                prices[code] = client.quote(code)
                errors.pop(code, None)
                break
            except Exception as exc:  # noqa: BLE001 - log and skip unreliable external quote failures.
                errors[code] = f"{type(exc).__name__}: {exc}"
                if attempt >= retries or not _is_rate_limit_error(exc):
                    break
                time.sleep(backoff * (attempt + 1))
    return prices, errors


def sync_kis_account(
    repo: FirestoreStrategyRepository,
    client: KISPaperClient,
    *,
    market: str,
    initial_cash: float,
) -> tuple[dict, dict[str, dict], dict]:
    """Sync Firestore from the real KIS virtual account and return account/positions."""
    previous_positions = repo.fetch_current_positions()
    account, positions = client.fetch_balance(market=market, initial_cash=initial_cash)
    repo.save_paper_positions(positions, previous_codes=set(previous_positions))
    repo.save_account_snapshot(account)
    return account, positions, {"accountSynced": True, "holdingCount": len(positions), "cash": account.get("cash"), "totalEquity": account.get("totalEquity")}


def run(args: argparse.Namespace, *, repo: FirestoreStrategyRepository | None = None, client: KISPaperClient | None = None, candidates: list[dict] | None = None) -> dict:
    market = str(args.market).upper()
    repo = repo or FirestoreStrategyRepository(init_firestore(args.cred_path))
    client = client or KISPaperClient(KISPaperConfig.from_env())
    candidates = candidates if candidates is not None else repo.fetch_meta_candidates(market)
    account_sync: dict = {"accountSynced": False}
    if not getattr(args, "skip_account_sync", False) and hasattr(client, "fetch_balance"):
        try:
            account, positions, account_sync = sync_kis_account(repo, client, market=market, initial_cash=args.initial_cash)
        except Exception as exc:  # noqa: BLE001 - executing without verified account state is unsafe.
            account_sync = {"accountSynced": False, "accountSyncError": f"{type(exc).__name__}: {exc}"}
            if args.execute:
                return {"status": "account_sync_failed", "market": market, "orderCount": 0, "executedCount": 0, "orders": [], "prices": {}, "quoteErrors": {}, **account_sync}
            positions = repo.fetch_current_positions()
            account = repo.fetch_account_snapshot() or initialize_account(args.initial_cash, market)
    else:
        positions = repo.fetch_current_positions()
        account = repo.fetch_account_snapshot() or initialize_account(args.initial_cash, market)
    ranked = sorted((item for item in candidates if item.get("code")), key=lambda item: float(item.get("confidenceScore", 0) or 0), reverse=True)
    live_candidates = ranked[: max(1, args.max_live_candidates)]
    codes = sorted({str(item.get("code")) for item in live_candidates} | set(positions))
    prices, quote_errors = fetch_live_prices(
        client,
        codes,
        args.quote_delay_seconds,
        args.quote_retries,
        args.quote_rate_limit_backoff_seconds,
    )
    equity = float(account.get("totalEquity", account.get("cash", args.initial_cash)) or args.initial_cash)
    policy = IntradayPolicyConfig(args.buy_score_min, args.score_exit_threshold, args.trailing_stop_pct, args.position_weight, args.rotation_score_gap)
    orders = build_intraday_orders(candidates, positions, equity, float(account.get("cash", 0) or 0), prices, policy)
    if not args.execute:
        return {"status": "dry_run", "market": market, "orderCount": len(orders), "orders": orders, "prices": prices, "quoteErrors": quote_errors, **account_sync}
    result = apply_paper_orders(account, positions, orders, prices, market=market, initial_cash=args.initial_cash)
    for log in result["logs"]:
        broker_response = client.submit_market_order(str(log["action"]), str(log["code"]), int(log["quantity"]))
        log["brokerOrderNo"] = broker_response.get("output", {}).get("ODNO")
    repo.save_paper_positions(result["positions"], previous_codes=set(positions))
    repo.append_trade_logs(result["logs"])
    repo.save_account_snapshot(result["snapshot"])
    return {"status": "applied", "market": market, "orderCount": len(orders), "executedCount": len(result["logs"]), "orders": orders, "quoteErrors": quote_errors, **account_sync}


def _compact_error(message: str, limit: int = 260) -> str:
    text = " ".join(str(message).split())
    return text if len(text) <= limit else f"{text[:limit]}..."


def log_event(payload: dict) -> None:
    at = datetime.now(KST).isoformat(timespec="seconds")
    quote_errors = payload.get("quoteErrors") or {}
    prices = payload.get("prices") or {}
    orders = payload.get("orders") or []
    summary_keys = [
        "status",
        "market",
        "date",
        "orderCount",
        "executedCount",
        "holdingCount",
        "cash",
        "totalEquity",
        "accountSynced",
        "type",
    ]
    summary = " ".join(f"{key}={payload[key]}" for key in summary_keys if key in payload)
    extra = [f"prices={len(prices)}", f"quoteErrors={len(quote_errors)}"]
    if orders:
        extra.append(f"orders={len(orders)}")
    print(f"[{at}] {summary} {' '.join(extra)}".rstrip(), flush=True)

    message = payload.get("message")
    if message:
        print(f"  message: {_compact_error(str(message))}", flush=True)

    account_sync_error = payload.get("accountSyncError")
    if account_sync_error:
        print(f"  accountSyncError: {_compact_error(str(account_sync_error))}", flush=True)

    for code, error in sorted(quote_errors.items()):
        print(f"  quoteError {code}: {_compact_error(error)}", flush=True)

    for order in orders:
        side = order.get("side", "-")
        code = order.get("code", "-")
        amount = order.get("tradeAmount", 0)
        reason = order.get("reason", "-")
        print(f"  order {side} {code} amount={amount} reason={reason}", flush=True)


def _parse_time(raw: str) -> clock_time:
    value = str(raw or "").strip()
    # Recover from a common .env edit mistake such as "15:35MESUGAK_FOO=...".
    candidate = value[:8] if len(value) >= 8 and value[2:3] == ":" and value[5:6] == ":" else value[:5]
    try:
        return clock_time.fromisoformat(candidate)
    except ValueError as exc:
        raise ValueError(f"Invalid time value {raw!r}. Expected HH:MM or HH:MM:SS in functions/.env") from exc


def run_loop(args: argparse.Namespace) -> None:
    load_server_env()
    repo = FirestoreStrategyRepository(init_firestore(args.cred_path))
    client = KISPaperClient(KISPaperConfig.from_env())
    candidates = repo.fetch_meta_candidates(str(args.market).upper())
    start, end = _parse_time(args.start_time), _parse_time(args.end_time)
    interval = max(5, int(args.poll_interval_seconds))
    now = datetime.now(KST)
    if now.weekday() >= 5:
        log_event({"status": "market_closed_weekend", "date": now.date().isoformat()})
        return
    try:
        trading_day = client.is_trading_day(now.date())
    except Exception as exc:  # noqa: BLE001 - KIS virtual API may reject the holiday TR.
        trading_day = True
        log_event({
            "status": "holiday_check_failed_continue_weekday",
            "date": now.date().isoformat(),
            "type": type(exc).__name__,
            "message": str(exc),
        })
    if not trading_day:
        log_event({"status": "market_closed", "date": now.date().isoformat()})
        return
    while True:
        now = datetime.now(KST)
        if now.weekday() >= 5:
            log_event({"status": "market_closed_weekend"})
            return
        if now.time() > end:
            log_event({"status": "market_session_complete", "sessionEndedAt": now.isoformat()})
            return
        if now.time() >= start:
            try:
                log_event(run(args, repo=repo, client=client, candidates=candidates))
            except Exception as exc:
                log_event({"status": "poll_error", "type": type(exc).__name__, "message": str(exc)})
        time.sleep(interval)


if __name__ == "__main__":
    load_server_env()
    arguments = build_parser().parse_args()
    if arguments.loop:
        run_loop(arguments)
    else:
        print(run(arguments))
