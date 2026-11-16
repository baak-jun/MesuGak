"""Recompute the shared daily indicators with the developing KIS session candle."""

from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd

from .indicators import add_all_indicators
from .realtime_policy import TradeTick
from .scoring import score_latest


class InsufficientHistoryError(ValueError):
    def __init__(self, available: int, required: int = 120):
        self.available, self.required = available, required
        super().__init__(f'Fewer than {required} valid completed candles: {available} available')


def valid_history(rows: list[dict[str, Any]], session_date: date, *, minimum_rows: int = 120) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    columns = ["date", "open", "high", "low", "close", "volume"]
    if not all(column in frame for column in columns):
        raise ValueError("Missing completed OHLCV history")
    frame = frame[columns].copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    for column in columns[1:]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame.dropna().sort_values("date").drop_duplicates("date", keep="last")
    frame = frame[frame["date"].dt.date < session_date]
    valid = (frame[["open", "high", "low", "close"]] > 0).all(axis=1)
    valid &= frame["high"] >= frame[["open", "close", "low"]].max(axis=1)
    valid &= frame["low"] <= frame[["open", "close", "high"]].min(axis=1)
    valid &= frame["volume"] >= 0
    frame = frame.loc[valid].tail(180).reset_index(drop=True)
    if len(frame) < minimum_rows:
        raise InsufficientHistoryError(len(frame), minimum_rows)
    return frame


def score_live_history(history: pd.DataFrame, tick: TradeTick, session_date: date) -> dict[str, Any]:
    if tick.price <= 0 or len(history) < 120:
        return {"liveScoreReady": False}
    opening = tick.day_open or tick.price
    high = max(tick.day_high, opening, tick.price)
    low = min(value for value in [tick.day_low, opening, tick.price] if value > 0)
    candle = {"date": pd.Timestamp(session_date), "open": opening, "high": high,
              "low": low, "close": tick.price, "volume": max(0.0, tick.cumulative_volume)}
    frame = pd.concat([history, pd.DataFrame([candle])], ignore_index=True)
    score = score_latest(add_all_indicators(frame))
    return {"liveScoreReady": True, "liveConfidenceScore": score.confidence_score,
            "liveConfidenceLabel": score.confidence_label, "liveScoreReasons": score.reasons,
            "liveComponentScores": score.component_scores,
            "scoreHistoryDate": history.iloc[-1]["date"].strftime("%Y-%m-%d"),
            "scoreSessionDate": session_date.isoformat(), "scoreBasis": "daily_indicators_with_live_candle"}
