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
        <AdSenseSlot placement="learning" title="광고" className="learning-inline-ad" />
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
        {page.slug === 'valuation' && <section className="guide-article-note" role="note"><ShieldCheck size={19} /><p>PER·PBR·ROE는 차트 지표와 성격이 다른 재무 지표이므로 기술적 종합점수에 반영하지 않고, 기업의 기초 체력을 점검하는 별도 참고값으로 다룹니다.</p></section>}
        <div className="guide-article-layout">
          <article className="guide-article">
            {sections.map((section) => <section key={section.title} className="guide-article-section"><h2>{section.title}</h2>{section.body.map((paragraph) => <p key={paragraph}>{paragraph}</p>)}</section>)}
            {workedExample && <section className="guide-worked-example" aria-labelledby={page.slug + '-worked-title'}>
              <div className="section-heading"><span>숫자로 직접 확인하기</span><h2 id={page.slug + '-worked-title'}>{workedExample.title}</h2><p>{workedExample.setup}</p></div>
              <ol className="guide-worked-steps">{workedExample.steps.map((step) => <li key={step.label}><strong>{step.label}</strong><code>{step.calculation}</code><p>{step.meaning}</p></li>)}</ol>
              <p className="guide-worked-reading"><strong>이렇게 읽어 볼 수 있어요</strong>{workedExample.reading}</p>
               <p className="guide-worked-caveat"><strong>한 번 더 볼 점</strong>{workedExample.caveat}</p>
            </section>}
            {guide?.points?.length ? <section className="guide-visual-section"><div className="section-heading"><span>그림으로 확인하기</span><h2>그림으로 보는 {page.label}</h2><p>선이 어디서 만나고 갈라지는지 핵심 패턴을 그림으로 비교해 보세요.</p></div><div className="guide-visual-grid">{guide.points.map((point) => <article key={point.label} className="guide-visual-card"><div className="guide-visual-art">{point.graphic}</div><h3>{point.label}</h3><p>{point.desc}</p></article>)}</div></section> : null}
            {learningCheck && <section className="learning-check-section" aria-labelledby={page.slug + '-check-title'}>
              <div className="section-heading"><span>이해 점검</span><h2 id={page.slug + '-check-title'}>이럴 땐 어떻게 읽을까요?</h2><p>조건 하나를 바꿔 보면 앞에서 배운 해석도 달라질까요?</p></div>
              <div className="learning-check-card">
                <h3>{learningCheck.title}</h3>
                <p className="learning-check-question">{learningCheck.question}</p>
                <details><summary>예시로 생각해 본 답</summary><p>{learningCheck.answer}</p></details>
                <p className="learning-counterexample"><strong>다른 장면에서는?</strong>{learningCheck.counterexample}</p>
              </div>
            </section>}
            <div className="source-box guide-source-box">
              <strong>계산 기준과 참고 자료</strong>
              <p>MesuGak은 금융위원회 공공데이터포털의 최근 거래일 확정 일봉을 기준으로 이 지표를 계산합니다. 차트 서비스마다 계산 기간, 표준편차 방식(표본·모집단), 평활법이나 당일 포함 여부가 다를 수 있으므로 아래 방법론과 원전 자료에서 정확한 산식을 함께 확인해 보세요.</p>
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
        <AdSenseSlot placement="learning" title="광고" className="learning-inline-ad" />
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
            {guide?.points?.[0] && <figure className="longread-figure"><div className="longread-figure-art">{guide.points[0].graphic}</div><figcaption>{guide.points[0].label} · 핵심 구조 도식</figcaption></figure>}
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
            <section className="longread-sources" aria-label="참고 자료"><h2>더 확인할 자료</h2><p>역사·일반 정의는 아래 원전과 기관 설명을 확인했습니다. MesuGak의 실제 설정은 V2 지표 계산 코드와 <a href="/methodology">분석 방법론</a>을 기준으로 서술했습니다.</p><ul>{article.sources.map((source) => <li key={source.href}><a href={source.href} target="_blank" rel="noopener noreferrer">{source.label} <ExternalLink size={14} /></a></li>)}</ul><p>문서 수정일 {article.updatedOn} · 내용 문의 및 오류 제보: <a href="mailto:or_not_official@naver.com">or_not_official@naver.com</a></p></section>
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

