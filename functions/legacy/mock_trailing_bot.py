import datetime as dt
import os
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

import firebase_admin
from dotenv import load_dotenv
from firebase_admin import credentials, firestore

from kis_api import KoreaStockTrader


load_dotenv()


@dataclass
class BotConfig:
    kis_mode: str = os.getenv("KIS_MODE", "mock")
    market: str = os.getenv("BOT_MARKET", "KR")
    budget_per_trade: int = int(os.getenv("BOT_BUDGET_PER_TRADE", "200000"))
    trailing_stop_pct: float = float(os.getenv("BOT_TRAILING_STOP_PCT", "0.018"))
    poll_interval_sec: int = int(os.getenv("BOT_POLL_INTERVAL_SEC", "15"))
    max_new_positions_per_cycle: int = int(os.getenv("BOT_MAX_NEW_POSITIONS_PER_CYCLE", "5"))
    token_refresh_minutes: int = int(os.getenv("BOT_TOKEN_REFRESH_MINUTES", "50"))
    firebase_cred_path: str = os.getenv("BOT_FIREBASE_CRED_PATH") or os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "./serviceAccountKey.json")
    portfolio_collection: str = os.getenv("BOT_PORTFOLIO_COLLECTION", "bot_portfolio")
    trade_log_collection: str = os.getenv("BOT_TRADE_LOG_COLLECTION", "bot_trade_logs")
    account_snapshot_collection: str = os.getenv("BOT_ACCOUNT_SNAPSHOT_COLLECTION", "bot_account_snapshot")


