import { adsenseSlotCountByRoute } from '../src/adsensePlacementPolicy.js';

/*
 * Read-only production-site check for the AdSense review checklist.
 * It never logs in, changes Hosting, reads Firebase, or enables advertising.
 * The result is evidence about the deployed HTML, not a claim that Google
 * will approve the site.
 */

const baseUrl = String(process.env.MESUGAK_SITE_URL || 'https://mesu-gak.web.app')
  .trim()
  .replace(/\/+$/, '');
const timeoutMs = Math.max(1000, Number(process.env.MESUGAK_LIVE_TIMEOUT_MS || 15000));
const expectAdsDisabled = String(process.env.MESUGAK_EXPECT_ADS_DISABLED || 'true').toLowerCase() !== 'false';
const expectAnalyticsDisabled = String(process.env.MESUGAK_EXPECT_ANALYTICS_DISABLED || 'true').toLowerCase() !== 'false';
const authoredRoutes = [
  '/',
  '/learn',
  '/learn/articles',
  '/learn/articles/ichimoku',
  '/learn/articles/bollinger',
  '/learn/articles/moving-average',
  '/learn/articles/rsi',
  '/learn/articles/volume',
  '/learn/articles/valuation',
  '/learn/ichimoku',
  '/learn/bollinger',
  '/learn/moving-average',
  '/learn/rsi',
  '/learn/volume',
  '/learn/valuation',
  '/learn/cases',
  '/learn/lab',
  '/learn/glossary',
  '/methodology',
  '/about',
  '/terms',
  '/privacy',
  '/data',
  '/disclaimer',
];
const routes = [...authoredRoutes, '/analysis'];
function absoluteUrl(path) {
  return new URL(path, `${baseUrl}/`).toString();
}

async function fetchText(path) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(absoluteUrl(path), {
      redirect: 'follow',
      signal: controller.signal,
      headers: { 'user-agent': 'MesuGak-AdSense-Preflight/1.0' },
    });
    return {
      path,
      status: response.status,
      finalUrl: response.url,
      text: await response.text(),
    };
  } finally {
    clearTimeout(timeout);
  }
}

function visibleText(html) {
  return html
    .replace(/<script[\s\S]*?<\/script>/gi, ' ')
    .replace(/<style[\s\S]*?<\/style>/gi, ' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function addFailure(failures, message) {
  failures.push(message);
}

const failures = [];
const results = [];
const htmlByRoute = new Map();
let rootHtml = '';
for (const route of routes) {
  try {
    const result = await fetchText(route);
    const html = result.text;
    htmlByRoute.set(route, html);
    if (route === '/') rootHtml = html;
    const title = html.match(/<title>([^<]+)<\/title>/i)?.[1]?.trim() || '';
    const heading = html.match(/<h1[^>]*>([\s\S]*?)<\/h1>/i)?.[1]?.trim() || '';
    const description = html.match(/<meta name="description" content="([^"]+)"/i)?.[1] || '';
    const canonical = html.match(/<link rel="canonical" href="([^"]+)"/i)?.[1] || '';
    const noindex = /<meta name="robots" content="noindex,follow"/i.test(html);
    const adSlots = html.match(/<ins\b[^>]*class="[^"]*\badsbygoogle\b[^"]*"[^>]*>/gi) || [];
    const staticAdMarkup = adSlots.length > 0 || /<script[^>]+adsbygoogle|adsbygoogle\.js\?client/i.test(html);
    const textLength = visibleText(html).length;

    if (result.status !== 200) addFailure(failures, `${route}: HTTP ${result.status}`);
    if (title.length < 8 || heading.length < 4 || description.length < 30) addFailure(failures, `${route}: incomplete metadata`);
    if (!canonical.startsWith(`${baseUrl}/`)) addFailure(failures, `${route}: canonical is outside ${baseUrl}`);
    if (!/<meta property="og:site_name" content="기술지표분석교실" \/>/i.test(html)) addFailure(failures, `${route}: Open Graph site name is missing`);
    if (!/<meta property="og:locale" content="ko_KR" \/>/i.test(html)) addFailure(failures, `${route}: Korean Open Graph locale is missing`);
    if (!/<meta name="twitter:card" content="summary" \/>/i.test(html)) addFailure(failures, `${route}: Twitter card metadata is missing`);
    if (route === '/analysis' && !noindex) addFailure(failures, '/analysis: noindex,follow is missing');
    if (route !== '/analysis' && noindex) addFailure(failures, `${route}: authored page is unexpectedly noindex`);
    if (route !== '/analysis' && textLength < 600) addFailure(failures, `${route}: body is below internal content floor`);
    const expectedSlotCount = !expectAdsDisabled ? adsenseSlotCountByRoute[route] || 0 : 0;
    if (adSlots.length !== expectedSlotCount) {
      addFailure(failures, `${route}: expected ${expectedSlotCount} AdSense slot(s), received ${adSlots.length}`);
    }
    if (/<script[^>]+adsbygoogle|adsbygoogle\.js\?client/i.test(html)) {
      addFailure(failures, `${route}: AdSense publisher requests must be created by the gated client bootstrap`);
    }
    if (/\uFFFD/.test(html)) addFailure(failures, `${route}: replacement character leaked into HTML`);

    results.push({ route, status: result.status, textLength, noindex, adSlots: adSlots.length, staticAdMarkup });
  } catch (error) {
    addFailure(failures, `${route}: ${error.name || 'fetch_error'} ${error.message || error}`);
  }
}

