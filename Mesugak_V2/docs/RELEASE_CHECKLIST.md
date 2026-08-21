# Mesugak V2 Release Checklist

## Before Deploy

- Run backend tests:
  - `python -m unittest discover -s Mesugak_V2\functions\tests`
- Run Python compile check:
  - `python -m py_compile Mesugak_V2\functions\main.py Mesugak_V2\functions\jobs\analyze_market.py Mesugak_V2\functions\jobs\rebalance.py Mesugak_V2\functions\jobs\apply_paper_orders.py Mesugak_V2\functions\jobs\run_paper_flow.py Mesugak_V2\functions\jobs\smoke_test_flow.py Mesugak_V2\functions\jobs\validate_scheduler_env.py Mesugak_V2\functions\jobs\emulator_smoke_flow.py`
- Run Firestore-free smoke test:
  - `python Mesugak_V2\functions\jobs\smoke_test_flow.py`
- Validate scheduler environment:
  - `python Mesugak_V2\functions\jobs\validate_scheduler_env.py`
- Build frontend:
  - `Set-Location Mesugak_V2\frontend`
  - `npm run build`

## First Deploy

- Deploy with a small universe first:
  - `MESUGAK_MAX_STOCKS=30`
  - `MESUGAK_DRY_RUN=true`
- Deploy:
  - `firebase deploy --only functions,hosting,firestore:rules`
- Check Cloud Functions logs for `scheduled_paper_flow`.
- Confirm no production write happens while `MESUGAK_DRY_RUN=true`.

## First Non-Dry Run

- Set `MESUGAK_DRY_RUN=false`.
- Keep `MESUGAK_MAX_STOCKS` small for the first non-dry run.
- Confirm these collections are updated:
  - `stock_analysis`
  - `meta_data`
  - `target_allocations`
  - `rebalance_orders`
  - `bot_portfolio`
  - `bot_trade_logs`
  - `bot_account_snapshot/latest`
  - `paper_order_applications`
- Confirm `bot_account_snapshot/latest.source` is `Mesugak_V2`.
- Confirm `appliedAllocationIds` prevents duplicate application for the same allocation.

## After Validation

- Increase `MESUGAK_MAX_STOCKS` gradually.
- Watch Cloud Functions duration, memory, and failure logs.
- Confirm frontend shows legal links and the no-live-data education screen by default. `public_analysis_meta` must remain administrator-only in deployed Firestore rules until the public data-rights gate is formally opened.
- Add README CI badge after the workflow is observed passing on GitHub.

## Compliance Gate

- Review `Mesugak_V2\docs\DATA_COMPLIANCE.md` before public deployment, advertising, or paid access.
- Keep `VITE_ENABLE_PUBLIC_LIVE_DATA=false`, `VITE_PUBLIC_DATA_RIGHTS_CONFIRMED=false`, and `VITE_ENABLE_ADSENSE=false` unless market-data display rights and the full commercial scope are confirmed in writing.
- Before opening public data, retain the written approval reference, review the exact feeds/territories/delay conditions, set the explicit frontend gates, and deploy a reviewed Firestore-rules change in the same release.
- Confirm the frontend legal links are visible: 개인정보처리방침, 이용약관, 면책고지, 데이터 사용 고지.
- Do not enable real AdSense code until AdSense approval, `ads.txt`, privacy cookie disclosures, consent requirements, and data-display rights are all ready.
