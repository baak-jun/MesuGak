import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { LegalPage } from './LegalPages.jsx';
import { LearningPage } from './LearningPages.jsx';

const routeMap = {
  '/': { kind: 'learning', key: 'home' },
  '/learn': { kind: 'learning', key: 'home' },
  '/learn/ichimoku': { kind: 'learning', key: 'ichimoku' },
  '/learn/bollinger': { kind: 'learning', key: 'bollinger' },
  '/learn/moving-average': { kind: 'learning', key: 'moving-average' },
  '/learn/rsi': { kind: 'learning', key: 'rsi' },
  '/learn/volume': { kind: 'learning', key: 'volume' },
  '/learn/valuation': { kind: 'learning', key: 'valuation' },
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
    : <LearningPage pageKey={route.key} />;
  return renderToStaticMarkup(<React.StrictMode>{element}</React.StrictMode>);
}

export function staticRoutes() {
  return Object.keys(routeMap);
}
