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
REENTRY_BLOCK_EXIT_REASONS = {"negative_score_exit", "trailing_stop", "profit_lock_trailing_stop", "same_day_stop_loss", "score_rotation"}


def load_server_env() -> None:
    """Read functions/.env regardless of cron's working directory."""
    load_dotenv(os.getenv("MESUGAK_ENV_FILE") or str(FUNCTIONS_DIR / ".env"))


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run one school-server KIS paper-trading poll")
    parser.add_argument("--market", default=os.getenv("MESUGAK_MARKET", "KR"))
    parser.add_argument("--initial-cash", type=float, default=float(os.getenv("MESUGAK_INITIAL_CASH", "100000000")))
    parser.add_argument("--buy-score-min", type=float, default=float(os.getenv("MESUGAK_BUY_SCORE_MIN", "65")))
    parser.add_argument("--score-exit-threshold", type=float, default=float(os.getenv("MESUGAK_SCORE_EXIT_THRESHOLD", "-15")))
    parser.add_argument("--trailing-stop-pct", type=float, default=float(os.getenv("MESUGAK_TRAILING_STOP_PCT", "0.08")))
    parser.add_argument("--profit-lock-activate-pct", type=float, default=float(os.getenv("MESUGAK_PROFIT_LOCK_ACTIVATE_PCT", "0.03")))
    parser.add_argument("--profit-lock-trailing-pct", type=float, default=float(os.getenv("MESUGAK_PROFIT_LOCK_TRAILING_PCT", "0.02")))
    parser.add_argument("--profit-lock-min-pnl-pct", type=float, default=float(os.getenv("MESUGAK_PROFIT_LOCK_MIN_PNL_PCT", "0.005")))
    parser.add_argument("--same-day-stop-loss-pct", type=float, default=float(os.getenv("MESUGAK_SAME_DAY_STOP_LOSS_PCT", "0.03")))
    parser.add_argument("--block-reentry-after-exit", action=argparse.BooleanOptionalAction, default=_env_bool("MESUGAK_BLOCK_REENTRY_AFTER_EXIT", True))
    parser.add_argument("--position-weight", type=float, default=float(os.getenv("MESUGAK_POSITION_WEIGHT", "0.10")))
    parser.add_argument("--rotation-score-gap", type=float, default=float(os.getenv("MESUGAK_ROTATION_SCORE_GAP", "10")))
    parser.add_argument("--max-live-candidates", type=int, default=int(os.getenv("MESUGAK_MAX_LIVE_CANDIDATES", "20")))
    parser.add_argument("--max-live-scan-candidates", type=int, default=int(os.getenv("MESUGAK_MAX_LIVE_SCAN_CANDIDATES", "60")))
    parser.add_argument("--live-watch-min-score", type=float, default=float(os.getenv("MESUGAK_LIVE_WATCH_MIN_SCORE", "45")))
    parser.add_argument("--live-drop-penalty-per-pct", type=float, default=float(os.getenv("MESUGAK_LIVE_DROP_PENALTY_PER_PCT", "4.0")))
    parser.add_argument("--live-rise-bonus-per-pct", type=float, default=float(os.getenv("MESUGAK_LIVE_RISE_BONUS_PER_PCT", "1.0")))
    parser.add_argument("--live-rise-bonus-max", type=float, default=float(os.getenv("MESUGAK_LIVE_RISE_BONUS_MAX", "8.0")))
    parser.add_argument("--quote-delay-seconds", type=float, default=float(os.getenv("MESUGAK_QUOTE_DELAY_SECONDS", os.getenv("KIS_PAPER_QUOTE_DELAY_SECONDS", "1.1"))))
    parser.add_argument("--quote-retries", type=int, default=int(os.getenv("MESUGAK_QUOTE_RETRIES", "2")))
    parser.add_argument("--quote-rate-limit-backoff-seconds", type=float, default=float(os.getenv("MESUGAK_QUOTE_RATE_LIMIT_BACKOFF_SECONDS", "2.0")))
    parser.add_argument("--poll-interval-seconds", type=int, default=int(os.getenv("MESUGAK_POLL_INTERVAL_SECONDS", "60")))
    parser.add_argument("--loop", action="store_true", help="Poll only during the Korean regular session, then exit")
    parser.add_argument("--start-time", default=os.getenv("MESUGAK_MARKET_START_TIME", "09:00"))
    parser.add_argument("--end-time", default=os.getenv("MESUGAK_MARKET_END_TIME", "15:35"))
    parser.add_argument("--execute", action="store_true", help="Submit KIS virtual orders; otherwise only report proposed orders")
    parser.add_argument("--skip-account-sync", action="store_true", help="Do not sync the KIS paper account before deciding orders")
    parser.add_argument("--process-refresh-requests", action="store_true", help="Process web-triggered KIS balance refresh requests only; never submit orders")
    parser.add_argument("--refresh-request-limit", type=int, default=int(os.getenv("MESUGAK_REFRESH_REQUEST_LIMIT", "5")))
    parser.add_argument("--cred-path", default=None)
    return parser


