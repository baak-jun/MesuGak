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
`functions/jobs/analyze_market.py`, which writes `meta_v2_*` documents used by
the V2 frontend. Deploy the whole `Mesugak_V2/functions/` directory and both
runner scripts to the path set by `MESUGAK_V2_ROOT`, then create `.env.server`
from `.env.server.example`.

For the managed school-server layout, use:

```cron
10 16 * * 1-5 /home/2023112374/mesugak/v2/run_v2_kr_close.sh
20 5,6 * * * /home/2023112374/mesugak/v2/run_v2_us_close.sh
```

The US wrapper checks the New York trading-day close and records a date stamp,
so the two calls handle daylight saving time without duplicate analysis.

Never commit the actual `.env.server` file or service-account JSON.
