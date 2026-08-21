import { Component, useEffect, useState } from 'react';
import ResearchApp from './ResearchApp.jsx';
import { ComplianceDock, LegalPage, normalizeLegalRoute } from './LegalPages.jsx';
import './legal.css';
import { BRAND_FULL, BRAND_SHORT } from './brand';
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
  return normalizeLegalRoute(window.location.hash);
}

export default function App() {
  const [legalRoute, setLegalRoute] = useState(currentRoute);

  useEffect(() => {
    const onHashChange = () => setLegalRoute(currentRoute());
    window.addEventListener('hashchange', onHashChange);
    return () => window.removeEventListener('hashchange', onHashChange);
  }, []);

  return (
    <AppErrorBoundary>
      {legalRoute ? <LegalPage pageKey={legalRoute} /> : <>
        <ResearchApp />
        <ComplianceDock />
      </>}
    </AppErrorBoundary>
  );
}
