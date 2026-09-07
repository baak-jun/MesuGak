"""Domestic market data from the Financial Services Commission public APIs."""

from __future__ import annotations

import datetime as dt
import json
import os
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlencode
from urllib.request import Request, urlopen

import pandas as pd


STOCK_PRICE_URL = "https://apis.data.go.kr/1160100/service/GetStockSecuritiesInfoService/getStockPriceInfo"
INDEX_PRICE_URL = "https://apis.data.go.kr/1160100/service/GetMarketIndexInfoService/getStockMarketIndex"
KR_INDEX_NAMES = {"KOSPI": "코스피", "KOSDAQ": "코스닥"}
KR_MARKETS = frozenset(KR_INDEX_NAMES)


class PublicDataApiError(RuntimeError):
    def __init__(self, message: str, code: str = ""):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class MarketTarget:
    code: str
    name: str
    marcap: float = 0.0
    exchange: str = ""


class PublicDataClient:
    """Small JSON/XML client for data.go.kr financial public data."""

    def __init__(
        self,
        service_key: str,
        *,
        timeout: float = 30.0,
        retries: int = 3,
        request_delay: float = 0.05,
        opener=urlopen,
    ):
        key = unquote(str(service_key).strip())
        if not key:
            raise ValueError("DATA_GO_KR_SERVICE_KEY is required for domestic market analysis.")
        self.service_key = key
        self.timeout = max(1.0, float(timeout))
        self.retries = max(0, int(retries))
        self.request_delay = max(0.0, float(request_delay))
        self.opener = opener
        self._last_request_at = 0.0

    @classmethod
    def from_env(cls) -> "PublicDataClient":
        return cls(
            os.getenv("DATA_GO_KR_SERVICE_KEY") or os.getenv("PUBLIC_DATA_SERVICE_KEY") or "",
            timeout=float(os.getenv("DATA_GO_KR_TIMEOUT_SECONDS", "30")),
            retries=int(os.getenv("DATA_GO_KR_RETRIES", "3")),
            request_delay=float(os.getenv("DATA_GO_KR_REQUEST_DELAY_SECONDS", "0.05")),
        )

    def _wait_for_rate_limit(self) -> None:
        wait = self.request_delay - (time.monotonic() - self._last_request_at)
        if wait > 0:
            time.sleep(wait)

    @staticmethod
    def _parse_xml(raw: bytes) -> tuple[list[dict[str, Any]], int]:
        root = ET.fromstring(raw)
        code = root.findtext(".//resultCode") or root.findtext(".//returnReasonCode") or ""
        message = (
            root.findtext(".//resultMsg")
            or root.findtext(".//errMsg")
            or root.findtext(".//returnAuthMsg")
            or "Public data API request failed"
        )
        if code and code not in {"0", "00"}:
            raise PublicDataApiError(message, code)
        rows = [{child.tag: child.text or "" for child in item} for item in root.findall(".//items/item")]
        return rows, int(root.findtext(".//totalCount") or len(rows))

    @staticmethod
    def _parse_json(raw: bytes) -> tuple[list[dict[str, Any]], int]:
        payload = json.loads(raw.decode("utf-8"))
        response = payload.get("response") or payload
        header = response.get("header") or {}
        code = str(header.get("resultCode") or "")
        if code and code not in {"0", "00"}:
            raise PublicDataApiError(str(header.get("resultMsg") or "Public data API request failed"), code)
        body = response.get("body") or {}
        items = body.get("items") or {}
        rows = items.get("item") if isinstance(items, dict) else []
        if isinstance(rows, dict):
            rows = [rows]
        return list(rows or []), int(body.get("totalCount") or len(rows or []))

    def _request_page(self, url: str, params: dict[str, Any]) -> tuple[list[dict[str, Any]], int]:
        query = urlencode({**params, "serviceKey": self.service_key, "resultType": "json"})
        request = Request(f"{url}?{query}", headers={"Accept": "application/json", "User-Agent": "MesugakV2/1.0"})
        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                self._wait_for_rate_limit()
                with self.opener(request, timeout=self.timeout) as response:
                    raw = response.read()
                self._last_request_at = time.monotonic()
                try:
                    return self._parse_json(raw)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    return self._parse_xml(raw)
            except PublicDataApiError as exc:
                last_error = exc
                if exc.code not in {"01", "04", "05", "23"} or attempt >= self.retries:
                    raise
            except (HTTPError, URLError, TimeoutError, ET.ParseError) as exc:
                last_error = exc
                if attempt >= self.retries:
                    break
            time.sleep(min(2**attempt, 8))
        raise PublicDataApiError(f"Public data API request failed after {self.retries + 1} attempt(s): {last_error}")

    def _fetch_all(self, url: str, params: dict[str, Any], *, num_rows: int) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        page = 1
        while True:
            page_rows, total = self._request_page(url, {**params, "pageNo": page, "numOfRows": num_rows})
            rows.extend(page_rows)
            if not page_rows or len(rows) >= total:
                return rows
            page += 1

    def stock_history(self, code: str, start: dt.date, end_exclusive: dt.date) -> list[dict[str, Any]]:
        rows = self._fetch_all(
            STOCK_PRICE_URL,
            {
                "beginBasDt": start.strftime("%Y%m%d"),
                "endBasDt": end_exclusive.strftime("%Y%m%d"),
                "likeSrtnCd": str(code).strip(),
            },
            num_rows=1000,
        )
        normalized_code = str(code).strip()
        return [row for row in rows if str(row.get("srtnCd") or "").strip() == normalized_code]

    def latest_stock_rows(self, *, max_age_days: int = 14) -> list[dict[str, Any]]:
        today = dt.date.today()
        for days_ago in range(max_age_days + 1):
            basedate = today - dt.timedelta(days=days_ago)
            rows = self._fetch_all(STOCK_PRICE_URL, {"basDt": basedate.strftime("%Y%m%d")}, num_rows=5000)
            if rows:
                return rows
        raise PublicDataApiError(f"No stock rows returned in the latest {max_age_days + 1} calendar days")

    def index_history(self, label: str, start: dt.date, end_exclusive: dt.date) -> list[dict[str, Any]]:
        normalized = str(label).upper().strip()
        if normalized not in KR_INDEX_NAMES:
            raise ValueError(f"Unsupported KR benchmark: {label}")
        rows = self._fetch_all(
            INDEX_PRICE_URL,
            {
                "beginBasDt": start.strftime("%Y%m%d"),
                "endBasDt": end_exclusive.strftime("%Y%m%d"),
                "idxNm": KR_INDEX_NAMES[normalized],
            },
            num_rows=1000,
        )
        expected = KR_INDEX_NAMES[normalized]
        return [row for row in rows if str(row.get("idxNm") or "").strip() == expected]