def _is_rate_limit_error(exc: Exception) -> bool:
    message = str(exc)
    return "EGW00201" in message or "rate limit" in message.lower()


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
    # KIS reports the current price but not this strategy's intraday high.
    # Preserve it across account syncs so trailing exits use a true high-water mark.
    for code, position in positions.items():
        previous = previous_positions.get(str(code), {})
        position["highestPrice"] = max(
            float(position.get("highestPrice", 0) or 0),
            float(position.get("lastPrice", 0) or 0),
            float(previous.get("highestPrice", 0) or 0),
        )
        if previous.get("boughtAt"):
            position["boughtAt"] = previous["boughtAt"]
    repo.save_paper_positions(positions, previous_codes=set(previous_positions))
    repo.save_account_snapshot(account)
    return account, positions, {"accountSynced": True, "holdingCount": len(positions), "cash": account.get("cash"), "totalEquity": account.get("totalEquity")}


def process_paper_refresh_requests(
    repo: FirestoreStrategyRepository,
    client: KISPaperClient,
    *,
    market: str = "KR",
    initial_cash: float = 0.0,
    limit: int = 5,
) -> dict:
    """Sync a web-requested paper-account snapshot without evaluating orders.

    The browser creates a Firestore request document, then this school-server
    task performs the KIS call. It intentionally does not load candidates,
    request symbol quotes, create orders, or submit trades.
    """
    target_market = str(market or "KR").upper()
    requests = repo.fetch_pending_paper_refresh_requests(limit=limit)
    completed = 0
    failed = 0

    for request in requests:
        request_id = str(request.get("id") or "").strip()
        request_market = str(request.get("market") or target_market).upper()
        if not request_id:
            continue
        if request_market != target_market:
            repo.finish_paper_refresh_request(
                request_id,
                {"status": "failed", "errorCode": "unsupported_market", "market": request_market},
            )
            failed += 1
            continue
        try:
            _, positions, account_sync = sync_kis_account(
                repo,
                client,
                market=request_market,
                initial_cash=initial_cash,
            )
            repo.finish_paper_refresh_request(
                request_id,
                {
                    "status": "completed",
                    "market": request_market,
                    "holdingCount": len(positions),
                    "accountSynced": bool(account_sync.get("accountSynced")),
                },
            )
            completed += 1
        except Exception as exc:  # noqa: BLE001 - surface a safe status to the requesting admin.
            repo.finish_paper_refresh_request(
                request_id,
                {
                    "status": "failed",
                    "market": request_market,
                    "errorCode": type(exc).__name__,
                    "errorMessage": _compact_error(str(exc)),
                },
            )
            failed += 1

    return {
        "status": "paper_refresh_requests_processed",
        "market": target_market,
        "requested": len(requests),
        "completed": completed,
        "failed": failed,
    }


def _float_value(value, default: float = 0.0) -> float:
    try:
        return float(value if value not in (None, "") else default)
    except (TypeError, ValueError):
        return default


