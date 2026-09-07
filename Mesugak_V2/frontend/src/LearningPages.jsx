/* eslint-disable react-refresh/only-export-components */
import { useEffect } from 'react';
import { ArrowRight, BookOpen, ExternalLink, Mail, ShieldCheck } from 'lucide-react';
import { AdSenseSlot } from './AdSenseSlot.jsx';
import { BRAND_FULL, BRAND_SHORT } from './brand';
import { ComplianceDock } from './LegalPages.jsx';
import {
  educationalGuides,
  publicIndicatorGuides,
} from './analysisEducationContent.jsx';
import './learning.css';

const indicatorPages = {
  ichimoku: {
    label: '일목균형표',
    slug: 'ichimoku',
    guideKey: 'ichimoku',
    summary: '가격과 전환선·기준선·구름대의 관계로 추세 환경을 읽는 방법을 배웁니다.',
    sections: [
      { title: '먼저 무엇을 보는 지표인가요?', body: ['일목균형표는 가격 하나만 보지 않고 현재 추세, 지지·저항이 될 수 있는 구간, 앞으로의 추세 환경을 한 화면에 겹쳐 읽는 도구입니다.', '구름대 위에 있다는 사실은 최근 가격이 두 선으로 만든 범위보다 높은 곳에서 형성되고 있다는 뜻입니다. 그래서 상승 추세가 유지되는 환경으로 해석할 수 있지만, 구름대가 두껍거나 기울기가 약하면 같은 의미의 강한 추세라고 단정하기는 어렵습니다.'] },
      { title: '조건은 어떻게 해석하나요?', body: ['가격이 구름대 위에 있고 전환선이 기준선 위에 있으면 단기 가격 흐름과 중기 기준이 함께 위쪽을 향하는지 살펴볼 수 있습니다.', '선행 구름이 양운이면 현재 가격뿐 아니라 앞으로 이동할 구간의 지지·저항 환경도 상대적으로 우호적인지 확인할 수 있습니다. 반대로 가격이 구름대 아래에 있거나 후행스팬이 과거 가격에 막히면 같은 상승 해석을 약하게 봅니다.'] },
      { title: '함께 확인하면 좋은 것', body: ['구름대 위라는 조건만으로 진입 시점을 정하지 말고 거래량, 볼린저 밴드의 확장 방향, 장기 이동평균의 기울기를 함께 확인하세요.', '횡보장에서는 가격이 구름대를 여러 번 오갈 수 있으므로 돌파가 며칠 유지되는지와 되돌림 때 구름대가 지지로 작동하는지를 살펴보는 것이 좋습니다.'] },
    ],
  },
  bollinger: {
    label: '볼린저 밴드',
    slug: 'bollinger',
    guideKey: 'bollinger',
    summary: '최근 변동성의 범위와 밴드가 좁아졌다가 넓어지는 흐름을 읽습니다.',
    sections: [
      { title: '밴드는 무엇을 보여주나요?', body: ['볼린저 밴드는 중심선과 최근 변동성을 반영한 위·아래 경계로 구성됩니다. 가격이 밴드 어느 쪽에 있는지와 밴드 폭이 변하는 방향을 함께 읽는 것이 핵심입니다.', '상단 밴드에 닿았다는 사실만으로 계속 오른다고 보지 않습니다. 강한 추세에서는 상단을 따라갈 수 있지만, 밴드 폭이 줄어드는 구간에서는 작은 움직임도 경계에 닿을 수 있습니다.'] },
      { title: '수축과 확장은 어떻게 보나요?', body: ['밴드 폭이 좁아지는 수축은 최근 변동성이 낮아졌다는 뜻입니다. 이후 밴드가 한쪽으로 넓어지면서 가격과 거래량이 함께 움직이면 새로운 방향성이 시작됐을 가능성을 살펴볼 수 있습니다.', '아래쪽으로 밴드가 넓어지고 가격이 하단 밖에 머무르면 하락 변동성이 커지는 상황일 수 있어, 단순한 저평가나 즉시 반등으로 해석하지 않는 편이 안전합니다.'] },
      { title: '확인하면 좋은 것', body: ['밴드 돌파 방향, 중심선 회복 여부, 상대 거래량을 같이 보세요. 거래량이 따라오지 않는 상단 돌파는 추세 확인이 더 필요할 수 있습니다.', '밴드는 가격의 상대적 위치를 보여주는 도구이지 기업의 가치나 미래 수익을 계산하는 도구가 아닙니다.'] },
    ],
  },
  movingAverage: {
    label: '이동평균과 지지',
    slug: 'moving-average',
    guideKey: 'maSupport',
    summary: '여러 기간의 평균 가격으로 추세의 방향과 되돌림 구간을 읽습니다.',
    sections: [
      { title: '이동평균은 왜 사용하나요?', body: ['이동평균은 일정 기간의 가격을 평균내 단기적인 흔들림을 줄여줍니다. 기간이 길수록 반응은 느리지만 더 긴 흐름을 보여줍니다.', '가격이 60일 이동평균 위에 있고 평균선 자체도 상승하면 중기 추세가 유지되는 환경으로 볼 수 있습니다. 그러나 평균선은 과거 자료를 요약한 값이어서 전환을 먼저 알려주는 신호는 아닙니다.'] },
      { title: '지지로 해석하는 이유', body: ['상승 추세에서 가격이 평균선 근처로 되돌아온 뒤 다시 반등하면 과거에 그 가격대를 매수 기준으로 본 참여자가 남아 있을 가능성을 생각해 볼 수 있습니다.', '평균선을 한 번 살짝 밑돈 것보다 종가 기준으로 이탈이 이어지는지, 평균선의 방향이 아래로 바뀌는지를 함께 확인해야 합니다.'] },
      { title: '다른 조건과의 조합', body: ['볼린저 하단과 60일 평균의 관계는 변동성 범위가 중기 추세와 어느 쪽에 놓였는지 보여줍니다.', '일목균형표의 구름대와 이동평균이 같은 방향을 가리키면 해석이 겹쳐질 수 있으므로, 같은 근거를 여러 번 센 것은 아닌지 점수 구조도 함께 확인하세요.'] },
    ],
  },
  rsi: {
    label: 'RSI와 다이버전스',
    slug: 'rsi',
    guideKey: 'rsi',
    summary: '최근 상승·하락 압력의 균형과 과열·침체 뒤의 회복을 읽습니다.',
    sections: [
      { title: 'RSI의 기본 뜻', body: ['RSI는 최근 일정 기간의 상승폭과 하락폭을 비교해 모멘텀을 0에서 100 사이로 표현합니다. 높은 RSI는 최근 상승 압력이 강했다는 뜻이고 낮은 RSI는 하락 압력이 강했다는 뜻입니다.', '일반적으로 70 이상을 과열, 30 이하를 침체로 참고하지만 시장과 종목에 따라 오래 머무를 수 있습니다. 숫자 하나만으로 반전 시점을 정하지 않습니다.'] },
      { title: '회복과 약세를 구분하는 법', body: ['침체권에서 RSI가 올라오고 기준선을 회복하면 하락 모멘텀이 약해졌을 가능성을 볼 수 있습니다. 가격이 이미 충분히 반등했는지와 거래량이 뒷받침되는지는 별도로 봐야 합니다.', '가격은 이전 고점을 높였는데 RSI 고점은 낮아지는 약세 다이버전스는 상승 힘이 예전만 못할 가능성을 보여주는 경고로 해석할 수 있습니다.'] },
      { title: '확인하면 좋은 것', body: ['RSI는 추세가 강한 종목에서 과열권에 오래 머물 수 있으므로 일목균형표·이동평균으로 추세를 먼저 살피세요.', '다이버전스는 관찰 구간과 고점 선택에 따라 달라질 수 있어, 한 번의 불일치보다 실제 가격 이탈과 함께 나타나는지 확인하는 편이 좋습니다.'] },
    ],
  },
  volume: {
    label: '거래량 확인',
    slug: 'volume',
    guideKey: 'volume',
    summary: '가격 움직임에 실제 참여가 얼마나 따라왔는지를 확인합니다.',
    sections: [
      { title: '거래량은 왜 필요한가요?', body: ['가격이 움직였다는 사실만으로는 그 움직임에 참여한 사람이 얼마나 많은지 알 수 없습니다. 거래량은 해당 가격 변화에 참여한 규모를 비교하는 참고자료입니다.', '최근 평균보다 큰 거래량과 함께 저항을 넘으면 돌파에 대한 참여가 늘었다고 해석할 수 있지만, 이벤트·공시·일시적인 주문으로도 거래량이 급증할 수 있습니다.'] },
      { title: '돌파 확인의 의미', body: ['가격 돌파와 거래량 증가가 동시에 나타나면 단순히 호가가 얇아서 생긴 움직임일 가능성을 조금 줄여볼 수 있습니다.', '반대로 가격은 올랐는데 거래량이 평균보다 약하면 상승 흐름이 넓게 참여받지 못했을 가능성을 염두에 두고 다음 봉의 유지 여부를 확인합니다.'] },
      { title: '주의할 점', body: ['거래량의 절대 크기는 종목마다 다르므로 같은 종목의 최근 평균과 비교해야 합니다.', '거래량은 방향을 단독으로 결정하지 않습니다. 하락 때 거래량이 커지는지, 상승 때 꾸준히 유지되는지와 가격 구조를 함께 보세요.'] },
    ],
  },
  valuation: {
    label: '가치 참고값',
    slug: 'valuation',
    guideKey: 'valuation',
    summary: 'PER·PBR·ROE·부채비율·영업이익 흐름을 비교할 때의 기준과 한계를 배웁니다.',
    sections: [
      { title: '가치 참고값은 어떤 역할인가요?', body: ['가치 참고값은 기술적 흐름만으로 놓칠 수 있는 재무상태를 함께 살펴보기 위한 보조 자료입니다. 종합점수에서 일부 조건으로 사용되더라도 기업의 적정가치를 확정하는 계산은 아닙니다.', '업종마다 자본 구조와 이익 특성이 다르므로 같은 PER·PBR 숫자라도 의미가 달라질 수 있습니다. 과거 값, 동종업계, 성장률을 함께 비교해야 합니다.'] },
      { title: '이 사이트의 참고 범위', body: ['PBR은 0 초과~1.5 이하를 낮은 편, 1.5 초과~3을 중간 범위, 5 초과를 높은 편으로 참고합니다. 3~5 구간은 업종과 성장성에 따라 해석이 크게 달라져 별도 판단이 필요합니다.', 'PER은 이익이 양수인 경우 낮은 편·중간·높은 편으로 나누어 참고하고, 적자·일회성 이익·급격한 성장 구간에서는 숫자만으로 비교하지 않습니다.', 'ROE는 8% 이상~15% 미만을 양호한 범위로 참고하며, 부채비율과 영업이익 증가 여부를 함께 봅니다. 이 수치는 법정 기준이나 매수 기준이 아니라 이 서비스의 교육용 분류값입니다.'] },
      { title: '왜 단독 판단을 피하나요?', body: ['낮은 PBR이 자산 대비 저렴하다는 뜻일 수 있지만 사업 전망이나 자산의 질이 낮아 시장에서 할인된 결과일 수도 있습니다.', '높은 ROE도 부채 증가나 일회성 이익으로 만들어질 수 있습니다. 재무제표의 기간, 업종 특성, 현금흐름과 함께 확인해야 의미가 생깁니다.'] },
    ],
  },
};

