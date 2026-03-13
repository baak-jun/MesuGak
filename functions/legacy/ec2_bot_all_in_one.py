import argparse
import datetime as dt
import os
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

import firebase_admin
import requests
from dotenv import load_dotenv
from firebase_admin import credentials, firestore


load_dotenv()


def env_first(*keys: str) -> Optional[str]:
    for key in keys:
        value = os.getenv(key)
        if value:
            return value
    return None


@dataclass
class BotConfig:
    kis_mode: str = os.getenv("KIS_MODE", "mock").lower()
    market: str = os.getenv("BOT_MARKET", "KR")
    budget_per_trade: int = int(os.getenv("BOT_BUDGET_PER_TRADE", "200000"))
    trailing_stop_pct: float = float(os.getenv("BOT_TRAILING_STOP_PCT", "0.018"))
    poll_interval_sec: int = int(os.getenv("BOT_POLL_INTERVAL_SEC", "15"))
    max_new_positions_per_cycle: int = int(os.getenv("BOT_MAX_NEW_POSITIONS_PER_CYCLE", "5"))
    token_refresh_minutes: int = int(os.getenv("BOT_TOKEN_REFRESH_MINUTES", "50"))
    firebase_cred_path: str = env_first("BOT_FIREBASE_CRED_PATH", "FIREBASE_SERVICE_ACCOUNT_PATH") or "./serviceAccountKey.json"

    portfolio_collection: str = os.getenv("BOT_PORTFOLIO_COLLECTION", "bot_portfolio")
    trade_log_collection: str = os.getenv("BOT_TRADE_LOG_COLLECTION", "bot_trade_logs")
    account_snapshot_collection: str = os.getenv("BOT_ACCOUNT_SNAPSHOT_COLLECTION", "bot_account_snapshot")
    runtime_heartbeat_sec: int = int(os.getenv("BOT_RUNTIME_HEARTBEAT_SEC", "60"))

    active_start_hhmm: str = os.getenv("BOT_ACTIVE_START_HHMM", "09:00")
    active_end_hhmm: str = os.getenv("BOT_ACTIVE_END_HHMM", "15:20")
    weekdays_only: bool = os.getenv("BOT_WEEKDAYS_ONLY", "true").lower() == "true"


