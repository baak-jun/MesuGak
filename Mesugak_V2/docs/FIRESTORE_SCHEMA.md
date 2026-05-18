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
