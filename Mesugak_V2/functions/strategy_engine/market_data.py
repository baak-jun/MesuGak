"""Market data loading for Mesugak V2."""

from __future__ import annotations

import datetime as dt
from io import StringIO
from dataclasses import dataclass
from typing import Any, Iterable
from urllib.request import Request, urlopen

import pandas as pd


SP500_WIKI_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
NASDAQ100_WIKI_URL = "https://en.wikipedia.org/wiki/Nasdaq-100"
KR_BENCHMARK_CODES = {"KOSPI": "KS11", "KOSDAQ": "KQ11"}


@dataclass(frozen=True)
class MarketTarget:
    code: str
    name: str
    marcap: float = 0.0


def normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy().reset_index()
    out.columns = [str(col).lower() for col in out.columns]
    out = out.rename(columns={"index": "date", "adj close": "adj_close"})

    if "date" not in out.columns:
        raise ValueError(f"OHLCV data is missing date column: {list(out.columns)}")
    if "close" not in out.columns and "adj_close" in out.columns:
        out["close"] = out["adj_close"]

    required = ["open", "high", "low", "close"]
    missing = [col for col in required if col not in out.columns]
    if missing:
        raise ValueError(f"OHLCV data is missing required columns: {missing}")

    if "volume" not in out.columns:
        out["volume"] = 0

    keep = ["date", "open", "high", "low", "close", "volume"]
    for col in keep[1:]:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    out = out.dropna(subset=keep).sort_values("date")
    return out[keep].reset_index(drop=True)


def load_ohlcv_with_fdr(code: str, lookback_days: int = 460) -> pd.DataFrame:
    import FinanceDataReader as fdr

    end = dt.datetime.now()
    start = end - dt.timedelta(days=lookback_days)
    return normalize_ohlcv(fdr.DataReader(code, start, end))

def load_kr_benchmark_return(label: str, baseline_date: dt.date) -> dict[str, Any]:
    """Return a private KOSPI/KOSDAQ closing-return comparison.

    This helper is for the administrator-only performance view. It never
    publishes index levels: callers receive only the agreed-baseline return,
    dates, and source label.
    """
    normalized_label = str(label).upper().strip()
    if normalized_label not in KR_BENCHMARK_CODES:
        raise ValueError(f"Unsupported KR benchmark: {label}")

    import FinanceDataReader as fdr

    start = pd.Timestamp(baseline_date).to_pydatetime()
    end = dt.datetime.now()
    frame = normalize_ohlcv(fdr.DataReader(KR_BENCHMARK_CODES[normalized_label], start, end))
    if frame.empty:
        raise RuntimeError(f"No benchmark rows returned for {normalized_label}")

    baseline_rows = frame[frame["date"].dt.date >= baseline_date]
    if baseline_rows.empty:
        raise RuntimeError(f"No benchmark close on or after {baseline_date.isoformat()} for {normalized_label}")
    baseline = baseline_rows.iloc[0]
    latest = frame.iloc[-1]
    baseline_close = float(baseline["close"])
    latest_close = float(latest["close"])
    if baseline_close <= 0:
        raise RuntimeError(f"Invalid benchmark baseline close for {normalized_label}")

    return {
        "label": normalized_label,
        "returnPct": round(((latest_close / baseline_close) - 1.0) * 100.0, 4),
        "baselineDate": baseline["date"].strftime("%Y-%m-%d"),
        "asOfDate": latest["date"].strftime("%Y-%m-%d"),
        "basis": "closing_price",
        "source": f"FinanceDataReader:{KR_BENCHMARK_CODES[normalized_label]}",
    }

def load_ohlcv_with_kis(code: str, lookback_days: int = 460) -> pd.DataFrame:
    """Load recent daily OHLCV data using KIS Open API."""
    from strategy_engine.kis_api import get_kis_client
    end = datetime.now()
    start = end - timedelta(days=lookback_days)
    
    if not os.environ.get("KIS_APP_KEY"):
        import FinanceDataReader as fdr
        return normalize_ohlcv(fdr.DataReader(code, start, end))
        
    client = get_kis_client()
    df = client.get_ohlcv(code, start.strftime("%Y%m%d"), end.strftime("%Y%m%d"))
    return normalize_ohlcv(df)

