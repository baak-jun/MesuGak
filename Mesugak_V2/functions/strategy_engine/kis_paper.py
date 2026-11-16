"""Minimal KIS virtual-investment REST client for the school server only."""

from __future__ import annotations

import json
import hashlib
import os
import sqlite3
from dataclasses import dataclass
from contextlib import closing
from datetime import date, datetime, timedelta
from pathlib import Path
from time import time
import threading
import time as clock
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
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
    hts_id: str = ""

    def __post_init__(self) -> None:
        parsed = urlparse(self.base_url)
        if parsed.scheme != "https" or parsed.hostname != "openapivts.koreainvestment.com":
            raise ValueError("KIS paper trading requires the openapivts.koreainvestment.com virtual-investment endpoint.")

    @classmethod
    def from_env(cls) -> "KISPaperConfig":
        values = {
            "app_key": os.getenv("KIS_PAPER_APP_KEY", ""),
            "app_secret": os.getenv("KIS_PAPER_APP_SECRET", ""),
            "cano": os.getenv("KIS_PAPER_CANO", ""),
            "account_product_code": os.getenv("KIS_PAPER_ACNT_PRDT_CD", ""),
            "base_url": os.getenv("KIS_PAPER_BASE_URL", "https://openapivts.koreainvestment.com:29443"),
            "token_cache_path": os.getenv("KIS_PAPER_TOKEN_CACHE", ""),
            "hts_id": os.getenv("KIS_PAPER_HTS_ID", ""),
        }
        if not all(values[key] for key in ("app_key", "app_secret", "cano", "account_product_code")):
            raise ValueError("Missing KIS paper credentials. Set KIS_PAPER_APP_KEY, KIS_PAPER_APP_SECRET, KIS_PAPER_CANO, and KIS_PAPER_ACNT_PRDT_CD.")
        return cls(**values)


class KISOrderRejectedError(RuntimeError):
    """The broker explicitly rejected the request; no order was accepted."""


