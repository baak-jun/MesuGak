# Mesugak V2 Architecture

## Goal

V2 replaces the single Bollinger Band scanner with a strategy engine that scores how well a stock satisfies multiple technical conditions, then uses that score to drive paper trading.

## Pipeline

1. Load market universe and OHLCV data.
2. Calculate indicators.
3. Score each stock.
4. Detect risk states and cash-ratio requirements.
5. Produce target portfolio weights.
6. Convert target weights into paper trades or staged orders.
7. Save analysis, allocations, orders, portfolio snapshots, and logs to Firestore.
8. Render the frontend from the stored analysis and paper trading state.

## Current Implementation

Implemented:

- Indicator calculations with deterministic tests.
- Confidence scoring with component scores and penalties.
- Risk flags, defensive cash target, and stop-loss calculation.
- Stock analysis payload assembly compatible with V1 `stock_analysis` and `meta_data`.
- Firestore repository boundary.
- Basic analysis and rebalance jobs.
- Full KR/US market universe loading.
- Local checkpoint/resume support for long analysis runs.
- Reusable backtest simulation with N+1 trade execution.
- Frontend strategy console with Firestore-backed signals, staged orders, and paper portfolio snapshot fallback.

Not implemented yet:

- Live paper-trading account ledger.

## Module Boundaries

- `market_data.py`: data loading and normalization.
- `indicators.py`: pure pandas indicator calculations.
- `scoring.py`: confidence score and reason generation.
- `risk.py`: downside, failed breakout, stop-loss, and cash target logic.
- `portfolio.py`: target allocation construction.
- `orders.py`: rebalance order generation.
- `repositories.py`: Firestore persistence.
- `backtest.py`: historical simulation using the same strategy modules.
