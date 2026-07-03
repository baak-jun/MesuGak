"""Submit one manual KIS paper order and persist an audit log to Firestore."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

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

from strategy_engine.kis_paper import KISPaperClient, KISPaperConfig  # noqa: E402
from strategy_engine.repositories import FirestoreStrategyRepository, init_firestore  # noqa: E402


KST = ZoneInfo("Asia/Seoul")


def load_server_env() -> None:
    load_dotenv(os.getenv("MESUGAK_ENV_FILE") or str(FUNCTIONS_DIR / ".env"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Submit one manual KIS paper order and write Mesugak logs")
    parser.add_argument("--side", choices=["BUY", "SELL"], required=True)
    parser.add_argument("--code", required=True, help="KR stock code, e.g. 005930")
    parser.add_argument("--quantity", type=int, required=True)
    parser.add_argument("--name", default="")
    parser.add_argument("--market", default=os.getenv("MESUGAK_MARKET", "KR"))
    parser.add_argument("--reason", default="manual_kis_order")
    parser.add_argument("--initial-cash", type=float, default=float(os.getenv("MESUGAK_INITIAL_CASH", "10000000")))
    parser.add_argument("--cred-path", default=None)
    parser.add_argument("--skip-account-sync", action="store_true")
    return parser


def _now() -> str:
    return datetime.now(KST).isoformat(timespec="seconds")


def _safe_quote(client: KISPaperClient, code: str) -> tuple[float, str]:
    try:
        return client.quote(code), ""
    except Exception as exc:  # noqa: BLE001 - quote failure should not hide the order attempt.
        return 0.0, f"{type(exc).__name__}: {exc}"


def _sync_account(repo: FirestoreStrategyRepository, client: KISPaperClient, *, market: str, initial_cash: float) -> dict:
    previous_positions = repo.fetch_current_positions()
    account, positions = client.fetch_balance(market=market, initial_cash=initial_cash)
    repo.save_paper_positions(positions, previous_codes=set(previous_positions))
    repo.save_account_snapshot(account)
    return {
        "accountSynced": True,
        "holdingCount": len(positions),
        "cash": account.get("cash"),
        "totalEquity": account.get("totalEquity"),
    }


def run(args: argparse.Namespace, *, repo: FirestoreStrategyRepository | None = None, client: KISPaperClient | None = None) -> dict:
    market = str(args.market).upper()
    code = str(args.code).strip()
    side = str(args.side).upper()
    quantity = int(args.quantity)
    if quantity <= 0:
        raise ValueError("--quantity must be positive")

    repo = repo or FirestoreStrategyRepository(init_firestore(args.cred_path))
    client = client or KISPaperClient(KISPaperConfig.from_env())
    price, quote_error = _safe_quote(client, code)

    log = {
        "source": "Mesugak_V2",
        "mode": "manual_kis_order",
        "market": market,
        "action": side,
        "code": code,
        "name": args.name or code,
        "price": price,
        "quantity": quantity,
        "amount": round(price * quantity, 2) if price > 0 else 0,
        "reason": args.reason,
        "orderStatus": "REQUESTED",
        "quoteError": quote_error,
        "createdAt": _now(),
    }

    payload: dict = {"status": "requested", "market": market, "order": log}
    exit_code = 0
    try:
        response = client.submit_market_order(side, code, quantity)
        broker_order_no = response.get("output", {}).get("ODNO")
        log.update({
            "orderStatus": "ACCEPTED",
            "brokerOrderNo": broker_order_no,
            "brokerResponse": response,
        })
        payload.update({"status": "accepted", "brokerOrderNo": broker_order_no, "brokerResponse": response})
    except Exception as exc:  # noqa: BLE001 - failed manual attempts must still be visible in the UI.
        exit_code = 1
        error = f"{type(exc).__name__}: {exc}"
        log.update({"orderStatus": "FAILED", "errorMessage": error})
        payload.update({"status": "failed", "errorMessage": error})

    try:
        repo.append_trade_logs([log])
        payload["firestoreLogged"] = True
    except Exception as exc:  # noqa: BLE001 - still print enough information for the file log.
        exit_code = 1
        payload["firestoreLogged"] = False
        payload["firestoreError"] = f"{type(exc).__name__}: {exc}"

    if log.get("orderStatus") == "ACCEPTED" and not args.skip_account_sync:
        try:
            payload["accountSync"] = _sync_account(repo, client, market=market, initial_cash=args.initial_cash)
        except Exception as exc:  # noqa: BLE001 - accepted order log is still valuable without balance sync.
            payload["accountSync"] = {"accountSynced": False, "accountSyncError": f"{type(exc).__name__}: {exc}"}

    payload["exitCode"] = exit_code
    return payload


if __name__ == "__main__":
    load_server_env()
    parsed = build_parser().parse_args()
    result = run(parsed)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    raise SystemExit(int(result.get("exitCode", 0)))
