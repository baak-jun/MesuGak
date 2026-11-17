import { ArrowRight, BookOpen, ShieldCheck } from 'lucide-react';
import { AdSenseSlot } from './AdSenseSlot.jsx';
import { BRAND_FULL } from './brand';
import { ComplianceDock } from './LegalPages.jsx';
import { LearningFooter, SiteNav } from './LearningPages.jsx';
import { pageCopy } from './content/pageCopy.js';
import './learning.css';

const home = pageCopy.home;

export function HomeLandingPage() {
  return (
    <main className="learning-page theme-light home-landing-page">
      <SiteNav />
      <div className="learning-container">
        <header className="learning-hero home-hero">
          <span className="learning-eyebrow"><BookOpen size={15} />{BRAND_FULL} · {home.eyebrow}</span>
          <h1>{home.title}</h1>
          <p>{home.summary}</p>
          <div className="learning-hero-actions">
            <a className="primary-learning-button" href="/analysis">종목 분석 결과 보기 <ArrowRight size={16} /></a>
            <a className="secondary-learning-button" href="/learn">지표 해석 방법 배우기</a>
          </div>
        </header>

        <section className="learning-section" aria-labelledby="home-questions-title">
          <div className="section-heading"><span>바로 풀어 볼 질문</span><h2 id="home-questions-title">숫자를 바꾸면 해석도 달라질까요?</h2><p>뜻을 읽는 데서 끝내지 않고 계산 과정과 반례까지 확인하는 수업입니다.</p></div>
          <div className="home-value-grid home-question-grid">
            <article className="home-value-card"><h3>오를 때와 내릴 때 폭이 같다면?</h3><p>96·98·100·102·104의 순서를 뒤집어 보세요. 평균과 분산은 같아도 마지막 가격의 위치는 달라집니다.</p><a href="/learn/lab#band-calculator">가상 종가로 직접 계산하기 <ArrowRight size={14} /></a></article>
            <article className="home-value-card"><h3>차트마다 밴드가 조금 다른 이유</h3><p>같은 20개 종가라도 표준편차를 N으로 나누는지 N−1로 나누는지에 따라 경계가 달라집니다. 두 방식의 차이를 계산해 봅니다.</p><a href="/learn/articles/bollinger">표준편차 비교 글 읽기 <ArrowRight size={14} /></a></article>
            <article className="home-value-card"><h3>거래량이 늘면 매수자가 더 많은 걸까?</h3><p>체결된 한 거래에는 사는 쪽과 파는 쪽이 함께 있습니다. 거래량의 뜻과 오늘을 포함한 평균의 영향을 살펴봅니다.</p><a href="/learn/articles/volume">거래량 계산 글 읽기 <ArrowRight size={14} /></a></article>
          </div>
        </section>

        <section className="learning-section home-purpose-section" aria-labelledby="home-purpose-title">
          <div className="section-heading"><span>{home.purpose.eyebrow}</span><h2 id="home-purpose-title">{home.purpose.title}</h2><p>{home.purpose.summary}</p></div>
          <div className="home-value-grid">
            {home.purpose.cards.map((card) => <article className="home-value-card" key={card.title}><strong>{card.title}</strong><p>{card.body}</p></article>)}
          </div>
        </section>

        <section className="learning-section home-path-section" aria-labelledby="home-path-title">
          <div className="section-heading"><span>{home.path.eyebrow}</span><h2 id="home-path-title">{home.path.title}</h2><p>{home.path.summary}</p></div>
          <ol className="home-step-list">
            {home.path.steps.map((step, index) => <li key={step.href}><span>{String(index + 1).padStart(2, '0')}</span><div><strong>{step.title}</strong><p>{step.body}</p><a href={step.href}>{step.label} <ArrowRight size={14} /></a></div></li>)}
          </ol>
        </section>

        <AdSenseSlot placement="learning" title="광고" className="learning-inline-ad" />

        <section className="learning-section learning-method-callout home-method-callout" aria-labelledby="home-method-title">
          <div><span>{home.method.eyebrow}</span><h2 id="home-method-title">{home.method.title}</h2><p>{home.method.body}</p></div>
          <a className="text-link-button" href="/methodology">방법론 읽기 <ArrowRight size={16} /></a>
        </section>

        <section className="learning-section home-originality-section" aria-labelledby="home-originality-title">
          <div className="section-heading"><span>{home.originality.eyebrow}</span><h2 id="home-originality-title">{home.originality.title}</h2></div>
          <div className="guide-article-note"><ShieldCheck size={19} aria-hidden="true" /><p>{home.originality.body} {home.originality.contactBefore} <a href="mailto:or_not_official@naver.com">or_not_official@naver.com</a>{home.originality.contactAfter}</p></div>
        </section>
        <AdSenseSlot placement="learning" title="광고" className="learning-inline-ad" />
      </div>
      <LearningFooter />
      <ComplianceDock />
    </main>
  );
}
