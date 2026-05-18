# Mesugak Agent Harness

This repository is split into two project folders.

- `Mesugak_V1/` is the preserved legacy implementation. Treat it as reference material unless the user explicitly asks to modify V1.
- `Mesugak_V2/` is the active rebuild target. New work should happen here by default.

## Required Startup Context

At the start of a new session, read these files before making implementation decisions:

1. `README.md`
2. `Mesugak_V2/README.md`
3. `Mesugak_V2/docs/ARCHITECTURE.md`
4. `Mesugak_V2/docs/FIRESTORE_SCHEMA.md`
5. `Mesugak_V2/docs/AGENT_HARNESS.md`

Use V1 source files as behavioral references:

- `Mesugak_V1/functions/oracle_chart_refresh.py`
- `Mesugak_V1/functions/local_chart_refresh.py`
- `Mesugak_V1/functions/legacy/analyzer.py`
- `Mesugak_V1/src/App.jsx`

## Project Direction

Mesugak V2 replaces the Bollinger-only scanner with a multi-indicator strategy system:

- Ichimoku Cloud
- Moving average support
- Bollinger Bands
- RSI
- Confidence scoring
- Risk flags
- Cash-ratio control
- Stop-loss logic
- Paper trading and rebalance simulation

The strategy engine must be reusable across analysis jobs, paper trading, and backtests.

## Ownership Boundaries

When using multiple agents, split work by file ownership.

- Indicator worker: `Mesugak_V2/functions/strategy_engine/indicators.py`, related tests.
- Scoring and risk worker: `scoring.py`, `risk.py`, related tests.
- Portfolio and order worker: `portfolio.py`, `orders.py`, related tests.
- Persistence worker: `repositories.py`, `jobs/`, Firestore schema wiring.
- Frontend worker: `Mesugak_V2/frontend/` only.
- Documentation worker: `Mesugak_V2/docs/` only.

Do not assign multiple workers to the same file set at the same time.

## Implementation Rules

- Prefer pure functions in `strategy_engine/`.
- Keep Firestore reads and writes inside `repositories.py` or job files.
- Keep V1 untouched unless the user explicitly asks for V1 changes.
- Preserve the V1 Firestore compatibility path where practical:
  - `stock_analysis`
  - `meta_data`
  - `bot_portfolio`
  - `bot_trade_logs`
  - `bot_account_snapshot`
- Avoid building new logic directly into a single all-in-one script.
- Add tests as soon as strategy behavior becomes non-trivial.

## Current V2 Status

V2 is scaffolded, not complete.

Existing scaffold:

- `Mesugak_V2/functions/strategy_engine/indicators.py`
- `Mesugak_V2/functions/strategy_engine/scoring.py`
- `Mesugak_V2/functions/strategy_engine/risk.py`
- `Mesugak_V2/functions/strategy_engine/portfolio.py`
- `Mesugak_V2/functions/strategy_engine/orders.py`
- `Mesugak_V2/functions/strategy_engine/repositories.py`
- `Mesugak_V2/functions/jobs/analyze_market.py`
- `Mesugak_V2/functions/jobs/rebalance.py`
- `Mesugak_V2/frontend/`

Current backend tests cover indicators, scoring, risk, analysis payloads, portfolio allocation, and order generation.

The next implementation step is to add the V1-style full market universe loader, checkpoint/resume support, and Firestore-backed frontend data loading.