class FirestoreTrailingStopBot:
    def __init__(self, config: BotConfig):
        self.config = config
        self.db = self._init_firestore(config.firebase_cred_path)
        self.trader = KoreaStockTrader(mode=config.kis_mode)
        self.last_auth: Optional[dt.datetime] = None

    @staticmethod
    def _init_firestore(cred_path: str):
        if not os.path.exists(cred_path):
            raise FileNotFoundError(f"Firebase credential file not found: {cred_path}")
        if not firebase_admin._apps:
            firebase_admin.initialize_app(credentials.Certificate(cred_path))
        return firestore.client()

    def refresh_token_if_needed(self):
        now = dt.datetime.now()
        if self.last_auth is None:
            self.trader.auth()
            self.last_auth = now
            return

        minutes = (now - self.last_auth).total_seconds() / 60
        if minutes >= self.config.token_refresh_minutes:
            self.trader.auth()
            self.last_auth = now

    def get_buy_signals(self) -> List[Dict]:
        query = (
            self.db.collection("stock_analysis")
            .where("type", "==", "buy_signal")
            .where("market", "==", self.config.market)
        )
        rows = []
        for doc in query.stream():
            data = doc.to_dict() or {}
            stock_id = data.get("id", doc.id)
            code = stock_id.split("_", 1)[1] if "_" in stock_id else stock_id
            rows.append(
                {
                    "id": stock_id,
                    "code": code,
                    "name": data.get("name", code),
                    "bandwidth": data.get("bandwidth", 999),
                    "updatedAt": data.get("updatedAt"),
                }
            )

        rows.sort(key=lambda x: x["bandwidth"])
        return rows

    def get_portfolio(self) -> Dict[str, Dict]:
        docs = self.db.collection(self.config.portfolio_collection).stream()
        result = {}
        for doc in docs:
            result[doc.id] = doc.to_dict() or {}
        return result

    def log_trade(self, action: str, code: str, name: str, price: int, qty: int, reason: str, pnl_pct: Optional[float] = None):
        payload = {
            "action": action,
            "code": code,
            "name": name,
            "price": price,
            "quantity": qty,
            "reason": reason,
            "amount": price * qty,
            "market": self.config.market,
            "createdAt": firestore.SERVER_TIMESTAMP,
        }
        if pnl_pct is not None:
            payload["pnlPct"] = round(pnl_pct, 4)

        self.db.collection(self.config.trade_log_collection).add(payload)

    def update_account_snapshot(self):
        balance_rows = self.trader.get_balance()
        total_eval = sum(float(row.get("evlu_amt", 0)) for row in balance_rows)
        total_buy = sum(float(row.get("pchs_amt", 0)) for row in balance_rows)
        holdings = []
        for row in balance_rows:
            holdings.append(
                {
                    "code": row.get("pdno"),
                    "name": row.get("prdt_name"),
                    "qty": int(row.get("hldg_qty", 0)),
                    "evalAmt": float(row.get("evlu_amt", 0)),
                    "buyAmt": float(row.get("pchs_amt", 0)),
                    "pnlPct": float(row.get("fltt_rt", 0)),
                }
            )

        payload = {
            "mode": self.config.kis_mode,
            "market": self.config.market,
            "holdingCount": len(holdings),
            "totalEvalAmt": total_eval,
            "totalBuyAmt": total_buy,
            "holdings": holdings,
            "updatedAt": firestore.SERVER_TIMESTAMP,
        }
        self.db.collection(self.config.account_snapshot_collection).document("latest").set(payload, merge=True)

    def try_buy_from_signals(self):
        signals = self.get_buy_signals()
        if not signals:
            print("[BOT] no buy_signal found")
            return

        portfolio = self.get_portfolio()
        buys = 0

        for signal in signals:
            if buys >= self.config.max_new_positions_per_cycle:
                break

            code = signal["code"]
            name = signal["name"]
            if code in portfolio:
                continue

            price = self.trader.get_current_price(code)
            if not price or price <= 0:
                continue

            qty = self.config.budget_per_trade // price
            if qty < 1:
                print(f"[BOT][BUY][SKIP] {name}({code}) price={price} budget={self.config.budget_per_trade}")
                continue

            ok = self.trader.buy_market_order(code, qty)
            if not ok:
                continue

            now = dt.datetime.now().isoformat(timespec="seconds")
            position = {
                "code": code,
                "name": name,
                "buyPrice": price,
                "highestPrice": price,
                "quantity": qty,
                "market": self.config.market,
                "signalType": "buy_signal",
                "boughtAt": now,
                "updatedAt": firestore.SERVER_TIMESTAMP,
            }
            self.db.collection(self.config.portfolio_collection).document(code).set(position)
            self.log_trade("BUY", code, name, price, qty, "buy_signal")
            buys += 1
            print(f"[BOT][BUY] {name}({code}) price={price} qty={qty}")

    def monitor_and_sell(self):
        portfolio = self.get_portfolio()
        if not portfolio:
            return

        for code, pos in portfolio.items():
            qty = int(pos.get("quantity", 0))
            if qty <= 0:
                continue

            buy_price = float(pos.get("buyPrice", 0))
            highest = float(pos.get("highestPrice", buy_price))
            name = pos.get("name", code)

            current = self.trader.get_current_price(code)
            if not current or current <= 0:
                continue

            new_highest = max(highest, current)
            stop_price = new_highest * (1 - self.config.trailing_stop_pct)

            if current <= stop_price:
                ok = self.trader.sell_market_order(code, qty)
                if ok:
                    pnl_pct = ((current - buy_price) / buy_price * 100) if buy_price > 0 else 0
                    self.log_trade("SELL", code, name, current, qty, "trailing_stop_1.8pct", pnl_pct=pnl_pct)
                    self.db.collection(self.config.portfolio_collection).document(code).delete()
                    print(
                        f"[BOT][SELL] {name}({code}) current={current} stop={int(stop_price)} pnl={pnl_pct:.2f}%"
                    )
                continue

            updates = {
                "highestPrice": new_highest,
                "lastPrice": current,
                "lastCheckedAt": dt.datetime.now().isoformat(timespec="seconds"),
                "updatedAt": firestore.SERVER_TIMESTAMP,
            }
            self.db.collection(self.config.portfolio_collection).document(code).set(updates, merge=True)

    def run_forever(self):
        print("[BOT] started")
        print(
            f"[BOT] mode={self.config.kis_mode}, market={self.config.market}, "
            f"budget_per_trade={self.config.budget_per_trade}, "
            f"trailing_stop_pct={self.config.trailing_stop_pct}"
        )

        while True:
            try:
                self.refresh_token_if_needed()
                self.try_buy_from_signals()
                self.monitor_and_sell()
                self.update_account_snapshot()
            except Exception as exc:
                print(f"[BOT] cycle error: {exc}")
            time.sleep(self.config.poll_interval_sec)


if __name__ == "__main__":
    cfg = BotConfig()
    bot = FirestoreTrailingStopBot(cfg)
    bot.run_forever()
