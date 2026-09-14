import test from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const root = resolve(process.cwd(), 'dist');
const routes = [
  '/',
  '/learn',
  '/learn/ichimoku',
  '/learn/bollinger',
  '/learn/moving-average',
  '/learn/rsi',
  '/learn/volume',
  '/learn/valuation',
  '/methodology',
  '/about',
  '/terms',
  '/privacy',
  '/data',
  '/disclaimer',
];

function fileFor(route) {
  return route === '/' ? resolve(root, 'index.html') : resolve(root, route.slice(1), 'index.html');
}

test('public learning and policy routes contain server-rendered content', () => {
  for (const route of routes) {
    const file = fileFor(route);
    assert.equal(existsSync(file), true, 'missing prerendered route: ' + route);
    const html = readFileSync(file, 'utf8');
    assert.match(html, /<div id="root">[\s\S]+<\/div>/, 'empty root: ' + route);
    assert.match(html, /<link rel="canonical"/, 'missing canonical: ' + route);
    assert.doesNotMatch(html, /광고 공간|AdSense 승인 후 실제 광고/, 'ad placeholder leaked: ' + route);
  }
  const valuationHtml = readFileSync(fileFor('/learn/valuation'), 'utf8');
  assert.match(valuationHtml, /PER[\s\S]*PBR/, 'valuation guide must mention PER and PBR');
  assert.match(valuationHtml, /반영하지/, 'valuation guide must state that PER/PBR are excluded from scoring');
});
