/* eslint-disable react-refresh/only-export-components */
import { Fragment, useEffect, useMemo, useState } from 'react';
import { ArrowRight, BookOpen, ExternalLink, Mail, ShieldCheck } from 'lucide-react';
import { AdSenseSlot } from './AdSenseSlot.jsx';
import CaseStudyVisual from './CaseStudyVisuals.jsx';
import { BRAND_FULL, BRAND_SHORT } from './brand';
import { ComplianceDock } from './LegalPages.jsx';
import {
  educationalGuides,
} from './analysisEducationContent.jsx';
import { articleBySlug, indicatorArticles } from './indicatorArticles.js';
import './learning.css';
import { pageCopy } from './content/pageCopy.js';
import BandCalculationLab from './BandCalculationLab.jsx';

import {
  indicatorPages, CONTENT_UPDATED_ON, editorialChangelog, workedExamples, learningReferences, learningChecks,
  methodologySections, caseStudies, labConditions, glossaryTerms, methodologySupplementSections, indicatorSupplementSections,
} from './content/learningCopy.js';
export { CONTENT_UPDATED_ON };

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
    if (slug === 'articles') return 'articles';
    if (slug.startsWith('articles/') && articleBySlug[slug.slice('articles/'.length)]) return slug;
    if (slug === 'cases' || slug === 'lab' || slug === 'glossary') return slug;
    return Object.values(indicatorPages).some((page) => page.slug === slug) ? slug : '';
  }
  return '';
}

export function SiteNav() {
  return (
    <nav className="learning-nav" aria-label="사이트 주요 메뉴">
      <a className="learning-nav-brand" href="/"><span>{BRAND_FULL}</span><strong>{BRAND_SHORT}</strong></a>
      <div className="learning-nav-links">
        <a href="/learn">지표 학습</a>
        <a href="/learn/articles">지표 읽을거리</a>
        <a href="/learn/cases">사례 수업</a>
        <a href="/learn/lab">조건 실험실</a>
        <a href="/learn/glossary">용어집</a>
        <a href="/methodology">분석 방법론</a>
        <a href="/about">운영 안내</a>
      </div>
      <a className="learning-nav-analysis-cta" href="/analysis">종목 분석 <ArrowRight size={16} aria-hidden="true" /></a>
    </nav>
  );
}

export function LearningFooter() {
  return (
    <footer className="learning-footer">
      <small>콘텐츠 안내 수정일 {CONTENT_UPDATED_ON} · 문의: or_not_official@naver.com</small>
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
          eyebrow={pageCopy.learning.eyebrow}
          title={pageCopy.learning.title}
          summary={pageCopy.learning.summary}
        >
          <div className="learning-hero-actions"><a className="primary-learning-button" href="/analysis">분석된 종목 보러 가기 <ArrowRight size={16} /></a><a className="secondary-learning-button" href="/learn/cases">사례 수업으로 먼저 배우기</a></div>
        </LearningHero>

        <section className="learning-section" aria-labelledby="learning-guides-title">
          <div className="section-heading"><span>{pageCopy.learning.guides.label}</span><h2 id="learning-guides-title">{pageCopy.learning.guides.title}</h2><p>{pageCopy.learning.guides.summary}</p></div>
          <div className="guide-grid">{Object.values(indicatorPages).map((page) => <GuideCard key={page.slug} page={page} />)}</div>
        </section>

        <section className="learning-section article-home-callout" aria-labelledby="article-home-title">
          <div><span>{pageCopy.learning.articles.label}</span><h2 id="article-home-title">{pageCopy.learning.articles.title}</h2><p>{pageCopy.learning.articles.summary}</p></div>
          <a className="text-link-button" href="/learn/articles">지표 읽을거리 보기 <ArrowRight size={16} /></a>
        </section>

        <section className="learning-section learning-method-callout" aria-labelledby="learning-method-title">
          <div><span>{pageCopy.learning.method.label}</span><h2 id="learning-method-title">{pageCopy.learning.method.title}</h2><p>{pageCopy.learning.method.summary}</p></div>
          <a className="text-link-button" href="/methodology">방법론 읽기 <ArrowRight size={16} /></a>
        </section>

        <section className="learning-section learning-practice-section" aria-labelledby="learning-practice-title">
          <div className="section-heading"><span>{pageCopy.learning.practice.label}</span><h2 id="learning-practice-title">{pageCopy.learning.practice.title}</h2><p>{pageCopy.learning.practice.summary}</p></div>
          <div className="guide-grid practice-grid">
            <a className="guide-card practice-card" href="/learn/cases"><div className="guide-card-top"><span>사례 수업 8편</span><ArrowRight size={17} /></div><p>구름대는 위인데 RSI는 내려갈 때, 무엇부터 봐야 할까요? 그림과 숫자로 여덟 장면을 따라가 봅니다.</p><small>그림 보기 · 숫자 읽기 · 다시 확인하기</small></a>
            <a className="guide-card practice-card" href="/learn/lab"><div className="guide-card-top"><span>조건 조합 실험실</span><ArrowRight size={17} /></div><p>조건을 골라 보면 좋아 보이는 점과 더 확인해야 할 점이 나란히 나와요.</p><small>가상 조건으로 직접 연습하기</small></a>
            <a className="guide-card practice-card" href="/learn/glossary"><div className="guide-card-top"><span>기술지표 용어집</span><ArrowRight size={17} /></div><p>일봉·기준일·추세·변동성 같은 기본 용어를 짧은 정의와 실제 읽는 순서로 정리합니다.</p><small>용어 · 예시 · 해석의 한계</small></a>
          </div>
        </section>
      </div>
      <LearningFooter />
      <ComplianceDock />
    </main>
  );
}

