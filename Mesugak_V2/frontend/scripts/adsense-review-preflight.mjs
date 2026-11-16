import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { adsenseSlotCountByRoute } from '../src/adsensePlacementPolicy.js';

// This is an internal release gate, not a claim about Google's approval criteria.
// It checks the artifact that would be submitted for review without contacting
// Firebase, AdSense, or any external service.
const distRoot = resolve(process.cwd(), 'dist');
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
const allRoutes = [...authoredRoutes, '/analysis'];
function fileFor(route) {
  return route === '/' ? resolve(distRoot, 'index.html') : resolve(distRoot, route.slice(1), 'index.html');
}

function visibleText(html) {
  return html
    .replace(/<script[\s\S]*?<\/script>/gi, ' ')
    .replace(/<style[\s\S]*?<\/style>/gi, ' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

const failures = [];
const canonicals = new Set();
const pages = new Map();

for (const route of allRoutes) {
  const file = fileFor(route);
  if (!existsSync(file)) {
    failures.push(`${route}: missing prerendered HTML`);
    continue;
  }
  const html = readFileSync(file, 'utf8');
  pages.set(route, html);
  if (html.includes('\uFFFD')) failures.push(`${route}: replacement character leaked into HTML`);
  if (/\b(?:bearish|bullish|failed|squeeze|cloud|rsi|volume)_[a-z0-9_]+\b/i.test(html)) {
    failures.push(`${route}: internal condition key leaked into HTML`);
  }
  if (/광고 공간|AdSense 승인 후 실제 광고|후원 링크 준비 중/.test(html)) {
    failures.push(`${route}: unfinished/ad placeholder leaked into HTML`);
  }
  const title = html.match(/<title>([^<]+)<\/title>/)?.[1]?.trim() || '';
  const heading = html.match(/<h1[^>]*>([\s\S]*?)<\/h1>/)?.[1]?.trim() || '';
  const description = html.match(/<meta name="description" content="([^"]+)"/)?.[1] || '';
  const canonical = html.match(/<link rel="canonical" href="([^"]+)"/)?.[1] || '';
  if (title.length < 8 || heading.length < 4 || description.length < 30) failures.push(`${route}: authored metadata is incomplete`);
  if (!canonical.startsWith('https://mesu-gak.web.app/')) failures.push(`${route}: canonical is outside the production site`);
  if (canonicals.has(canonical)) failures.push(`${route}: duplicate canonical`);
  canonicals.add(canonical);
  if (visibleText(html).length < 600) failures.push(`${route}: body is below the internal content floor`);
  if (route === '/analysis' && !/<meta name="robots" content="noindex,follow"/.test(html)) failures.push('/analysis: noindex,follow is missing');
  if (route !== '/analysis' && /<meta name="robots" content="noindex/.test(html)) failures.push(`${route}: authored page is unexpectedly noindex`);
}

const methodology = pages.get('/methodology') || '';
if (!methodology.includes('editorial-history-title')) failures.push('/methodology: editorial change record is missing');
if (!methodology.includes('or_not_official@naver.com')) failures.push('/methodology: correction contact is missing');
if (!(pages.get('/') || '').includes('종목 분석 결과 보기')) failures.push('/: prominent stock-analysis link is missing');
if (!(pages.get('/learn') || '').includes('분석된 종목 보러 가기')) failures.push('/learn: prominent stock-analysis link is missing');

const cases = pages.get('/learn/cases') || '';
if ((cases.match(/class="case-study"/g) || []).length < 8) failures.push('/learn/cases: authored case set is unexpectedly short');
const glossary = pages.get('/learn/glossary') || '';
if ((glossary.match(/class="glossary-item"/g) || []).length < 15) failures.push('/learn/glossary: authored term set is unexpectedly short');

const privacy = pages.get('/privacy') || '';
if (!privacy.includes('legal-runtime-status')) failures.push('/privacy: current feature-state disclosure is missing');
const adsEnabled = privacy.includes('AdSense 요청 게이트가 켜져 있습니다.');

const adRoutesWithSlots = [];
const adSlotCounts = {};
for (const [route, html] of pages) {
  const adSlots = html.match(/<ins\b[^>]*class="[^"]*\badsbygoogle\b[^"]*"[^>]*>/gi) || [];
  const expectedSlotCount = adsEnabled ? adsenseSlotCountByRoute[route] || 0 : 0;
  adSlotCounts[route] = adSlots.length;
  if (adSlots.length !== expectedSlotCount) {
    failures.push(`${route}: expected ${expectedSlotCount} AdSense slot(s), found ${adSlots.length}`);
  }
  if (!adsEnabled && /<script[^>]+adsbygoogle|adsbygoogle\.js\?client/i.test(html)) {
    failures.push(`${route}: static HTML must not issue an AdSense request when ads are disabled`);
  }
  if (adSlots.length) adRoutesWithSlots.push(route);
}
const staticAdMarkup = adRoutesWithSlots.length > 0;

const adsTxtPath = resolve(process.cwd(), 'public', 'ads.txt');
const report = {
  authoredRoutes: authoredRoutes.length,
  checkedRoutes: pages.size,
  adsEnabled,
  adRoutesWithSlots,
  adSlotCounts: Object.fromEntries(Object.entries(adSlotCounts).filter(([, count]) => count > 0)),
  adsTxtPresent: existsSync(adsTxtPath),
  staticAdMarkup,
  failures,
};
console.log(JSON.stringify(report, null, 2));
if (failures.length) process.exitCode = 1;
else console.log('[adsense preflight] PASS: artifact is ready for operator/account checks');