class KISClient:
    def __init__(self, mode: str = "mock"):
        self.mode = (mode or "mock").lower()
        self.base_url = "https://openapi.koreainvestment.com:9443" if self.mode == "real" else "https://openapivts.koreainvestment.com:29443"

        self.appkey = env_first("REAL_APP_KEY", "KIS_REAL_APP_KEY") if self.mode == "real" else env_first("MOCK_APP_KEY", "KIS_MOCK_APP_KEY", "VITE_KIS_APP_KEY")
        self.appsecret = env_first("REAL_APP_SECRET", "KIS_REAL_APP_SECRET") if self.mode == "real" else env_first("MOCK_APP_SECRET", "KIS_MOCK_APP_SECRET", "VITE_KIS_APP_SECRET")
        self.acc_no = env_first("REAL_ACC_NO", "KIS_REAL_ACC_NO") if self.mode == "real" else env_first("MOCK_ACC_NO", "KIS_MOCK_ACC_NO")

        self.tr_id_buy = "TTTC0802U" if self.mode == "real" else "VTTC0802U"
        self.tr_id_sell = "TTTC0801U" if self.mode == "real" else "VTTC0801U"
        self.tr_id_balance = "TTTC8434R" if self.mode == "real" else "VTTC8434R"

        self.access_token: Optional[str] = None
        self.last_auth: Optional[dt.datetime] = None

        self._validate_config()
        self.acc_code, self.acc_prod = self._parse_account(self.acc_no)

    def _validate_config(self):
        missing = []
        if not self.appkey:
            missing.append("APP_KEY")
        if not self.appsecret:
            missing.append("APP_SECRET")
        if not self.acc_no:
            missing.append("ACC_NO")
        if missing:
            prefix = "REAL" if self.mode == "real" else "MOCK"
            raise ValueError(f"Missing {prefix} settings: {', '.join(missing)}")

    @staticmethod
    def _parse_account(acc_no: str):
        if "-" not in acc_no:
            raise ValueError("Invalid ACC_NO format. Expected: 12345678-01")
        return acc_no.split("-", 1)

    def _ensure_token(self, refresh_minutes: int = 50):
        now = dt.datetime.now()
        if self.access_token is None or self.last_auth is None:
            self.auth()
            return
        age_min = (now - self.last_auth).total_seconds() / 60
        if age_min >= refresh_minutes:
            self.auth()

    def auth(self):
        url = f"{self.base_url}/oauth2/tokenP"
        body = {
            "grant_type": "client_credentials",
            "appkey": self.appkey,
            "appsecret": self.appsecret,
        }
        res = requests.post(url, json=body, timeout=10)
        res.raise_for_status()
        data = res.json()
        token = data.get("access_token")
        if not token:
            raise RuntimeError(f"KIS token response missing access_token: {data}")
        self.access_token = token
        self.last_auth = dt.datetime.now()
        print(f"[KIS] token refreshed ({self.mode})")

    def _headers(self, tr_id: str, body: Optional[dict] = None):
        headers = {
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.appkey,
            "appsecret": self.appsecret,
            "tr_id": tr_id,
            "custtype": "P",
        }
        if body is not None:
            hashkey = self._get_hashkey(body)
            if hashkey:
                headers["hashkey"] = hashkey
        return headers

    def _get_hashkey(self, payload: dict) -> Optional[str]:
        try:
            res = requests.post(
                f"{self.base_url}/uapi/hashkey",
                headers={
                    "content-type": "application/json; charset=utf-8",
                    "appkey": self.appkey,
                    "appsecret": self.appsecret,
                },
                json=payload,
                timeout=10,
            )
            if res.status_code != 200:
                return None
            return res.json().get("HASH")
        except Exception:
            return None

    def get_current_price(self, code: str) -> Optional[int]:
        self._ensure_token()
        path = "/uapi/domestic-stock/v1/quotations/inquire-price"
        params = {"fid_cond_mrkt_div_code": "J", "fid_input_iscd": code}
        try:
            res = requests.get(
                f"{self.base_url}{path}",
                headers=self._headers("FHKST01010100"),
                params=params,
                timeout=10,
            )
            if res.status_code != 200:
                print(f"[KIS][PRICE][{code}] http={res.status_code} body={res.text}")
                return None
            price = res.json().get("output", {}).get("stck_prpr")
            return int(price) if price else None
        except Exception as exc:
            print(f"[KIS][PRICE][{code}] error: {exc}")
            return None

    def _order(self, code: str, qty: int, tr_id: str, side: str) -> bool:
        self._ensure_token()
        path = "/uapi/domestic-stock/v1/trading/order-cash"
        body = {
            "CANO": self.acc_code,
            "ACNT_PRDT_CD": self.acc_prod,
            "PDNO": code,
            "ORD_DVSN": "01",
            "ORD_QTY": str(qty),
            "ORD_UNPR": "0",
        }

        try:
            res = requests.post(
                f"{self.base_url}{path}",
                headers=self._headers(tr_id, body=body),
                json=body,
                timeout=10,
            )
            if res.status_code != 200:
                print(f"[KIS][{side}] http={res.status_code} body={res.text}")
                return False
            data = res.json()
            if data.get("rt_cd") == "0":
                order_no = data.get("output", {}).get("ODNO", "N/A")
                print(f"[KIS][{side}] success code={code} qty={qty} order_no={order_no}")
                return True
            print(f"[KIS][{side}] fail msg={data.get('msg1')} data={data}")
            return False
        except Exception as exc:
            print(f"[KIS][{side}] error: {exc}")
            return False

    def buy_market(self, code: str, qty: int) -> bool:
        return self._order(code, qty, self.tr_id_buy, "BUY")

    def sell_market(self, code: str, qty: int) -> bool:
        return self._order(code, qty, self.tr_id_sell, "SELL")

    def get_balance(self) -> List[Dict]:
        self._ensure_token()
        path = "/uapi/domestic-stock/v1/trading/inquire-balance"
        params = {
            "CANO": self.acc_code,
            "ACNT_PRDT_CD": self.acc_prod,
            "AFHR_FLPR_YN": "N",
            "OFL_YN": "N",
            "INQR_DVSN": "02",
            "UNPR_DVSN": "01",
            "FUND_STTL_ICLD_YN": "N",
            "FNCG_AMT_AUTO_RDPT_YN": "N",
            "PRCS_DVSN": "00",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": "",
        }
        try:
            res = requests.get(
                f"{self.base_url}{path}",
                headers=self._headers(self.tr_id_balance),
                params=params,
                timeout=10,
            )
            if res.status_code != 200:
                print(f"[KIS][BAL] http={res.status_code} body={res.text}")
                return []
            data = res.json()
            out = []
            for item in data.get("output1", []):
                qty = int(item.get("hldg_qty", 0))
                if qty <= 0:
                    continue
                out.append(
                    {
                        "pdno": item.get("pdno"),
                        "prdt_name": item.get("prdt_name"),
                        "hldg_qty": qty,
                        "pchs_amt": float(item.get("pchs_amt", 0)),
                        "evlu_amt": float(item.get("evlu_amt", 0)),
                        "evlu_pfls_rt": float(item.get("evlu_pfls_rt", 0)),
                    }
                )
            return out
        except Exception as exc:
            print(f"[KIS][BAL] error: {exc}")
            return []