const methodologySections = [
  { title: '분석 흐름', body: ['금융위원회 공공데이터포털에서 제공하는 최근 거래일 확정 일봉을 서버에서 받아 지표를 계산합니다.', '일목균형표·이동평균·볼린저 밴드·RSI·거래량·가치 참고값을 각각 평가한 뒤 조건별 결과를 종합점수와 해설 상태로 변환합니다.', '공개 화면에는 종목명·종목코드·자체 점수·상태 해설만 표시하고 원시 시세와 숫자 지표는 공개하지 않습니다.'] },
  { title: '점수 읽는 법', body: ['점수는 미래 수익률이나 성공 확률이 아니라 현재 데이터에서 미리 정한 조건이 얼마나 함께 나타났는지를 나타내는 내부 정렬값입니다.', '조건이 많다고 반드시 좋은 종목이라는 뜻은 아니며, 서로 비슷한 근거가 중복 반영될 수 있고 시장 국면이 바뀌면 해석도 달라질 수 있습니다.'] },
  { title: '데이터 부족 처리', body: ['필요한 일봉이 부족하거나 유효하지 않은 값이 있으면 해당 지표는 긍정·부정 점수에 억지로 포함하지 않고 데이터 부족 상태로 표시합니다.', '데이터 날짜와 출처를 확인하고, 거래정지·신규 상장·누락 구간이 있는지 먼저 살펴보는 것이 좋습니다.'] },
  { title: '공개 범위와 한계', body: ['이 서비스는 교육과 연구를 위한 단방향 정보 제공 서비스입니다. 개인별 투자상담, 주문대행, 목표가·수익률 보장은 제공하지 않습니다.', '최종 투자 판단은 이용자에게 있으며, 화면의 상태와 점수만으로 매수·매도 결정을 내리지 않도록 하세요.'] },
];

