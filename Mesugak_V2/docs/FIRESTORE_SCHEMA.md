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
- `fundamentals`: latest reported fundamental inputs and source metadata, when available
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
- `strategy_candidates/{runId}_{MARKET}_{CODE}`: detailed score reasons.
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
- `createdAt`

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
