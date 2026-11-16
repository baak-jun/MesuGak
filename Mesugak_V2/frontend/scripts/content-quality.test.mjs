import test from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const root = resolve(process.cwd(), 'dist');
const routes = [
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
const renderedRoutes = new Set([...routes, '/analysis']);

function fileFor(route) {
  return route === '/' ? resolve(root, 'index.html') : resolve(root, route.slice(1), 'index.html');
}

function firstMatch(html, pattern) {
  return html.match(pattern)?.[1]?.trim() || '';
}

function visibleTokens(html) {
  return new Set(
    html
      .replace(/<script[\s\S]*?<\/script>/gi, ' ')
      .replace(/<style[\s\S]*?<\/style>/gi, ' ')
      .replace(/<[^>]+>/g, ' ')
      .toLowerCase()
      .match(/[가-힣a-z0-9]{2,}/g) || [],
  );
}

test('static public pages expose unique authored metadata and content', () => {
  const titles = new Set();
  const canonicals = new Set();

  for (const route of routes) {
    const file = fileFor(route);
    assert.equal(existsSync(file), true, `missing content route: ${route}`);
    const html = readFileSync(file, 'utf8');
    const title = firstMatch(html, /<title>([^<]+)<\/title>/);
    const h1 = firstMatch(html, /<h1[^>]*>([\s\S]*?)<\/h1>/);
    const description = firstMatch(html, /<meta name="description" content="([^"]+)"/);
    const canonical = firstMatch(html, /<link rel="canonical" href="([^"]+)"/);
    const visibleText = html
      .replace(/<script[\s\S]*?<\/script>/gi, ' ')
      .replace(/<style[\s\S]*?<\/style>/gi, ' ')
      .replace(/<[^>]+>/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();

    assert.ok(title.length >= 8, `missing/short title: ${route}`);
    assert.ok(h1.length >= 4, `missing/short H1: ${route}`);
    assert.ok(description.length >= 30, `missing/short description: ${route}`);
    assert.ok(canonical.startsWith('https://mesu-gak.web.app/'), `invalid canonical: ${route}`);
    assert.match(html, /<meta property="og:site_name" content="기술지표분석교실" \/>/, `missing Open Graph site name: ${route}`);
    assert.match(html, /<meta property="og:locale" content="ko_KR" \/>/, `missing Korean Open Graph locale: ${route}`);
    assert.match(html, /<meta name="twitter:card" content="summary" \/>/, `missing Twitter card metadata: ${route}`);
    // This is a local regression floor, not a Google policy minimum. It prevents
    // an authored page from silently regressing to a nearly empty template.
    assert.ok(visibleText.length >= 600, `thin prerendered body: ${route}`);
    // A broken encoding or an internal condition key makes an otherwise useful
    // lesson look unfinished to both readers and reviewers.
    assert.doesNotMatch(html, /\uFFFD/, `replacement character leaked into public HTML: ${route}`);
    assert.doesNotMatch(
      html,
      /\b(?:bearish|bullish|failed|squeeze|cloud|rsi|volume)_[a-z0-9_]+\b/i,
      `internal condition key leaked into public HTML: ${route}`,
    );
    assert.equal(titles.has(title), false, `duplicate title: ${title}`);
    assert.equal(canonicals.has(canonical), false, `duplicate canonical: ${canonical}`);
    assert.doesNotMatch(html, /href="#(?:"|')/, `empty hash link: ${route}`);
    assert.doesNotMatch(html, /광고 공간|AdSense 승인 후 실제 광고/, `ad placeholder: ${route}`);
    assert.doesNotMatch(html, /망개의 기지분 교실/, `stale brand label: ${route}`);
    for (const match of html.matchAll(/<a\b[^>]*href="(\/[^"#?]*)/gi)) {
      const linkedRoute = match[1].replace(/\/$/, '') || '/';
      assert.equal(renderedRoutes.has(linkedRoute), true, `broken internal link ${linkedRoute} from ${route}`);
    }
    titles.add(title);
    canonicals.add(canonical);
  }

  const homeHtml = readFileSync(fileFor('/'), 'utf8');
  const learnHtml = readFileSync(fileFor('/learn'), 'utf8');
  assert.match(homeHtml, /home-purpose-title/, 'root must expose a unique service-purpose section');
  assert.doesNotMatch(homeHtml, /기술지표분석교실 는|기술지표분석교실는/, 'root must not publish a broken Korean postposition');
  assert.match(learnHtml, /learning-guides-title/, 'learning hub must expose its curriculum section');
  assert.doesNotMatch(homeHtml, /learning-guides-title/, 'root must not reuse the learning hub section');
});

test('analysis tool stays out of the authored sitemap and is marked noindex', () => {
  const sitemap = readFileSync(resolve(process.cwd(), 'public', 'sitemap.xml'), 'utf8');
  const analysisHtml = readFileSync(resolve(root, 'analysis', 'index.html'), 'utf8');
  const researchSource = readFileSync(resolve(process.cwd(), 'src', 'ResearchApp.jsx'), 'utf8');
  assert.doesNotMatch(sitemap, /<loc>[^<]*\/analysis<\/loc>/);
  assert.match(analysisHtml, /<meta name="robots" content="noindex,follow"/);
  assert.match(analysisHtml, /여기서 볼 수 있는 것/);
  assert.match(analysisHtml, /신호가 엇갈리는 예/);
  assert.match(analysisHtml, /점수를 읽기 전에/);
  assert.match(analysisHtml, /learn\/glossary/);
  assert.match(researchSource, /public-list-freshness/);
  assert.match(researchSource, /publicFreshnessNotice\(selected\.updatedAt\)/);
});

test('indicator lessons retain the authored teaching structure', () => {
  const lessonTokens = new Map();
  const signatures = {
    '/learn/ichimoku': ['구름대', '전환선', '기준선'],
    '/learn/bollinger': ['볼린저', '밴드폭', '중심선'],
    '/learn/moving-average': ['이동평균', '지지', '추세'],
    '/learn/rsi': ['rsi', '다이버전스', '과열'],
    '/learn/volume': ['거래량', '평균', '돌파'],
    '/learn/valuation': ['pbr', 'per', 'roe'],
  };
  for (const route of ['/learn/ichimoku', '/learn/bollinger', '/learn/moving-average', '/learn/rsi', '/learn/volume', '/learn/valuation']) {
    const html = readFileSync(fileFor(route), 'utf8');
    assert.match(html, /class="guide-article-section"/, `missing lesson sections: ${route}`);
    assert.match(html, /class="learning-check-section"/, `missing learning check: ${route}`);
    assert.match(html, /class="guide-worked-example"/, `missing worked example: ${route}`);
    assert.ok(html.indexOf('class="guide-worked-example"') < html.indexOf('class="learning-check-section"'), `reading check must follow the worked example: ${route}`);
    assert.match(html, /class="[^"]*\bguide-source-box\b/, `missing source context: ${route}`);
    const tokens = visibleTokens(html);
    lessonTokens.set(route, tokens);
    for (const signature of signatures[route]) {
      assert.equal(tokens.has(signature), true, `missing route-specific teaching term ${signature}: ${route}`);
    }
  }

  const routes = [...lessonTokens.keys()];
  for (let left = 0; left < routes.length; left += 1) {
    for (let right = left + 1; right < routes.length; right += 1) {
      const a = lessonTokens.get(routes[left]);
      const b = lessonTokens.get(routes[right]);
      const intersection = [...a].filter((token) => b.has(token)).length;
      const union = a.size + b.size - intersection;
      const similarity = union ? intersection / union : 1;
      assert.ok(similarity < 0.75, `near-duplicate lesson bodies: ${routes[left]} vs ${routes[right]}`);
    }
  }
});

test('public score method stays aligned with the implemented weights', () => {
  const methodology = readFileSync(fileFor('/methodology'), 'utf8');
  const scoringSource = readFileSync(
    resolve(process.cwd(), '..', 'functions', 'strategy_engine', 'scoring.py'),
    'utf8',
  );
  const weights = [
    ['bollinger', '볼린저 밴드'],
    ['maSupport', '이동평균 지지'],
    ['ichimoku', '일목균형표'],
    ['rsi', 'RSI'],
    ['volume', '거래량'],
  ];

  for (const [key, label] of weights) {
    const match = scoringSource.match(new RegExp(`['\"]${key}['\"]\\s*:\\s*([0-9.]+)`));
    assert.ok(match, `missing implemented scoring weight: ${key}`);
    const ratio = Math.round(Number(match[1]) * 100);
    assert.match(methodology, new RegExp(`${label}\\s+${ratio}(?!\\d)`), `public weight is out of sync: ${key}`);
  }

  assert.match(methodology, /계산할 수 있을 때 실제 비중/);
  assert.match(methodology, /필요한 입력이 없는 지표는 0점으로 간주하지 않고/);
  assert.match(methodology, /볼린저 하단보다 낮으면 15점을 감점/);
  assert.match(methodology, /가치 참고값은 종합점수에 넣지/);
});

test('public copy does not claim unverified operator review or server polling', () => {
  const publicHtml = routes.map((route) => readFileSync(fileFor(route), 'utf8')).join('\n');
  assert.doesNotMatch(
    publicHtml,
    /운영자가[\s\S]{0,140}?(?:만들|작성|검토|편집|수정)|직접 만든[\s\S]{0,40}(?:그림|도식|예시)|3분(?: 간격|마다)|학교 서버 중단|서버 감시 상태|마지막 검토일/,
  );
});

test('condition lab instructions match the supported selection count', () => {
  const lab = readFileSync(fileFor('/learn/lab'), 'utf8');
  const learningSource = readFileSync(resolve(process.cwd(), 'src', 'content', 'learningCopy.js'), 'utf8');
  const conditionsStart = learningSource.indexOf('const labConditions = [');
  const conditionsEnd = learningSource.indexOf('const glossaryTerms = [', conditionsStart);
  const labConditions = learningSource.slice(conditionsStart, conditionsEnd);
  const pageSource = readFileSync(resolve(process.cwd(), 'src', 'LearningPages.jsx'), 'utf8');
  const labComponentStart = pageSource.indexOf('function ConditionLabPage()');
  const labComponentEnd = pageSource.indexOf('function GlossaryPage()', labComponentStart);
  const labComponent = pageSource.slice(labComponentStart, labComponentEnd);

  assert.match(lab, /조건을 하나 이상 선택해 보세요/);
  assert.doesNotMatch(lab, /조건을 두 개 이상 선택해 보세요/);
  assert.match(lab, /점수나 추천을 계산하지 않습니다/);
  assert.match(lab, /밴드가 넓어진 것만으로는 상승인지 하락인지 알 수 없어요/);
  assert.match(lab, /거래량도 최근 평균의 0\.8배라 돌파에 참여가 늘었다고 보기는 어렵습니다/);
  assert.match(lab, /더 확인할 점/);
  assert.match(labConditions, /bandExpand[\s\S]*?가격이 어느 방향으로 움직이는지는 밴드 폭만으로 알 수 없어요[\s\S]*?하락 방향으로 넓어질 수도 있어요/);
  assert.doesNotMatch(labConditions, /tone:/, 'conditions must not be preclassified as positive or cautionary');
  assert.match(labComponent, /selected\.map\(\(condition\) => <p key=\{condition\.key\}>[\s\S]*?condition\.support/);
  assert.match(labComponent, /selected\.map\(\(condition\) => <p key=\{condition\.key\}>[\s\S]*?condition\.caution/);
});

test('legal page dates do not imply a completed legal review', () => {
  for (const route of ['/terms', '/privacy', '/data', '/disclaimer']) {
    const html = readFileSync(fileFor(route), 'utf8');
    assert.match(html, /문서 수정일: 2026-10-01/, `missing accurate update label: ${route}`);
    assert.doesNotMatch(html, /마지막 검토일/);
  }
});

test('freshness case uses checks readers can observe', () => {
  const cases = readFileSync(fileFor('/learn/cases'), 'utf8');
  assert.match(cases, /화면에 데이터 부족 또는 갱신 지연 안내가 있는지/);
  assert.doesNotMatch(cases, /학교 서버 중단|서버 감시 상태가 정상인지/);
});

test('PBR case calculates peer position and labels its limits', () => {
  const cases = readFileSync(fileFor('/learn/cases'), 'utf8');
  assert.match(cases, /class="case-study-comparison"/);
  assert.match(cases, /동종 업종 중앙값/);
  assert.match(cases, /\+33%/);
  assert.match(cases, /−33%/);
  assert.match(cases, /가상/);
  assert.match(cases, /상대 위치만 보여줍니다/);
  assert.match(cases, /저평가 여부를 말해주지 않으므로/);
});

test('case lessons use numeric practice and describe V2 data handling accurately', () => {
  const cases = readFileSync(fileFor('/learn/cases'), 'utf8');
  const methodology = readFileSync(fileFor('/methodology'), 'utf8');
  const analysisSource = readFileSync(
    resolve(process.cwd(), '..', 'functions', 'strategy_engine', 'analysis.py'),
    'utf8',
  );
  const jobSource = readFileSync(
    resolve(process.cwd(), '..', 'functions', 'jobs', 'analyze_market.py'),
    'utf8',
  );
  const scoringSource = readFileSync(
    resolve(process.cwd(), '..', 'functions', 'strategy_engine', 'scoring.py'),
    'utf8',
  );

  assert.equal((cases.match(/class="case-study-example"/g) ?? []).length, 7);
  assert.match(cases, /종가 102, 구름대 상단 98/);
  assert.match(cases, /0\.040 → 0\.045 → 0\.061/);
  assert.match(cases, /전일 28, 오늘 34, RSI 신호선 31/);
  assert.match(cases, /T−2 거래일/);
  assert.match(cases, /120행/);
  assert.match(analysisSource, /len\(df\) < 120/);
  assert.match(jobSource, /"reason": "insufficient_data"/);
  assert.match(scoringSource, /if rsi_state\.get\("state"\) != "NO_DATA": active_weights\["rsi"\]/);
  assert.match(scoringSource, /confidence \+= component_scores\[key\] \* \(weight \/ total_weight\)/);
  assert.match(methodology, /120개보다 적으면 새 분석 결과를 만들지 않고/);
  assert.match(methodology, /계산 불가 상태/);
  assert.match(methodology, /남은 지표의 가중치 합으로 평균을 다시 계산/);
});

test('indicator lessons link relevant references and disclose implemented calculation choices', () => {
  const references = [
    ['/learn/ichimoku', 'https://www.mql5.com/en/code/34'],
    ['/learn/bollinger', 'https://www.bollingerbands.com/bollinger-bands'],
    ['/learn/moving-average', 'https://www.tradingview.com/support/solutions/43000502589-moving-averages/'],
    ['/learn/rsi', 'https://www.tradingview.com/support/solutions/43000502338-relative-strength-index-rsi/'],
    ['/learn/volume', 'https://www.tradingview.com/support/solutions/43000591617-volume/'],
    ['/learn/valuation', 'https://syndication.finra.org/content/defining-value-investment'],
  ];

  for (const [route, href] of references) {
    const html = readFileSync(fileFor(route), 'utf8');
    assert.ok(html.includes(`href="${href}"`), `missing topic reference: ${route}`);
    assert.match(html, /target="_blank" rel="noopener noreferrer"/, `external link safety attributes missing: ${route}`);
  }
  const rsiLesson = readFileSync(fileFor('/learn/rsi'), 'utf8');
  assert.ok(rsiLesson.includes('href="https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.ewm.html"'));

  const methodology = readFileSync(fileFor('/methodology'), 'utf8');
  const indicatorSource = readFileSync(
    resolve(process.cwd(), '..', 'functions', 'strategy_engine', 'indicators.py'),
    'utf8',
  );
  assert.match(methodology, /5·20·60·120일 단순평균/);
  assert.match(methodology, /9·26·52일 고가와 저가의 중간값/);
  assert.match(methodology, /ddof=1\(표본 표준편차\)/);
  assert.match(methodology, /alpha=1\/14, adjust=False 설정으로 지수평활/);
  assert.match(methodology, /유효한 변화 14개부터 값을 냅니다/);
  assert.match(methodology, /Pandas EWM 초기화에 따라 다른 도구와 초기 RSI 값이 달라질 수 있습니다/);
  assert.match(methodology, /당일을 포함한 최근 20개 관측치/);
  assert.match(indicatorSource, /rolling\(window=window, min_periods=window\)\.std\(\)/);
  assert.match(indicatorSource, /ewm\(alpha=1 \/ period, adjust=False, min_periods=period\)/);
  assert.match(indicatorSource, /out\["volume"\]\.rolling\(window=window, min_periods=window\)\.mean\(\)/);
  assert.match(indicatorSource, /out\["senkou_a_leading"\]\.shift\(26\)/);

  const cases = readFileSync(fileFor('/learn/cases'), 'utf8');
  assert.match(cases, /FINRA의 P\/B 계산과 동종 기업 비교 설명/);
});
