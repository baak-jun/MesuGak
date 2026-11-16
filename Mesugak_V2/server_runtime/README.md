# Managed school-server runtime

Current deployed paths, schedules, and contest/site behavior: [2026-10-15 operations handover](../docs/operations/README.md).

This folder is the repository-tracked source for files deployed to the school server.

The examples below use a managed checkout such as
`~/mesugak/repo/Mesugak_V2`. If the active checkout is the existing
`~/mesugak/v2` layout, use that directory as `ROOT` instead; do not create a
second checkout just to match the example path.

## V2 deployment

`run_v2_kr_close.sh` is the V2 domestic entry point. It runs
`functions/jobs/analyze_market.py`, which analyses the configured KOSPI
public-data universe locally, keeps gzip payloads only on the school server
during the run, and writes at most `MESUGAK_MAX_STOCKS` ranked results to
Firestore (hard cap: 200). The whole configured universe is still analyzed.
Ranking is `confidenceScore` descending, then
market cap descending, then code ascending. The selected IDs are written to a
checkpoint file for the following KR retention step; regenerable backups and
non-selected local payloads are not retained after a successful run.
After that, `publish_public_analysis.py` writes the price-free
`public_analysis_meta` feed. The deployed Firestore rule allows only the
explicitly named public feed documents, while the frontend gate remains
disabled until written data-rights review.
Keep the checked-out `Mesugak_V2/` directory intact on the server. The runner
scripts resolve their V2 root from their own location, so a normal Git update
does not require copying individual files. Create the ignored `.env.server`
from `.env.server.example` and keep the protected `functions/.env` beside the
checkout.

For the managed school-server layout, use the low-cost public-data watcher:

```cron
*/3 13-23 * * 1-5 /usr/bin/flock -n /tmp/mesugak-v2-watch.lock /home/USER/mesugak/repo/Mesugak_V2/server_runtime/run_v2_kr_watch.sh >> /home/USER/mesugak/repo/Mesugak_V2/runtime/cron/v2_kr_watch.log 2>&1
```

`run_v2_kr_watch.sh` probes the FSC public API from 13:00 through 23:59 KST on
weekdays. Each probe requests one row per candidate date and never reads or
writes Firestore. When a newer `basDt` appears, the local marker at
`runtime/watch/public_data_KR.json` permits one `run_v2_kr_close.sh` attempt;
the existing cost guard and runner lock remain in force. A failed attempt has a
30-minute local retry cooldown. Public holidays naturally produce no new date,
so no analysis is started. If the existing Pacific quota-day ledger is already
used, the watcher records `cost_cooldown` and keeps polling without invoking the
runner until the next quota day. Run `run_v2_kr_close.sh` manually only when an
operator intentionally wants an immediate, cost-guarded refresh.

The US wrapper is not part of the current public-data deployment. The
one-time `functions/jobs/delete_analysis_market.py --market US` command is
restricted to analysis collections and is not scheduled.

Never commit the actual `.env.server` file or service-account JSON.

The wrappers do not run `source venv/bin/activate`; they invoke the interpreter
from `MESUGAK_PYTHON_BIN`. Set that path in `.env.server` and keep it outside
the Git checkout when possible.

## On-demand paper-account refresh

`run_paper_refresh_requests.sh` is the managed school-server entry point for
browser-triggered KIS virtual-account refreshes. It only runs
`school_paper_trader.py --process-refresh-requests`; it cannot create or submit
an order.

Deploy it alongside the V2 functions directory, then add this cron line on the
school server (KST):

```cron
* 8-18 * * 1-5 /usr/bin/flock -n /tmp/mesugak-paper-refresh.lock /home/USER/mesugak/repo/Mesugak_V2/server_runtime/run_paper_refresh_requests.sh >> /home/USER/mesugak/logs/paper_refresh_$(date +\%Y-\%m).log 2>&1
```

The worker reads only pending requests, so an idle run makes no KIS API call.

## KIS realtime contest trader

`run_kis_realtime_trader.sh` starts the all-day WebSocket runner with an
exclusive lock. It uses `functions/.env.contest` when present, unless
`MESUGAK_CONTEST_ENV_FILE` is set, and is dry-run unless the protected environment
contains `MESUGAK_REALTIME_EXECUTE=true`; set that only after replay and
dry-run acceptance. A weekday systemd service should start it before 09:00 KST
and stop it after 15:35. p102 currently uses a five-minute cron restart cadence
with the same exclusive lock; do not add a second scheduler. Site-linked
automatic orders are paused for contest priority as of 2026-10-12.

