# School Server Paper Trading

> Historical implementation notes. Current contest/site separation, effective settings, and observed cloud remnants are documented in [운영 인수인계](operations/README.md). In particular, the statement below that Functions hold no KIS credentials is not confirmed-current: an older cloud function still has credential environment variables. Do not copy their values into documentation.

## Ownership

The school server is the only process that runs market analysis, accesses the
Korea Investment & Securities (KIS) virtual-investment API, and writes paper
orders. Firebase Hosting and Functions do not hold KIS credentials and do not
run a trading schedule.

## Daily flow

As of 2026-10-12 the operator requests contest priority. The p102 weekday
09:05 site-linked trader is paused; its crontab line remains commented for
restoration after the contest. The shared KOSPI/KOSDAQ analysis and contest
runner remain active.

The complete scored universe is published atomically to
`runtime/checkpoints/realtime_candidates_KR.json` on the school server.
The contest runner reads this snapshot rather than the Firebase top-200 feed.
Firebase persistence retains its existing 200-symbol cap. Alphanumeric
six-character share codes are included alongside numeric codes.

The realtime watch set reserves approximately 10% of its slots for random
exploration; the remainder keeps holdings/pending orders first and then the
highest daily scores. At 39 symbols this is 35 core slots plus 4 explorers;
at 20 symbols it is 18 plus 2. Exploration draws without replacement until
the remaining pool has been visited, then reshuffles. The default cycle is
60 seconds, and unsubscribed quote history is discarded to bound memory.

The WebSocket budget is 40 subscriptions including the virtual-account
fill-notice channel, so execution watches at most 39 price symbols. A provider
limit rejection halves the price watch budget before reconnecting, while
protecting holdings/pending orders. REST requests are serialized with an
initial two-second interval; explicit `EGW00201`, `EGW00215`, and HTTP 429 rejections increase the
interval and permit bounded retries. Ambiguous order network failures are
never retried automatically and pause new entries until reconciliation.
Token caches are keyed and validated by API key so site and contest credentials
cannot reuse each other's access token.

In the p102 connectivity check on 2026-10-12, port 31000 closed the HTTP
handshake. The operator's existing virtual-account approval was accepted for
both `H0STCNT0` and `H0STCNI9` on
`ws://ops.koreainvestment.com:21000/tryitout`, configured only in the protected
contest environment. REST orders remain restricted to the virtual-investment
host. Verify both subscriptions before using an alternative WebSocket route.

