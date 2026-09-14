# Mesugak V2 Release Checklist

## Before Deploy

- Review `docs/FIREBASE_COST_PLAN.md` and identify the expected Firebase product
  and usage change. A deployment with unknown recurring cost does not proceed.

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
  - `python Mesugak_V2\functions\jobs\run_paper_flow.py --market KR --max-stocks 30 --dry-run`
- Deploy Hosting only unless a separately reviewed release truly changes rules
  or indexes:
  - `firebase deploy --only hosting`
- Do not deploy Firebase Functions for V2. The school server owns scheduled
  analysis and paper-account jobs.
- Copy the complete `Mesugak_V2\functions` directory to the school server,
  install `functions\requirements.txt`, and run the server-side job with the
  protected KIS virtual-account/Firebase environment.
- Confirm no production write happens with the `--dry-run` option.

## First Non-Dry Run

- Remove `--dry-run` only after the rehearsal succeeds.
- Keep `--max-stocks` small for the first non-dry run.
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

- Increase `--max-stocks` gradually.
- Watch school-server duration, upstream data-source failures, and failure logs.
- Confirm frontend shows legal links and the no-live-data education screen by default. `public_analysis_meta` rules allow only the explicitly named `public_meta_v2_KR_{manifest|number}` documents; the frontend must keep the public-data gate disabled until the written data-rights review is complete.
- Add README CI badge after the workflow is observed passing on GitHub.

## Compliance Gate

- Review `Mesugak_V2\docs\DATA_COMPLIANCE.md` before public deployment, advertising, or paid access.
- Keep `VITE_ENABLE_PUBLIC_LIVE_DATA=false`, `VITE_PUBLIC_DATA_RIGHTS_CONFIRMED=false`, and `VITE_ENABLE_ADSENSE=false` unless market-data display rights and the full commercial scope are confirmed in writing.
- Before opening public data, retain the written approval reference, review the exact feeds/territories/delay conditions, set the explicit frontend gates, and deploy a reviewed Firestore-rules change in the same release.
- Confirm the frontend legal links are visible: 개인정보처리방침, 이용약관, 면책고지, 데이터 사용 고지.
- Do not enable real AdSense code until AdSense approval, `ads.txt`, privacy cookie disclosures, consent requirements, and data-display rights are all ready.
- Keep separate AdSense unit IDs for authored learning pages and the optional generated-analysis placement. Confirm that no ad appears on list, loading, error, legal, administrator, or navigation screens.
