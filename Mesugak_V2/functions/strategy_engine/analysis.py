"""Stock analysis assembly for Mesugak V2."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from .indicators import add_all_indicators
from .risk import evaluate_risk
from .scoring import score_latest


HISTORY_COLUMNS = {
    "ma5": "ma5",
    "ma20": "ma20",
    "ma60": "ma60",
    "ma120": "ma120",
    "bb_upper": "upper",
    "bb_lower": "lower",
    "bb_mid": "bbMid",
    "bb_bandwidth": "bandwidth",
    "bb_percent_b": "percentB",
    "rsi": "rsi",
    "rsi_signal": "rsiSignal",
    "tenkan": "tenkan",
    "kijun": "kijun",
    "senkou_a": "senkouA",
    "senkou_b": "senkouB",
    "chikou": "chikou",
}


@dataclass(frozen=True)
class StockIdentity:
    market: str
    code: str
    name: str
    marcap: float = 0.0

    @property
    def doc_id(self) -> str:
        return f"{self.market}_{self.code}"


def _clean_number(value: Any, digits: int | None = None) -> float | None:
    if value is None or pd.isna(value):
        return None
    number = float(value)
    return round(number, digits) if digits is not None else number


def _latest_number(row: pd.Series, key: str, default: float = 0.0) -> float:
    value = _clean_number(row.get(key))
    return default if value is None else value


def build_history(df: pd.DataFrame, limit: int = 260) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    recent = df.tail(limit).copy()

    for _, row in recent.iterrows():
        date_value = row.get("date")
        if hasattr(date_value, "strftime"):
            date_text = date_value.strftime("%Y-%m-%d")
        else:
            date_text = str(date_value)

        item: dict[str, Any] = {
            "date": date_text,
            "open": _clean_number(row.get("open"), 4),
            "high": _clean_number(row.get("high"), 4),
            "low": _clean_number(row.get("low"), 4),
            "close": _clean_number(row.get("close"), 4),
            "volume": _clean_number(row.get("volume"), 0) or 0,
        }
        for source_key, target_key in HISTORY_COLUMNS.items():
            item[target_key] = _clean_number(row.get(source_key), 4)
        rows.append(item)

    return rows


def analyze_stock(df: pd.DataFrame, identity: StockIdentity) -> dict[str, Any] | None:
    if df is None or df.empty or len(df) < 120:
        return None

    enriched = add_all_indicators(df)
    enriched = enriched.replace([float("inf"), float("-inf")], pd.NA)
    latest = enriched.iloc[-1]

    score = score_latest(enriched)
    risk = evaluate_risk(enriched)
    history = build_history(enriched)
    current_price = _latest_number(latest, "close")
    bandwidth = _latest_number(latest, "bb_bandwidth")
    percent_b = _latest_number(latest, "bb_percent_b")

    if score.confidence_label in {"STRONG_BUY", "BUY_CANDIDATE"} and risk.risk_state != "DEFENSIVE":
        action = "BUY_CANDIDATE"
        legacy_type = "buy_signal"
        status = "BUY_CANDIDATE"
    elif risk.risk_state == "DEFENSIVE":
        action = "REDUCE"
        legacy_type = "sell_signal"
        status = "DEFENSIVE"
    elif score.confidence_score >= 45:
        action = "WATCH"
        legacy_type = "watch"
        status = "WATCH"
    else:
        action = "HOLD"
        legacy_type = "normal"
        status = "HOLD"

    last_date = history[-1]["date"] if history else ""
    return {
        "id": identity.doc_id,
        "code": identity.code,
        "name": identity.name,
        "market": identity.market,
        "strategyVersion": "V2",
        "marcap": float(identity.marcap or 0),
        "status": status,
        "type": legacy_type,
        "currentPrice": current_price,
        "volume": _latest_number(latest, "volume"),
        "bandwidth": round(bandwidth, 4),
        "percentB": round(percent_b, 4),
        "lastDate": last_date,
        "history": history,
        "confidenceScore": score.confidence_score,
        "confidenceLabel": score.confidence_label,
        "componentScores": score.component_scores,
        "confidenceReasons": score.reasons,
        "indicatorStates": score.indicator_states or {},
        "riskState": risk.risk_state,
        "riskFlags": risk.risk_flags,
        "cashTargetPct": risk.cash_target_pct,
        "stopLoss": risk.stop_loss,
        "signal": {
            "action": action,
            "strength": score.confidence_score,
            "reasons": score.reasons,
            "riskFlags": risk.risk_flags,
            "indicatorStates": score.indicator_states or {},
        },
    }


def to_summary(payload: dict[str, Any]) -> dict[str, Any]:
    keys = [
        "id",
        "code",
        "name",
        "market",
        "strategyVersion",
        "status",
        "type",
        "currentPrice",
        "volume",
        "bandwidth",
        "percentB",
        "marcap",
        "lastDate",
        "confidenceScore",
        "confidenceLabel",
        "riskState",
        "riskFlags",
        "cashTargetPct",
        "stopLoss",
        "signal",
        "indicatorStates",
    ]
    return {key: payload.get(key) for key in keys}
