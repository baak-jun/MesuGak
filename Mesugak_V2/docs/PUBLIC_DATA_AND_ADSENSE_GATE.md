# Public Data and AdSense Release Gate

Status: **disabled by default**. This is an operating control, not legal advice
or a substitute for a data-provider contract.

## What the code enforces

The production build runs `npm run monetization:check` before Vite. It refuses
to build an enabled public-data or AdSense configuration unless every required
environment value is present. The browser also refuses to load the Google ad
script unless the same full set of gates passes.

The deployed Firestore rules are an additional boundary: `public_analysis_meta`
is administrator-only today. Turning an environment variable on cannot make the
feed public. A reviewed rules deployment is required separately.

## Required evidence before public market-derived analysis

Keep the evidence outside the repository (contract vault or dated internal
record), then put a non-sensitive reference ID in the build environment.

1. Written permission or a written provider determination covering the exact
   sources, markets, territories, delay/realtime status, derived outputs,
   public display, and commercial/ad-supported use.
2. An upstream-source check for every FinanceDataReader path used in production.
   A library installation does not itself grant redistribution rights.
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
   client ID and numeric ad-unit slot ID from AdSense.
3. Privacy notice, cookie notice, opt-out/consent flows, and region handling are
   reviewed for the actual audience. For EEA/UK/Switzerland traffic, use a
   Google-certified CMP integrated with the IAB TCF before global serving.
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
VITE_ADSENSE_CLIENT_ID=ca-pub-0000000000000000
VITE_ADSENSE_PUBLIC_SLOT_ID=0000000000
VITE_ADSENSE_ADS_TXT_VERIFIED=true
VITE_ADSENSE_CMP_STATUS=certified_cmp_live
```

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
- [KIS Developers partnership guide](https://apiportal.koreainvestment.com/provider-info): third-party quote-service use and exchange information-use agreements.
- [Google AdSense site connection and ad code](https://support.google.com/adsense/answer/7584263): real client/slot code comes only from the approved account.
- [Google ads.txt guide](https://support.google.com/adsense/answer/12171612): the root seller declaration must use the exact publisher ID.
- [Google publisher CMP requirements](https://support.google.com/adsense/answer/13554116): certified CMP/TCF requirements for EEA, UK, and Switzerland traffic.

Re-check all sources and actual agreements at the time of release because
provider terms and regional regulatory requirements can change.