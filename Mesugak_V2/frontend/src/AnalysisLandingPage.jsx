import { ArrowRight, BookOpen, ShieldCheck } from 'lucide-react';
import { BRAND_FULL, BRAND_SHORT } from './brand';
import { pageCopy } from './content/pageCopy.js';
import './learning.css';

const analysis = pageCopy.analysis;

export function AnalysisLandingPage() {
  return (
    <main className="learning-page theme-light analysis-landing-page">
      <nav className="learning-nav" aria-label="사이트 주요 메뉴">
        <a className="learning-nav-brand" href="/"><span>{BRAND_FULL}</span><strong>{BRAND_SHORT}</strong></a>
        <div className="learning-nav-links"><a href="/learn">지표 학습</a><a href="/learn/cases">사례 수업</a><a href="/learn/glossary">용어집</a><a href="/methodology">분석 방법론</a></div>
      </nav>
      <div className="learning-container">
        <header className="learning-hero">
          <span className="learning-eyebrow"><BookOpen size={15} />{analysis.eyebrow}</span>
          <h1>{analysis.title}</h1>
          <p>{analysis.summary}</p>
          <div className="learning-hero-actions"><a className="primary-learning-button" href="/learn">먼저 지표 수업 읽기 <ArrowRight size={16} /></a><a className="secondary-learning-button" href="/methodology">공개 범위와 방법론</a></div>
        </header>
        <article className="analysis-landing-article">
          <section><h2>{analysis.what.title}</h2><p>{analysis.what.body}</p></section>
          <section><h2>{analysis.order.title}</h2><ol>{analysis.order.steps.map((step) => <li key={step}>{step}</li>)}</ol></section>
          <section><h2>{analysis.conflict.title}</h2>{analysis.conflict.paragraphs.map((paragraph) => <p key={paragraph}>{paragraph}</p>)}</section>
          <section><h2>{analysis.score.title}</h2><p>{analysis.score.body} 가중치와 계산 예시는 <a href="/methodology">분석 방법론</a>에 적었습니다.</p><p>{analysis.score.dateReminder} 낯선 말은 <a href="/learn/glossary">기술지표 용어집</a>에서 확인할 수 있습니다.</p></section>
          <section className="guide-article-note"><ShieldCheck size={19} /><p>{analysis.caution}</p></section>
        </article>
      </div>
      <footer className="learning-footer"><small>문의: or_not_official@naver.com</small><nav aria-label="정책 페이지"><a href="/privacy">개인정보처리방침</a><a href="/data">데이터 안내</a><a href="/disclaimer">면책 안내</a></nav></footer>
    </main>
  );
}