let notFoundStatus = null;
try {
  const notFoundResult = await fetchText('/__mesugak_live_preflight_not_found__');
  notFoundStatus = notFoundResult.status;
  if (notFoundStatus !== 404) addFailure(failures, `unknown route: expected HTTP 404, received ${notFoundStatus}`);
} catch (error) {
  addFailure(failures, `unknown route: ${error.name || 'fetch_error'} ${error.message || error}`);
}

let adsTxtPublisherId = '';
let metaPublisherId = '';
let robotsText = '';
let sitemapXml = '';
for (const [path, required] of [
  ['/ads.txt', 'google.com,'],
  ['/robots.txt', 'Sitemap: https://mesu-gak.web.app/sitemap.xml'],
  ['/sitemap.xml', '<loc>https://mesu-gak.web.app/learn/glossary</loc>'],
]) {
  try {
    const result = await fetchText(path);
    if (result.status !== 200) addFailure(failures, `${path}: HTTP ${result.status}`);
    if (!result.text.includes(required)) addFailure(failures, `${path}: required marker is missing`);
    if (path === '/ads.txt') {
      adsTxtPublisherId = result.text.match(/google\.com,\s*(pub-\d{10,20}),\s*DIRECT,/i)?.[1] || '';
      if (!adsTxtPublisherId) addFailure(failures, '/ads.txt: Google seller line has no numeric publisher ID');
    }
    if (path === '/robots.txt') robotsText = result.text;
    if (path === '/sitemap.xml' && /\/analysis(?:<|\/)/i.test(result.text)) addFailure(failures, '/sitemap.xml: analysis route is indexed');
    if (path === '/sitemap.xml') sitemapXml = result.text;
  } catch (error) {
    addFailure(failures, `${path}: ${error.name || 'fetch_error'} ${error.message || error}`);
  }
}

const robotLines = new Set(robotsText.split(/\r?\n/).map((line) => line.trim()));
if (!robotLines.has('User-agent: *') || !robotLines.has('Allow: /') || !robotLines.has('Sitemap: https://mesu-gak.web.app/sitemap.xml')) {
  addFailure(failures, '/robots.txt: public crawling or the sitemap reference is missing');
}

const sitemapUrls = [...sitemapXml.matchAll(/<loc>([^<]+)<\/loc>/gi)].map((match) => match[1].trim());
const expectedSitemapUrls = authoredRoutes.map(absoluteUrl);
const sitemapUrlSet = new Set(sitemapUrls);
const missingSitemapUrls = expectedSitemapUrls.filter((url) => !sitemapUrlSet.has(url));
const unexpectedSitemapUrls = sitemapUrls.filter((url) => !expectedSitemapUrls.includes(url));
if (sitemapUrls.length !== sitemapUrlSet.size || missingSitemapUrls.length || unexpectedSitemapUrls.length) {
  addFailure(
    failures,
    `/sitemap.xml: route set differs from authored public routes (missing ${missingSitemapUrls.length}, unexpected ${unexpectedSitemapUrls.length}, duplicates ${sitemapUrls.length - sitemapUrlSet.size})`,
  );
}

metaPublisherId = rootHtml.match(/name="google-adsense-account"\s+content="(ca-pub-\d{10,20})"/i)?.[1] || '';
if (metaPublisherId && adsTxtPublisherId && metaPublisherId !== `ca-${adsTxtPublisherId}`) {
  addFailure(failures, `root publisher meta ${metaPublisherId} does not match ads.txt ${adsTxtPublisherId}`);
}
const searchConsoleVerificationMetaCount = (rootHtml.match(/name="google-site-verification"/gi) || []).length;
if (searchConsoleVerificationMetaCount !== 1) {
  addFailure(failures, `root Search Console verification marker count is ${searchConsoleVerificationMetaCount}; expected 1`);
}