class FirebaseRepo:
    def __init__(self, cred_path: str):
        if not os.path.exists(cred_path):
            raise FileNotFoundError(f"Firebase credential file not found: {cred_path}")
        if not firebase_admin._apps:
            firebase_admin.initialize_app(credentials.Certificate(cred_path))
        self.db = firestore.client()

    def fetch_buy_signals(self, market: str) -> List[Dict]:
        q = (
            self.db.collection("stock_analysis")
            .where("type", "==", "buy_signal")
            .where("market", "==", market)
        )
        items = []
        for snap in q.stream():
            d = snap.to_dict() or {}
            sid = d.get("id", snap.id)
            code = sid.split("_", 1)[1] if "_" in sid else sid
            items.append(
                {
                    "id": sid,
                    "code": code,
                    "name": d.get("name", code),
                    "bandwidth": float(d.get("bandwidth", 999)),
                    "updatedAt": d.get("updatedAt"),
                }
            )
        items.sort(key=lambda x: x["bandwidth"])
        return items

    def get_portfolio(self, collection_name: str) -> Dict[str, Dict]:
        out = {}
        for doc in self.db.collection(collection_name).stream():
            out[doc.id] = doc.to_dict() or {}
        return out

    def upsert_position(self, collection_name: str, code: str, payload: Dict, merge: bool = False):
        self.db.collection(collection_name).document(code).set(payload, merge=merge)

    def delete_position(self, collection_name: str, code: str):
        self.db.collection(collection_name).document(code).delete()

    def add_trade_log(self, collection_name: str, payload: Dict):
        self.db.collection(collection_name).add(payload)

    def update_snapshot(self, collection_name: str, payload: Dict):
        self.db.collection(collection_name).document("latest").set(payload, merge=True)

    def set_user_role(self, email: str, role: str):
        user_docs = self.db.collection("users").where("email", "==", email).limit(1).stream()
        target = None
        for d in user_docs:
            target = d
            break
        if not target:
            raise RuntimeError(f"User not found in Firestore users collection: {email}")
        self.db.collection("users").document(target.id).update({"role": role})