function GuidePage({ page }) {
  const guide = educationalGuides[page.guideKey];
  const learningCheck = learningChecks[page.slug];
  const workedExample = workedExamples[page.slug];
  const lessonOrder = Object.values(indicatorPages);
  const nextLesson = lessonOrder[lessonOrder.findIndex((item) => item.slug === page.slug) + 1];
  const sections = [...page.sections, ...(indicatorSupplementSections[page.slug] || [])];
  return (
    <main className="learning-page theme-light">
      <SiteNav />
      <div className="learning-container">
        <LearningHero eyebrow={`지표 학습 · ${page.label}`} title={page.label} summary={page.summary}>
          <div className="learning-hero-actions"><a className="primary-learning-button" href="/analysis">종목 분석 결과 보기 <ArrowRight size={16} /></a><a className="back-learning-link" href="/learn">← 모든 지표 보기</a><a className="back-learning-link" href={`/learn/articles/${page.slug}`}>계산과 배경 깊이 읽기 →</a></div>
        </LearningHero>
        {page.slug === 'valuation' && <section className="guide-article-note" role="note"><ShieldCheck size={19} /><p>{'\uC774 \uD398\uC774\uC9C0\uC758 PER\u00B7PBR\uC740 \uC77D\uB294 \uBC95\uB9CC \uC548\uB0B4\uD558\uBA70, \uC885\uD569\uC810\uC218\uC5D0\uB294 \uBC18\uC601\uD558\uC9C0 \uC54A\uC2B5\uB2C8\uB2E4.'}</p></section>}
        <div className="guide-article-layout">
          <article className="guide-article">
            {sections.map((section) => <section key={section.title} className="guide-article-section"><h2>{section.title}</h2>{section.body.map((paragraph) => <p key={paragraph}>{paragraph}</p>)}</section>)}
            {workedExample && <section className="guide-worked-example" aria-labelledby={page.slug + '-worked-title'}>
              <div className="section-heading"><span>가상 숫자로 직접 확인하기</span><h2 id={page.slug + '-worked-title'}>{workedExample.title}</h2><p>{workedExample.setup}</p></div>
              <ol className="guide-worked-steps">{workedExample.steps.map((step) => <li key={step.label}><strong>{step.label}</strong><code>{step.calculation}</code><p>{step.meaning}</p></li>)}</ol>
              <p className="guide-worked-reading"><strong>이렇게 읽어 볼 수 있어요</strong>{workedExample.reading}</p>
               <p className="guide-worked-caveat"><strong>한 번 더 볼 점</strong>{workedExample.caveat}</p>
            </section>}
            {guide?.points?.length ? <section className="guide-visual-section"><div className="section-heading"><span>그림으로 확인하기</span><h2>그림으로 보는 {page.label}</h2><p>선이 어디서 만나고 갈라지는지 그림으로 살펴볼게요. 이해를 돕기 위해 만든 도식입니다.</p></div><div className="guide-visual-grid">{guide.points.map((point) => <article key={point.label} className="guide-visual-card"><div className="guide-visual-art">{point.graphic}</div><h3>{point.label}</h3><p>{point.desc}</p></article>)}</div></section> : null}
            {learningCheck && <section className="learning-check-section" aria-labelledby={page.slug + '-check-title'}>
              <div className="section-heading"><span>이해 점검</span><h2 id={page.slug + '-check-title'}>이럴 땐 어떻게 읽을까요?</h2><p>조건 하나를 바꿔 보면 앞에서 배운 해석도 달라질까요?</p></div>
              <div className="learning-check-card">
                <h3>{learningCheck.title}</h3>
                <p className="learning-check-question">{learningCheck.question}</p>
                <details><summary>예시로 생각해 본 답</summary><p>{learningCheck.answer}</p></details>
                <p className="learning-counterexample"><strong>다른 장면에서는?</strong>{learningCheck.counterexample}</p>
              </div>
            </section>}
            <section className="guide-article-note"><ShieldCheck size={19} /><p>수업 속 숫자는 이해를 돕기 위해 만든 값이에요. 실제 종목이나 과거 수익률을 보여 주지는 않습니다. 같은 신호도 시장 상황과 데이터 상태에 따라 다르게 읽힐 수 있어요.</p></section>
            <div className="source-box guide-source-box">
              <strong>계산 기준과 참고 자료</strong>
              <p>이 수업의 용어와 해석 순서는 서비스의 분석 방법론을 기준으로 정리했습니다. 공개 분석은 금융위원회 공공데이터포털의 최근 거래일 확정 일봉을 사용하며, 수업 페이지에서는 원시 가격·지표 수치·API 응답을 재배포하지 않습니다.</p>
              <p>아래 외부 참고 자료는 지표의 일반 정의와 계산을 더 읽기 위한 링크입니다. 실제 V2 계산 설정은 이 사이트의 방법론 설명과 가상 예시를 따르며, 다른 서비스의 숫자와는 입력 기간·표준편차 정의·당일 포함 여부가 다를 수 있습니다.</p>
              <div className="source-box-links">
                <a href="/methodology">분석 방법론 읽기 <ArrowRight size={14} /></a>
                {learningReferences[page.slug] && <a href={learningReferences[page.slug].href} target="_blank" rel="noopener noreferrer">{learningReferences[page.slug].label} <ExternalLink size={14} /></a>}
                {learningReferences[page.slug]?.implementationHref && <a href={learningReferences[page.slug].implementationHref} target="_blank" rel="noopener noreferrer">{learningReferences[page.slug].implementationLabel} <ExternalLink size={14} /></a>}
                <a href="https://www.data.go.kr/data/15094808/openapi.do" target="_blank" rel="noreferrer">주식시세정보 출처 <ExternalLink size={14} /></a>
              </div>
            </div>
            <AdSenseSlot placement="learning" title="광고" className="learning-inline-ad" />
          </article>
          <aside className="guide-side-rail"><div className="guide-side-card"><span>다음에 읽기</span><a href={`/learn/articles/${page.slug}`}>계산과 배경 깊이 읽기 <ArrowRight size={15} /></a>{nextLesson ? <a href={`/learn/${nextLesson.slug}`}>다음 지표 · {nextLesson.label} <ArrowRight size={15} /></a> : <a href="/learn/cases">사례 수업에서 조합하기 <ArrowRight size={15} /></a>}<a href="/methodology">종합점수 방법론 <ArrowRight size={15} /></a><a href="/analysis">실제 분석 화면 <ArrowRight size={15} /></a></div></aside>
        </div>
      </div>
      <LearningFooter />
      <ComplianceDock />
    </main>
  );
}

