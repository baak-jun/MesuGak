# Firebase Cost Control Plan

## Operating rule

MesuGak treats recurring cloud cost as a release blocker. Do not deploy
Functions, Firestore rules, indexes, scheduled jobs, or new data copies unless
their expected read/write/storage/egress impact has been measured first.
Hosting-only releases are allowed after the frontend checks pass.

## Current cost boundaries

- The school server owns the weekday KR analysis and monitoring schedule.
- Firebase Hosting serves the static frontend.
- Firestore stores the private analysis and the price-free public feed.
- KIS is restricted to the administrator's virtual-account workflow.
- V2 does not require a deployed Firebase Function.

## Changes in this release

1. A signed-out public page load reads only the KR public manifest and page 0.
   A short in-flight/recent-load guard prevents the auth initialization callback
   from immediately repeating the same two reads.
2. Administrator trade-log reads are limited to the latest 120 documents.
3. Administrator rebalance-order reads are limited to the latest 200 documents.
4. Daily analysis no longer duplicates every full `stock_analysis` payload into
   the run-scoped `strategy_candidates` collection.
5. Hashed frontend assets receive a one-year immutable cache header. The HTML
   shell remains revalidated so releases still appear promptly.
6. The analysis/Firebase bundle is lazy-loaded only on the analysis route.
7. Daily analysis skips the full-collection retention scan by default. Enable
   `MESUGAK_ENABLE_RETENTION_CLEANUP=true` only for a deliberate maintenance
   run, because cleanup reads and deletes are billable operations.

## Expected request budget

- Normal signed-out first visit to `/analysis`: 2 document reads
  (`public_meta_v2_KR_manifest` and `public_meta_v2_KR_0`).
- Additional public search pages: only the pages needed for the query, with an
  existing cap of eight page documents per search.
- Manual refresh: another 2 public document reads after the five-second
  duplicate guard.
- Administrator trade history: at most 120 document reads per refresh.
- Administrator staged orders: at most 200 document reads per refresh.
- Weekday analysis: one overwrite per analyzed symbol in `stock_analysis`, plus
  bounded meta/public page documents and run metadata. It must not create a
  second full per-symbol snapshot collection.

These are code-level upper bounds, not a bill estimate. Confirm the actual SKU
and usage in Google Cloud Billing before attributing a charge.

## Cloud cleanup candidates (not automatic)

The 2026-09-04 count-only audit found:

- `strategy_candidates`: 85,673 documents; one sampled JSON payload was about
  70 KB.
- `stock_analysis`: 4,315 documents; one sampled JSON payload was about 134 KB.
- `strategy_runs`: 54 documents.
- `meta_data`: 20 documents.
- `public_analysis_meta`: 109 documents.

The samples are not a billed-size measurement, but they confirm that the
run-scoped candidate collection is the largest avoidable accumulation. Its
routine writer is now disabled. Deleting the existing collection requires a
separate explicit approval because the operation is irreversible and billed as
document deletes.

The project currently has legacy deployed Functions even though V2 runs on the
school server. Before removal, verify that no V1 `pending_orders` consumer is
still in use, then explicitly remove the obsolete scheduled Function and its
failed V2 Function. Rotate any credentials that were stored in Function
environment variables. Do not retain plaintext broker secrets in Function
configuration.

The project also has both the `mesu-gak` Hosting site and the Firebase default
site. Do not delete the default site until its content and traffic are checked.
An unused site has little impact by itself; retained releases and served bytes
are the meaningful Hosting cost inputs.

## Billing verification checklist

In Google Cloud Console, set the report period to the current invoice month and
group by **Service**, then by **SKU**. Record:

- service and SKU name;
- usage quantity and unit;
- cost before and after credits;
- project and date range.

Check Firestore document reads/writes/storage, Hosting data transfer/storage,
Cloud Run/Functions, Cloud Scheduler, Artifact Registry, Logging, and network
egress separately. A budget alert is useful for notification but does not stop
usage or cap the bill.

## Release gate

Before every Firebase change:

1. State which product will change and why.
2. Estimate the new reads, writes, stored bytes, scheduled invocations, and
   outbound bytes.
3. Prefer school-server batch work, stable document IDs, bounded queries, and
   CDN caching.
4. Run frontend policy, lint, and build checks.
5. Deploy Hosting only unless another Firebase product is explicitly required
   and approved.
6. After deployment, verify the site and response cache headers without forcing
   repeated Firestore refreshes.

## Official references

- Firebase pricing: <https://firebase.google.com/pricing>
- Cloud Firestore pricing and aggregation charges:
  <https://firebase.google.com/docs/firestore/pricing>
- Firebase Hosting usage, release retention, caching, and budget guidance:
  <https://firebase.google.com/docs/hosting/usage-quotas-pricing>
