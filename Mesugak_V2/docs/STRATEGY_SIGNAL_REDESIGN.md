# Strategy Signal Redesign

## Objective

Score discrete, confirmable long-term buy setups rather than rewarding a stock
merely for being in an established uptrend. Each component has three outcomes:

- bullish setup: positive score;
- bearish failure state: negative score;
- no setup: zero.

No component receives a neutral baseline score.

## Implementation order

1. **Data contract and indicator support**
   - Add 20-day average volume and relative volume.
   - Preserve the plotted Ichimoku cloud while exposing forward-cloud and
     lagging-span confirmation values for scoring.
   - Persist new metrics in analysis payloads and chart history where useful.

2. **Bollinger and MA60 long-term structure**
   - Keep only a 25-day squeeze and a squeeze-to-upper-band breakout as
     positive Bollinger events.
   - Treat a Bollinger lower-band cross above MA60, or sustained lower-band
     support above MA60, as the moving-average bullish structure.
   - Penalize failed upper-band releases, downside expansion, and a lower-band
     fall below MA60.

3. **Ichimoku confirmation**
   - Reward price above the current cloud, Tenkan above Kijun, a bullish
     forward cloud, and Chikou confirmation above price 26 sessions ago.
   - Penalize the inverse conditions; do not score an otherwise neutral cloud.

4. **RSI confirmation and failure signals**
   - Reward a confirmed RSI 50 cross and a recovery from oversold territory
     only when RSI is above its signal line.
   - Penalize an RSI breakdown below 45 and a detected bearish divergence.
   - Do not penalize RSI solely for being high during a strong trend.

5. **Volume confirmation**
   - Reward a 20-session price breakout with relative volume at least 1.5x.
   - Penalize a Bollinger squeeze breakout that lacks average-volume support.

6. **Fundamental value and quality**
   - Use only latest reported, not forecast, financial statements.
   - Score earnings quality, ROE, debt, operating-profit growth, and valuation.
   - Prefer industry-relative PER/PBR when a reliable sector mapping is
     available; retain an explicit fallback state rather than inventing a peer
     comparison.

7. **Decision gates and validation**
   - Require a Bollinger setup plus long-term MA60 structure for a buy label.
   - Require technical confirmation from Ichimoku, RSI, or volume before the
     strongest label.
   - Add deterministic unit tests and a live, Firestore-free Korean dry run.

## Analysis record

- **1. Data contract: complete.** OHLCV already contains volume. The engine now
  derives a 20-session volume average and relative volume. The displayed cloud
  remains time-shifted; separate leading spans are used only for forward-cloud
  scoring.
- **2. Bollinger and MA60: complete.** The 25-session squeeze and its genuine
  upper-band breakout are the only bullish Bollinger states. The lower-band /
  MA60 structure is the only bullish moving-average state.
- **3. Ichimoku: complete.** The score includes current-cloud position,
  Tenkan/Kijun, forward-cloud direction, and a 26-session Chikou comparison.
- **4. RSI: complete.** A 50 cross or oversold recovery needs an RSI signal-line
  confirmation. Breakdown and an approximate 30-session bearish-divergence
  detector are negative states.
- **5. Volume: complete.** A close above the prior 20-session high needs at
  least 1.5x relative volume for a positive confirmation. A squeeze release
  below average volume is negative.
- **6. Value: partial by design.** The KRX listing endpoint currently failed
  during inspection, so no reliable industry mapping is available. Latest
  reported Naver financial statements supply the quality/value inputs; peer
  relative PER/PBR stays explicitly unavailable instead of using an invented
  industry comparison.
- **7. Validation: complete.** The backend suite passes 44 tests and a
  Firestore-free Korean single-stock analysis dry run succeeds.

## Scoring guardrails

- Individual component scores may be negative.
- A missing input yields state `NO_DATA` and score zero; it does not become a
  bullish neutral score.
- The frontend must surface signed component scores and the exact reasons.
- A score is a screening aid, not a trade instruction or return forecast.