@lru_cache(maxsize=1)
def get_public_data_client() -> PublicDataClient:
    return PublicDataClient.from_env()


def normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "date" not in {str(column).lower() for column in out.columns}:
        out = out.reset_index()
    else:
        out = out.reset_index(drop=True)
    out.columns = [str(col).lower() for col in out.columns]
    out = out.rename(columns={"index": "date", "adj close": "adj_close"})
    if "date" not in out.columns:
        raise ValueError(f"OHLCV data is missing date column: {list(out.columns)}")
    if "close" not in out.columns and "adj_close" in out.columns:
        out["close"] = out["adj_close"]
    required = ["open", "high", "low", "close"]
    missing = [column for column in required if column not in out.columns]
    if missing:
        raise ValueError(f"OHLCV data is missing required columns: {missing}")
    if "volume" not in out.columns:
        out["volume"] = 0
    keep = ["date", "open", "high", "low", "close", "volume"]
    for column in keep[1:]:
        out[column] = pd.to_numeric(out[column], errors="coerce")
    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    return out.dropna(subset=keep).sort_values("date")[keep].reset_index(drop=True)


def load_ohlcv_with_public_data(
    code: str,
    lookback_days: int = 460,
    *,
    client: PublicDataClient | None = None,
) -> pd.DataFrame:
    end_exclusive = dt.date.today() + dt.timedelta(days=1)
    start = end_exclusive - dt.timedelta(days=lookback_days + 1)
    rows = (client or get_public_data_client()).stock_history(code, start, end_exclusive)
    frame = pd.DataFrame(
        {
            "date": [row.get("basDt") for row in rows],
            "open": [row.get("mkp") for row in rows],
            "high": [row.get("hipr") for row in rows],
            "low": [row.get("lopr") for row in rows],
            "close": [row.get("clpr") for row in rows],
            "volume": [row.get("trqu") for row in rows],
        }
    )
    return normalize_ohlcv(frame)


