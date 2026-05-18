# Mesugak V2 Deployment Notes

## Firebase Hosting And Rules

Build and deploy from `Mesugak_V2/`.

```powershell
Set-Location Mesugak_V2\frontend
npm run build
Set-Location ..
firebase deploy --only hosting,firestore:rules
```

## Scheduled Paper Flow

V2 includes a Python scheduled function in `functions/main.py`.

- Function: `scheduled_paper_flow`
- Schedule: `30 8 * * 1-5`
- Effective Korea time: 17:30 on weekdays
- Flow: analyze market -> generate rebalance orders -> apply paper orders

Deploy:

```powershell
Set-Location Mesugak_V2
firebase deploy --only functions,hosting,firestore:rules
```

Runtime controls are environment variables:

- `MESUGAK_MARKET`: default `KR`
- `MESUGAK_CODES`: optional comma-separated explicit code list
- `MESUGAK_KR_MARKETS`: default `KOSPI,KOSDAQ`
- `MESUGAK_MAX_STOCKS`: default `300`
- `MESUGAK_MAX_POSITIONS`: default `5`
- `MESUGAK_MIN_CONFIDENCE`: default `65.0`
- `MESUGAK_DRY_RUN`: default `false`
- `MESUGAK_SKIP_ANALYSIS`: default `false`
- `MESUGAK_SKIP_REBALANCE`: default `false`
- `MESUGAK_SKIP_APPLY`: default `false`

Start production validation with a small `MESUGAK_MAX_STOCKS` value, then increase after checking Cloud Functions duration and memory behavior.

Example environment values for a small first run:

```powershell
MESUGAK_MARKET=KR
MESUGAK_KR_MARKETS=KOSPI
MESUGAK_MAX_STOCKS=30
MESUGAK_MAX_POSITIONS=3
MESUGAK_MIN_CONFIDENCE=65
MESUGAK_DRY_RUN=true
```

See `functions/.env.example` for the full list of scheduler environment variables.

## Local Smoke Test

This command verifies analysis, allocation, order generation, and ledger application without Firestore or market-data network calls:

```powershell
python Mesugak_V2\functions\jobs\smoke_test_flow.py
```

Validate the scheduler environment template:

```powershell
python Mesugak_V2\functions\jobs\validate_scheduler_env.py
```

Optional Firestore emulator smoke path:

```powershell
firebase emulators:start --only firestore
$env:FIRESTORE_EMULATOR_HOST="127.0.0.1:8080"
$env:GCLOUD_PROJECT="mesugak-v2-emulator"
python Mesugak_V2\functions\jobs\emulator_smoke_flow.py
```

## First Scheduler Deploy Checklist

- Run backend tests locally.
- Run `smoke_test_flow.py`.
- Run frontend build.
- Deploy with `MESUGAK_DRY_RUN=true` or with `MESUGAK_MAX_STOCKS` set to a small value first.
- Confirm Cloud Functions logs include `scheduled_paper_flow` result output.
- Confirm no duplicate `appliedAllocationIds` are written for the same allocation.
- Confirm `paper_order_applications/{allocationId}` is written after the first non-dry run.
- Confirm frontend account snapshot shows `source: Mesugak_V2`.
- Increase `MESUGAK_MAX_STOCKS` only after checking function duration and memory.

## CI Verification

```powershell
pip install -r Mesugak_V2\functions\requirements.ci.txt
python -m unittest discover -s Mesugak_V2\functions\tests
python -m py_compile Mesugak_V2\functions\main.py Mesugak_V2\functions\jobs\analyze_market.py Mesugak_V2\functions\jobs\rebalance.py Mesugak_V2\functions\jobs\apply_paper_orders.py Mesugak_V2\functions\jobs\run_paper_flow.py Mesugak_V2\functions\jobs\smoke_test_flow.py Mesugak_V2\functions\jobs\validate_scheduler_env.py Mesugak_V2\functions\jobs\emulator_smoke_flow.py
Set-Location Mesugak_V2\frontend
npm run build
```

## Index Notes

Current server-side Python queries use simple equality filters and should not require composite indexes:

- `meta_data`: `market == MARKET`
- `rebalance_orders`: `market == MARKET`, optionally `allocationId == ID`

Current frontend queries use simple `in` filters without explicit ordering:

- `meta_data`: `market in ["KR", "US"]`
- `rebalance_orders`: `market in ["KR", "US"]`

If the frontend later adds server-side ordering or pagination on these collections, add matching composite indexes before deployment.
