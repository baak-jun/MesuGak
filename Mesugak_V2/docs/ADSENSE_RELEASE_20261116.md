# AdSense activation release — 2026-11-16

## Operator-confirmed account state

- The operator confirmed that the required public-data permissions have already
  been obtained.
- Screenshots supplied in the conversation show the European regulations
  message published for `mesu-gak.web.app` and enabled.
- The operator supplied the AdSense publisher ID `ca-pub-5493583869107151` and
  display-unit slot `5445136358`.

The screenshots and the operator's underlying permission records remain with
the operator; this repository does not contain private agreements or account
credentials. This note records the basis for the release request. It is not a
legal opinion or a guarantee of ad fill or revenue.

## Placement and runtime boundary

- The display unit is enabled on the six authored indicator lesson pages only.
- Generated analysis, the watchlist, loading/error states, administrator
  screens, legal pages, navigation, and the learning hub remain ad-free.
- The publisher tag loads through a gated client bootstrap so the published
  Google CMP can run on the site. Each approved lesson slot is pushed after
  the publisher tag loads; Google applies the visitor's regional consent to
  ad serving. Analytics remains separately consent-gated.
- Analysis-page ads and Google Analytics remain disabled.
- `ads.txt` must match the publisher ID and return the expected line at the
  site root after Hosting deployment.

## Deployment scope

- Firebase Hosting target: `mesugak-target` → `mesu-gak`.
- This release deploys Hosting only. It does not deploy Firestore rules,
  Functions, indexes, scheduled jobs, or billing changes.
- The build reads ad settings from the ignored local
  `frontend/.env.production.local`; that file contains only public publisher
  configuration and release flags, not Firebase credentials.

## Release verification — 2026-11-16

- `npm run build`, `npm run lint`, `npm run test:static`, and
  `npm run test:policy` pass. The build's content-quality suite passed all 11
  checks and AdSense preflight found exactly six approved lesson routes.
- Live preflight passed all 25 public routes, the unknown-route 404, robots and
  sitemap checks, metadata, privacy disclosure, and policy/content checks.
- Exactly one slot is prerendered on each of the six indicator lessons; the
  other 19 checked routes have no slot. Analysis-page ads remain disabled.
- `/ads.txt` returns HTTP 200 and its seller line matches the publisher meta
  tag. The publisher script is present in the delivered production bundle.
- The Google CMP preview appeared in the live browser with the three choices
  shown in the account screenshot. No choice was made during verification.
- Google ad creative/fill and earnings are not guaranteed by code deployment;
  they depend on AdSense delivery and eligible demand. The forced CMP preview
  was not accepted or rejected for the operator.
- Firebase CLI printed a stale-credential/update-check warning and exited 1
  after reporting Hosting release complete. The live site and new bundle were
  reachable and passed the independent live preflight, confirming the release.
- No Firestore, Functions, rules, indexes, scheduled jobs, or billing settings
  were deployed or changed.

## Follow-up: analysis CTA and editorial ad placements — 2026-11-16

The prior Hosting release enabled one display slot on the six short indicator
lessons, but it did not include the locally edited, more prominent analysis
button. This follow-up release carries the current CTA to Hosting and places
the same operator-provided responsive display unit in the reading flow:

- Six short indicator lessons: one slot after the lesson and source notes.
- Six long indicator articles: two slots after sections 3 and 7.
- Case studies: two slots after cases 3 and 6.
- Glossary: one slot after its full term list and before the FAQ.
- Total: 21 slots across 14 editorial routes. Hubs, indexes, the interactive
  lab, analysis, admin, loading/error, and policy pages stay ad-free.

The placement count is enforced by the shared route allowlist
`frontend/src/adsensePlacementPolicy.js`. The build and live preflights also
check the home and learning-hub analysis links. The analysis-ad gate and Google
Analytics remain disabled. Only Firebase Hosting is in scope; Firestore,
Functions, rules, indexes, scheduled jobs, and billing are unchanged.

### Follow-up verification

- `npm run build` passed: 25 prerendered pages; editorial-content checks passed
  11/11; the AdSense build preflight found 21 slots on the 14 allowlisted
  routes and zero unexpected placements.
- `npm run test:policy`, `npm run test:static`, `npm run test:adsense`, and
  `npx eslint src scripts` passed. The repository-wide `npm run lint` also
  scanned a stale generated bundle under `frontend/.cache/ui-cta-20261116/`
  and failed on minified third-party code; the changed source and scripts
  passed the targeted lint.
- `firebase deploy --only hosting:mesugak-target --project
  studio-5459225470-8cee2 --non-interactive` reported upload, version
  finalization, release completion, and `Deploy complete!`. The Firebase CLI
  then exited with code 1 after its expired-credential/MOTD update-check
  warnings. The deployed site was independently verified, so no re-login was
  needed for this release.
- `npm run test:live` passed all 25 routes, the expected unknown-route 404,
  publisher/ads.txt consistency, privacy disclosure, content checks, and the
  new homepage and learning-hub analysis CTA checks.
- Live slot counts match the allowlist: 6 short lessons × 1, 6 long articles ×
  2, case studies × 2, glossary × 1. Home, hubs, article index, lab, analysis,
  about, legal, and privacy pages have zero slots. Analysis ads remain off.
- Google Analytics remains off. A deployed slot requests an eligible ad; this
  code check cannot guarantee that Google fills it or that an ad creative is
  visible for every visitor, region, consent state, or visit.
- Firestore, Functions, rules, indexes, jobs, and billing were not deployed or
  changed.
