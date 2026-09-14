# School Server Paper Trading

## Ownership

The school server is the only process that runs market analysis, accesses the
Korea Investment & Securities (KIS) virtual-investment API, and writes paper
orders. Firebase Hosting and Functions do not hold KIS credentials and do not
run a trading schedule.

## Daily flow

1. After market close, the school server performs the full-universe analysis
   and saves V2 candidates to Firestore.
2. During the next Korean regular session, the school-server trader polls
   Firestore candidates and KIS current prices at a configurable interval.
   It polls only held stocks plus the top-ranked live-candidate limit; it does
   not request a quote for the entire market on every iteration.
3. It evaluates the pure policy, submits virtual orders through KIS, then
   writes executions, positions, and an account snapshot to Firestore.

## Score meaning during the first implementation

`confidenceScore` is the latest completed-market analysis score. It is a
daily score, not a tick-by-tick score. Polling therefore monitors price and
trailing-stop conditions while using the latest saved analysis score for entry,
rotation, and score exits. Intraday re-scoring requires a separate live-bar
pipeline and is intentionally not inferred from a single quote.

## Policy

### Entry

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

### Rotation and proportional profit taking

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

## Safety defaults

- KIS virtual-investment mode only; production mode requires an explicit code
  and environment change.
- `dry_run=true` by default.
- KIS credentials exist only on the school server through a protected
  environment file or a secret manager.
- Token values, app keys, app secrets, and account numbers must never be
  written to Firestore, logs, or source control.

## Server operation

Start one process at 08:50 KST on weekdays. It waits until 09:00, polls every
30 seconds by default, and exits after 15:35. Use a systemd service/timer with
an exclusive process lock rather than spawning overlapping cron loops.

Before the loop starts, the runner checks KIS's domestic-stock holiday feed.
On a non-operating day it exits immediately without polling quotes or creating
orders. The default environment path is `functions/.env`, independent of the
cron working directory; set `MESUGAK_ENV_FILE` only to override it.

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

모든 주문은 KIS 모의투자 시장가(`ORD_DVSN=01`, `ORD_UNPR=0`)로 전송됩니다. 현재 장중 루프는 단일 현재가만 보므로, 분봉 기반 볼린저 상단 재진입/중앙선 이탈 규칙은 별도 분봉 데이터 경로를 추가하기 전에는 적용하지 않습니다.
