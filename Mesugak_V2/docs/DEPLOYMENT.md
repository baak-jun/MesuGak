# Mesugak V2 Deployment Notes

## Firebase Hosting And Rules

Build and deploy from `Mesugak_V2/`.

```powershell
Set-Location Mesugak_V2\frontend
npm run build
Set-Location ..
firebase deploy --only hosting,firestore:rules
```

## School-server paper flow

V2 does not deploy the analysis worker as a Firebase Function. The school
server owns Financial Services Commission public-data KR market analysis, KIS virtual-account credentials,
paper orders, and Firestore writes. Upload the complete `Mesugak_V2\functions` directory, install its
requirements, and run the jobs from that server with the protected environment
file described in `docs\SCHOOL_SERVER_PAPER_TRADING.md`.

The command-line flow controls are:

- `--market`, `--codes`, `--kr-markets`, `--max-stocks`
- `--max-positions`, `--min-confidence`, `--dry-run`
- `--skip-analysis`, `--skip-rebalance`, `--skip-apply`

Start production validation with a small `--max-stocks` value, then increase
after checking the school-server job duration and upstream data-source stability.

Example command for a small first run:

```bash
python functions/jobs/run_paper_flow.py --market KR --kr-markets KOSPI --max-stocks 30 --max-positions 3 --min-confidence 65 --dry-run
```

See `functions/.env.example` for public-data, KIS virtual-account, Firebase, and paper-trading environment
values. Never copy that file with real secrets into source control.

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

## First school-server rollout checklist

- Run backend tests locally.
- Run `smoke_test_flow.py`.
- Run frontend build.
- Run the paper flow with `--dry-run --max-stocks 30` first.
- Confirm the school-server log contains the analysis, rebalance, and apply
  results before enabling the normal schedule.
- Confirm no duplicate `appliedAllocationIds` are written for the same allocation.
- Confirm `paper_order_applications/{allocationId}` is written after the first non-dry run.
- Confirm frontend account snapshot shows `source: Mesugak_V2`.
- Increase `--max-stocks` only after checking job duration and upstream request failures.

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

Current frontend queries use simple equality filters without explicit ordering:

- `meta_data`: `market == "KR"`
- `rebalance_orders`: `market == "KR"`

If the frontend later adds server-side ordering or pagination on these collections, add matching composite indexes before deployment.

## Frontend Live-Data Safety Gate

The production frontend defaults to a no-live-data education view. Firestore permits anonymous `get` only for the explicitly named `public_meta_v2_KR_{manifest|number}` feed documents; all other analysis documents remain administrator-only. A frontend environment value alone cannot expose data that has not been published to those documents.

Do not open public market-derived analysis or advertising until the written approval reference, exact public/commercial data-display scope, privacy/cookie requirements, and a reviewed Firestore-rules deployment have all been completed. `frontend/.env.example` documents the disabled-by-default gates.
