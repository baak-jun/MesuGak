"""Minimal KIS virtual-investment REST client for the school server only."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from time import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def _as_float(value) -> float:
    try:
        return float(str(value or "0").replace(",", ""))
    except (TypeError, ValueError):
        return 0.0


def _first_number(payload: dict, keys: tuple[str, ...]) -> float:
    for key in keys:
        if payload.get(key) not in (None, ""):
            return _as_float(payload.get(key))
    return 0.0


@dataclass(frozen=True)
class KISPaperConfig:
    app_key: str
    app_secret: str
    cano: str
    account_product_code: str
    base_url: str = "https://openapivts.koreainvestment.com:29443"
    token_cache_path: str = ""

    @classmethod
    def from_env(cls) -> "KISPaperConfig":
        values = {
            "app_key": os.getenv("KIS_PAPER_APP_KEY", ""),
            "app_secret": os.getenv("KIS_PAPER_APP_SECRET", ""),
            "cano": os.getenv("KIS_PAPER_CANO", ""),
            "account_product_code": os.getenv("KIS_PAPER_ACNT_PRDT_CD", ""),
            "base_url": os.getenv("KIS_PAPER_BASE_URL", "https://openapivts.koreainvestment.com:29443"),
            "token_cache_path": os.getenv("KIS_PAPER_TOKEN_CACHE", ""),
        }
        if not all(values[key] for key in ("app_key", "app_secret", "cano", "account_product_code")):
            raise ValueError("Missing KIS paper credentials. Set KIS_PAPER_APP_KEY, KIS_PAPER_APP_SECRET, KIS_PAPER_CANO, and KIS_PAPER_ACNT_PRDT_CD.")
        return cls(**values)


class KISPaperClient:
    def __init__(self, config: KISPaperConfig):
        self.config = config
        self._access_token: str | None = None

    def _json(self, path: str, *, method: str = "GET", headers: dict[str, str] | None = None, payload: dict | None = None, params: dict | None = None) -> dict:
        url = f"{self.config.base_url.rstrip('/')}{path}"
        if params:
            url = f"{url}?{urlencode(params)}"
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = Request(url, data=body, method=method, headers={"content-type": "application/json", **(headers or {})})
        try:
            with urlopen(request, timeout=15) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise RuntimeError(f"KIS HTTP {exc.code} for {path}: {detail or exc.reason}") from exc
        except URLError as exc:
            raise RuntimeError(f"KIS network error for {path}: {exc.reason}") from exc

    def _token_cache_path(self) -> Path:
        if self.config.token_cache_path:
            return Path(self.config.token_cache_path).expanduser()
        return Path.home() / ".cache" / "mesugak" / "kis_paper_token.json"

    def _read_cached_token(self) -> str:
        path = self._token_cache_path()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return ""
        expires_at = float(data.get("expiresAt", 0) or 0)
        token = str(data.get("accessToken") or "")
        if token and expires_at > time() + 300:
            return token
        return ""

    def _write_cached_token(self, token: str, response: dict) -> None:
        if not token:
            return
        expires_in = int(response.get("expires_in") or 0)
        expires_at = time() + max(300, expires_in - 300) if expires_in else time() + 6 * 60 * 60
        raw_expiry = response.get("access_token_token_expired")
        if raw_expiry:
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y%m%d%H%M%S"):
                try:
                    expires_at = datetime.strptime(str(raw_expiry), fmt).timestamp() - 300
                    break
                except ValueError:
                    continue
        path = self._token_cache_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({"accessToken": token, "expiresAt": expires_at}), encoding="utf-8")
            try:
                path.chmod(0o600)
            except OSError:
                pass
        except OSError:
            pass

    def access_token(self) -> str:
        if self._access_token:
            return self._access_token
        cached = self._read_cached_token()
        if cached:
            self._access_token = cached
            return cached
        response = self._json("/oauth2/tokenP", method="POST", payload={"grant_type": "client_credentials", "appkey": self.config.app_key, "appsecret": self.config.app_secret})
        token = str(response.get("access_token") or "")
        if not token:
            raise RuntimeError(f"KIS token request failed: {response.get('msg1', 'unknown error')}")
        self._access_token = token
        self._write_cached_token(token, response)
        return token

    def quote(self, code: str) -> float:
        response = self._json(
            "/uapi/domestic-stock/v1/quotations/inquire-price",
            headers={"authorization": f"Bearer {self.access_token()}", "appkey": self.config.app_key, "appsecret": self.config.app_secret, "tr_id": "FHKST01010100"},
            params={"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": str(code)},
        )
        price = response.get("output", {}).get("stck_prpr")
        if response.get("rt_cd") != "0" or not price:
            raise RuntimeError(f"KIS quote failed for {code}: {response.get('msg1', 'unknown error')}")
        return float(price)

    def fetch_balance(self, *, market: str = "KR", initial_cash: float = 0.0) -> tuple[dict, dict[str, dict]]:
        """Fetch the real KIS virtual-account balance and convert it to Mesugak ledger fields."""
        if market.upper() != "KR":
            raise ValueError("KIS paper balance sync currently supports KR only")
        headers = {
            "authorization": f"Bearer {self.access_token()}",
            "appkey": self.config.app_key,
            "appsecret": self.config.app_secret,
            "tr_id": "VTTC8434R",
            "custtype": "P",
        }
        params = {
            "CANO": self.config.cano,
            "ACNT_PRDT_CD": self.config.account_product_code,
            "AFHR_FLPR_YN": "N",
            "OFL_YN": "",
            "INQR_DVSN": "02",
            "UNPR_DVSN": "01",
            "FUND_STTL_ICLD_YN": "N",
            "FNCG_AMT_AUTO_RDPT_YN": "N",
            "PRCS_DVSN": "00",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": "",
        }
        rows: list[dict] = []
        summary: dict = {}
        while True:
            response = self._json("/uapi/domestic-stock/v1/trading/inquire-balance", headers=headers, params=params)
            if response.get("rt_cd") != "0":
                raise RuntimeError(f"KIS balance lookup failed: {response.get('msg1', 'unknown error')}")
            output1 = response.get("output1") or []
            output2 = response.get("output2") or []
            if isinstance(output1, dict):
                output1 = [output1]
            if isinstance(output2, list) and output2:
                summary = output2[0] or {}
            elif isinstance(output2, dict):
                summary = output2
            rows.extend(row for row in output1 if isinstance(row, dict))
            next_fk = str(response.get("ctx_area_fk100") or response.get("CTX_AREA_FK100") or "").strip()
            next_nk = str(response.get("ctx_area_nk100") or response.get("CTX_AREA_NK100") or "").strip()
            if not next_fk and not next_nk:
                break
            params["CTX_AREA_FK100"] = next_fk
            params["CTX_AREA_NK100"] = next_nk

        positions: dict[str, dict] = {}
        holdings = []
        for row in rows:
            code = str(row.get("pdno") or row.get("code") or "").strip()
            qty = _first_number(row, ("hldg_qty", "quantity", "qty"))
            if not code or qty <= 0:
                continue
            buy_price = _first_number(row, ("pchs_avg_pric", "avgPrice", "buyPrice"))
            last_price = _first_number(row, ("prpr", "now_pric", "lastPrice", "currentPrice")) or buy_price
            eval_amt = _first_number(row, ("evlu_amt", "evalAmt")) or qty * last_price
            buy_amt = _first_number(row, ("pchs_amt", "buyAmt")) or qty * buy_price
            pnl = _first_number(row, ("evlu_pfls_amt", "pnl")) or eval_amt - buy_amt
            pnl_pct = _first_number(row, ("evlu_pfls_rt", "pnlPct"))
            position = {
                "code": code,
                "name": row.get("prdt_name") or row.get("name") or code,
                "quantity": qty,
                "buyPrice": buy_price,
                "lastPrice": last_price,
                "highestPrice": max(buy_price, last_price),
                "market": market.upper(),
                "signalType": "kis_paper_sync",
            }
            positions[code] = position
            holdings.append({
                "code": code,
                "name": position["name"],
                "qty": qty,
                "evalAmt": round(eval_amt, 2),
                "buyAmt": round(buy_amt, 2),
                "price": last_price,
                "buyPrice": buy_price,
                "pnl": round(pnl, 2),
                "pnlPct": round(pnl_pct, 4),
            })

        cash = _first_number(summary, ("dnca_tot_amt", "nxdy_excc_amt", "prvs_rcdl_excc_amt", "cash", "cashAmt"))
        total_eval = _first_number(summary, ("scts_evlu_amt", "totalEvalAmt")) or sum(float(item["evalAmt"]) for item in holdings)
        total_buy = _first_number(summary, ("pchs_amt_smtl_amt", "totalBuyAmt")) or sum(float(item["buyAmt"]) for item in holdings)
        total_equity = _first_number(summary, ("tot_evlu_amt", "nass_amt", "totalEquity")) or cash + total_eval
        unrealized_pnl = _first_number(summary, ("evlu_pfls_smtl_amt", "unrealizedPnl")) or total_eval - total_buy
        initial = float(initial_cash or total_equity or cash or 0.0)
        account = {
            "mode": "paper",
            "source": "KIS_PAPER",
            "market": market.upper(),
            "cash": round(cash, 2),
            "initialCash": round(initial, 2),
            "holdingCount": len(holdings),
            "totalEvalAmt": round(total_eval, 2),
            "totalBuyAmt": round(total_buy, 2),
            "totalEquity": round(total_equity, 2),
            "realizedPnl": 0.0,
            "unrealizedPnl": round(unrealized_pnl, 2),
            "totalPnl": round(unrealized_pnl, 2),
            "returnPct": round(((total_equity - initial) / initial) * 100, 4) if initial > 0 else 0.0,
            "holdings": holdings,
        }
        return account, positions

    def is_trading_day(self, target_date: date) -> bool:
        """Use KIS's domestic-stock holiday feed instead of guessing holidays."""
        response = self._json(
            "/uapi/domestic-stock/v1/quotations/chk-holiday",
            headers={"authorization": f"Bearer {self.access_token()}", "appkey": self.config.app_key, "appsecret": self.config.app_secret, "tr_id": "CTCA0903R"},
            params={"BASS_DT": target_date.strftime("%Y%m%d"), "CTX_AREA_NK": "", "CTX_AREA_FK": ""},
        )
        if response.get("rt_cd") != "0":
            raise RuntimeError(f"KIS holiday lookup failed: {response.get('msg1', 'unknown error')}")
        today = target_date.strftime("%Y%m%d")
        rows = response.get("output", []) or response.get("output1", []) or []
        for row in rows:
            if str(row.get("bass_dt", "")) == today:
                return str(row.get("opnd_yn", "N")).upper() == "Y"
        return False

    def submit_market_order(self, side: str, code: str, quantity: int) -> dict:
        if side not in {"BUY", "SELL"} or quantity <= 0:
            raise ValueError("KIS order requires BUY/SELL and a positive quantity")
        tr_id = "VTTC0802U" if side == "BUY" else "VTTC0801U"
        response = self._json(
            "/uapi/domestic-stock/v1/trading/order-cash",
            method="POST",
            headers={"authorization": f"Bearer {self.access_token()}", "appkey": self.config.app_key, "appsecret": self.config.app_secret, "tr_id": tr_id, "custtype": "P"},
            payload={"CANO": self.config.cano, "ACNT_PRDT_CD": self.config.account_product_code, "PDNO": str(code), "ORD_DVSN": "01", "ORD_QTY": str(quantity), "ORD_UNPR": "0"},
        )
        if response.get("rt_cd") != "0":
            raise RuntimeError(f"KIS {side} order failed for {code}: {response.get('msg1', 'unknown error')}")
        return response
