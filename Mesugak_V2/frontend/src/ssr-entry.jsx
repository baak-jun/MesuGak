import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { LegalPage } from './LegalPages.jsx';
import { LearningPage } from './LearningPages.jsx';
import { AnalysisLandingPage } from './AnalysisLandingPage.jsx';
import { HomeLandingPage } from './HomeLandingPage.jsx';

const routeMap = {
  '/': { kind: 'landing', key: 'landing' },
  '/analysis': { kind: 'analysis', key: 'analysis' },
  '/learn': { kind: 'learning', key: 'home' },
  '/learn/articles': { kind: 'learning', key: 'articles' },
  '/learn/articles/ichimoku': { kind: 'learning', key: 'articles/ichimoku' },
  '/learn/articles/bollinger': { kind: 'learning', key: 'articles/bollinger' },
  '/learn/articles/moving-average': { kind: 'learning', key: 'articles/moving-average' },
  '/learn/articles/rsi': { kind: 'learning', key: 'articles/rsi' },
  '/learn/articles/volume': { kind: 'learning', key: 'articles/volume' },
  '/learn/articles/valuation': { kind: 'learning', key: 'articles/valuation' },
  '/learn/ichimoku': { kind: 'learning', key: 'ichimoku' },
  '/learn/bollinger': { kind: 'learning', key: 'bollinger' },
  '/learn/moving-average': { kind: 'learning', key: 'moving-average' },
  '/learn/rsi': { kind: 'learning', key: 'rsi' },
  '/learn/volume': { kind: 'learning', key: 'volume' },
  '/learn/valuation': { kind: 'learning', key: 'valuation' },
  '/learn/cases': { kind: 'learning', key: 'cases' },
  '/learn/lab': { kind: 'learning', key: 'lab' },
  '/learn/glossary': { kind: 'learning', key: 'glossary' },
  '/methodology': { kind: 'learning', key: 'methodology' },
  '/about': { kind: 'learning', key: 'about' },
  '/terms': { kind: 'legal', key: 'terms' },
  '/privacy': { kind: 'legal', key: 'privacy' },
  '/data': { kind: 'legal', key: 'data' },
  '/disclaimer': { kind: 'legal', key: 'disclaimer' },
};

export function renderStaticRoute(pathname) {
  const route = routeMap[pathname];
  if (!route) return '';
  const element = route.kind === 'legal'
    ? <LegalPage pageKey={route.key} />
    : route.kind === 'analysis'
      ? <AnalysisLandingPage />
      : route.kind === 'landing'
        ? <HomeLandingPage />
      : <LearningPage pageKey={route.key} />;
  return renderToStaticMarkup(<React.StrictMode>{element}</React.StrictMode>);
}

export function staticRoutes() {
  return Object.keys(routeMap);
}