function pageTitle(page) {
  return `${page.label} | ${BRAND_SHORT}`;
}

export function normalizeLearningRoute(value) {
  const normalized = String(value || '').replace(/^#\/?/, '').replace(/^\/+|\/+$/g, '');
  if (!normalized || normalized === 'learn') return 'home';
  if (normalized === 'methodology') return 'methodology';
  if (normalized === 'about') return 'about';
  if (normalized.startsWith('learn/')) {
    const slug = normalized.slice('learn/'.length);
    return Object.values(indicatorPages).some((page) => page.slug === slug) ? slug : '';
  }
  return '';
}

function SiteNav() {
  return (
    <nav className="learning-nav" aria-label="사이트 주요 메뉴">
      <a className="learning-nav-brand" href="/"><span>{BRAND_FULL}</span><strong>{BRAND_SHORT}</strong></a>
      <div className="learning-nav-links">
        <a href="/learn">지표 학습</a>
        <a href="/methodology">분석 방법론</a>
        <a href="/analysis">종목 분석</a>
        <a href="/about">운영 안내</a>
      </div>
    </nav>
  );
}

function LearningFooter() {
  return (
    <footer className="learning-footer">
      <div><strong>{BRAND_SHORT}</strong><span>기술지표를 읽는 방법을 함께 공부하는 공개 학습 서비스</span></div>
      <nav aria-label="정책 페이지">
        <a href="/terms">이용약관</a><a href="/privacy">개인정보처리방침</a><a href="/data">데이터 안내</a><a href="/disclaimer">면책 안내</a>
      </nav>
    </footer>
  );
}

function LearningHero({ eyebrow, title, summary, children }) {
  return (
    <header className="learning-hero">
      <span className="learning-eyebrow"><BookOpen size={15} />{eyebrow}</span>
      <h1>{title}</h1>
      <p>{summary}</p>
      {children}
    </header>
  );
}

function GuideCard({ page }) {
  return (
    <a className="guide-card" href={`/learn/${page.slug}`}>
      <div className="guide-card-top"><span>{page.label}</span><ArrowRight size={17} /></div>
      <p>{page.summary}</p>
      <small>뜻 · 해석 · 확인할 것</small>
    </a>
  );
}

function LearningHome() {
  return (
    <main className="learning-page theme-light">
      <SiteNav />
      <div className="learning-container">
        <LearningHero
          eyebrow="기술지표분석교실 · 공개 학습 홈"
          title="숫자를 외우기보다, 조건이 함께 나타난 맥락을 읽어보세요"
          summary="기술지표가 무엇을 계산하는지, 왜 특정 상태를 긍정적 또는 주의할 상황으로 읽을 수 있는지, 언제 해석을 멈춰야 하는지를 설명합니다."
        >
          <div className="learning-hero-actions"><a className="primary-learning-button" href="/analysis">최근 종목 분석 보기 <ArrowRight size={16} /></a><a className="secondary-learning-button" href="/methodology">점수 산출 방법</a></div>
        </LearningHero>

        <section className="learning-section" aria-labelledby="learning-guides-title">
          <div className="section-heading"><span>01 · 지표별 기초</span><h2 id="learning-guides-title">어떤 조건을 보고 있나요?</h2><p>각 페이지에서 조건의 뜻과 해석할 수 있는 이유, 함께 확인할 항목을 순서대로 설명합니다.</p></div>
          <div className="guide-grid">{Object.values(indicatorPages).map((page) => <GuideCard key={page.slug} page={page} />)}</div>
        </section>

        <section className="learning-section learning-method-callout" aria-labelledby="learning-method-title">
          <div><span>02 · 이 서비스의 읽는 순서</span><h2 id="learning-method-title">지표 하나보다 조합과 한계를 먼저 확인합니다</h2><p>최근 거래일 확정 일봉을 바탕으로 여러 조건을 계산하지만, 점수는 매수·매도 신호나 수익률 예측이 아닙니다.</p></div>
          <a className="text-link-button" href="/methodology">방법론 읽기 <ArrowRight size={16} /></a>
        </section>
      </div>
      <LearningFooter />
      <ComplianceDock />
    </main>
  );
}

function GuidePage({ page }) {
  const guide = educationalGuides[page.guideKey];
  return (
    <main className="learning-page theme-light">
      <SiteNav />
      <div className="learning-container">
        <LearningHero eyebrow={`지표 학습 · ${page.label}`} title={page.label} summary={page.summary}>
          <a className="back-learning-link" href="/learn">← 모든 지표 보기</a>
        </LearningHero>
        <div className="guide-article-layout">
          <article className="guide-article">
            {page.sections.map((section) => <section key={section.title} className="guide-article-section"><h2>{section.title}</h2>{section.body.map((paragraph) => <p key={paragraph}>{paragraph}</p>)}</section>)}
            {guide?.points?.length ? <section className="guide-visual-section"><div className="section-heading"><span>그림으로 확인하기</span><h2>{publicIndicatorGuides[page.guideKey]?.label || page.label}의 대표적인 모습</h2><p>아래 그림은 실제 가격 차트를 재현한 것이 아니라 조건을 읽는 순서를 설명하는 교육용 도식입니다.</p></div><div className="guide-visual-grid">{guide.points.map((point) => <article key={point.label} className="guide-visual-card"><div className="guide-visual-art">{point.graphic}</div><h3>{point.label}</h3><p>{point.desc}</p></article>)}</div></section> : null}
            <section className="guide-article-note"><ShieldCheck size={19} /><p>이 페이지의 설명은 교육용 기준입니다. 같은 상태라도 업종·시장 국면·데이터 품질에 따라 의미가 달라질 수 있어요.</p></section>
          </article>
          <aside className="guide-side-rail"><div className="guide-side-card"><span>다음에 읽기</span><a href="/methodology">종합점수 방법론 <ArrowRight size={15} /></a><a href="/analysis">실제 분석 화면 <ArrowRight size={15} /></a></div><AdSenseSlot placement="learning" title="학습 본문 광고" /></aside>
        </div>
      </div>
      <LearningFooter />
      <ComplianceDock />
    </main>
  );
}

function MethodologyPage() {
  return (
    <main className="learning-page theme-light">
      <SiteNav />
      <div className="learning-container">
        <LearningHero eyebrow="분석 방법론" title="이 점수는 무엇을 뜻하나요?" summary="점수와 상태는 최근 확정 일봉에서 미리 정한 기술적 조건이 함께 나타났는지를 요약한 교육용 정렬값입니다."><a className="back-learning-link" href="/learn">← 학습 홈으로</a></LearningHero>
        <article className="methodology-article">{methodologySections.map((section) => <section key={section.title} className="guide-article-section"><h2>{section.title}</h2>{section.body.map((paragraph) => <p key={paragraph}>{paragraph}</p>)}</section>)}<div className="source-box"><strong>데이터 출처</strong><p>금융위원회 공공데이터포털의 주식시세정보·지수시세정보를 사용합니다. 화면에는 원시 시세와 원시 API 응답을 공개하지 않습니다.</p><a href="https://www.data.go.kr/data/15094808/openapi.do" target="_blank" rel="noreferrer">주식시세정보 원문 보기 <ExternalLink size={14} /></a></div></article>
        <AdSenseSlot placement="learning" title="방법론 본문 광고" />
      </div>
      <LearningFooter />
      <ComplianceDock />
    </main>
  );
}

function AboutPage() {
  return (
    <main className="learning-page theme-light">
      <SiteNav />
      <div className="learning-container">
        <LearningHero eyebrow="운영 안내" title="기술지표를 함께 공부하는 공개 서비스" summary="MesuGak은 투자상담이나 주문 서비스가 아니라, 공개 데이터로 계산한 기술지표 해석 방법을 설명하는 개인 프로젝트입니다."><a className="back-learning-link" href="/learn">← 학습 홈으로</a></LearningHero>
        <div className="about-grid"><article className="about-card"><ShieldCheck size={21} /><h2>운영 원칙</h2><p>최근 거래일 확정 일봉을 사용하고, 공개 화면에는 자체 계산 결과와 해설만 표시합니다. 원시 가격·거래량·차트·관리자용 계정 정보는 공개하지 않습니다.</p></article><article className="about-card"><BookOpen size={21} /><h2>편집 원칙</h2><p>지표의 이름을 나열하는 데서 그치지 않고 조건의 뜻, 그렇게 읽을 수 있는 이유, 해석이 빗나갈 수 있는 상황을 함께 설명합니다. 자동 분석 결과는 교육용 참고자료로만 제공합니다.</p></article><article className="about-card"><Mail size={21} /><h2>문의</h2><p>개인정보 및 서비스 관련 문의는 아래 이메일로 보내주세요.</p><a className="contact-link" href="mailto:or_not_official@naver.com">or_not_official@naver.com</a></article></div>
        <section className="support-note"><h2>커피로 응원하기</h2><p>후원은 서비스 운영을 위한 자율적인 응원이며, 후원 여부에 따라 추가 분석·개인별 추천·우선 답변을 제공하지 않습니다.</p><a href={import.meta.env.VITE_SUPPORT_URL || '#'} className={!import.meta.env.VITE_SUPPORT_URL ? 'disabled' : ''} target={import.meta.env.VITE_SUPPORT_URL ? '_blank' : undefined} rel={import.meta.env.VITE_SUPPORT_URL ? 'noopener noreferrer' : undefined} aria-disabled={!import.meta.env.VITE_SUPPORT_URL}>커피 후원 링크 {import.meta.env.VITE_SUPPORT_URL ? <ExternalLink size={14} /> : null}</a></section>
      </div>
      <LearningFooter />
      <ComplianceDock />
    </main>
  );
}

export function LearningPage({ pageKey = 'home' }) {
  useEffect(() => {
    const page = pageKey === 'home' ? { label: '기술지표 학습 홈' } : pageKey === 'methodology' ? { label: '분석 방법론' } : pageKey === 'about' ? { label: '운영 안내' } : Object.values(indicatorPages).find((candidate) => candidate.slug === pageKey);
    document.title = pageTitle(page || { label: '기술지표 학습' });
  }, [pageKey]);
  if (pageKey === 'methodology') return <MethodologyPage />;
  if (pageKey === 'about') return <AboutPage />;
  if (pageKey === 'home') return <LearningHome />;
  const guidePage = Object.values(indicatorPages).find((candidate) => candidate.slug === pageKey) || indicatorPages.ichimoku;
  return <GuidePage page={guidePage} />;
}