class AutoTraderBot:
    def __init__(self, cfg: BotConfig):
        self.cfg = cfg
        self.repo = FirebaseRepo(cfg.firebase_cred_path)
        self.kis = KISClient(cfg.kis_mode)
        self.last_runtime_heartbeat: Optional[dt.datetime] = None

    @staticmethod
    def _now_hhmm() -> str:
        return dt.datetime.now().strftime("%H:%M")

    def _is_active_time(self) -> bool:
        now = dt.datetime.now()
        if self.cfg.weekdays_only and now.weekday() >= 5:
            return False
        hhmm = now.strftime("%H:%M")
        return self.cfg.active_start_hhmm <= hhmm <= self.cfg.active_end_hhmm

    def _log_trade(self, action: str, code: str, name: str, price: int, qty: int, reason: str, pnl_pct: Optional[float] = None):
        payload = {
            "action": action,
            "code": code,
            "name": name,
            "price": price,
            "quantity": qty,
            "amount": price * qty,
            "reason": reason,
            "market": self.cfg.market,
            "createdAt": firestore.SERVER_TIMESTAMP,
        }
        if pnl_pct is not None:
            payload["pnlPct"] = round(float(pnl_pct), 4)
        self.repo.add_trade_log(self.cfg.trade_log_collection, payload)

    def _log_runtime(self, message: str, reason: str = "runtime", level: str = "INFO"):
        payload = {
            "action": level,
            "code": "-",
            "name": "SYSTEM",
            "price": 0,
            "quantity": 0,
            "amount": 0,
            "reason": reason,
            "message": message,
            "market": self.cfg.market,
            "runtime": True,
            "createdAt": firestore.SERVER_TIMESTAMP,
        }
        self.repo.add_trade_log(self.cfg.trade_log_collection, payload)

    def _update_account_snapshot(self):
        rows = self.kis.get_balance()
        holdings = []
        total_eval = 0.0
        total_buy = 0.0

        for r in rows:
            eval_amt = float(r.get("evlu_amt", 0))
            buy_amt = float(r.get("pchs_amt", 0))
            total_eval += eval_amt
            total_buy += buy_amt
            holdings.append(
                {
                    "code": r.get("pdno"),
                    "name": r.get("prdt_name"),
                    "qty": int(r.get("hldg_qty", 0)),
                    "evalAmt": eval_amt,
                    "buyAmt": buy_amt,
                    "pnlPct": float(r.get("evlu_pfls_rt", 0)),
                }
            )

        self.repo.update_snapshot(
            self.cfg.account_snapshot_collection,
            {
                "mode": self.cfg.kis_mode,
                "market": self.cfg.market,
                "holdingCount": len(holdings),
                "totalEvalAmt": total_eval,
                "totalBuyAmt": total_buy,
                "holdings": holdings,
                "updatedAt": firestore.SERVER_TIMESTAMP,
            },
        )

    def _buy_cycle(self):
        signals = self.repo.fetch_buy_signals(self.cfg.market)
        if not signals:
            print("[BOT] no buy signals")
            self._log_runtime("No buy_signal candidates from Firestore", reason="buy_cycle")
            return

        portfolio = self.repo.get_portfolio(self.cfg.portfolio_collection)
        buys = 0

        for sig in signals:
            if buys >= self.cfg.max_new_positions_per_cycle:
                break

            code = sig["code"]
            name = sig["name"]
            if code in portfolio:
                continue

            price = self.kis.get_current_price(code)
            if not price or price <= 0:
                continue

            qty = self.cfg.budget_per_trade // price
            if qty < 1:
                continue

            if not self.kis.buy_market(code, qty):
                continue

            now_iso = dt.datetime.now().isoformat(timespec="seconds")
            self.repo.upsert_position(
                self.cfg.portfolio_collection,
                code,
                {
                    "code": code,
                    "name": name,
                    "buyPrice": float(price),
                    "highestPrice": float(price),
                    "quantity": int(qty),
                    "signalType": "buy_signal",
                    "market": self.cfg.market,
                    "boughtAt": now_iso,
                    "updatedAt": firestore.SERVER_TIMESTAMP,
                },
            )
            self._log_trade("BUY", code, name, price, qty, "buy_signal")
            print(f"[BOT][BUY] {name}({code}) price={price} qty={qty}")
            buys += 1

        if buys == 0:
            self._log_runtime(f"Buy cycle done: signals={len(signals)}, executed=0", reason="buy_cycle")
        else:
            self._log_runtime(f"Buy cycle done: signals={len(signals)}, executed={buys}", reason="buy_cycle")

    def _sell_cycle(self):
        portfolio = self.repo.get_portfolio(self.cfg.portfolio_collection)
        if not portfolio:
            self._log_runtime("Sell monitor: no open positions", reason="sell_cycle")
            return

        sold = 0
        for code, pos in portfolio.items():
            qty = int(pos.get("quantity", 0))
            if qty <= 0:
                continue

            name = pos.get("name", code)
            buy_price = float(pos.get("buyPrice", 0))
            highest = float(pos.get("highestPrice", buy_price))

            current = self.kis.get_current_price(code)
            if not current or current <= 0:
                continue

            new_high = max(highest, float(current))
            stop_price = new_high * (1.0 - self.cfg.trailing_stop_pct)

            if float(current) <= stop_price:
                ok = self.kis.sell_market(code, qty)
                if ok:
                    pnl_pct = ((float(current) - buy_price) / buy_price * 100.0) if buy_price > 0 else 0.0
                    self._log_trade("SELL", code, name, current, qty, f"trailing_stop_{self.cfg.trailing_stop_pct}", pnl_pct)
                    self.repo.delete_position(self.cfg.portfolio_collection, code)
                    print(f"[BOT][SELL] {name}({code}) current={current} stop={int(stop_price)} pnl={pnl_pct:.2f}%")
                    sold += 1
                continue

            self.repo.upsert_position(
                self.cfg.portfolio_collection,
                code,
                {
                    "highestPrice": new_high,
                    "lastPrice": float(current),
                    "lastCheckedAt": dt.datetime.now().isoformat(timespec="seconds"),
                    "updatedAt": firestore.SERVER_TIMESTAMP,
                },
                merge=True,
            )

        self._log_runtime(f"Sell monitor done: tracked={len(portfolio)}, sold={sold}", reason="sell_cycle")

    def run_cycle(self):
        self.kis._ensure_token(self.cfg.token_refresh_minutes)

        active = self._is_active_time()
        now = dt.datetime.now()
        if (
            self.last_runtime_heartbeat is None
            or (now - self.last_runtime_heartbeat).total_seconds() >= self.cfg.runtime_heartbeat_sec
        ):
            self._log_runtime(
                f"Heartbeat: active={active}, poll={self.cfg.poll_interval_sec}s, trailing_stop={self.cfg.trailing_stop_pct}",
                reason="heartbeat",
            )
            self.last_runtime_heartbeat = now

        if active:
            self._buy_cycle()
            self._sell_cycle()
        else:
            print(f"[BOT] outside active time ({self._now_hhmm()})")
            self._log_runtime(f"Outside active time: now={self._now_hhmm()}", reason="schedule")

        self._update_account_snapshot()

    def run_forever(self):
        print("[BOT] started")
        print(
            f"[BOT] mode={self.cfg.kis_mode}, market={self.cfg.market}, "
            f"budget={self.cfg.budget_per_trade}, trailing_stop={self.cfg.trailing_stop_pct}, "
            f"active={self.cfg.active_start_hhmm}-{self.cfg.active_end_hhmm}"
        )

        while True:
            try:
                self.run_cycle()
            except Exception as exc:
                print(f"[BOT] cycle error: {exc}")
                self._log_runtime(f"Cycle error: {exc}", reason="exception", level="ERROR")
            time.sleep(self.cfg.poll_interval_sec)


def cmd_run(args):
    cfg = BotConfig()
    bot = AutoTraderBot(cfg)
    if args.once:
        bot.run_cycle()
    else:
        bot.run_forever()


def cmd_set_role(args):
    cfg = BotConfig()
    repo = FirebaseRepo(cfg.firebase_cred_path)
    role = args.role.strip().lower()
    if role not in {"member", "user", "admin"}:
        raise ValueError("role must be one of: member, user, admin")
    repo.set_user_role(args.email.strip(), role)
    print(f"[ROLE] updated: {args.email} -> {role}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="MesuGak EC2 all-in-one bot")
    sub = p.add_subparsers(dest="cmd", required=True)

    run_p = sub.add_parser("run", help="run auto-trader")
    run_p.add_argument("--once", action="store_true", help="run one cycle and exit")
    run_p.set_defaults(func=cmd_run)

    role_p = sub.add_parser("set-role", help="set users/{uid}.role by email")
    role_p.add_argument("--email", required=True)
    role_p.add_argument("--role", required=True)
    role_p.set_defaults(func=cmd_set_role)

    return p


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
