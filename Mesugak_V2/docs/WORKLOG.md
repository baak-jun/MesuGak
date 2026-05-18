# Mesugak V2 Worklog

This document is the running handoff list for continuing V2 work without re-asking for direction.

## Done

- Split the repository into preserved `Mesugak_V1/` and active `Mesugak_V2/`.
- Added V2 strategy engine modules:
  - `indicators.py`
  - `scoring.py`
  - `risk.py`
  - `portfolio.py`
  - `orders.py`
  - `analysis.py`
  - `market_data.py`
  - `repositories.py`
  - `checkpoints.py`
  - `backtest.py`
- Implemented multi-indicator analysis:
  - Ichimoku Cloud
  - moving average support
  - Bollinger Bands
  - RSI
  - confidence score
  - risk flags
  - cash target
  - stop-loss
- Implemented V1-compatible analysis payloads:
  - `stock_analysis/{MARKET}_{CODE}`
  - `meta_data/meta_v2_{MARKET}_{N}`
- Implemented full market universe loading:
  - KR through FinanceDataReader KRX listing
  - US through S&P 500 and Nasdaq 100 constituent lists plus FDR exchange listings
- Implemented checkpoint/resume support for long analysis runs.
- Fixed dry-run behavior so default `--dry-run` analysis does not read or write production checkpoint files.
- Implemented rebalance target allocation and staged order generation.
- Implemented Firestore repository methods for:
  - stock analysis
  - meta chunks
  - strategy runs
  - strategy candidates
  - target allocations
  - rebalance orders
  - risk state
  - current V1-compatible positions
- Implemented a reusable backtest engine with N+1 trade execution to avoid lookahead bias.
- Implemented V2 pure paper ledger logic.
- Implemented Firestore persistence helpers for V2 paper positions, trade logs, account snapshots, rebalance order reads, and latest price reads.
- Added `apply_paper_orders.py` job to apply staged orders to the V1-compatible paper account collections.
- Added integration tests for the rebalance-to-ledger job path using a fake repository.
- Added duplicate allocation protection through `appliedAllocationIds`.
- Enhanced the frontend paper panel with source/mode, total equity, cash, realized PnL, and recent trade logs.
- Added `run_paper_flow.py` orchestration command for analyze -> rebalance -> apply.
- Added `paper_order_applications/{allocationId}` audit writes for applied paper orders.
- Split the frontend build into manual chunks for Firebase, charting, and core vendor packages.
- Added Firestore rules coverage for `paper_order_applications`.
- Added Firebase Python scheduled function wiring for the paper flow.
- Added dedicated frontend execution history table with action/source filters and execution summary.
- Added deployment notes and Firestore index notes.
- Added Firestore-free local smoke-test command for the operator flow.
- Added production scheduler validation checklist and CI verification commands.
- Added GitHub Actions workflow for V2 backend tests, Python compile, smoke test, and frontend build.
- Added separate frontend workspace mode for execution history.
- Added scheduler environment validation helper.
- Added optional Firestore emulator smoke path guarded by `FIRESTORE_EMULATOR_HOST`.
- Split CI Python dependencies into `functions/requirements.ci.txt`.
- Confirmed GitHub Actions CI success on run `26025876706`.
- Added CI badge to root and V2 README files.
- Added V2 release checklist.
- Built V2 frontend strategy console:
  - signal list
  - technical chart
  - indicator toggles and style controls
  - score breakdown
  - risk panel
  - staged rebalance orders
  - Firestore-backed data loading with mock fallback
  - Google login and per-user chart setting persistence
  - paper portfolio snapshot panel reading V1-compatible bot collections
- Added backend tests for:
  - indicators
  - scoring
  - risk
  - analysis payloads
  - market data helpers
  - checkpoint behavior
  - portfolio allocation
  - order generation
  - backtest behavior
- Last verified:
  - `python -m unittest discover -s Mesugak_V2\functions\tests`: 43 tests passing
  - `python Mesugak_V2\functions\jobs\smoke_test_flow.py`: passing
  - `python Mesugak_V2\functions\jobs\validate_scheduler_env.py`: passing
  - `npm run build` in `Mesugak_V2\frontend`: passing

## Current Gaps

- Scheduled paper flow is wired for Firebase Functions, but production runtime limits need to be validated on a real deploy with the target market size.
- CI workflow has been observed passing on GitHub.
- Firebase Functions environment variables are documented and validated locally; production runtime limits still need real deploy observation.

## Next Work Queue

1. Add production runtime observations after the first scheduled run.
2. Add emulator-backed CI job only if Firebase emulator startup is needed in CI.
3. Add deployment result notes after the first Firebase deploy.

## Operating Rule

When continuing work, take the first incomplete item in `Next Work Queue`, implement it, add focused tests, run verification, then update this file before moving to the next item.