const privacyHtml = htmlByRoute.get('/privacy') || '';
const homeHtml = htmlByRoute.get('/') || '';
const learnHtml = htmlByRoute.get('/learn') || '';
const methodologyHtml = htmlByRoute.get('/methodology') || '';
const casesHtml = htmlByRoute.get('/learn/cases') || '';
if (!homeHtml.includes('home-purpose-title')) addFailure(failures, '/: unique service-purpose content is missing');
if (!homeHtml.includes('종목 분석 결과 보기')) addFailure(failures, '/: prominent stock-analysis link is missing');
if (!learnHtml.includes('learning-guides-title')) addFailure(failures, '/learn: curriculum content is missing');
if (!learnHtml.includes('분석된 종목 보러 가기')) addFailure(failures, '/learn: prominent stock-analysis link is missing');
if (homeHtml.includes('learning-guides-title')) addFailure(failures, '/: learning hub content is duplicated on the root route');
const adsDisabledText = privacyHtml.includes('AdSense 요청은 현재 비활성화되어 광고 요청을 보내지 않습니다.');
const adsEnabledText = privacyHtml.includes('AdSense 요청 게이트가 켜져 있습니다.');
const analyticsLoaderAbsent = !/googletagmanager\.com\/gtag\/js|google-analytics\.com\/analytics\.js/i.test(privacyHtml);
if (expectAdsDisabled && !adsDisabledText) addFailure(failures, '/privacy: disabled AdSense runtime status is missing');
if (!expectAdsDisabled && !adsEnabledText) addFailure(failures, '/privacy: enabled AdSense runtime status is missing');
if (expectAnalyticsDisabled && !analyticsLoaderAbsent) addFailure(failures, '/privacy: Analytics loader is present while consent/configuration is disabled');

const legalRoutes = ['/terms', '/privacy', '/data', '/disclaimer'];
const legalDatesAreUpdates = legalRoutes.every((route) => {
  const html = htmlByRoute.get(route) || '';
  return html.includes('문서 수정일: 2026-10-01') && !html.includes('마지막 검토일');
});
const currentEditorialCopy = methodologyHtml.includes('2026-10-01')
  && methodologyHtml.includes('결측 처리')
  && /콘텐츠 안내 수정일\s+20\d{2}-\d{2}-\d{2}/.test(casesHtml)
  && (casesHtml.match(/class="case-study-visual"/g) || []).length === 8
  && (casesHtml.match(/class="case-study-caution"/g) || []).length === 8;
const unsupportedClaimsAbsent = !routes
  .map((route) => htmlByRoute.get(route) || '')
  .join('\n')
  .match(/운영자가[\s\S]{0,160}?(?:만들|작성|검토|편집|수정)|직접 만든[\s\S]{0,40}(?:그림|도식|예시)|3분(?: 간격|마다)|학교 서버 중단|서버 감시 상태|마지막 검토일/);
if (!legalDatesAreUpdates) addFailure(failures, 'legal pages: an update date still claims a completed legal review or is stale');
if (!currentEditorialCopy) addFailure(failures, 'editorial pages: the current methodology and case-study copy is missing');
if (!unsupportedClaimsAbsent) addFailure(failures, 'public pages: an unsupported authorship, review, or polling claim remains');

const report = {
  baseUrl,
  checkedRoutes: results.length,
  authoredRoutes: authoredRoutes.length,
  unknownRouteStatus: notFoundStatus,
  searchConsoleVerificationMetaPresent: searchConsoleVerificationMetaCount === 1,
  publisherMeta: metaPublisherId || null,
  adsTxtPublisher: adsTxtPublisherId || null,
  publisherSelfConsistency: Boolean(metaPublisherId && adsTxtPublisherId && metaPublisherId === `ca-${adsTxtPublisherId}`),
  expectedAdsDisabled: expectAdsDisabled,
  expectedAnalyticsDisabled: expectAnalyticsDisabled,
  adSlotCounts: Object.fromEntries(results.filter((result) => result.adSlots > 0).map((result) => [result.route, result.adSlots])),
  privacyRuntimeChecks: { adsDisabledText, adsEnabledText, analyticsLoaderAbsent },
  editorialChecks: { legalDatesAreUpdates, currentEditorialCopy, unsupportedClaimsAbsent },
  results,
  failures,
};
console.log(JSON.stringify(report, null, 2));
if (failures.length) process.exitCode = 1;
else console.log('[live site preflight] PASS: deployed public surface matches the local review gates');
