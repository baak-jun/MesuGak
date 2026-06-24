"""Minimal KIS virtual-investment REST client for the school server only."""

from __future__ import annotations

import json
import os
from datetime import date
from dataclasses import dataclass
from urllib.parse import urlencode
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class KISPaperConfig:
    app_key: str
    app_secret: str
    cano: str
    account_product_code: str
    base_url: str = "https://openapivts.koreainvestment.com:29443"

    @classmethod
    def from_env(cls) -> "KISPaperConfig":
        values = {
            "app_key": os.getenv("KIS_PAPER_APP_KEY", ""),
            "app_secret": os.getenv("KIS_PAPER_APP_SECRET", ""),
            "cano": os.getenv("KIS_PAPER_CANO", ""),
            "account_product_code": os.getenv("KIS_PAPER_ACNT_PRDT_CD", ""),
            "base_url": os.getenv("KIS_PAPER_BASE_URL", "https://openapivts.koreainvestment.com:29443"),
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
        with urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))

    def access_token(self) -> str:
        if self._access_token:
            return self._access_token
        response = self._json("/oauth2/tokenP", method="POST", payload={"grant_type": "client_credentials", "appkey": self.config.app_key, "appsecret": self.config.app_secret})
        token = str(response.get("access_token") or "")
        if not token:
            raise RuntimeError(f"KIS token request failed: {response.get('msg1', 'unknown error')}")
        self._access_token = token
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
