import { Component, lazy, Suspense, useEffect, useState } from 'react';
import { LegalPage, normalizeLegalRoute } from './LegalPages.jsx';
import { LearningPage, normalizeLearningRoute } from './LearningPages.jsx';
import './legal.css';
import { BRAND_FULL, BRAND_SHORT } from './brand';
import { trackPageView } from './analytics.js';

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
            <span>최신 화면으로 다시 불러오거나 잠시 후 재시도해 주세요.</span>
            <button type="button" onClick={() => window.location.reload()}>화면 다시 불러오기</button>
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
  if (legalRoute) return { legalRoute, learningRoute: '' };
  const hashLearningRoute = window.location.hash ? normalizeLearningRoute(window.location.hash) : '';
  const learningRoute = path ? (normalizeLearningRoute(path) || hashLearningRoute) : (hashLearningRoute || 'home');
  return { legalRoute: '', learningRoute };
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
      {route.legalRoute ? <LegalPage pageKey={route.legalRoute} /> : route.learningRoute ? <LearningPage pageKey={route.learningRoute} /> : (
        <Suspense fallback={<main className="app-loading-shell"><p>{BRAND_FULL}</p></main>}>
          <ResearchApp />
        </Suspense>
      )}
    </AppErrorBoundary>
  );
}
