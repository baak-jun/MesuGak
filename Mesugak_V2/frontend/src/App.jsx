import { Component, lazy, Suspense, useEffect, useState } from 'react';
import { LegalPage, normalizeLegalRoute } from './LegalPages.jsx';
import { LearningPage, normalizeLearningRoute } from './LearningPages.jsx';
import './legal.css';
import { BRAND_FULL, BRAND_SHORT } from './brand';
import { trackPageView } from './analytics.js';
import { AnalysisLoadingScene } from './LoadingScene.jsx';
import { AnalysisLandingPage } from './AnalysisLandingPage.jsx';
import { HomeLandingPage } from './HomeLandingPage.jsx';

const ResearchApp = lazy(() => import('./ResearchApp.jsx'));

class AppErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { failed: false };
  }

  static getDerivedStateFromError() {
    return { failed: true };
  }

  componentDidCatch(error) {
    console.error(`${BRAND_SHORT} 화면 렌더 실패`, error);
  }

  render() {
    if (this.state.failed) {
      return (
        <main className="app-error-shell">
          <section className="app-error-panel">
            <p>{BRAND_FULL}</p>
            <h1>화면을 불러오지 못했습니다.</h1>
            <span>잠시 후 새로고침하거나 다른 화면으로 이동해 주세요.</span>
            <button type="button" onClick={() => window.location.reload()}>화면 새로고침</button>
          </section>
        </main>
      );
    }
    return this.props.children;
  }
}

function currentRoute() {
  const path = window.location.pathname.replace(/^\/+|\/+$/g, '');
  const legalRoute = normalizeLegalRoute(path) || normalizeLegalRoute(window.location.hash);
  if (legalRoute) return { legalRoute, learningRoute: '', landingRoute: false, analysisRoute: false, notFound: false };

  const hashLearningRoute = window.location.hash ? normalizeLearningRoute(window.location.hash) : '';
  const hashValue = String(window.location.hash || '').replace(/^#\/?/, '').replace(/^\/+|\/+$/g, '');
  const analysisRoute = path === 'analysis' || hashValue === 'analysis';
  if (analysisRoute) return { legalRoute: '', learningRoute: '', landingRoute: false, analysisRoute: true, notFound: false };

  const learningRoute = path ? normalizeLearningRoute(path) : hashLearningRoute;
  if (learningRoute) return { legalRoute: '', learningRoute, landingRoute: false, analysisRoute: false, notFound: false };
  if (!path && !hashValue) return { legalRoute: '', learningRoute: '', landingRoute: true, analysisRoute: false, notFound: false };
  return { legalRoute: '', learningRoute: '', landingRoute: false, analysisRoute: false, notFound: true };
}

function NotFoundPage() {
  return (
    <main className="app-error-shell">
      <section className="app-error-panel">
        <p>{BRAND_FULL}</p>
        <h1>페이지를 찾을 수 없습니다.</h1>
        <span>학습 자료 또는 공개 분석 화면으로 이동해 주세요.</span>
        <div className="app-error-actions">
          <a href="/learn">학습 자료 보기</a>
          <a href="/analysis">공개 분석 보기</a>
        </div>
      </section>
    </main>
  );
}

function AnalysisRoute() {
  const [interactive, setInteractive] = useState(false);

  useEffect(() => {
    // The first render must match the static analysis introduction for hydration.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setInteractive(true);
  }, []);

  if (!interactive) return <AnalysisLandingPage />;
  return (
    <Suspense fallback={<AnalysisLoadingScene />}>
      <ResearchApp />
    </Suspense>
  );
}

export default function App() {
  const [route, setRoute] = useState(currentRoute);

  useEffect(() => {
    const onRouteChange = () => setRoute(currentRoute());
    window.addEventListener('hashchange', onRouteChange);
    window.addEventListener('popstate', onRouteChange);
    return () => {
      window.removeEventListener('hashchange', onRouteChange);
      window.removeEventListener('popstate', onRouteChange);
    };
  }, []);

  useEffect(() => {
    trackPageView(`${window.location.pathname}${window.location.hash}`);
  }, [route]);

  return (
    <AppErrorBoundary>
      {route.legalRoute ? <LegalPage pageKey={route.legalRoute} /> : route.landingRoute ? <HomeLandingPage /> : route.learningRoute ? <LearningPage pageKey={route.learningRoute} /> : route.analysisRoute ? <AnalysisRoute /> : <NotFoundPage />}
    </AppErrorBoundary>
  );
}