function ArticlesIndexPage() {
  return (
    <main className="learning-page theme-light">
      <SiteNav />
      <div className="learning-container">
        <LearningHero eyebrow={pageCopy.articles.eyebrow} title={pageCopy.articles.title} summary={pageCopy.articles.summary}>
          <a className="back-learning-link" href="/learn">← 짧은 지표 수업으로</a>
        </LearningHero>
        <section className="article-index-intro"><p>{pageCopy.articles.intro}</p></section>
        <div className="article-index-grid">
          {indicatorArticles.map((article, index) => (
            <a className="article-index-card" href={`/learn/articles/${article.slug}`} key={article.slug}>
              <span className="article-index-number">{String(index + 1).padStart(2, '0')} / {article.category}</span>
              <h2>{article.title}</h2>
              <p>{article.deck}</p>
              <span className="article-index-more">약 {article.minutes}분 · 글 읽기 <ArrowRight size={16} /></span>
            </a>
          ))}
        </div>
      </div>
      <LearningFooter />
      <ComplianceDock />
    </main>
  );
}

function IndicatorArticlePage({ article }) {
  const index = indicatorArticles.findIndex((item) => item.slug === article.slug);
  const next = indicatorArticles[(index + 1) % indicatorArticles.length];
  const guide = educationalGuides[article.guideKey];
  return (
    <main className="learning-page theme-light">
      <SiteNav />
      <div className="learning-container">
        <LearningHero eyebrow={`지표 읽을거리 · ${article.category} · 약 ${article.minutes}분`} title={article.title} summary={article.deck}>
          <a className="back-learning-link" href="/learn/articles">← 글 목록</a>
        </LearningHero>
        <div className="longread-layout">
          <article className="longread-article">
            <p className="longread-lead">{article.lead}</p>
            {guide?.points?.[0] && <figure className="longread-figure"><div className="longread-figure-art">{guide.points[0].graphic}</div><figcaption>{guide.points[0].label} · 이해를 돕기 위해 만든 도식</figcaption></figure>}
            {article.sections.map((section, sectionIndex) => (
              <Fragment key={section.title}>
              <section className="longread-section" id={`section-${sectionIndex + 1}`}>
                <span className="longread-section-number">{String(sectionIndex + 1).padStart(2, '0')}</span>
                <h2 id={`section-${sectionIndex + 1}-title`}>{section.title}</h2>
                {section.formula && <div className="longread-formula"><span>계산식</span><code>{section.formula}</code></div>}
                {section.blocks.map((block, blockIndex) => block.type === 'paragraph' ? <p key={blockIndex}>{block.text}</p> : (
                  <div className="longread-table-wrap" role="region" aria-label={`${section.title} 표`} tabIndex={0} key={blockIndex}>
                    <table className="longread-table" aria-labelledby={`section-${sectionIndex + 1}-title`}>
                      <thead><tr>{block.headers.map((header, columnIndex) => <th scope="col" key={columnIndex}>{header}</th>)}</tr></thead>
                      <tbody>{block.rows.map((row, rowIndex) => <tr key={rowIndex}>{row.map((cell, columnIndex) => columnIndex === 0 ? <th scope="row" key={columnIndex}>{cell}</th> : <td key={columnIndex}>{cell}</td>)}</tr>)}</tbody>
                    </table>
                  </div>
                ))}
                {section.example && <div className="longread-example"><strong>숫자로 따라가기</strong><dl><div><dt>조건</dt><dd>{section.example.input}</dd></div><div><dt>계산</dt><dd>{section.example.calculation}</dd></div></dl><p>{section.example.reading}</p></div>}
              </section>
              {(sectionIndex === 2 || sectionIndex === 6) && <AdSenseSlot placement="learning" title="광고" className="learning-inline-ad" />}
              </Fragment>
            ))}
            <section className="longread-sources" aria-label="참고 자료"><h2>더 확인할 자료</h2><p>역사·일반 정의는 아래 원전과 기관 설명을 확인했습니다. MesuGak의 실제 설정은 V2 지표 계산 코드와 <a href="/methodology">분석 방법론</a>을 기준으로 서술했습니다.</p><ul>{article.sources.map((source) => <li key={source.href}><a href={source.href} target="_blank" rel="noopener noreferrer">{source.label} <ExternalLink size={14} /></a></li>)}</ul><p>수정일 {article.updatedOn} · 설명 속 계산 예시는 가상 값입니다. 오류 제보: <a href="mailto:or_not_official@naver.com">or_not_official@naver.com</a></p></section>
            {article.slug === 'bollinger' && <div className="guide-article-note"><p>숫자를 직접 바꿔 보고 싶다면 <a href="/learn/lab#band-calculator">밴드 계산 실습</a>에서 상승·하락 순서와 표준편차 방식을 비교해 보세요.</p></div>}
            <nav className="longread-end-links" aria-label="이어 읽기"><a href={`/learn/${article.slug}`}>짧은 수업과 그림 보기 <ArrowRight size={16} /></a><a href={`/learn/articles/${next.slug}`}>다음 글 · {next.title} <ArrowRight size={16} /></a></nav>
          </article>
          <aside className="longread-aside"><div className="guide-side-card"><span>이 글에서 읽기</span>{article.sections.map((section, sectionIndex) => <a href={`#section-${sectionIndex + 1}`} key={section.title}>{section.title}</a>)}<a href="/learn/cases">사례 수업으로 이어가기 <ArrowRight size={15} /></a></div></aside>
        </div>
      </div>
      <LearningFooter />
      <ComplianceDock />
    </main>
  );
}

