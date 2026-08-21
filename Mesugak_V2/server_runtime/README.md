# Managed school-server runtime

This folder is the repository-tracked source for files deployed to the school server.

## v1_compat

`v1_compat/` contains the exact Python modules used by the current live server
runner. `analyzer.py` uses `FIRESTORE_BATCH_SIZE = 40` for full stock documents
and keeps `META_CHUNK_SIZE = 400` for summary documents. This avoids Firestore's
10 MiB commit limit while retaining the existing list format.

Deploy the compatibility fix with:

```bash
scp -P <port> Mesugak_V2/server_runtime/v1_compat/analyzer.py <user>@<host>:~/chartbot/analyzer.py
scp -P <port> Mesugak_V2/server_runtime/run_v1_kr_close.sh <user>@<host>:~/chartbot/run_kr_close.sh
scp -P <port> Mesugak_V2/server_runtime/run_v1_us_close.sh <user>@<host>:~/chartbot/run_us_close.sh
ssh -p <port> <user>@<host> 'chmod 755 ~/chartbot/run_v1_*_close.sh'
```

The current server cron can continue invoking its existing `run_kr_close.sh` and
`run_us_close.sh`; copy the managed wrappers over those names if desired.

## V2 migration

`run_v2_kr_close.sh` and `run_v2_us_close.sh` are the V2 entry points. They run
`functions/jobs/analyze_market.py`, which writes private `meta_v2_*` documents.
After a successful analysis they also run `publish_public_analysis.py`, which
writes the price-free `public_analysis_meta` feed. The deployed Firestore rule
currently keeps that feed administrator-only pending written data-rights review.
Deploy the whole `Mesugak_V2/functions/` directory and both runner scripts to
the path set by `MESUGAK_V2_ROOT`, then create `.env.server` from
`.env.server.example`.

For the managed school-server layout, use:

```cron
10 16 * * 1-5 /home/2023112374/mesugak/v2/run_v2_kr_close.sh
20 5,6 * * * /home/2023112374/mesugak/v2/run_v2_us_close.sh
```

The US wrapper checks the New York trading-day close and records a date stamp,
so the two calls handle daylight saving time without duplicate analysis.

Never commit the actual `.env.server` file or service-account JSON.

## On-demand paper-account refresh

`run_paper_refresh_requests.sh` is the managed school-server entry point for
browser-triggered KIS virtual-account refreshes. It only runs
`school_paper_trader.py --process-refresh-requests`; it cannot create or submit
an order.

Deploy it alongside the V2 functions directory, then add this cron line on the
school server (KST):

```cron
* 8-18 * * * /usr/bin/flock -n /tmp/mesugak-paper-refresh.lock /home/2023112374/mesugak/v2/run_paper_refresh_requests.sh >> /home/2023112374/mesugak/logs/paper_refresh_$(date +\%Y-\%m).log 2>&1
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