def live_adjust_candidate(candidate: dict, price: float | None, args: argparse.Namespace) -> dict:
    """Adjust a daily candidate with the latest quote without pretending to recompute full indicators."""
    item = dict(candidate)
    daily_score = _float_value(item.get("confidenceScore"))
    adjusted = daily_score
    reasons: list[str] = []
    quote = _float_value(price)
    reference = _float_value(item.get("currentPrice"))
    stop_loss = _float_value(item.get("stopLoss"))

    if quote > 0:
        item["livePrice"] = quote
    if quote > 0 and reference > 0:
        move_pct = (quote / reference - 1.0) * 100.0
        item["liveMovePct"] = round(move_pct, 4)
        if move_pct < 0:
            penalty = abs(move_pct) * max(0.0, _float_value(args.live_drop_penalty_per_pct, 4.0))
            adjusted -= penalty
            reasons.append(f"live_price_drop_{round(move_pct, 2)}pct")
        elif move_pct > 0:
            bonus = min(
                move_pct * max(0.0, _float_value(args.live_rise_bonus_per_pct, 1.0)),
                max(0.0, _float_value(args.live_rise_bonus_max, 8.0)),
            )
            adjusted += bonus
            if bonus > 0:
                reasons.append(f"live_price_rise_{round(move_pct, 2)}pct")
    if quote > 0 and stop_loss > 0 and quote <= stop_loss:
        adjusted -= 100.0
        item["liveStopLossBreached"] = True
        reasons.append("live_stop_loss_breached")

    live_score = round(max(0.0, min(100.0, adjusted)), 2)
    item["dailyConfidenceScore"] = daily_score
    item["liveConfidenceScore"] = live_score
    item["liveScoreDelta"] = round(live_score - daily_score, 2)
    item["liveReasons"] = reasons
    item["confidenceScore"] = live_score
    if live_score < _float_value(args.buy_score_min, 65.0) and str(item.get("status", item.get("confidenceLabel", ""))).upper() in {"BUY_CANDIDATE", "STRONG_BUY"}:
        item["status"] = "WATCH" if live_score >= _float_value(args.live_watch_min_score, 45.0) else "HOLD"
        item["confidenceLabel"] = item["status"]
    return item