def load_kr_fundamentals_with_kis(code: str) -> dict[str, Any]:
    """Load fundamentals using KIS Open API."""
    if not os.environ.get("KIS_APP_KEY"):
        import FinanceDataReader as fdr
        frame = fdr.SnapDataReader(f"NAVER/FINSTATE/{str(code).strip()}")
        if frame is None or frame.empty:
            return {}
        reported = frame[pd.to_numeric(frame.get("영업이익"), errors="coerce").notna()].copy()
        if reported.empty:
            return {}
        latest = reported.iloc[-1]
        previous = reported.iloc[-2] if len(reported) >= 2 else None
        operating_profit = _number_or_none(latest.get("영업이익"))
        previous_operating_profit = _number_or_none(previous.get("영업이익")) if previous is not None else None
        growth = None
        if operating_profit is not None and previous_operating_profit not in (None, 0):
            growth = (operating_profit / previous_operating_profit - 1.0) * 100.0
        as_of = getattr(latest, "name", None)
        return {
            "source": "NAVER/FINSTATE",
            "asOf": as_of.strftime("%Y-%m-%d") if hasattr(as_of, "strftime") else str(as_of or ""),
            "per": _number_or_none(latest.get("PER(배)")),
            "pbr": _number_or_none(latest.get("PBR(배)")),
            "roe": _number_or_none(latest.get("ROE(%)")),
            "debtRatio": _number_or_none(latest.get("부채비율")),
            "operatingProfit": operating_profit,
            "operatingProfitGrowth": growth,
        }

    from strategy_engine.kis_api import get_kis_client
    client = get_kis_client()
    return client.get_fundamentals(code)

def _number_or_none(value: Any) -> float | None:
    number = pd.to_numeric(value, errors="coerce")
    return None if pd.isna(number) else float(number)

def targets_from_codes(codes: Iterable[str]) -> list[MarketTarget]:
    return [MarketTarget(code=str(code).strip(), name=str(code).strip()) for code in codes if str(code).strip()]

def _normalize_listing_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename_map = {
        "Symbol": "Code",
        "Ticker": "Code",
        "Name": "Name",
        "Company": "Name",
        "MarketCap": "Marcap",
        "Marcap": "Marcap",
    }
    out = df.rename(columns={key: value for key, value in rename_map.items() if key in df.columns}).copy()
    if "Code" not in out.columns:
        raise ValueError(f"Stock listing is missing Code/Symbol column: {list(df.columns)}")
    if "Name" not in out.columns:
        out["Name"] = out["Code"]
    if "Marcap" not in out.columns:
        out["Marcap"] = 0
    out["Code"] = out["Code"].astype(str).str.strip()
    out["Name"] = out["Name"].astype(str).str.strip()
    out["Marcap"] = pd.to_numeric(out["Marcap"], errors="coerce").fillna(0)
    out = out[out["Code"] != ""]
    return out


def _normalize_us_symbol_for_fdr(symbol: str) -> str:
    return str(symbol).strip().upper().replace(".", "-")


def _load_wiki_symbols(url: str, column_name: str) -> set[str]:
    request = Request(url, headers={"User-Agent": "MesugakV2/1.0"})
    with urlopen(request, timeout=30) as response:
        html = response.read().decode("utf-8", errors="replace")
    tables = pd.read_html(StringIO(html))
    for df in tables:
        columns = [str(col).strip() for col in df.columns]
        if column_name in columns:
            return {
                _normalize_us_symbol_for_fdr(value)
                for value in df[column_name].astype(str).tolist()
                if str(value).strip()
            }
    raise RuntimeError(f"Constituent table not found: {url}")


def load_market_universe(
    market: str,
    kr_markets: Iterable[str] | None = None,
    max_stocks: int | None = None,
) -> list[MarketTarget]:
    import FinanceDataReader as fdr

    normalized_market = str(market).upper().strip()
    if normalized_market == "KR":
        df = fdr.StockListing("KRX")
        wanted = {str(item).strip().upper() for item in kr_markets or [] if str(item).strip()}
        if wanted and "Market" in df.columns:
            df = df.copy()
            df["Market"] = df["Market"].astype(str).str.upper()
            df = df[df["Market"].isin(wanted)]
        df = _normalize_listing_columns(df).sort_values(["Marcap", "Code"], ascending=[False, True])
    elif normalized_market == "US":
        symbols = _load_wiki_symbols(SP500_WIKI_URL, "Symbol") | _load_wiki_symbols(NASDAQ100_WIKI_URL, "Ticker")
        frames: list[pd.DataFrame] = []
        for exchange in ("NASDAQ", "NYSE", "AMEX"):
            try:
                exchange_df = _normalize_listing_columns(fdr.StockListing(exchange))
                exchange_df["Code"] = exchange_df["Code"].map(_normalize_us_symbol_for_fdr)
                exchange_df = exchange_df[exchange_df["Code"].isin(symbols)]
                if not exchange_df.empty:
                    frames.append(exchange_df)
            except Exception:
                continue
        if frames:
            df = pd.concat(frames, ignore_index=True).drop_duplicates(subset=["Code"], keep="first")
            df = df.sort_values(["Code"], ascending=[True])
        else:
            df = pd.DataFrame(columns=["Code", "Name", "Marcap"])
    else:
        raise ValueError(f"Unsupported market: {market}")

    if max_stocks is not None and max_stocks > 0:
        df = df.head(max_stocks)

    return [
        MarketTarget(code=str(row.Code), name=str(row.Name), marcap=float(row.Marcap or 0))
        for row in df[["Code", "Name", "Marcap"]].itertuples(index=False)
    ]
