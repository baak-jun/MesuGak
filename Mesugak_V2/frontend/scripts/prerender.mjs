import { createServer } from 'vite';
import { readFile, mkdir, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const frontendRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const distRoot = resolve(frontendRoot, 'dist');
const template = await readFile(resolve(distRoot, 'index.html'), 'utf8');
const server = await createServer({
  root: frontendRoot,
  appType: 'custom',
  logLevel: 'error',
  server: { middlewareMode: true },
});

const { renderStaticRoute, staticRoutes } = await server.ssrLoadModule('/src/ssr-entry.jsx');

const metadata = {
  '/': {
    title: '기술지표분석교실 | 기술지표를 배우는 공개 학습 서비스',
    description: '최근 거래일 확정 일봉을 바탕으로 일목균형표, 볼린저 밴드, 이동평균, RSI와 가치 참고값을 배우는 공개 학습 서비스입니다.',
  },
  '/learn': {
    title: '기술지표 학습 홈 | 기술지표분석교실',
    description: '기술지표의 뜻, 해석할 수 있는 이유, 함께 확인할 조건을 한국어로 배우는 학습 자료입니다.',
  },
  '/learn/ichimoku': { title: '일목균형표 학습 | 기술지표분석교실', description: '구름대와 전환선·기준선의 관계를 추세 환경과 함께 읽는 방법을 배웁니다.' },
  '/learn/bollinger': { title: '볼린저 밴드 학습 | 기술지표분석교실', description: '최근 변동성의 범위와 밴드 수축·확장을 해석하는 방법을 배웁니다.' },
  '/learn/moving-average': { title: '이동평균과 지지 학습 | 기술지표분석교실', description: '이동평균으로 추세 방향과 되돌림 구간을 읽는 방법을 배웁니다.' },
  '/learn/rsi': { title: 'RSI와 다이버전스 학습 | 기술지표분석교실', description: 'RSI의 모멘텀, 과열·침체, 다이버전스를 해석하는 방법을 배웁니다.' },
  '/learn/volume': { title: '거래량 학습 | 기술지표분석교실', description: '가격 움직임에 참여가 얼마나 따라왔는지 거래량으로 확인하는 방법을 배웁니다.' },
  '/learn/valuation': { title: '가치 참고값 학습 | 기술지표분석교실', description: 'PER·PBR·ROE와 부채비율을 업종과 재무상태의 맥락에서 비교하는 방법을 배웁니다.' },
  '/methodology': { title: '분석 방법론 | 기술지표분석교실', description: '공공데이터 기반 확정 일봉 분석, 점수 산출, 데이터 부족 처리와 공개 범위를 설명합니다.' },
  '/about': { title: '운영 안내 | 기술지표분석교실', description: '기술지표분석교실의 운영 목적, 문의 방법, 교육용 분석 원칙을 안내합니다.' },
  '/terms': { title: '이용약관 | 기술지표분석교실', description: '기술지표분석교실 공개 분석 정보를 이용할 때의 조건과 분석 기준을 안내합니다.' },
  '/privacy': { title: '개인정보처리방침 | 기술지표분석교실', description: '기술지표분석교실의 개인정보, 쿠키, 분석·광고 기능 처리 방식을 안내합니다.' },
  '/data': { title: '분석 데이터 안내 | 기술지표분석교실', description: '공개 분석의 데이터 기준일, 출처, 공개·비공개 범위를 안내합니다.' },
  '/disclaimer': { title: '면책고지 | 기술지표분석교실', description: '기술지표 점수와 해설의 교육 목적, 한계, 투자 판단 책임을 안내합니다.' },
};

function escapeAttribute(value) {
  return String(value).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;');
}

function withMetadata(html, pathname) {
  const page = metadata[pathname] || metadata['/'];
  const canonical = 'https://mesu-gak.web.app' + (pathname === '/' ? '/' : pathname);
  const head = [
    '<meta name="description" content="' + escapeAttribute(page.description) + '" />',
    '<link rel="canonical" href="' + escapeAttribute(canonical) + '" />',
    '<meta property="og:title" content="' + escapeAttribute(page.title) + '" />',
    '<meta property="og:description" content="' + escapeAttribute(page.description) + '" />',
    '<meta property="og:url" content="' + escapeAttribute(canonical) + '" />',
    '<meta property="og:type" content="website" />',
  ].join('\n    ');
  return html
    .replace(/<title>[^<]*<\/title>/, '<title>' + page.title + '</title>')
    .replace(/<meta name="description"[^>]*\/>/, '')
    .replace('</head>', '    ' + head + '\n  </head>');
}

try {
  for (const pathname of staticRoutes()) {
    const body = renderStaticRoute(pathname);
    if (!body) continue;
    const html = withMetadata(
      template.replace('<div id="root"></div>', '<div id="root">' + body + '</div>'),
      pathname,
    );
    const outputDir = pathname === '/' ? distRoot : resolve(distRoot, pathname.slice(1));
    await mkdir(outputDir, { recursive: true });
    await writeFile(resolve(outputDir, 'index.html'), html, 'utf8');
  }
  console.log('[prerender] generated ' + staticRoutes().length + ' public pages');
} finally {
  await server.close();
}