def choose_live_candidates(
    candidates: list[dict],
    positions: dict[str, dict],
    client: KISPaperClient,
    args: argparse.Namespace,
) -> tuple[list[dict], dict[str, float], dict[str, str], dict]:
    """Observe a wider ranked pool, drop weakened names, and refill watch slots."""
    ranked = sorted((item for item in candidates if item.get("code")), key=lambda item: _float_value(item.get("confidenceScore")), reverse=True)
    max_live = max(1, int(args.max_live_candidates))
    max_scan = max(max_live, int(getattr(args, "max_live_scan_candidates", max_live * 3) or max_live * 3))
    scan_pool = ranked[:max_scan]
    position_codes = {str(code) for code in positions}
    scan_codes = [str(item.get("code")) for item in scan_pool if item.get("code")]
    # Exit checks are time-sensitive: request held symbols first, then use the
    # remaining rate-limited calls for the larger candidate observation pool.
    codes = sorted(position_codes) + list(dict.fromkeys(code for code in scan_codes if code not in position_codes))
    prices, quote_errors = fetch_live_prices(
        client,
        codes,
        args.quote_delay_seconds,
        args.quote_retries,
        args.quote_rate_limit_backoff_seconds,
    )

    adjusted_by_code = {
        str(item.get("code")): live_adjust_candidate(item, prices.get(str(item.get("code"))), args)
        for item in scan_pool
        if item.get("code")
    }
    selected: list[dict] = []
    rejected = 0
    min_score = _float_value(args.live_watch_min_score, 45.0)
    for item in scan_pool:
        code = str(item.get("code"))
        adjusted = adjusted_by_code.get(code, item)
        if code in position_codes or _float_value(adjusted.get("liveConfidenceScore", adjusted.get("confidenceScore"))) >= min_score:
            selected.append(adjusted)
            if len([row for row in selected if str(row.get("code")) not in position_codes]) >= max_live:
                break
        else:
            rejected += 1

    for code in position_codes:
        if code not in {str(item.get("code")) for item in selected}:
            selected.append(adjusted_by_code.get(code, {"code": code, **positions.get(code, {})}))

    telemetry = {
        "liveScanned": len(scan_pool),
        "liveSelected": len(selected),
        "liveRejected": rejected,
        "liveObserved": len(prices),
    }
    return selected, prices, quote_errors, telemetry


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
    session_day = datetime.now(KST).date()
    session_date = session_day.isoformat()
    intraday_state = repo.fetch_intraday_trade_state(market, session_date) if hasattr(repo, "fetch_intraday_trade_state") else {}
    blocked_entry_codes = {str(code) for code in (intraday_state.get("blockedEntryCodes") or [])}
    live_candidates, prices, quote_errors, live_telemetry = choose_live_candidates(candidates, positions, client, args)
    equity = float(account.get("totalEquity", account.get("cash", args.initial_cash)) or args.initial_cash)
    policy = IntradayPolicyConfig(
        buy_score_min=args.buy_score_min,
        score_exit_threshold=args.score_exit_threshold,
        trailing_stop_pct=args.trailing_stop_pct,
        position_weight=args.position_weight,
        rotation_score_gap=args.rotation_score_gap,
        profit_lock_activate_pct=float(getattr(args, "profit_lock_activate_pct", 0.03)),
        profit_lock_trailing_pct=float(getattr(args, "profit_lock_trailing_pct", 0.02)),
        profit_lock_min_pnl_pct=float(getattr(args, "profit_lock_min_pnl_pct", 0.005)),
        same_day_stop_loss_pct=float(getattr(args, "same_day_stop_loss_pct", 0.03)),
    )
    orders = build_intraday_orders(
        live_candidates, positions, equity, float(account.get("cash", 0) or 0), prices, policy,
        entry_blocked_codes=blocked_entry_codes if getattr(args, "block_reentry_after_exit", True) else set(),
        session_date=session_day,
    )
    telemetry = {"sameDayEntryBlocked": len(blocked_entry_codes)}
    if not args.execute:
        return {"status": "dry_run", "market": market, "orderCount": len(orders), "orders": orders, "prices": prices, "quoteErrors": quote_errors, **live_telemetry, **telemetry, **account_sync}
    result = apply_paper_orders(account, positions, orders, prices, market=market, initial_cash=args.initial_cash)
    for log in result["logs"]:
        broker_response = client.submit_market_order(str(log["action"]), str(log["code"]), int(log["quantity"]))
        log["orderType"] = "MARKET"
        log["brokerOrderNo"] = broker_response.get("output", {}).get("ODNO")
    new_exit_locks = {
        str(log["code"]): {"reason": str(log.get("reason") or ""), "brokerOrderNo": log.get("brokerOrderNo")}
        for log in result["logs"]
        if str(log.get("action")).upper() == "SELL" and str(log.get("reason") or "") in REENTRY_BLOCK_EXIT_REASONS
    }
    if getattr(args, "block_reentry_after_exit", True) and new_exit_locks and hasattr(repo, "save_intraday_trade_state"):
        prior_locks = intraday_state.get("exitLocks") if isinstance(intraday_state.get("exitLocks"), dict) else {}
        repo.save_intraday_trade_state(market, session_date, {"blockedEntryCodes": sorted(blocked_entry_codes | set(new_exit_locks)), "exitLocks": {**prior_locks, **new_exit_locks}})
    telemetry["newSameDayEntryLocks"] = len(new_exit_locks)
    repo.save_paper_positions(result["positions"], previous_codes=set(positions))
    repo.append_trade_logs(result["logs"])
    repo.save_account_snapshot(result["snapshot"])
    return {"status": "applied", "market": market, "orderCount": len(orders), "executedCount": len(result["logs"]), "orders": orders, "quoteErrors": quote_errors, **live_telemetry, **telemetry, **account_sync}

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
        "liveScanned",
        "liveSelected",
        "liveRejected",
        "liveObserved",
        "sameDayEntryBlocked",
        "newSameDayEntryLocks",
        "requested",
        "completed",
        "failed",
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
        cycle_started = time.monotonic()
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
        elapsed = time.monotonic() - cycle_started
        time.sleep(max(0.0, interval - elapsed))


if __name__ == "__main__":
    load_server_env()
    arguments = build_parser().parse_args()
    if arguments.process_refresh_requests:
        refresh_repo = FirestoreStrategyRepository(init_firestore(arguments.cred_path))
        refresh_client = KISPaperClient(KISPaperConfig.from_env())
        log_event(
            process_paper_refresh_requests(
                refresh_repo,
                refresh_client,
                market=arguments.market,
                initial_cash=arguments.initial_cash,
                limit=arguments.refresh_request_limit,
            )
        )
    elif arguments.loop:
        run_loop(arguments)
    else:
        print(run(arguments))
