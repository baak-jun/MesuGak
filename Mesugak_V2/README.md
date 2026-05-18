# Mesugak V2

Mesugak V2 rebuilds the project around a strategy engine instead of a Bollinger-only scanner.

Core signals:

- Ichimoku Cloud
- Moving average support
- Bollinger Bands
- RSI
- Risk and cash-ratio controls
- Paper trading and rebalance simulation

## Layout

- `frontend/`: new React/Vite app surface.
- `functions/strategy_engine/`: pure strategy modules shared by analysis, paper trading, and backtests.
- `functions/jobs/`: runnable jobs that connect the strategy engine to Firestore or schedulers.
- `docs/`: schema, architecture, and agent harness notes.

Continue implementation from `docs/WORKLOG.md`.

## Development Order

1. Indicator functions are scaffolded and covered by tests.
2. Scoring and risk rules are scaffolded and covered by tests.
3. Firestore repository boundaries and basic jobs are wired.
4. Portfolio target and order generation are scaffolded and covered by tests.
5. The frontend renders the strategy console from Firestore when Firebase env vars are configured, with mock fallback data for local development.

## Current Commands

Run backend tests:

```powershell
python -m unittest discover -s Mesugak_V2\functions\tests
```

Compile Python modules:

```powershell
python -m py_compile Mesugak_V2\functions\strategy_engine\analysis.py Mesugak_V2\functions\strategy_engine\market_data.py Mesugak_V2\functions\strategy_engine\repositories.py Mesugak_V2\functions\jobs\analyze_market.py Mesugak_V2\functions\jobs\rebalance.py
```

Build frontend:

```powershell
Set-Location Mesugak_V2\frontend
npm run build
```

Analyze explicit codes:

```powershell
python Mesugak_V2\functions\jobs\analyze_market.py --market KR --codes 005930,000660 --dry-run
```

Analyze the full V1-style market universe with checkpoint/resume:

```powershell
python Mesugak_V2\functions\jobs\analyze_market.py --market KR --kr-markets KOSPI,KOSDAQ
```

Generate rebalance decisions from Firestore:

```powershell
python Mesugak_V2\functions\jobs\rebalance.py --market KR --dry-run
```

Apply staged rebalance orders to the paper ledger:

```powershell
python Mesugak_V2\functions\jobs\apply_paper_orders.py --market KR --dry-run
```

Run the full paper flow:

```powershell
python Mesugak_V2\functions\jobs\run_paper_flow.py --market KR --max-stocks 50
```

For a read-only rehearsal, use `--dry-run`; note that dry-run analysis and rebalance results are not written before the apply step.

Run a Firestore-free local smoke test:

```powershell
python Mesugak_V2\functions\jobs\smoke_test_flow.py
```

Validate scheduled function environment values:

```powershell
python Mesugak_V2\functions\jobs\validate_scheduler_env.py
```

Run the Firestore emulator smoke path after starting the emulator:

```powershell
$env:FIRESTORE_EMULATOR_HOST="127.0.0.1:8080"
$env:GCLOUD_PROJECT="mesugak-v2-emulator"
python Mesugak_V2\functions\jobs\emulator_smoke_flow.py
```

CI-style verification:

```powershell
python -m unittest discover -s Mesugak_V2\functions\tests
python -m py_compile Mesugak_V2\functions\main.py Mesugak_V2\functions\jobs\analyze_market.py Mesugak_V2\functions\jobs\rebalance.py Mesugak_V2\functions\jobs\apply_paper_orders.py Mesugak_V2\functions\jobs\run_paper_flow.py Mesugak_V2\functions\jobs\smoke_test_flow.py Mesugak_V2\functions\jobs\validate_scheduler_env.py Mesugak_V2\functions\jobs\emulator_smoke_flow.py
Set-Location Mesugak_V2\frontend
npm run build
```

The same checks are defined in `.github/workflows/mesugak-v2-ci.yml`.

Run the frontend:

```powershell
Set-Location Mesugak_V2\frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

The frontend reads Firestore when these Vite env vars are configured, and falls back to mock data otherwise:

- `VITE_FIREBASE_API_KEY`
- `VITE_FIREBASE_AUTH_DOMAIN`
- `VITE_FIREBASE_PROJECT_ID`
- `VITE_FIREBASE_STORAGE_BUCKET`
- `VITE_FIREBASE_MESSAGING_SENDER_ID`
- `VITE_FIREBASE_APP_ID`

Deploy V2 hosting and Firestore rules from `Mesugak_V2/`:

```powershell
firebase deploy --only hosting,firestore:rules
```

Deploy scheduled Python functions too:

```powershell
firebase deploy --only functions,hosting,firestore:rules
```

The scheduled paper flow runs weekdays at `08:30 UTC` (`17:30` Korea time). It can be configured with environment variables such as `MESUGAK_MAX_STOCKS`, `MESUGAK_MAX_POSITIONS`, `MESUGAK_MIN_CONFIDENCE`, and `MESUGAK_DRY_RUN`.
See `functions/.env.example` for the full environment template.
