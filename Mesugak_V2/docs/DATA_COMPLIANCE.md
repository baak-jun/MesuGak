# Data, Ads, and Legal Compliance Notes

Last reviewed: 2026-09-01

This is an engineering/operating note, not legal advice.

## Production data path

- KR symbol metadata and completed daily OHLCV are loaded through the Financial Services Commission `주식시세정보` public API.
- KOSPI/KOSDAQ benchmark history is loaded through the Financial Services Commission `지수시세정보` public API when that API is approved for the service key.
- Valuation and financial reference values are currently omitted from the active public-data route.
- The daily analysis end date is yesterday, so an in-progress current-day candle is not included.
- KIS is used only for the administrator's virtual-account balance, quotes, and orders; it is not the active public-analysis input.

## Public/private boundary

The public `public_analysis_meta` feed is an allowlist, not a redacted copy of
the private record. It contains:

- stock identity and completed analysis date;
- one proprietary aggregate score and a neutral alignment band;
- categorical indicator states, reason codes, and risk flags.

It does not contain OHLC/history, current price, volume, market cap, component
scores, %B, RSI values, relative volume, other numeric indicator inputs,
stop-loss, cash targets, fundamentals, or order-like actions. Public documents
contain 30 rows and a compact manifest/search index. `stock_analysis`,
`meta_data`, account data, charts, and raw measurements remain admin-only.

Filtering and transforming data does not itself create a redistribution
license. Keep the exact public-data API pages, utilization approvals, response
date behavior, and the permitted public-display scope as release evidence.

## Provider findings

The active stock-price and index datasets are provided through the Financial
Services Commission public-data gateway and their portal pages currently show
free use with no listed license restriction. Retain the API utilization
approval and re-check the provider page when the service scope changes; this
engineering note is not a legal opinion.

KIS personal-account access remains limited to the administrator's private
virtual-account workflow and is not used to generate the public analysis feed.

- Financial Services Commission stock prices: https://www.data.go.kr/data/15094808/openapi.do
- Financial Services Commission index prices: https://www.data.go.kr/data/15094807/openapi.do
- KIS provider guide: https://apiportal.koreainvestment.com/provider
- KRX legal notice: https://info.krx.co.kr/contents/KRX/06/06070200/KRX06070200.jsp

Before release, retain a non-secret approval/reference ID in:

```dotenv
VITE_ENABLE_PUBLIC_LIVE_DATA=true
VITE_PUBLIC_DATA_RIGHTS_CONFIRMED=true
VITE_PUBLIC_DATA_RIGHTS_APPROVAL_REFERENCE=internal-record-id
VITE_PUBLIC_DATA_RULES_RELEASE_REFERENCE=release-id
```

## Investment-information posture

- Describe results as automated indicator-condition summaries, not recommended stocks.
- Use neutral bands such as condition alignment/caution, not public buy/sell actions.
- State that scores summarize past/current inputs and do not predict direction or profit.
- Do not provide one-to-one answers, user-specific portfolios, or interactive paid advice.
- The user makes the final investment decision and bears the result.

Korean regulatory classification depends on the actual service, consideration,
interaction, and marketing—not merely a disclaimer or the fact that a score is
proprietary. Obtain Korean counsel before paid subscriptions, paid stock
candidate access, chat/DM interaction, or personalized outputs.

- FSC 2021 interpretation examples: https://www.fsc.go.kr/no010101/75847
- FSC 2024 investor-protection changes: https://www.fsc.go.kr/no010101/82887
- Capital Markets Act Article 101-2: https://law.go.kr/lsLinkCommonInfo.do?chrClsCd=010202&lsJoLnkSeq=1032435905

## AdSense

AdSense support remains in the application, but the browser loads it only when
the public-data gate, legal/policy reference, approved account, exact real
publisher and slot IDs, root ads.txt, and certified-CMP status all pass. The
known example IDs are rejected. The current UI permits separate learning and
optional analysis placements only after their respective content gates pass;
list, empty/error, admin, legal, and navigation screens are ad-free. The
generated-analysis placement can be disabled independently with
`VITE_ENABLE_ANALYSIS_ADS=false`. Ads must be labelled, separated from controls,
and must never be presented as an invitation to click.

- Program policies: https://support.google.com/adsense/answer/48182
- ads.txt: https://support.google.com/adsense/answer/12171612
- CMP requirements: https://support.google.com/adsense/answer/13554116

Advertising revenue alone may be treated differently from direct consideration
for investment advice, but it is not a blanket exemption. Do not tie ad access
or ad removal to personalized recommendations without a fresh legal review.
