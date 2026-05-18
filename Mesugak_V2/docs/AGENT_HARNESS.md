# Agent Harness

Use agents by ownership boundary. Avoid assigning multiple agents to the same files at the same time.

## Suggested Workers

- Indicator worker: `functions/strategy_engine/indicators.py` and tests.
- Scoring worker: `scoring.py`, `risk.py`, and tests.
- Portfolio worker: `portfolio.py`, `orders.py`, and tests.
- Firestore worker: `repositories.py` and job integration.
- Frontend worker: `frontend/src` only.

## Current Test Commands

Backend:

```powershell
python -m unittest discover -s Mesugak_V2\functions\tests
```

Frontend:

```powershell
Set-Location Mesugak_V2\frontend
npm run build
```

## Integration Rule

The main agent reviews and integrates worker outputs. Strategy math should stay in pure modules so analysis jobs, paper trading, and backtests use the same code path.
