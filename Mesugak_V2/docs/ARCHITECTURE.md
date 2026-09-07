# Mesugak V2 Architecture

## Goal

V2 replaces the single Bollinger Band scanner with a strategy engine that scores how well a stock satisfies multiple technical conditions, then uses that score to drive paper trading.

## Pipeline

1. Load the KR market universe and completed daily OHLCV through the Financial Services Commission public stock-price API.
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
- Financial Services Commission public-data-backed KR market universe and completed daily OHLCV.
- Financial Services Commission public index loading for optional KOSPI/KOSDAQ benchmark comparison.
- Valuation/fundamental inputs are optional and are not part of the active public-data route.
- KIS virtual-account access remains isolated to administrator-only paper-account jobs.
- Local checkpoint/resume support for long analysis runs.
- Reusable backtest simulation with N+1 trade execution.
- Public aggregate-only 30-item pages/search manifest plus admin-only charts and raw analysis.

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