function CaseStudiesPage() {
  return (
    <main className="learning-page theme-light">
      <SiteNav />
      <div className="learning-container">
        <LearningHero eyebrow={pageCopy.cases.eyebrow} title={pageCopy.cases.title} summary={pageCopy.cases.summary}>
          <a className="back-learning-link" href="/learn">← 지표 학습 홈으로</a>
        </LearningHero>
        <article className="case-study-collection">
          <div className="guide-article-note" role="note"><ShieldCheck size={19} /><p>{pageCopy.cases.note}</p></div>
          {caseStudies.map((study, index) => (
            <Fragment key={study.title}>
            <section className="case-study">
              <div className="case-study-heading"><span>{study.eyebrow}</span><h2>{String(index + 1).padStart(2, '0')}. {study.title}</h2><p>{study.question}</p></div>
              <CaseStudyVisual visual={study.visual} />
              <div className="case-study-columns">
                <div><h3>먼저 관찰할 것</h3><ul>{study.observation.map((item) => <li key={item}>{item}</li>)}</ul></div>
                <div><h3>이렇게 해석할 수도 있어요</h3><p>{study.interpretation}</p></div>
              </div>
              {study.comparison && <section className="case-study-comparison" aria-label={study.comparison.heading}>
                <h3>{study.comparison.heading}</h3>
                <p>{study.comparison.setup}</p>
                <p className="case-study-comparison-formula"><strong>비교식</strong><code>{study.comparison.formula}</code></p>
                <div className="case-study-comparison-grid">
                  {study.comparison.rows.map((row) => <article className="case-study-comparison-card" key={row.company}>
                    <h4>{row.company}</h4>
                    <dl>
                      <div><dt>기업 PBR</dt><dd>0.8배</dd></div>
                      <div><dt>동종 업종 중앙값</dt><dd>{row.peerMedian}</dd></div>
                      <div><dt>중앙값 대비 계산</dt><dd><code>{row.calculation}</code></dd></div>
                    </dl>
                    <p>{row.meaning}</p>
                  </article>)}
                </div>
                <p className="case-study-comparison-caveat">{study.comparison.caveat}</p>
                <a className="case-study-comparison-source" href={study.comparison.reference.href} target="_blank" rel="noopener noreferrer">{study.comparison.reference.label} <ExternalLink size={14} /></a>
              </section>}
              {study.example && <section className="case-study-example" aria-label={study.example.heading}>
                <h3>{study.example.heading}</h3>
                <dl>{study.example.rows.map((row) => <div key={row.label}><dt>{row.label}</dt><dd>{row.value}</dd></div>)}</dl>
                {study.example.note && <p>{study.example.note}</p>}
              </section>}
              <div className="case-study-caution"><strong>잠깐, 이런 장면도 있어요</strong><p>{study.counterexample}</p></div>
              <div className="case-study-check"><strong>차트를 다시 볼 때</strong><ul>{study.checklist.map((item) => <li key={item}>{item}</li>)}</ul></div>
            </section>
            {(index === 2 || index === 5) && <AdSenseSlot placement="learning" title="광고" className="learning-inline-ad" />}
            </Fragment>
          ))}
        </article>
      </div>
      <LearningFooter />
      <ComplianceDock />
    </main>
  );
}