class KISPaperClient:
    def __init__(self, config: KISPaperConfig):
        self.config = config
        self._access_token: str | None = None
        self.request_interval = max(0.5, float(os.getenv("KIS_PAPER_REQUEST_INTERVAL_SECONDS", "2.0")))
        self._request_lock = threading.Lock()
        self._last_request_at = 0.0

    def _shared_request_slot(self, path: str) -> None:
        """Share the contest quota between trader, candle scan and report jobs."""
        configured = os.getenv('KIS_PAPER_RATE_STATE', '')
        if not configured:
            return
        target = Path(configured).expanduser()
        target.parent.mkdir(parents=True, exist_ok=True)
        key = hashlib.sha256(self.config.app_key.encode()).hexdigest()[:16]
        chart = path.endswith('/inquire-daily-itemchartprice')
        order = path.endswith('/order-cash') or path.endswith('/order-rvsecncl')
        with closing(sqlite3.connect(target, timeout=5, isolation_level=None)) as gate:
            gate.execute('CREATE TABLE IF NOT EXISTS pacing (app TEXT PRIMARY KEY, next_at REAL, order_until REAL)')
            gate.execute('INSERT OR IGNORE INTO pacing VALUES (?,0,0)', (key,))
            target.chmod(0o600)
            if not chart:
                # Reconciliation, balance, approval and watch discovery must not
                # starve behind a continuous full-market candle scan either.
                priority_window = max(5, self.request_interval + 3) if order else self.request_interval + 1
                gate.execute('UPDATE pacing SET order_until=max(order_until,?) WHERE app=?', (time() + priority_window, key))
            while True:
                gate.execute('BEGIN IMMEDIATE')
                next_at, order_until = gate.execute('SELECT next_at,order_until FROM pacing WHERE app=?', (key,)).fetchone()
                now = time()
                blocked_until = order_until if chart else 0
                ready_at = max(next_at, blocked_until)
                if now >= ready_at:
                    gate.execute('UPDATE pacing SET next_at=? WHERE app=?', (now + self.request_interval, key))
                    gate.execute('COMMIT')
                    return
                gate.execute('ROLLBACK')
                clock.sleep(min(.2, ready_at - now))

    def _json(self, path: str, *, method: str = "GET", headers: dict[str, str] | None = None, payload: dict | None = None, params: dict | None = None) -> dict:
        url = f"{self.config.base_url.rstrip('/')}{path}"
        if params:
            url = f"{url}?{urlencode(params)}"
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = Request(url, data=body, method=method, headers={"content-type": "application/json", **(headers or {})})
        with self._request_lock:
            for attempt in range(4):
                clock.sleep(max(0.0, self.request_interval - (clock.monotonic() - self._last_request_at)))
                self._last_request_at = clock.monotonic()
                self._shared_request_slot(path)
                try:
                    with urlopen(request, timeout=5 if path.endswith('/inquire-daily-itemchartprice') else 25) as response:
                        result = json.loads(response.read().decode("utf-8"))
                    if str(result.get("rt_cd") or "") == "0" or str(result.get("msg_cd") or "") not in {"EGW00201", "EGW00215"}:
                        return result
                    error = KISOrderRejectedError(f"KIS request rate rejected for {path}: {result.get('msg_cd')}")
                except HTTPError as exc:
                    detail = exc.read().decode("utf-8", errors="replace")[:500]
                    error_class = KISOrderRejectedError if exc.code == 429 or any(code in detail for code in ['EGW00201', 'EGW00215']) else RuntimeError
                    error = error_class(f"KIS HTTP {exc.code} for {path}: {detail or exc.reason}")
                    if exc.code != 429 and not any(code in detail for code in ["EGW00201", "EGW00215"]):
                        raise error from exc
                except (URLError, TimeoutError) as exc:
                    reason = getattr(exc, "reason", str(exc))
                    # Never repeat an order after an ambiguous network failure.
                    raise RuntimeError(f"KIS network error for {path}: {reason}") from exc
                self.request_interval = min(8.0, self.request_interval * 2)
                if attempt == 3:
                    raise error
                clock.sleep(self.request_interval)
        raise RuntimeError(f"KIS request failed for {path}")

    def _token_cache_path(self) -> Path:
        if self.config.token_cache_path:
            return Path(self.config.token_cache_path).expanduser()
        key_hash = hashlib.sha256(self.config.app_key.encode()).hexdigest()[:16]
        return Path.home() / ".cache" / "mesugak" / f"kis_paper_token_{key_hash}.json"

    def _read_cached_token(self) -> str:
        path = self._token_cache_path()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return ""
        if data.get('appKeyHash') != hashlib.sha256(self.config.app_key.encode()).hexdigest():
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
            path.write_text(json.dumps({"accessToken": token, "expiresAt": expires_at, "appKeyHash": hashlib.sha256(self.config.app_key.encode()).hexdigest()}), encoding="utf-8")
            try:
                path.chmod(0o600)
            except OSError:
                pass
        except OSError:
            pass

    def _clear_cached_token(self) -> None:
        self._access_token = None
        try:
            self._token_cache_path().unlink(missing_ok=True)
        except OSError:
            pass

    @staticmethod
    def _is_expired_token_error(exc: Exception) -> bool:
        message = str(exc)
        return "EGW00123" in message or "기간이 만료된 token" in message

    def _auth_headers(self, tr_id: str, *, custtype: str | None = None) -> dict[str, str]:
        headers = {
            "authorization": f"Bearer {self.access_token()}",
            "appkey": self.config.app_key,
            "appsecret": self.config.app_secret,
            "tr_id": tr_id,
        }
        if custtype:
            headers["custtype"] = custtype
        return headers

    def _json_with_token_retry(
        self,
        path: str,
        *,
        tr_id: str,
        method: str = "GET",
        payload: dict | None = None,
        params: dict | None = None,
        custtype: str | None = None,
    ) -> dict:
        for attempt in range(2):
            try:
                return self._json(
                    path,
                    method=method,
                    headers=self._auth_headers(tr_id, custtype=custtype),
                    payload=payload,
                    params=params,
                )
            except RuntimeError as exc:
                if attempt == 0 and self._is_expired_token_error(exc):
                    self._clear_cached_token()
                    continue
                raise
        raise RuntimeError(f"KIS request failed after token retry for {path}")

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

    def websocket_approval_key(self) -> str:
        """Issue the short-lived approval key used by the paper WebSocket."""
        response = self._json(
            "/oauth2/Approval",
            method="POST",
            payload={
                "grant_type": "client_credentials",
                "appkey": self.config.app_key,
                "secretkey": self.config.app_secret,
            },
        )
        key = str(response.get("approval_key") or "")
        if not key:
            raise RuntimeError(f"KIS WebSocket approval failed: {response.get('msg1', 'unknown error')}")
        return key

    @staticmethod
    def websocket_url() -> str:
        return os.getenv("KIS_PAPER_WS_URL", "ws://ops.koreainvestment.com:31000")

    def fluctuation(self, *, count: int = 20, market_code: str = "0000") -> list[dict]:
        """Return current KRX gainers for watch-list discovery."""
        response = self._json_with_token_retry(
            "/uapi/domestic-stock/v1/ranking/fluctuation",
            tr_id="FHPST01700000",
            params={
                "fid_cond_mrkt_div_code": "J",
                "fid_cond_scr_div_code": "20170",
                "fid_input_iscd": str(market_code),
                "fid_rank_sort_cls_code": "0",
                "fid_input_cnt_1": str(max(1, min(30, int(count)))),
                "fid_prc_cls_code": "0",
                "fid_input_price_1": "1000",
                "fid_input_price_2": "",
                "fid_vol_cnt": "",
                "fid_trgt_cls_code": "0",
                # Exclude warning/management/halting/preferred/ETF/ETN/SPAC
                # classes at the provider boundary.
                "fid_trgt_exls_cls_code": "1111111111",
                "fid_div_cls_code": "0",
                "fid_rsfl_rate1": "",
                "fid_rsfl_rate2": "",
            },
        )
        if response.get("rt_cd") != "0":
            raise RuntimeError(f"KIS fluctuation lookup failed: {response.get('msg1', 'unknown error')}")
        rows = response.get("output") or response.get("output1") or []
        if isinstance(rows, dict):
            rows = [rows]
        return [row for row in rows if isinstance(row, dict)]

    def volume_rank(self, *, market_code: str = "0000") -> list[dict]:
        """Provider's current volume leaders, at most 30 rows per market."""
        response = self._json_with_token_retry(
            '/uapi/domestic-stock/v1/quotations/volume-rank', tr_id='FHPST01710000',
            params={'FID_COND_MRKT_DIV_CODE':'J','FID_COND_SCR_DIV_CODE':'20171',
                    'FID_INPUT_ISCD':market_code,'FID_DIV_CLS_CODE':'0','FID_BLNG_CLS_CODE':'0',
                    'FID_TRGT_CLS_CODE':'111111111','FID_TRGT_EXLS_CLS_CODE':'0000000000',
                    'FID_INPUT_PRICE_1':'','FID_INPUT_PRICE_2':'','FID_VOL_CNT':'','FID_INPUT_DATE_1':''})
        if response.get('rt_cd') != '0':
            raise RuntimeError(f"KIS volume rank failed: {response.get('msg_cd')}")
        rows = response.get('output') or []
        if not isinstance(rows, list) or not rows:
            raise ValueError('KIS volume rank returned no rows')
        return rows

    def quote(self, code: str) -> float:
        response = self._json_with_token_retry(
            "/uapi/domestic-stock/v1/quotations/inquire-price",
            tr_id="FHKST01010100",
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
            response = self._json_with_token_retry("/uapi/domestic-stock/v1/trading/inquire-balance", tr_id="VTTC8434R", custtype="P", params=params)
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

        # `dnca_tot_amt` is a settlement/deposit figure and can include cash
        # that is not part of the portfolio's current net asset value. Use it
        # only as a fallback; otherwise derive the displayed cash from the
        # same total-equity basis as the holdings.
        reported_cash = _first_number(summary, ("dnca_tot_amt", "nxdy_excc_amt", "prvs_rcdl_excc_amt", "cash", "cashAmt"))
        total_eval = _first_number(summary, ("scts_evlu_amt", "totalEvalAmt")) or sum(float(item["evalAmt"]) for item in holdings)
        total_buy = _first_number(summary, ("pchs_amt_smtl_amt", "totalBuyAmt")) or sum(float(item["buyAmt"]) for item in holdings)
        total_equity = _first_number(summary, ("tot_evlu_amt", "nass_amt", "totalEquity")) or reported_cash + total_eval
        derived_cash = total_equity - total_eval
        cash = derived_cash if total_equity > 0 and derived_cash >= 0 else reported_cash
        unrealized_pnl = _first_number(summary, ("evlu_pfls_smtl_amt", "unrealizedPnl")) or total_eval - total_buy
        initial = float(initial_cash or total_equity or cash or 0.0)
        total_pnl = total_equity - initial
        cash_and_realized_pnl = total_pnl - unrealized_pnl
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
            # The balance endpoint does not expose a separate lifetime realized
            # P&L. This residual keeps account-level P&L consistent with the
            # current holdings' unrealized P&L.
            "realizedPnl": round(cash_and_realized_pnl, 2),
            "unrealizedPnl": round(unrealized_pnl, 2),
            "totalPnl": round(total_pnl, 2),
            "returnPct": round(((total_equity - initial) / initial) * 100, 4) if initial > 0 else 0.0,
            "holdings": holdings,
        }
        return account, positions

    def is_trading_day(self, target_date: date) -> bool:
        """Use KIS's domestic-stock holiday feed instead of guessing holidays."""
        response = self._json_with_token_retry(
            "/uapi/domestic-stock/v1/quotations/chk-holiday",
            tr_id="CTCA0903R",
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

    def daily_candles(self, code: str, end_date: date) -> list[dict]:
        response = self._json_with_token_retry('/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice', tr_id='FHKST03010100',
            params={'FID_COND_MRKT_DIV_CODE':'J', 'FID_INPUT_ISCD':str(code), 'FID_INPUT_DATE_1':(end_date-timedelta(days=500)).strftime('%Y%m%d'),
                    'FID_INPUT_DATE_2':end_date.strftime('%Y%m%d'), 'FID_PERIOD_DIV_CODE':'D', 'FID_ORG_ADJ_PRC':'0'})
        if response.get('rt_cd') != '0':
            raise RuntimeError(f"KIS candle lookup failed for {code}: {response.get('msg1', 'unknown error')}")
        rows = []
        for raw in response.get('output2') or []:
            if not raw.get('stck_bsop_date'):
                continue
            rows.append({'date':datetime.strptime(raw['stck_bsop_date'],'%Y%m%d').date().isoformat(),
                         **{key:_as_float(raw.get(field)) for key,field in [('open','stck_oprc'),('high','stck_hgpr'),('low','stck_lwpr'),('close','stck_clpr'),('volume','acml_vol')]}})
        return rows

    def submit_market_order(self, side: str, code: str, quantity: int) -> dict:
        return self._submit_cash_order(side, code, quantity, order_division="01", unit_price=0)

    def submit_limit_order(self, side: str, code: str, quantity: int, unit_price: float) -> dict:
        if unit_price <= 0:
            raise ValueError("KIS limit order requires a positive unit price")
        return self._submit_cash_order(side, code, quantity, order_division="00", unit_price=unit_price)

    def _submit_cash_order(self, side: str, code: str, quantity: int, *, order_division: str, unit_price: float) -> dict:
        if side not in {"BUY", "SELL"} or quantity <= 0:
            raise ValueError("KIS order requires BUY/SELL and a positive quantity")
        tr_id = "VTTC0802U" if side == "BUY" else "VTTC0801U"
        response = self._json_with_token_retry(
            "/uapi/domestic-stock/v1/trading/order-cash",
            method="POST",
            tr_id=tr_id,
            custtype="P",
            payload={
                "CANO": self.config.cano,
                "ACNT_PRDT_CD": self.config.account_product_code,
                "PDNO": str(code),
                "ORD_DVSN": str(order_division),
                "ORD_QTY": str(int(quantity)),
                "ORD_UNPR": str(unit_price if order_division == "00" else 0),
                "EXCG_ID_DVSN_CD": "KRX",
            },
        )
        if response.get("rt_cd") != "0":
            raise KISOrderRejectedError(f"KIS {side} order failed for {code}: {response.get('msg1', 'unknown error')}")
        return response

    def cancel_order(
        self,
        broker_order_no: str,
        quantity: int,
        unit_price: float,
        *,
        order_branch: str = "06010",
    ) -> dict:
        if not broker_order_no or quantity <= 0:
            raise ValueError("KIS cancel requires an order number and quantity")
        response = self._json_with_token_retry(
            "/uapi/domestic-stock/v1/trading/order-rvsecncl",
            method="POST",
            tr_id="VTTC0013U",
            custtype="P",
            payload={
                "CANO": self.config.cano,
                "ACNT_PRDT_CD": self.config.account_product_code,
                "KRX_FWDG_ORD_ORGNO": str(order_branch),
                "ORGN_ODNO": str(broker_order_no),
                "ORD_DVSN": "00",
                "RVSE_CNCL_DVSN_CD": "02",
                "ORD_QTY": str(int(quantity)),
                "ORD_UNPR": str(unit_price),
                "QTY_ALL_ORD_YN": "Y",
                "EXCG_ID_DVSN_CD": "KRX",
            },
        )
        if response.get("rt_cd") != "0":
            raise RuntimeError(f"KIS cancel failed for {broker_order_no}: {response.get('msg1', 'unknown error')}")
        return response

    def inquire_daily_orders(self, *, order_date: date | None = None, pending_only: bool = False) -> list[dict]:
        target = order_date or date.today()
        params = {
            "CANO": self.config.cano,
            "ACNT_PRDT_CD": self.config.account_product_code,
            "INQR_STRT_DT": target.strftime("%Y%m%d"),
            "INQR_END_DT": target.strftime("%Y%m%d"),
            "SLL_BUY_DVSN_CD": "00",
            "PDNO": "",
            "CCLD_DVSN": "02" if pending_only else "00",
            "INQR_DVSN": "00",
            "INQR_DVSN_3": "00",
            "ORD_GNO_BRNO": "",
            "ODNO": "",
            "INQR_DVSN_1": "",
            "INQR_DVSN_2": "",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": "",
            "EXCG_ID_DVSN_CD": "KRX",
        }
        rows: list[dict] = []
        for _ in range(10):
            response = self._json_with_token_retry(
                "/uapi/domestic-stock/v1/trading/inquire-daily-ccld",
                tr_id="VTTC0081R",
                params=params,
            )
            if response.get("rt_cd") != "0":
                raise RuntimeError(f"KIS order lookup failed: {response.get('msg1', 'unknown error')}")
            output = response.get("output1") or []
            if isinstance(output, dict):
                output = [output]
            rows.extend(row for row in output if isinstance(row, dict))
            next_fk = str(response.get("ctx_area_fk100") or "").strip()
            next_nk = str(response.get("ctx_area_nk100") or "").strip()
            if not next_fk and not next_nk:
                break
            params["CTX_AREA_FK100"] = next_fk
            params["CTX_AREA_NK100"] = next_nk
        return rows
