import test from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const root = resolve(process.cwd(), 'dist');
const routes = [
  '/',
  '/analysis',
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

function fileFor(route) {
  return route === '/' ? resolve(root, 'index.html') : resolve(root, route.slice(1), 'index.html');
}

test('public learning and policy routes contain server-rendered content', () => {
  for (const route of routes) {
    const file = fileFor(route);
    assert.equal(existsSync(file), true, 'missing prerendered route: ' + route);
    const html = readFileSync(file, 'utf8');
    assert.match(html, /<div id="root">[\s\S]+<\/div>/, 'empty root: ' + route);
    assert.match(html, /<link rel="canonical"/, 'missing canonical: ' + route);
    assert.doesNotMatch(html, /광고 공간|AdSense 승인 후 실제 광고/, 'ad placeholder leaked: ' + route);
  }
  const valuationHtml = readFileSync(fileFor('/learn/valuation'), 'utf8');
  const homeHtml = readFileSync(fileFor('/'), 'utf8');
  const learnHtml = readFileSync(fileFor('/learn'), 'utf8');
  assert.match(homeHtml, /home-purpose-title/, 'root must expose the authored service purpose');
  assert.match(learnHtml, /learning-guides-title/, 'learning hub must expose the curriculum');
  assert.doesNotMatch(homeHtml, /learning-guides-title/, 'root must not duplicate the learning hub body');
  assert.match(valuationHtml, /PER[\s\S]*PBR/, 'valuation guide must mention PER and PBR');
  assert.match(valuationHtml, /반영하지/, 'valuation guide must state that PER/PBR are excluded from scoring');
  const casesHtml = readFileSync(fileFor('/learn/cases'), 'utf8');
  assert.match(casesHtml, /구름대 위, RSI는 약세/, 'case studies must contain an indicator-conflict lesson');
  assert.equal((casesHtml.match(/class="case-study-caution"/g) || []).length, 8, 'each case must explain a counterexample');
  assert.match(casesHtml, /오래된 기준일 확인하기/, 'case studies must explain stale data handling');
  assert.match(casesHtml, /자료가 부족하면 계산 보류/, 'case studies must explain calculation deferral');
  assert.equal((casesHtml.match(/class="case-study"/g) || []).length, 8, 'case studies must retain eight authored examples');
  const labHtml = readFileSync(fileFor('/learn/lab'), 'utf8');
  const methodologyHtml = readFileSync(fileFor('/methodology'), 'utf8');
  assert.match(methodologyHtml, /publication-status-title/, 'methodology must expose editorial review status');
  assert.match(methodologyHtml, /or_not_official@naver\.com/, 'methodology must expose the correction contact');
  assert.match(methodologyHtml, /editorial-history-title/, 'methodology must expose a real editorial change record');
  assert.match(methodologyHtml, /콘텐츠 변경 기록/, 'methodology must explain why the change record exists');
  assert.match(labHtml, /조건을 조합해 보기/, 'condition lab must have an educational introduction');
  assert.match(labHtml, /가상의 지표 상태/, 'condition lab must identify its invented inputs');
  assert.match(labHtml, /band-calculator/, 'calculation lab is present before JavaScript loads');
  assert.match(labHtml, /106\.3246/, 'default calculation is prerendered');
  assert.match(labHtml, /0÷0/, 'zero-width interpretation is readable without interaction');
  assert.match(labHtml, /특정 종목의 매수·매도·보유 판단/, 'condition lab must state that it is not a live recommendation tool');
  const privacyHtml = readFileSync(fileFor('/privacy'), 'utf8');
  assert.match(privacyHtml, /legal-runtime-status/, 'privacy page must expose the current feature state');
  assert.match(privacyHtml, /AdSense 요청은 현재 비활성화되어 광고 요청을 보내지 않습니다|AdSense 요청 게이트가 켜져 있습니다/, 'privacy page must state whether ad requests are enabled');
  const aboutHtml = readFileSync(fileFor('/about'), 'utf8');
  assert.match(aboutHtml, /publication-schedule-title/, 'about page must explain publication freshness and delay handling');
  assert.match(aboutHtml, /새 거래일/, 'about page must state that a new provider date triggers publication');
  const bollingerHtml = readFileSync(fileFor('/learn/bollinger'), 'utf8');
  assert.match(bollingerHtml, /수축 뒤 확장을 읽는 가상 예시/, 'indicator guides must contain a worked interpretation example');
  const rsiHtml = readFileSync(fileFor('/learn/rsi'), 'utf8');
  assert.match(rsiHtml, /다이버전스가 약해지는 경우/, 'indicator guides must explain when an interpretation weakens');
  for (const route of ['/learn/ichimoku', '/learn/bollinger', '/learn/moving-average', '/learn/rsi', '/learn/volume', '/learn/valuation']) {
    const guideHtml = readFileSync(fileFor(route), 'utf8');
    assert.match(guideHtml, /계산 기준과 참고 자료/, `indicator guide must expose its calculation/source context: ${route}`);
    assert.match(guideHtml, /data\.go\.kr\/data\/15094808/, `indicator guide must link the public-data source: ${route}`);
    assert.match(guideHtml, /class="guide-visual-section"/, `indicator guide must contain a visual teaching section: ${route}`);
    assert.match(guideHtml, /class="guide-visual-art"[\s\S]*?<svg/, `indicator guide must render an authored explanatory diagram: ${route}`);
  }
  const analysisHtml = readFileSync(fileFor('/analysis'), 'utf8');
  assert.match(analysisHtml, /여기서 볼 수 있는 것/, 'analysis route must have a static educational introduction');
  assert.match(analysisHtml, /<meta name="robots" content="noindex,follow"/, 'analysis tool route must not be in search index');
});

test('glossary retains independent definitions and interpretation limits', () => {
  const html = readFileSync(fileFor('/learn/glossary'), 'utf8');
  assert.match(html, /glossary-list/);
  assert.match(html, /\uC77C\uBD09/);
  assert.match(html, /\uAE30\uC900\uC77C/);
  assert.match(html, /\uC885\uD569\uC810\uC218/);
  assert.match(html, /\uC0C1\uC2B9 \uD655\uB960/);
  assert.match(html, /glossary-faq/);
  assert.equal((html.match(/class="glossary-item"/g) || []).length, 15, 'glossary must retain the authored term set');
});

test('indicator articles are substantial, sourced, and reachable from their lessons', () => {
  const slugs = ['ichimoku', 'bollinger', 'moving-average', 'rsi', 'volume', 'valuation'];
  const indexHtml = readFileSync(fileFor('/learn/articles'), 'utf8');
  for (const slug of slugs) {
    const route = `/learn/articles/${slug}`;
    const html = readFileSync(fileFor(route), 'utf8');
    const guide = readFileSync(fileFor(`/learn/${slug}`), 'utf8');
    const body = html.match(/<article class="longread-article">([\s\S]*?)<\/article>/)?.[1] || '';
    const visible = body.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
    assert.ok(visible.length >= 1400, `article is unexpectedly short: ${route}`);
    assert.ok((body.match(/class="longread-section"/g) || []).length >= 5, `article needs multiple distinct sections: ${route}`);
    assert.match(body, /class="longread-formula"/, `article needs a visible calculation: ${route}`);
    assert.match(body, /class="longread-example"/, `article needs a worked example: ${route}`);
    assert.match(body, /<table class="longread-table"[\s\S]*?<th scope="col"[\s\S]*?<th scope="row"/, `article must render readable calculation tables: ${route}`);
    assert.doesNotMatch(body, /:::formula|:::example|\| --- \|/, `article must not expose raw manuscript markers: ${route}`);
    assert.match(body, /class="longread-figure"[\s\S]*?<svg/, `article needs an explanatory graphic: ${route}`);
    assert.match(body, /class="longread-sources"[\s\S]*?https:\/\//, `article needs a verifiable source: ${route}`);
    assert.match(indexHtml, new RegExp(`href="${route}"`), `collection does not link article: ${route}`);
    assert.match(guide, new RegExp(`href="${route}"`), `lesson does not link article: ${route}`);
  }
});