function ConditionLabPage() {
  const [selectedKeys, setSelectedKeys] = useState(['cloudAbove', 'rsiRecover']);
  const selected = useMemo(() => labConditions.filter((condition) => selectedKeys.includes(condition.key)), [selectedKeys]);

  const toggleCondition = (key) => {
    setSelectedKeys((current) => current.includes(key) ? current.filter((item) => item !== key) : [...current, key]);
  };

  return (
    <main className="learning-page theme-light">
      <SiteNav />
      <div className="learning-container">
        <LearningHero eyebrow={pageCopy.lab.eyebrow} title={pageCopy.lab.title} summary={pageCopy.lab.summary}>
          <a className="back-learning-link" href="/learn">← 지표 학습 홈으로</a>
        </LearningHero>
        <BandCalculationLab />
        <section className="guide-worked-example lab-worked-example" aria-labelledby="lab-worked-example-title">
          <div className="section-heading"><span>{pageCopy.lab.example.label}</span><h2 id="lab-worked-example-title">{pageCopy.lab.example.title}</h2><p>{pageCopy.lab.example.summary}</p></div>
          <ol className="guide-worked-steps">
            <li><strong>상황 보기</strong><p>종가는 구름대 위에 있고, RSI는 전일 28에서 오늘 34로 회복했으며 신호선 31보다 높다고 가정합니다. 볼린저 밴드 폭은 넓어지고 당일 거래량은 최근 평균의 0.8배입니다.</p></li>
            <li><strong>좋아 보이는 점</strong><p>가격이 구름대 위에 있고 RSI도 회복했어요. 가격 위치와 최근 하락 압력이 조금 나아졌다는 단서로 읽을 수 있습니다.</p></li>
            <li><strong>걸리는 점</strong><p>밴드가 넓어진 것만으로는 상승인지 하락인지 알 수 없어요. 거래량도 최근 평균의 0.8배라 돌파에 참여가 늘었다고 보기는 어렵습니다.</p></li>
            <li><strong>다음 날 볼 것</strong><p>다음 확정 일봉에서 종가가 어디로 움직였는지, 밴드 안팎의 위치와 거래량이 어떻게 달라졌는지 살펴보세요. 이 숫자는 연습용이며 점수나 매매 판단을 계산하지 않습니다.</p></li>
          </ol>
        </section>
        <section className="lab-layout" aria-labelledby="lab-title">
          <div className="lab-panel">
            <div className="section-heading"><span>01 · 조건 선택</span><h2 id="lab-title">어떤 신호가 보이나요?</h2><p>조건을 하나 이상 선택해 보세요. 이 도구는 점수나 추천을 계산하지 않습니다.</p></div>
            <div className="lab-condition-grid">
              {labConditions.map((condition) => <label className={`lab-condition ${selectedKeys.includes(condition.key) ? 'selected' : ''}`} key={condition.key}><input type="checkbox" checked={selectedKeys.includes(condition.key)} onChange={() => toggleCondition(condition.key)} /><span><strong>{condition.label}</strong><small>가능한 해석과 한계를 함께 확인</small></span></label>)}
            </div>
          </div>
          <div className="lab-result" aria-live="polite">
            <span className="lab-result-eyebrow">02 · 선택 결과</span>
            <h2>{selected.length ? '선택한 조건 읽기' : '조건을 하나 이상 선택해 주세요'}</h2>
            {selected.length ? <>
              <div className="lab-result-block lab-result-support"><strong>먼저 알 수 있는 것</strong>{selected.map((condition) => <p key={condition.key}><span className="lab-result-item-label">{condition.label}: </span>{condition.support}</p>)}</div>
              <div className="lab-result-block lab-result-caution"><strong>더 확인할 점</strong>{selected.map((condition) => <p key={condition.key}><span className="lab-result-item-label">{condition.label}: </span>{condition.caution}</p>)}</div>
              <div className="lab-result-note"><strong>정리하면</strong><p>여러 조건을 골라도 이 도구는 점수나 추천을 만들지 않습니다. 방향이 정해지지 않은 조건은 따로 구분하고, 기준일과 다음 확정 일봉을 확인해 해석의 강도를 조절해 보세요.</p></div>
            </> : <p className="lab-empty">선택한 조건을 바탕으로 설명이 여기에 표시됩니다.</p>}
          </div>
        </section>
        <section className="guide-article-note lab-disclaimer"><ShieldCheck size={19} /><p>이 실험실은 기술지표의 해석 방법을 연습하기 위한 교육용 도구입니다. 특정 종목의 매수·매도·보유 판단이나 미래 수익률을 계산하지 않습니다.</p></section>
      </div>
      <LearningFooter />
      <ComplianceDock />
    </main>
  );
}

