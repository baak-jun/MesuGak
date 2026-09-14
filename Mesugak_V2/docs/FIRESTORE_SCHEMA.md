# Firestore Schema

## `stock_analysis/{MARKET}_{CODE}`

Detailed stock analysis document.

- `id`
- `code`
- `name`
- `market`
- `currentPrice`
- `volume`
- `marcap`
- `lastDate`
- `type`
- `status`
- `confidenceScore`
- `confidenceLabel`
- `componentScores`
- `riskFlags`
- `signal`
- `targetWeight`
- `stopLoss`
- `cashTargetPct`
- `confidenceReasons`
- `fundamentals`: optional reference-only fundamental inputs and source metadata; never used in confidence scoring
- `history`
- `updatedAt`

## `meta_data/meta_{MARKET}_{N}`

Chunked list data for fast frontend loading.

- `market`
- `updatedAt`
- `list[]`

Each list item should include fields needed for sorting and filtering:

- `id`
- `code`
- `name`
- `market`
- `currentPrice`
- `confidenceScore`
- `confidenceLabel`
- `riskState`
- `targetWeight`
- `stopLoss`
- `type`
- `status`

## New Strategy Collections

- `strategy_runs/{runId}`: run metadata and parameters.
- `strategy_candidates/{runId}_{MARKET}_{CODE}`: legacy run snapshots. The
  active daily analysis does not write these because `stock_analysis` already
  stores the detailed score reasons and history.
- `target_allocations/{MARKET}_{DATE}`: cash target and per-stock target weights.
- `rebalance_orders/{MARKET}_{DATE}_{CODE}`: staged buy/sell/hold decisions.
- `risk_state/{MARKET}`: current defensive mode and cash ratio.
- `paper_order_applications/{allocationId}`: audit record for applied paper orders.

## `rebalance_orders/{MARKET}_{DATE}_{CODE}`

- `market`
- `allocationId`
- `code`
- `name`
- `side`: `BUY`, `SELL`, or `HOLD`
- `targetWeight`
- `currentWeight`
- `targetAmount`
- `tradeAmount`
- `reason`
- `updatedAt`

## Existing Bot Collections

- `bot_portfolio`
- `bot_trade_logs`
- `bot_account_snapshot/latest`
- `paper_trading_runtime/latest`
- `paper_trading_runtime_events`

## `paper_order_applications/{allocationId}`

- `market`
- `allocationId`
- `orderCount`
- `executedCount`
- `missingPriceCodes[]`
- `snapshot`
- `logs[]`
- `updatedAt`

## `bot_portfolio/{CODE}`

V2 paper ledger writes V1-compatible positions here.

- `code`
- `name`
- `quantity`
- `buyPrice`
- `highestPrice`
- `lastPrice`
- `market`
- `signalType`: `v2_paper`
- `boughtAt`
- `updatedAt`

## `bot_trade_logs/{autoId}`

V2 paper ledger appends executions here.

- `source`: `Mesugak_V2`
- `market`
- `action`: `BUY` or `SELL`
- `code`
- `name`
- `price`
- `quantity`
- `amount`
- `pnl`
- `pnlPct`
- `reason`
- `orderStatus`: `ACCEPTED`, `FAILED`, or execution status for manual/KIS orders
- `brokerOrderNo`: KIS virtual-account order number when accepted
- `errorMessage`: failure detail when a manual/KIS order is rejected
- `createdAt`: Firestore server timestamp; the administrator UI renders it as
  `YYYY-MM-DD HH:mm` in Asia/Seoul time.

## `bot_account_snapshot/latest`

V2 paper ledger writes the latest account state here.

- `mode`: `paper`
- `source`: `Mesugak_V2`
- `market`
- `cash`
- `initialCash`
- `holdingCount`
- `totalEvalAmt`
- `totalBuyAmt`
- `totalEquity`
- `realizedPnl`
- `unrealizedPnl`
- `totalPnl`
- `returnPct`
- `holdings[]`
- `appliedAllocationIds[]`
- `lastAppliedAllocationId`
- `updatedAt`

## `paper_refresh_requests/{autoId}`

Authenticated administrator request created by the web UI when a current KIS
virtual-account snapshot is needed. The school server consumes it and writes
only the completion state; it never exposes KIS credentials to the browser.

- `status`: `pending`, `completed`, or `failed`
- `market`: currently `KR`
- `requestedAt`
- `requestedByUid`
- `source`: `web`
- `holdingCount`, `accountSynced`: completed-request metadata
- `errorCode`, `errorMessage`: failure metadata for the administrator only
- `updatedAt`

The fresh account state remains in `bot_account_snapshot/latest` and
`bot_portfolio/{CODE}`. Both are admin-only reads.
## `public_analysis_meta/public_meta_v2_{MARKET}_{N}`

Sanitized aggregate-only analysis feed. Anonymous direct reads are allowed only
for the explicitly named `public_meta_v2_KR_{manifest|number}` documents;
all other analysis collections and document IDs remain administrator-only.

- `market`, `strategyVersion`, `pageIndex`, `pageSize`, `updatedAt`, `list[]`
- Each item includes identity, analysis date, one proprietary aggregate score/band, interpretation reasons, indicator state names, and risk flags.
- It intentionally excludes OHLC/history, current price, volume, market cap, stop-loss, cash target, numeric indicator metrics, and fundamentals.

Public result documents contain 30 items each. `public_meta_v2_{MARKET}_manifest`
contains `totalCount`, `chunkCount`, `pageSize`, and a compact
map-based `{code, name, page}` search index so the browser fetches only pages
needed for initial display, pagination, or search.

## `paper_performance_private/latest`

Administrator-only aggregate comparison for the operator's KIS virtual-account experiment. This document is never readable by anonymous or ordinary authenticated users.

- `visibility`: always `admin_only`
- `baselineDate`, `initialCash`, `totalEquity`, `totalPnl`, `returnPct`, `holdingCount`
- `benchmarks.KOSPI` and `benchmarks.KOSDAQ`: cumulative return, same-baseline gap in percentage points, baseline/as-of dates, and source label
- `benchmarkStatus`, `benchmarkErrors`, `methodology`, `updatedAt`

It deliberately excludes KIS account numbers, token/credential values, holdings, order history, and raw KOSPI/KOSDAQ index levels.

## `paper_trading_runtime/latest`

School-server intraday paper trader writes the latest loop status here so the UI can show monitored stocks even when no order is executed.

- `source`: `Mesugak_V2`
- `mode`: `school_server_paper`
- `status`: `dry_run`, `applied`, `account_sync_failed`, or loop status
- `market`
- `execute`
- `candidateCount`
- `monitoredCount`
- `buyWatchCount`
- `holdingCount`
- `orderCount`
- `quoteErrorCount`
- `accountSynced`
- `cash`
- `totalEquity`
- `policy`
- `monitored[]`: top live candidates quoted by the intraday trader
- `buyWatch[]`: candidates currently eligible for buying
- `holdingsWatch[]`: held stocks watched for sell/rotation rules
- `orders[]`: proposed orders for this loop
- `quoteErrors`
- `checkedAt`
- `updatedAt`

## `paper_trading_runtime_events/{autoId}`

Append-only copy of each intraday runtime loop. This is useful for auditing why the trader watched, bought, skipped, or sold a stock during the session.

Fields match `paper_trading_runtime/latest`, with `createdAt` instead of only `updatedAt`.