function summarizeLabSelection(selectedKeys) {
  const hasPositive = selectedKeys.includes('cloudAbove') || selectedKeys.includes('rsiRecover');
  const hasCaution = selectedKeys.includes('volumeWeak') || selectedKeys.includes('maFalling');
  const hasBandExpand = selectedKeys.includes('bandExpand');

  if (selectedKeys.length === 1) {
    if (hasBandExpand) {
      return '밴드 폭 확대는 변동성이 커졌다는 신호일 뿐 방향을 뜻하지 않습니다. 구름대 위치나 RSI, 거래량 조건을 함께 선택해 어느 쪽으로 변동성이 열리는지 비교해 보세요.';
    }
    return '단일 조건만 선택했습니다. 하나의 지표만으로는 돌파나 추세의 지속성을 판단하기 어려우므로, 거래량이나 중기 이동평균선 조건을 함께 선택해 신호가 일치하는지 대조해 보세요.';
  }
  if (hasPositive && hasCaution) {
    return '긍정적인 위치·모멘텀 신호와 거래량 부족·중기 추세 약세 조건이 함께 선택되었습니다. 단기 반등이나 돌파가 나타나더라도 거래 참여가 약하거나 60일선이 하락 중이면 되밀릴 수 있으므로, 다음 확정 일봉에서 거래량 회복과 지지 유지 여부를 먼저 확인해 보세요.';
  }
  if (hasPositive && hasBandExpand) {
    return '우호적인 가격·모멘텀 조건에 변동성 확대(밴드 폭 확장)가 더해진 조합입니다. 밴드 폭 자체는 방향을 말해주지 않으므로, 종가가 중심선과 구름대 위를 유지하며 상단 밴드 쪽으로 뻗어 가는지와 거래량이 동반되는지를 함께 점검해 보세요.';
  }
  if (hasCaution && hasBandExpand) {
    return '변동성이 커지는 구간(밴드 폭 확장)에서 거래량이 약하거나 중기 추세가 하락 중인 조합입니다. 밴드가 아래쪽으로 열리며 하락 변동성이 확대되는 장면일 수 있으므로 하단 밴드 이탈 여부와 지지선 반응을 주의 깊게 살펴야 합니다.';
  }
  if (hasPositive) {
    return '가격 위치(구름대 위)와 단기 모멘텀 회복(RSI)이 같은 방향을 가리키는 조합입니다. 두 신호가 맞물릴 때는 돌파 과정에서 상대 거래량이 평균 이상으로 붙는지, 60일 이동평균선의 기울기도 돌아서는지 추가로 확인하면 추세의 신뢰도를 높일 수 있습니다.';
  }
  return '거래 참여가 약하고 중기 이동평균선도 하락 방향인 조합입니다. 단기 반등이 나타나더라도 추세 전환으로 이어지기엔 힘이 부족할 수 있으므로, 거래량이 최근 평균을 회복하고 평균선 기울기가 완만해지는지 먼저 관찰해 보세요.';
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
            <li><strong>다음 날 볼 것</strong><p>다음 확정 일봉에서 종가가 구름대 위를 유지하는지, 밴드 중심선 위에서 거래량이 평균 수준으로 올라오는지 함께 확인하면 반등의 지속성을 판단하기 좋습니다.</p></li>
          </ol>
        </section>
        <section className="lab-layout" aria-labelledby="lab-title">
          <div className="lab-panel">
            <div className="section-heading"><span>01 · 조건 선택</span><h2 id="lab-title">어떤 신호가 보이나요?</h2><p>조건을 하나 이상 선택해 보세요. 함께 나타난 신호들의 의미와 추가로 확인할 점을 나란히 비교할 수 있습니다.</p></div>
            <div className="lab-condition-grid">
              {labConditions.map((condition) => <label className={`lab-condition ${selectedKeys.includes(condition.key) ? 'selected' : ''}`} key={condition.key}><input type="checkbox" checked={selectedKeys.includes(condition.key)} onChange={() => toggleCondition(condition.key)} /><span><strong>{condition.label}</strong><small>{condition.hint}</small></span></label>)}
            </div>
          </div>
          <div className="lab-result" aria-live="polite">
            <span className="lab-result-eyebrow">02 · 선택 결과</span>
            <h2>{selected.length ? '선택한 조건 읽기' : '조건을 하나 이상 선택해 주세요'}</h2>
            {selected.length ? <>
              <div className="lab-result-block lab-result-support"><strong>먼저 알 수 있는 것</strong>{selected.map((condition) => <p key={condition.key}><span className="lab-result-item-label">{condition.label}: </span>{condition.support}</p>)}</div>
              <div className="lab-result-block lab-result-caution"><strong>더 확인할 점</strong>{selected.map((condition) => <p key={condition.key}><span className="lab-result-item-label">{condition.label}: </span>{condition.caution}</p>)}</div>
              <div className="lab-result-note"><strong>조합해서 읽는 포인트</strong><p>{summarizeLabSelection(selectedKeys)}</p></div>
            </> : <p className="lab-empty">왼쪽에서 조건을 하나 이상 선택하면 각 조건의 의미와 조합 해석이 여기에 표시됩니다.</p>}
          </div>
        </section>
        <AdSenseSlot placement="learning" title="광고" className="learning-inline-ad" />
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
          <details open><summary>종합점수가 높으면 상승 확률도 높다는 뜻인가요?</summary><p>종합점수는 다섯 가지 기술적 조건이 얼마나 동시에 충족되었는지를 0~100으로 요약한 정렬 지표입니다. 상승 확률을 뜻하지 않으며, 추세 지표들이 같은 가격 움직임을 중복 반영해 점수가 높아진 것인지 세부 근거를 함께 확인해야 합니다.</p></details>
          <details><summary>기준일이 최근이면 분석 결과를 그대로 적용해도 되나요?</summary><p>기준일은 장 마감 후 확정된 일봉 데이터의 날짜입니다. 장중 실시간 변동이나 공시·이벤트는 반영되지 않으므로, 기준일 확인과 더불어 지표 간 충돌 여부를 함께 살펴야 합니다.</p></details>
          <details><summary>RSI 70·30이나 PBR 1배 같은 숫자는 절대적인 기준인가요?</summary><p>관찰을 시작하기 위해 널리 쓰이는 참고 구간일 뿐입니다. 강한 추세에서는 RSI가 70 이상이나 30 이하에 오래 머물 수 있고, 업종과 자본 구조에 따라 적정 PBR 수준도 크게 달라지므로 추세와 업종 맥락을 함께 봐야 합니다.</p></details>
          <details><summary>여러 지표에서 동시에 긍정 신호가 나오면 근거가 그만큼 늘어난 건가요?</summary><p>반드시 그렇지는 않습니다. 예를 들어 주가가 구름대 위, 60일 이동평균선 위, 볼린저 중심선 위에 있다는 세 조건은 모두 최근 가격이 평균보다 높다는 하나의 현상을 다른 기간으로 표현한 것일 수 있습니다. 따라서 거래량이나 RSI처럼 성격이 다른 지표가 함께 뒷받침하는지 확인하는 것이 중요합니다.</p></details>
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
          <h2 id="publication-status-title">산식 기준과 안내</h2>
          <p>이 페이지의 산식과 가중치는 현재 운영 중인 MesuGak V2 분석 엔진(`indicators.py`, `scoring.py`, `risk.py`) 코드 기준입니다.</p>
          <p>문서 최근 수정일은 {CONTENT_UPDATED_ON}이며, 계산식·출처·설명에 오류가 있으면 <a href="mailto:or_not_official@naver.com">or_not_official@naver.com</a>으로 알려 주세요.</p>
        </section>
        <section className="editorial-note editorial-history" aria-labelledby="editorial-history-title">
          <h2 id="editorial-history-title">콘텐츠 변경 기록</h2>
          <p>산식 설명이나 학습 콘텐츠가 추가·수정된 내역입니다.</p>
          <ol>
            {editorialChangelog.map((entry) => <li key={`${entry.date}-${entry.title}`}><strong>{entry.date} · {entry.title}</strong><span>{entry.body}</span></li>)}
          </ol>
        </section>
         <article className="methodology-article">{[...methodologySections, ...methodologySupplementSections].map((section) => <section key={section.title} className="guide-article-section"><h2>{section.title}</h2>{section.body.map((paragraph) => <p key={paragraph}>{paragraph}</p>)}</section>)}<div className="source-box"><strong>데이터 출처</strong><p>금융위원회 공공데이터포털의 주식시세정보·지수시세정보 API를 통해 확정 일봉 데이터를 수집합니다.</p><a href="https://www.data.go.kr/data/15094808/openapi.do" target="_blank" rel="noreferrer">주식시세정보 원문 보기 <ExternalLink size={14} /></a></div><AdSenseSlot placement="learning" title="광고" className="learning-inline-ad" /></article>
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
          <p>공개 분석에는 실제 차트 분석에 사용하는 다중 기술지표 규칙을 코드로 구현해 적용했습니다. 볼린저 밴드·이동평균·일목균형표·RSI·거래량을 함께 평가하며, 기간 부족 등으로 계산할 수 없는 지표가 있으면 해당 가중치를 제외하고 남은 비중을 재정규화합니다. 자세한 산식은 <a href="/methodology">점수 계산 방법</a>에서 확인할 수 있습니다.</p>
        </section>
        <section className="editorial-note" aria-labelledby="publication-schedule-title">
          <h2 id="publication-schedule-title">갱신과 지연 처리</h2>
          <p>공개 분석은 장 마감 후 금융위원회 공공데이터포털에 새 거래일의 확정 일봉이 게시되면 이를 감지해 갱신합니다. 목록 상단에 표시되는 기준일이 실제 계산에 사용된 마지막 거래일입니다.</p>
          <p>주말·휴장일이나 공공데이터 반영 전에는 직전 거래일 분석 결과가 유지되며, 평일 기준 3일 이상 경과한 경우 화면 상단에 기준일 경과 안내가 함께 표시됩니다.</p>
        </section>
        <section className="editorial-note"><h2>콘텐츠 운영과 정정 안내</h2><p>지표 수업과 사례 수업은 각 조건의 정의, 수식 계산 과정, 그리고 신호가 엇갈리는 반례를 중심으로 구성합니다. 최근 콘텐츠 수정일은 {CONTENT_UPDATED_ON}이며, 오류 제보나 문의는 <a href="mailto:or_not_official@naver.com">or_not_official@naver.com</a>으로 보내 주세요.</p></section>
         {import.meta.env.VITE_SUPPORT_URL && <section className="support-note"><h2>커피로 응원하기</h2><p>후원은 서비스 운영을 위한 자율적인 응원이며, 후원 여부에 따라 추가 분석·개인별 추천·우선 답변을 제공하지 않습니다.</p><a href={import.meta.env.VITE_SUPPORT_URL} target="_blank" rel="noopener noreferrer">커피 후원 링크 <ExternalLink size={14} /></a></section>}
         <AdSenseSlot placement="learning" title="광고" className="learning-inline-ad" />
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