function GlossaryPage() {
  return (
    <main className="learning-page theme-light">
      <SiteNav />
      <div className="learning-container">
        <LearningHero
          eyebrow={pageCopy.glossary.eyebrow}
          title={pageCopy.glossary.title}
          summary={pageCopy.glossary.summary}
        >
          <a className="back-learning-link" href="/learn">← 지표 학습 홈으로</a>
        </LearningHero>
        <section className="editorial-note glossary-intro" aria-labelledby="glossary-intro-title">
          <h2 id="glossary-intro-title">용어집을 읽는 방법</h2>
          <p>{pageCopy.glossary.intro}</p>
          <p>분석 화면에서 낯선 말이 나오면 여기서 찾아보고, <a href="/learn/cases">사례 수업</a>에서 다른 지표와 엇갈릴 때는 어떤지도 살펴보세요. 계산이 궁금하면 <a href="/methodology">분석 방법론</a>으로 이어집니다.</p>
        </section>
        <section className="glossary-section" aria-labelledby="glossary-list-title">
          <div className="section-heading"><span>01 · 기본 용어</span><h2 id="glossary-list-title">뜻과 읽는 방법</h2><p>뜻을 확인한 뒤, 실제 화면에서 그 말을 어떻게 읽을지도 함께 보세요.</p></div>
          <dl className="glossary-list">
            {glossaryTerms.map((item) => (
              <div className="glossary-item" key={item.term}>
                <dt>{item.term}</dt>
                <dd>
                  <p><strong>뜻</strong>{item.meaning}</p>
                  <p><strong>읽는 방법</strong>{item.use}</p>
                </dd>
              </div>
            ))}
          </dl>
          <AdSenseSlot placement="learning" title="광고" className="learning-inline-ad" />
        </section>
        <section className="glossary-faq" aria-labelledby="glossary-faq-title">
          <div className="section-heading"><span>02 · 자주 생기는 오해</span><h2 id="glossary-faq-title">뜻만 알면 충분할까요?</h2></div>
          <details open><summary>종합점수가 높으면 상승 확률도 높다는 뜻인가요?</summary><p>아닙니다. 종합점수는 미리 정한 조건이 함께 나타났는지를 정렬한 내부 요약값입니다. 미래 수익률이나 성공 확률을 계산한 값이 아니며, 비슷한 지표가 같은 흐름을 반복해서 보여줄 수도 있습니다.</p></details>
          <details><summary>기준일이 최근이면 분석을 바로 믿어도 되나요?</summary><p>기준일은 데이터가 언제까지 확정되었는지를 알려주는 정보일 뿐입니다. 지표의 한계, 데이터 누락, 지표 간 충돌을 함께 확인해야 하며 기준일이 최신이어도 해석이 맞는다고 보장하지 않습니다.</p></details>
          <details><summary>PBR이나 RSI의 경계값은 법정 기준인가요?</summary><p>아닙니다. 경계값은 학습을 위해 자주 쓰이는 참고 구간일 뿐이고 업종·시장 국면·계산 기간에 따라 의미가 달라집니다. 이 사이트의 참고 범위는 매수·매도 기준이 아닙니다.</p></details>
          <details><summary>원시 가격을 보지 않고도 지표를 배울 수 있나요?</summary><p>이 사이트는 공개 데이터 이용 범위에 맞춰 원시 시세 대신 가상 도식과 문장형 상태를 사용합니다. 실제 적용을 연습할 때는 해당 데이터의 이용 조건과 기준일을 확인해야 하며, 공개 문장만으로 원시값을 역산하려고 하지 않습니다.</p></details>
        </section>
        <section className="guide-article-note glossary-disclaimer" role="note">
          <ShieldCheck size={19} />
          <p>이 용어집은 기술지표를 읽는 방법을 설명하는 교육 자료입니다. 특정 종목의 취득·처분이나 수익을 권유하지 않으며, 용어 하나만으로 투자 판단을 확정하지 않습니다.</p>
        </section>
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
        <LearningHero eyebrow={pageCopy.methodology.eyebrow} title={pageCopy.methodology.title} summary={pageCopy.methodology.summary}><a className="back-learning-link" href="/learn">← 학습 홈으로</a></LearningHero>
        <section className="editorial-note" aria-labelledby="publication-status-title">
          <h2 id="publication-status-title">먼저 짚고 갈 것</h2>
          <p>여기 적은 산식은 현재 V2 코드 기준입니다. 수업 속 숫자와 그림은 조건을 읽는 연습을 위해 만들었어요. 실제 종목 결과를 옮긴 것은 아닙니다.</p>
          <p>이 설명은 {CONTENT_UPDATED_ON}에 수정했습니다. 공개 분석 화면의 데이터 기준일은 별개예요. 화면에 나온 날짜가 최신 거래일인지 확인해 주세요.</p>
          <p>계산·출처·문장에 오류가 있으면 <a href="mailto:or_not_official@naver.com">or_not_official@naver.com</a>으로 알려 주세요. 확인된 오류는 수정 사유와 함께 기록합니다.</p>
        </section>
        <section className="editorial-note editorial-history" aria-labelledby="editorial-history-title">
          <h2 id="editorial-history-title">콘텐츠 변경 기록</h2>
          <p>학습 내용이나 공개 범위를 언제, 왜 고쳤는지 남겨 두었습니다.</p>
          <ol>
            {editorialChangelog.map((entry) => <li key={`${entry.date}-${entry.title}`}><strong>{entry.date} · {entry.title}</strong><span>{entry.body}</span></li>)}
          </ol>
        </section>
         <article className="methodology-article">{[...methodologySections, ...methodologySupplementSections].map((section) => <section key={section.title} className="guide-article-section"><h2>{section.title}</h2>{section.body.map((paragraph) => <p key={paragraph}>{paragraph}</p>)}</section>)}<div className="source-box"><strong>데이터 출처</strong><p>금융위원회 공공데이터포털의 주식시세정보·지수시세정보를 사용합니다. 화면에는 원시 시세와 원시 API 응답을 공개하지 않습니다.</p><a href="https://www.data.go.kr/data/15094808/openapi.do" target="_blank" rel="noreferrer">주식시세정보 원문 보기 <ExternalLink size={14} /></a></div></article>
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
        <LearningHero eyebrow={pageCopy.about.eyebrow} title={pageCopy.about.title} summary={pageCopy.about.summary}><a className="back-learning-link" href="/learn">← 학습 홈으로</a></LearningHero>
        <div className="about-grid"><article className="about-card"><ShieldCheck size={21} /><h2>{pageCopy.about.cards[0].title}</h2><p>{pageCopy.about.cards[0].body}</p></article><article className="about-card"><BookOpen size={21} /><h2>{pageCopy.about.cards[1].title}</h2><p>{pageCopy.about.cards[1].body}</p></article><article className="about-card"><Mail size={21} /><h2>{pageCopy.about.cards[2].title}</h2><p>{pageCopy.about.cards[2].body}</p><a className="contact-link" href="mailto:or_not_official@naver.com">or_not_official@naver.com</a></article></div>
        <section className="editorial-note" aria-labelledby="analysis-method-origin">
          <h2 id="analysis-method-origin">분석 기준</h2>
          <p>공개 분석에는 제가 실제 분석에 쓰는 기술지표 기준을 코드로 옮겼습니다. 볼린저 밴드·이동평균·일목균형표·RSI·거래량을 함께 보고, 계산할 수 없는 지표가 있으면 그 항목을 빼고 남은 비중을 다시 나눕니다. 자세한 산식과 한계는 <a href="/methodology">점수 계산 방법</a>에 적었습니다.</p>
        </section>
        <section className="editorial-note" aria-labelledby="publication-schedule-title">
          <h2 id="publication-schedule-title">갱신과 지연 처리</h2>
          <p>공개 분석은 장이 끝난 뒤 확정된 일봉을 씁니다. 목록의 기준일은 계산에 쓴 마지막 거래일이에요. 이 날짜만으로 데이터 제공기관이나 서버가 지금 정상적으로 갱신 중인지는 알 수 없습니다.</p>
          <p>새 거래일 자료가 나오기 전에는 이전 결과가 계속 보일 수 있어요. 현재 상황으로 읽기 전에 기준일을 살펴보고, 날짜가 오래되었거나 자료 부족 안내가 있다면 그 점을 감안해 주세요.</p>
        </section>
        <section className="editorial-note"><h2>콘텐츠 운영 기록</h2><p>지표 수업은 조건의 뜻, 계산 예시, 해석이 약해지는 반대 근거, 다음에 확인할 질문을 중심으로 구성합니다. 수치 예시는 가상이며 성과 검증이나 추천 근거로 사용하지 않습니다.</p><p>이 안내의 최근 수정일은 {CONTENT_UPDATED_ON}입니다. 계산·출처·문장 오류가 있으면 <a href="mailto:or_not_official@naver.com">or_not_official@naver.com</a>으로 알려 주세요. 확인 후 수정한 내용과 사유를 편집 기록에 남깁니다.</p></section>
         {import.meta.env.VITE_SUPPORT_URL && <section className="support-note"><h2>커피로 응원하기</h2><p>후원은 서비스 운영을 위한 자율적인 응원이며, 후원 여부에 따라 추가 분석·개인별 추천·우선 답변을 제공하지 않습니다.</p><a href={import.meta.env.VITE_SUPPORT_URL} target="_blank" rel="noopener noreferrer">커피 후원 링크 <ExternalLink size={14} /></a></section>}
      </div>
      <LearningFooter />
      <ComplianceDock />
    </main>
  );
}