def load_kr_benchmark_return(
    label: str,
    baseline_date: dt.date,
    *,
    client: PublicDataClient | None = None,
) -> dict[str, Any]:
    normalized = str(label).upper().strip()
    rows = (client or get_public_data_client()).index_history(
        normalized,
        baseline_date,
        dt.date.today() + dt.timedelta(days=1),
    )
    frame = pd.DataFrame({"date": [row.get("basDt") for row in rows], "close": [row.get("clpr") for row in rows]})
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["close"] = pd.to_numeric(frame["close"], errors="coerce")
    frame = frame.dropna().sort_values("date")
    if frame.empty:
        raise RuntimeError(f"No public benchmark rows returned for {normalized}")
    baseline = frame.iloc[0]
    latest = frame.iloc[-1]
    baseline_close = float(baseline["close"])
    if baseline_close <= 0:
        raise RuntimeError(f"Invalid benchmark baseline close for {normalized}")
    return {
        "label": normalized,
        "returnPct": round((float(latest["close"]) / baseline_close - 1.0) * 100.0, 4),
        "baselineDate": baseline["date"].strftime("%Y-%m-%d"),
        "asOfDate": latest["date"].strftime("%Y-%m-%d"),
        "basis": "closing_price",
        "source": "FSC_PUBLIC_DATA:getStockMarketIndex",
    }


def targets_from_codes(codes: Iterable[str]) -> list[MarketTarget]:
    return [MarketTarget(code=value, name=value) for raw in codes if (value := str(raw).strip())]


def load_market_universe(
    market: str,
    kr_markets: Iterable[str] | None = None,
    max_stocks: int | None = None,
    *,
    client: PublicDataClient | None = None,
) -> list[MarketTarget]:
    if str(market).upper().strip() != "KR":
        raise ValueError("Financial Services Commission public analysis supports KR only")
    wanted = {str(item).upper().strip() for item in kr_markets or KR_MARKETS}
    wanted &= KR_MARKETS
    rows = (client or get_public_data_client()).latest_stock_rows()
    targets = []
    for row in rows:
        exchange = str(row.get("mrktCtg") or "").upper().strip()
        code = str(row.get("srtnCd") or "").strip()
        if exchange not in wanted or len(code) != 6 or not code.isdigit():
            continue
        raw_marcap = pd.to_numeric(row.get("mrktTotAmt"), errors="coerce")
        targets.append(
            MarketTarget(
                code=code,
                name=str(row.get("itmsNm") or code).strip(),
                marcap=float(raw_marcap) if pd.notna(raw_marcap) else 0.0,
                exchange=exchange,
            )
        )
    ordered = sorted({target.code: target for target in targets}.values(), key=lambda item: (-item.marcap, item.code))
    if max_stocks is not None and max_stocks > 0:
        ordered = ordered[:max_stocks]
    if not ordered:
        raise RuntimeError("Financial Services Commission public data returned no KOSPI/KOSDAQ symbols")
    return ordered
