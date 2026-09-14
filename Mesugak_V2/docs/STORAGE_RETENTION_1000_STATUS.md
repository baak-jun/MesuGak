# Storage retention status — 2026-09-09

## Applied

- `analyze_market.py` rejects a requested limit above 1,000 before market-data
  or Firestore I/O.
- The scheduled KR job now analyses the bounded full universe on the school
  server first and writes only the ranked result set to Firebase.
- Ranking is deterministic: `confidenceScore` descending, `marcap` descending,
  then code ascending. This makes the 1,000-symbol criterion explicit.
- The school-server environment is set to `MESUGAK_MAX_STOCKS=1000`.
- Candidate payloads are gzip-compressed on the school server and, after a
  successful run, only the selected IDs are retained for recovery/inspection;
  regenerable non-selected files are pruned locally.
- `run_v2_kr_close.sh` runs the bounded retention job before publishing the
  public feed.
- The retention job keeps the current KR public-data universe and deletes stale
  KR analysis documents with conditional batched deletes. Regenerable analysis
  backups are disabled; the school server can fetch them again from the public
  API if needed.

## One-time cleanup result

- Before cleanup: 4,315 `stock_analysis` documents.
- Current KOSPI universe: 916 symbols; all 916 already had analysis documents.
- KR stale documents archived and deleted: 1,971.
- The previously created 1,971-entry local archive was removed after the user
  confirmed that these API-reproducible inputs do not need to be backed up.
- After the KR cleanup, 916 KR `stock_analysis` documents remained. A
  read-only US inventory then found exactly 1,428 `stock_analysis` documents,
  19 public-analysis pages, 4 legacy meta chunks, and 15 strategy-run records.
- The user-authorized retired-market cleanup deleted those 1,466 US analysis
  records without a local archive. It was restricted to the fixed analysis
  allow-list (`stock_analysis`, `public_analysis_meta`, `meta_data`,
  `strategy_runs`); account, order, portfolio, and paper-trading collections
  were not selected. Verification found zero remaining US records in each
  allowed collection.

## Next automatic run

The existing weekday cron remains the owner of the next analysis. The first
manual attempts after cleanup were correctly stopped by the local one-run-per-
day guard; they did not write analysis data. The next scheduled run will
analyse the full configured KOSPI public-data universe on the school server,
then write only the deterministic top 1,000 (or fewer successful candidates)
to Firebase before KR retention and public publishing.