export function LearningPage({ pageKey = 'home' }) {
  useEffect(() => {
    const article = pageKey.startsWith('articles/') ? articleBySlug[pageKey.slice('articles/'.length)] : null;
    const page = article ? { label: article.title } : pageKey === 'articles' ? { label: '지표 읽을거리' } : pageKey === 'home' ? { label: '기술지표 학습 홈' } : pageKey === 'methodology' ? { label: '분석 방법론' } : pageKey === 'about' ? { label: '운영 안내' } : pageKey === 'cases' ? { label: '사례 수업' } : pageKey === 'lab' ? { label: '조건 조합 실험실' } : pageKey === 'glossary' ? { label: '기술지표 용어집' } : Object.values(indicatorPages).find((candidate) => candidate.slug === pageKey);
    document.title = pageTitle(page || { label: '기술지표 학습' });
  }, [pageKey]);
  if (pageKey === 'methodology') return <MethodologyPage />;
  if (pageKey === 'about') return <AboutPage />;
  if (pageKey === 'cases') return <CaseStudiesPage />;
  if (pageKey === 'lab') return <ConditionLabPage />;
  if (pageKey === 'glossary') return <GlossaryPage />;
  if (pageKey === 'home') return <LearningHome />;
  if (pageKey === 'articles') return <ArticlesIndexPage />;
  if (pageKey.startsWith('articles/') && articleBySlug[pageKey.slice('articles/'.length)]) return <IndicatorArticlePage article={articleBySlug[pageKey.slice('articles/'.length)]} />;
  const guidePage = Object.values(indicatorPages).find((candidate) => candidate.slug === pageKey) || indicatorPages.ichimoku;
  return <GuidePage page={guidePage} />;
}
