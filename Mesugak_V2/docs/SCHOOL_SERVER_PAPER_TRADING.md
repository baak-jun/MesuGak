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
