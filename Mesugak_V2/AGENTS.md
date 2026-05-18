# Mesugak V2 Agent Rules

This folder is the active rebuild target.

## Mission

Build a strategy-first Mesugak system that scores stock buy confidence from:

- Ichimoku Cloud
- Moving average support
- Bollinger Bands
- RSI
- Downside risk and failed breakout conditions

The system must also support paper trading:

- Allocate more money to higher-confidence stocks.
- Sell or reduce lower-confidence holdings when stronger candidates appear.
- Increase cash ratio during defensive market or stock-specific risk states.
- Maintain stop-loss prices and trade logs.

## Source Of Truth

Read these docs before changing code:

- `README.md`
- `docs/ARCHITECTURE.md`
- `docs/FIRESTORE_SCHEMA.md`
- `docs/AGENT_HARNESS.md`
- `docs/WORKLOG.md`
- `docs/DEPLOYMENT.md`
- `docs/RELEASE_CHECKLIST.md`

Reference legacy behavior from:

- `../Mesugak_V1/functions/legacy/analyzer.py`
- `../Mesugak_V1/functions/local_chart_refresh.py`
- `../Mesugak_V1/src/App.jsx`

## Backend Design

Keep strategy modules pure:

- `functions/strategy_engine/indicators.py`: indicator calculations only.
- `functions/strategy_engine/scoring.py`: confidence score and reasons only.
- `functions/strategy_engine/risk.py`: risk flags, cash target, stop-loss only.
- `functions/strategy_engine/portfolio.py`: target allocation only.
- `functions/strategy_engine/orders.py`: rebalance decisions only.
- `functions/strategy_engine/repositories.py`: persistence boundary.

Job files may connect pure modules to Firestore, schedulers, or local execution.

## Frontend Design

Frontend work lives under `frontend/`.

The target UI is not a landing page. It should be an operational strategy console with:

- Signal list sorted by confidence.
- Technical chart with Ichimoku, moving averages, Bollinger Bands, RSI.
- Score breakdown.
- Risk panel.
- Paper portfolio snapshot.
- Rebalance/trade log table.

## Data Contract

Prefer extending V1-compatible collections instead of replacing them immediately:

- `stock_analysis/{MARKET}_{CODE}`
- `meta_data/meta_{MARKET}_{N}`
- `bot_portfolio`
- `bot_trade_logs`
- `bot_account_snapshot/latest`

New strategy collections:

- `strategy_runs`
- `strategy_candidates`
- `target_allocations`
- `rebalance_orders`
- `risk_state`

## Testing Expectations

Add focused tests for:

- Indicator calculations.
- Scoring cases.
- Risk flags and stop-loss.
- Portfolio allocation.
- Rebalance order generation.

Backtests must avoid lookahead bias. Default rule: signal from day N can only trade from day N+1.

## Current Status

Backend tests currently run with:

```powershell
python -m unittest discover -s Mesugak_V2\functions\tests
```

The next useful backend work is:

- Paper account ledger execution and persisted trade snapshots.
