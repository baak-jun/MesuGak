# Managed school-server runtime

This folder is the repository-tracked source for files deployed to the school server.

## V2 deployment

`run_v2_kr_close.sh` is the V2 domestic entry point. It runs
`functions/jobs/analyze_market.py`, which writes private `meta_v2_*` documents.
After a successful analysis they also run `publish_public_analysis.py`, which
writes the price-free `public_analysis_meta` feed. The deployed Firestore rule
allows only the explicitly named public feed documents, while the frontend
gate remains disabled until written data-rights review.
Keep the checked-out `Mesugak_V2/` directory intact on the server. The runner
scripts resolve their V2 root from their own location, so a normal Git update
does not require copying individual files. Create the ignored `.env.server`
from `.env.server.example` and keep the protected `functions/.env` beside the
checkout.

For the managed school-server layout, use:

```cron
10 16 * * 1-5 /usr/bin/flock -n /tmp/mesugak-v2-kr.lock /home/USER/mesugak/repo/Mesugak_V2/server_runtime/run_v2_kr_close.sh
```

The US wrapper is not part of the current public-data deployment. Remove any
old US cron entry before enabling this schedule.

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
It sends one recovery message after the next healthy check.

Enable Google 2-Step Verification, create an app password, and add these values
only to the protected `functions/.env` on the school server:

```bash
MESUGAK_GMAIL_USER=sender@gmail.com
MESUGAK_GMAIL_APP_PASSWORD=16-character-app-password
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
venv/bin/python functions/jobs/validate_scheduler_env.py
venv/bin/python functions/jobs/smoke_test_flow.py
```

The checkout contains code and examples only. Keep `Mesugak_V2/.env.server`,
`Mesugak_V2/functions/.env`, the Firebase credential JSON, `venv/`, and
`runtime/` outside Git or in ignored paths. A Git update must never overwrite
those files. After the smoke checks pass, the next cron invocation uses the new
commit; no Firebase Function deployment is required.