The realtime runner reads the full server snapshot at
`runtime/checkpoints/realtime_candidates_KR.json`. It defaults to 39 price
symbols (35 high-score/protected symbols and 4 rotating random explorers),
leaving one of the 40 subscriptions for virtual-account fills. At a lower
provider limit the watch set is reduced automatically. The shared analyzer
must use `MESUGAK_KR_MARKETS=KOSPI,KOSDAQ`; `MESUGAK_MAX_STOCKS=200` remains
only the Firebase persistence cap.

## Administrator-only KIS paper performance comparison

The KR close runner also calls `publish_private_performance.py`. It writes only
an aggregate, administrator-only comparison document at
`paper_performance_private/latest`; it never writes a KIS account number,
holdings, trades, token, or raw index levels to that document.

Before its first run, set the actual virtual-account experiment start date in
the school server's `functions/.env`:

```bash
MESUGAK_PERFORMANCE_BASELINE_DATE=YYYY-MM-DD
```

The job skips safely when that date is blank. Use the same date for the KIS
account and KOSPI/KOSDAQ comparison; do not expose this comparison publicly
without a separate data-rights and legal review.

## Gmail refresh alerts

`run_v2_kr_close.sh` sends an immediate Gmail alert when the analysis or public
publication pipeline exits with an error. `run_v2_health_monitor.sh` separately
detects an interrupted or stalled checkpoint and a missing weekday publication.
When the recent public-data watcher reports `unchanged` with no newer trading
date, the monitor treats that as a provider-side holiday-like delay instead of
a publication failure. Missing, stale, or `poll_failed` watcher state still
raises the stale-publication alert. It sends one recovery message after the
next healthy check.

Enable Google 2-Step Verification, create an app password, and add these values
only to the protected `functions/.env` on the school server:

```bash
MESUGAK_GMAIL_USER=sender@gmail.com
MESUGAK_GMAIL_APP_PASSWORD=__SET_IN_PROTECTED_ENV__
MESUGAK_ALERT_EMAIL_TO=recipient@gmail.com
```

Send one test message before installing cron:

```bash
set -a; source functions/.env; set +a
venv/bin/python functions/jobs/monitor_school_server.py --send-test
```

Deploy both runner scripts, make them executable, and check health every 30
minutes:

```cron
*/30 * * * * /usr/bin/flock -n /tmp/mesugak-v2-health.lock /home/USER/mesugak/repo/Mesugak_V2/server_runtime/run_v2_health_monitor.sh || true
```

Monitor state is stored under the Git-ignored `runtime/health/` directory. A
monitor on the school server cannot send mail while that server is fully
offline; it reports a missed refresh when the server or cron starts again.

## Git-based update

Run updates from the repository root with the scheduled jobs stopped or idle:

```bash
cd /home/USER/mesugak/repo
git pull --ff-only
cd Mesugak_V2
chmod 755 server_runtime/*.sh
sed -i 's/\r$//' server_runtime/*.sh
venv/bin/python functions/jobs/validate_scheduler_env.py
venv/bin/python functions/jobs/smoke_test_flow.py
```

The checkout contains code and examples only. Keep `Mesugak_V2/.env.server`,
`Mesugak_V2/functions/.env`, the Firebase credential JSON, `venv/`, and
`runtime/` outside Git or in ignored paths. A Git update must never overwrite
those files. After the smoke checks pass, the next cron invocation uses the new
commit; no Firebase Function deployment is required.

For a read-only post-copy check that does not call the public API, Firestore,
or print secret values, run:

```bash
chmod 755 server_runtime/verify_v2_release.sh
server_runtime/verify_v2_release.sh
```

The check prints hashes for the deployed runner files, verifies the protected
environment variable names are present, reports the local public-data watcher
marker, and shows matching cron entries. `VERIFY_V2_RELEASE_OK` is emitted
only when those checks pass. It does not prove that the school server is
reachable from the Internet or that the provider has published a newer date;
the next watcher/health-monitor run is still required for that.

The scheduled KR retention step deletes stale analysis documents with
conditional batched deletes and passes `--skip-archive`; the source data can
be regenerated from the approved public API. Other retention cleanup remains
disabled by default. Set `MESUGAK_ENABLE_RETENTION_CLEANUP=true` in the
protected `functions/.env` only for a planned maintenance run, then turn it
off again.