Official examples: [frame layout and ping echo](https://github.com/koreainvestment/open-trading-api/blob/main/legacy/websocket/python/ops_ws_sample.py),
[40-subscription budget](https://github.com/koreainvestment/open-trading-api/blob/main/backtester/kis_backtest/providers/kis/websocket.py).

1. After market close, the school server performs the full-universe analysis
   and saves V2 candidates to Firestore.
2. During the next Korean regular session, `jobs/kis_realtime_trader.py`
   subscribes to KIS `H0STCNT0` trade ticks for a bounded watch list. The list
   is refreshed from KIS fluctuation rankings every 60 seconds, while held
   symbols remain subscribed first. It does not request a REST quote for every
   symbol on every tick.
3. It evaluates the pure realtime policy, writes periodic runtime heartbeats
   to Firestore, and keeps order idempotency/reconciliation state in a local
   SQLite WAL file. KIS order submission is opt-in with `--execute`; the
   default is dry-run.

The stream still records the latest tick needed for one-second replay bars,
but policy evaluation is throttled to at most four evaluations per symbol per
second and the in-memory history is bounded. This prevents a high-volume
symbol from turning every provider tick into a Python/Firestore operation.

## Score meaning during the first implementation

`confidenceScore` is the latest completed-market analysis score. It is a
daily score, not a tick-by-tick score. Polling therefore monitors price and
trailing-stop conditions while using the latest saved analysis score for entry,
rotation, and score exits. Intraday re-scoring requires a separate live-bar
pipeline and is intentionally not inferred from a single quote. The realtime
runner combines that daily score with short-window return, trade value, volume
acceleration, VWAP, breakout, and spread guards.

## Policy

### Poller entry (legacy one-shot compatibility path)

- A candidate must have `BUY_CANDIDATE` or `STRONG_BUY`, no defensive risk
  state, and score at least `buy_score_min`.
- Each new position targets 10% of current total equity by default.
- Do not buy a symbol already held or already pending an order.

### Exit

Exit an entire position when either condition is met:

- latest analysis score is at or below `score_exit_threshold` (negative by
  default); or
- current price is at least `trailing_stop_pct` below the highest price seen
  since purchase.

The server updates each position's high-water mark from every successful quote
poll before evaluating the trailing stop.

### Realtime entry

- The daily gate remains `BUY_CANDIDATE`/`STRONG_BUY`, score at least 60, no
  defensive risk, price at least 1,000 KRW, prior turnover at least 5 billion
  KRW, and market cap at least 50 billion KRW.
- In the first minute, require a 10-second return of at least 0.8% and
  10-second trade value of at least 300 million KRW. Later, require 10/30/60
  second returns of 0.4%/0.8%/1--4%, 30-second trade value of at least 1
  billion KRW, two-times volume acceleration, and a 60-second breakout.
- Reject spreads above 0.3%, prices more than 3% above the 60-second VWAP,
  and a symbol until two positive evaluations confirm the signal.
- Entries use a KIS limit order at the current best ask. An accepted limit is
  cancelled after two seconds and repriced at most once; exits use a market
  order. A lost response is reconciled against the local SQLite order state
  and KIS daily-order inquiry before another signal is allowed.

### Realtime exit and session rules

The realtime runner updates the high-water mark from every tick. Same-day stop
loss is 3%, trailing stop is 6%, profit lock activates at +3% and trails by 2%,
and a 10-second return of -0.8% below VWAP is a momentum-reversal exit. A
symbol exited during the session is blocked from same-day re-entry. New
entries stop at 15:15; a position is held overnight only when it is profitable,
above VWAP, still has a positive 30-second trend, and retains a qualifying
daily score.

The runner has no P&L-based daily halt or global daily entry-count cap by
design for the university contest profile. It does enforce the configured
maximum of five concurrent positions and a 20% target weight per position.

### Poller rotation and proportional profit taking (legacy)

When a higher-scored candidate needs capital:

1. Sell a held negative-score position first.
2. Otherwise, a lower-scored position at or below the negative exit threshold
   is sold in full to fund the new entry.
3. If no whole position is eligible, all holdings are non-loss-making, and the
   candidate still exceeds the weakest score by the same gap, sell `1 / n` of
   each of the `n` holdings. This realizes gains across the portfolio while
   retaining every position, and funds one new target-sized entry.

No order is created if live prices are unavailable, the market is closed, or a
KIS order for the same symbol and side is already pending.

The realtime contest runner does not force a score-based proportional
rotation on every refresh; it keeps the daily gate stable and uses the
explicit realtime exit rules above. This avoids turning a temporary ranking
refresh into a burst of replacement orders.

## Safety defaults

- KIS virtual-investment mode only; production mode requires an explicit code
  and environment change.
- `dry_run=true` by default.
- KIS credentials exist only on the school server through a protected
  environment file or a secret manager.
- Token values, app keys, app secrets, and account numbers must never be
  written to Firestore, logs, or source control.

## Server operation

Start one process at 08:50 KST on weekdays. It waits until 09:00, keeps one
WebSocket connection through 15:35, and refreshes the watch list every 60
seconds. Use a systemd service with an exclusive process lock rather than
spawning overlapping cron loops. A REST poller remains available for
compatibility, but it is not the all-day contest path.

Before the loop starts, the runner checks KIS's domestic-stock holiday feed.
On a non-operating day it exits immediately without polling quotes or creating
orders. The direct Python runner defaults to `functions/.env`; the managed
`run_kis_realtime_trader.sh` wrapper prefers `functions/.env.contest` when it
exists. Set `MESUGAK_ENV_FILE` to override either default.

### Realtime runner commands

```bash
# Credentialed validation: no order endpoint is called.
python Mesugak_V2/functions/jobs/kis_realtime_trader.py \
  --env-file Mesugak_V2/functions/.env.contest

# Offline policy replay (JSONL or JSONL.GZ; no KIS or Firestore access).
python Mesugak_V2/functions/jobs/kis_realtime_trader.py \
  --replay runtime/realtime_bars/realtime_2026-09-23.jsonl.gz \
  --candidates runtime/candidates.json

# Explicit virtual-order mode, only after replay and dry-run acceptance.
python Mesugak_V2/functions/jobs/kis_realtime_trader.py \
  --env-file Mesugak_V2/functions/.env.contest --execute
```

`--execute` requires `KIS_PAPER_HTS_ID` so the `H0STCNI9` fill-notice
subscription can reconcile accepted, partial, filled, and rejected orders. The
runner pauses new entries when the holiday check, watch refresh, account sync,
WebSocket, or order reconciliation is uncertain; it does not guess through an
operational failure.

## On-demand account refresh from the web

The **모의투자 새로고침** button does not call KIS from the browser. An
administrator-authenticated browser creates a `paper_refresh_requests` document;
the school server reads it, calls only KIS `inquire-balance`, writes the fresh
`bot_account_snapshot` and `bot_portfolio` values, then marks the request
`completed` or `failed`.

This path does **not** load strategy candidates, request per-symbol quotes,
create paper orders, or submit trades.

Install the managed worker and process waiting requests once per minute while
the site is normally used (server timezone: Asia/Seoul):

```bash
chmod 755 ~/mesugak/repo/Mesugak_V2/server_runtime/run_paper_refresh_requests.sh
```

```cron
* 8-18 * * 1-5 /usr/bin/flock -n /tmp/mesugak-paper-refresh.lock /home/USER/mesugak/repo/Mesugak_V2/server_runtime/run_paper_refresh_requests.sh >> /home/USER/mesugak/logs/paper_refresh_$(date +\%Y-\%m).log 2>&1
```

With that cron entry, a clicked refresh is normally processed within one minute.
If it is outside the worker window, the button remains pending until the next
worker run; no order is ever created by the request itself.

### Administrator setup

Firestore rules intentionally grant private account reads and refresh-request
creation only when `admins/{Google-login-email}` exists. Create that document
once in the Firebase Console with any non-sensitive field such as
`enabled: true`. Do not use a user-editable `users/{uid}.role` field to grant
this privilege.
## 당일 재진입과 빠른 하락 보호

- `MESUGAK_BLOCK_REENTRY_AFTER_EXIT=true`이면 `trailing_stop`, `profit_lock_trailing_stop`, 점수 청산 또는 회전 청산으로 **체결된 종목은 당일 재매수하지 않습니다**. 서버 재시작 뒤에도 `intraday_trade_state`에 잠금이 보존됩니다.
- `MESUGAK_PROFIT_LOCK_ACTIVATE_PCT=0.03`: 매수 후 고점이 3% 이상일 때 이익보호를 활성화합니다.
- `MESUGAK_PROFIT_LOCK_TRAILING_PCT=0.02`: 활성화 뒤 고점에서 2% 되밀리면 청산 후보가 됩니다.
- `MESUGAK_PROFIT_LOCK_MIN_PNL_PCT=0.005`: 실제 청산 시점에도 최소 0.5% 이익이 남을 때만 이 규칙으로 청산합니다.
- `MESUGAK_SAME_DAY_STOP_LOSS_PCT=0.03`: 당일 새로 매수한 종목의 실시간 호가가 평균 매수가보다 3% 이상 내려가면 전량 시장가 매도합니다. 이 사유로 매도된 종목은 당일 재진입하지 않습니다.

기존 `school_paper_trader.py` 호환 폴러는 시장가 주문을 사용하지만, 대회용
`kis_realtime_trader.py`는 진입 지정가(`ORD_DVSN=00`)와 청산 시장가
(`ORD_DVSN=01`)를 분리합니다. 실시간 정책은 순수 함수로 분리되어 있어
동일한 규칙을 JSONL/압축 JSONL 리플레이에서 먼저 검증할 수 있습니다.
