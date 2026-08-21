# Data, Ads, and Legal Compliance Notes

Last reviewed: 2026-07-13

This note records the conservative compliance position for Mesugak V2 before public monetization.
It is an engineering checklist and operating note, not a substitute for legal advice.

## Current data paths in the codebase

`functions/strategy_engine/market_data.py` currently loads:

- Korean listings, market capitalization, and OHLCV through `FinanceDataReader.StockListing("KRX")` and `FinanceDataReader.DataReader(...)`.
- Korean financial reference values through `FinanceDataReader.SnapDataReader("NAVER/FINSTATE/{code}")`.
- US universe filters from Wikipedia tables for S&P 500 and Nasdaq-100 constituents.
- Paper-trading balances and executions from Firestore and the operator's KIS mock-investment API integration.

## Official policy findings

### KRX

KRX's legal notice says KRX-provided data and analysis are for information purposes, not trading. It also states that KRX service copyrights and other intellectual-property rights belong to KRX, and that users may not reproduce, transmit, publish, distribute, broadcast, or redistribute KRX services to third parties without prior consent.

Engineering implication:

- Do not assume KRX-origin market data can be publicly redistributed or monetized.
- Before public ad-supported display of KR quotes, charts, market capitalization, or derived screens that effectively re-display exchange data, obtain or confirm the appropriate KRX/Koscom/data-provider permission.

Source: https://info.krx.co.kr/contents/KRX/06/06070200/KRX06070200.jsp

### KIS Developers

KIS Developers' partnership guide says third-party services using KIS OpenAPI should check whether they are partnership targets. For quote APIs, it specifically asks providers to confirm whether they have information-use agreements with KRX and overseas exchanges, and notes that a branded app screen using quote information can be restricted without the required market-data contract.

Engineering implication:

- Token success or API access does not equal permission to redistribute quote data in a public Mesugak screen.
- The KIS paper-trading integration should remain an operator-side/private experiment unless account, order, and quote usage rights are separately confirmed.

Source: https://apiportal.koreainvestment.com/provider-info

### Google AdSense

Google AdSense requires publishers to follow AdSense Program policies and Google Publisher Policies. Relevant points for Mesugak:

- Do not encourage or artificially generate ad clicks.
- Do not make ads indistinguishable from content or navigation.
- Do not monetize content that infringes intellectual-property rights.
- Privacy policy text must disclose Google/third-party advertising cookies and opt-out choices when Google ads are active.

Engineering implication:

- Keep ad containers clearly labeled.
- Do not add actual AdSense code until data rights, privacy policy, and account approval are ready.
- Keep finance claims educational; avoid "guaranteed profit", "recommended buy", or similar framing.

Sources:

- https://support.google.com/adsense/answer/48182
- https://support.google.com/adsense/answer/10502938
- https://support.google.com/adsense/answer/1348695

### Wikipedia/Wikimedia

Wikipedia/Wikimedia content can generally be read and reused under free/open licenses, but reuse carries license and attribution responsibilities. Wikipedia content also does not constitute professional financial advice.

Engineering implication:

- If constituent-list data from Wikipedia is shown or redistributed, include attribution/license handling.
- Using Wikipedia only as a backend universe filter is lower-risk than presenting copied tables as Mesugak-owned content, but public reuse still needs attribution review.

Source: https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use

## Current operating decision

Until data-provider permissions are confirmed:

1. Keep the service framed as "technical-indicator research / education / paper-trading experiment".
2. Do not enable actual AdSense scripts or public ad placeholders.
3. Keep `public_analysis_meta` administrator-only in Firestore rules. A frontend build flag alone is not an access-control mechanism.
4. Keep production public live-data loading disabled. Reopening it requires written data-rights confirmation, a retained approval reference, all three frontend gate values, and a deliberate Firestore-rules deployment.
5. Keep legal links visible:
   - Privacy Policy
   - Terms
   - Disclaimer
   - Data Use Notice
6. Do not market the screen as stock recommendations, profit guarantees, or individualized investment advice.
7. Treat public commercial redistribution of KR/US quote/chart/market-cap data as not yet cleared.

## Public monetization checklist

Before turning on public ads, paid subscriptions, or public user onboarding:

- Confirm KRX/Koscom/KIS and any overseas exchange data-display rights in writing.
- Confirm whether the specific displayed data is delayed, real-time, derived, or redistributable.
- Confirm whether FinanceDataReader's upstream sources allow the intended public/commercial use.
- Add required source attributions for any third-party content.
- Keep `VITE_ENABLE_PUBLIC_LIVE_DATA=false`, `VITE_PUBLIC_DATA_RIGHTS_CONFIRMED=false`, and `VITE_ENABLE_ADSENSE=false` by default.
- Before any public market-derived result is released, retain a written approval reference in `VITE_PUBLIC_DATA_RIGHTS_APPROVAL_REFERENCE`, review the exact permitted scope, and deliberately change the Firestore rule for `public_analysis_meta` in the same release.
- Add `ads.txt` only after AdSense approval and after public data rights, privacy/cookie disclosures, and consent requirements are ready.
- Update the privacy policy with active ad-cookie vendors and opt-out links.
- Review whether paid "candidate" screens could trigger Korean 유사투자자문업, 투자자문업, 투자일임업, or financial-service partnership requirements.


## Public result feed

`public_analysis_meta` is a price-free derived-output feed: it must not contain raw price, OHLC/history, volume, market cap, raw indicator measurements, stop-loss, cash targets, or fundamentals. It is currently locked to administrators at the Firestore rule layer; the private `meta_data` and `stock_analysis` collections are also administrator-only.

`paper_performance_private/latest` contains only an administrator-only aggregate comparison of the operator's KIS virtual-account return with KOSPI/KOSDAQ returns on the same baseline date. It excludes account numbers, positions, trade logs, and raw index levels. It must not be republished as a public performance claim without the same rights and legal review.

Technical filtering reduces exposure but is not a license to redistribute market-data-derived content. Reconfirm source-specific rights before any public release, advertising, subscription, or monetization.