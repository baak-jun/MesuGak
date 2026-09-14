# Public Data and AdSense Release Gate

Status: **disabled by default**. This is an operating control, not legal advice
or a substitute for a data-provider contract.

## What the code enforces

The production build runs `npm run monetization:check` before Vite. It refuses
to build an enabled public-data or AdSense configuration unless every required
environment value is present. The browser also refuses to load the Google ad
script unless the same full set of gates passes.

The deployed Firestore rules expose only direct reads of the explicitly named
`public_meta_v2_KR_{manifest|number}` documents in `public_analysis_meta`.
The writer uses an aggregate-only allowlist; private `meta_data` and
`stock_analysis` remain administrator-only. A reviewed rules deployment is
still required.

## Required evidence before public market-derived analysis

Keep the evidence outside the repository (contract vault or dated internal
record), then put a non-sensitive reference ID in the build environment.

1. Written permission or a written provider determination covering the exact
   sources, markets, territories, delay/realtime status, derived outputs,
   public display, and commercial/ad-supported use.
2. A dated record of the official data.go.kr license page and approved API
   application for the Financial Services Commission stock/index sources.
3. A dated legal/compliance review of the public screens and copy.
4. A reviewed Firestore-rules change that intentionally opens only the approved
   documents and fields.

Required build values after those steps:

```dotenv
VITE_ENABLE_PUBLIC_LIVE_DATA=true
VITE_PUBLIC_DATA_RIGHTS_CONFIRMED=true
VITE_PUBLIC_DATA_RIGHTS_APPROVAL_REFERENCE=internal-record-id
VITE_PUBLIC_DATA_RULES_RELEASE_REFERENCE=change-or-release-id
```

## Additional evidence before AdSense

Do not enable AdSense merely because the technical check passes. All of the
following are required first:

1. The public-data gate above is complete for the exact pages where ads appear.
2. The AdSense account and this site are approved; obtain the real `ca-pub-...`
   client ID and separate numeric ad-unit slot IDs for authored learning pages
   and the optional public-analysis placement.
3. Privacy notice, cookie notice, opt-out/consent flows, and region handling are
   reviewed for the actual audience. For EEA/UK/Switzerland traffic, use a
   Google-certified CMP integrated with the IAB TCF before global serving.
   If using Google's CMP, paste the exact account-specific message script from
   AdSense Privacy & messaging into frontend/index.html; an environment flag
   alone is not a live CMP.
4. Publish the exact root `ads.txt` seller line using the AdSense-provided
   publisher ID and verify it returns HTTP 200 at `/ads.txt`.
5. Keep a dated legal/policy sign-off reference and verify that ads are visibly
   labelled and not placed as navigation or a call to click.

Only then set:

```dotenv
VITE_ENABLE_ADSENSE=true
VITE_ADSENSE_LEGAL_REVIEW_CONFIRMED=true
VITE_ADSENSE_LEGAL_REVIEW_REFERENCE=internal-record-id
VITE_ADSENSE_ACCOUNT_APPROVED=true
VITE_ADSENSE_CLIENT_ID=ca-pub-<real-16-digit-publisher-id>
VITE_ADSENSE_LEARNING_SLOT_ID=<real-numeric-learning-ad-unit-id>
VITE_ADSENSE_ANALYSIS_SLOT_ID=<real-numeric-analysis-ad-unit-id>
VITE_ENABLE_ANALYSIS_ADS=true
VITE_ADSENSE_ADS_TXT_VERIFIED=true
VITE_ADSENSE_CMP_STATUS=certified_cmp_live
```

The application allows only two named placements: one on authored learning
articles and one optional slot after a complete public report. The watchlist,
empty/loading/error states, administrator screens, legal pages, and navigation
remain ad-free. Set `VITE_ENABLE_ANALYSIS_ADS=false` to keep ads on learning
pages while immediately disabling the generated-analysis placement. Set
`VITE_SHOW_AD_PLACEHOLDERS=true` only to preview reserved spaces without
loading Google's ad script; it does not approve or enable ads.

Run the two release checks in this order:

```powershell
npm run ads:txt
npm run monetization:check
npm run build
```

`ads:txt` refuses to write a seller declaration while any gate is incomplete.
Never use a placeholder publisher ID. The created `public/ads.txt` is a public
identifier, not a secret, but it must exactly match the AdSense account.

## Official sources checked

- [KRX legal notice](https://info.krx.co.kr/contents/KRX/06/06070200/KRX06070200.jsp): market-service rights and redistribution restrictions.
- [Financial Services Commission stock prices](https://www.data.go.kr/data/15094808/openapi.do): completed daily stock-price source and license scope.
- [Financial Services Commission index prices](https://www.data.go.kr/data/15094807/openapi.do): completed daily benchmark source and license scope.
- [KIS Developers partnership guide](https://apiportal.koreainvestment.com/provider-info): administrator-only virtual-account use and third-party quote-service boundaries.
- [Google AdSense site connection and ad code](https://support.google.com/adsense/answer/7584263): real client/slot code comes only from the approved account.
- [Google ads.txt guide](https://support.google.com/adsense/answer/12171612): the root seller declaration must use the exact publisher ID.
- [Google publisher CMP requirements](https://support.google.com/adsense/answer/13554116): certified CMP/TCF requirements for EEA, UK, and Switzerland traffic.

Re-check all sources and actual agreements at the time of release because
provider terms and regional regulatory requirements can change.
