# Storage and request controls

The school cron checks Cloud Monitoring before analysis and paper refresh.
Missing/unauthorized/stale storage metrics stop cloud work. The storage ceiling
is 700 MiB, including indexes. Observed rolling-24-hour operation thresholds are
30,000 reads and 12,000 writes/deletes. Metrics are delayed: this is not a hard
project-wide spending cap, and does not control browsers or legacy cloud jobs.
Spark and removal of paid-service dependencies are needed for a provider-enforced
no-overage policy. Do not claim zero cost while Blaze remains linked.

- Analysis: one attempt per Pacific quota day and no more than 3,000 stocks.
- Paper refresh: 48 attempts per Pacific quota day.
- `runtime/cost/budget.sqlite3` persists reservations across process restarts.
  Failed/partial attempts consume allowance; do not delete this file to retry.
- Firestore analysis: at most 130 recent chart rows and a 64 KiB JSON payload
  budget. Scores are calculated from full data. JSON size is not billed size.
- `MESUGAK_ANALYSIS_ARCHIVE_DIR`: optional private server directory for original
  latest analysis payloads, overwritten by stock id; at most 5,000 files of
  512 KiB compressed each. Configure it on the school server.
- Historical `strategy_candidates` writes are disabled at the repository.
- Public document responses are cached for 15 minutes in browser sessionStorage;
  simultaneous requests share a promise. This is an optimization, not security
  rate limiting. Admin metadata and holdings queries have 30/200-document limits.
- Heavy history/list fields and the unused candidate/public-feed fields are
  excluded from indexing. Keep indexes used by actual queries.

## Existing cloud data maintenance

`functions/jobs/maintain_cloud_storage.py --mode archive-candidates --limit 5000`
archives and deletes at most 5,000 legacy candidate documents. Daily maintenance
allowances: 15,000 reads, 5,000 deletes, 5,000 writes across all invocations on this
server. Cloud Monitoring rolling-24-hour read/write/delete counts plus planned
operations are checked before the first read and again every 500 documents.
Missing permissions or exhausted thresholds block maintenance. Storage thresholds
do not block cleanup itself. Other clients can still race delayed metrics. There can still be cleanup costs
if other clients consumed the free quota, and storage is billed until reduced.

`--mode compact-analysis --limit 5000` archives original stock documents before
shortening their history; it does not delete stocks, scores, or account data.

Archives are gzip JSONL under `runtime/cloud-archives`, private mode 0600, capped
at 2 GiB. Maintenance stops below 1 GiB free server disk or if this cap is reached.
Each row stores a Firestore Document protobuf in base64. The file is flushed,
fsynced, reopened and verified before changes. A last-update precondition prevents
removal/overwrite of a document changed after backup. Failed commits keep archives.
Archives are not automatically deleted.

To inspect/recover a row with the installed Firestore SDK:

```python
from google.cloud.firestore_v1.types import Document
from google.cloud.firestore_v1 import _helpers
import base64
document = Document.deserialize(base64.b64decode(row['protobuf']))
fields = _helpers.decode_dict(document.fields, db)
# Review destination and write budget before an explicit recovery:
# db.document(row['path']).set(fields)
```

The daily maintenance wrapper drains legacy candidates and compacts existing
stock charts once. Completion markers are written only after an exhausted query;
subsequent runs return locally without Firestore requests.
Current status is recorded locally in `runtime/cost/status.json` and maintenance
progress in `runtime/cost/maintenance.log`.
