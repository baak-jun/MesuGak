import test from 'node:test';
import assert from 'node:assert/strict';
import { hasSubstantialAnalysisContent } from '../src/contentPolicy.js';
import { monetizationGate } from '../src/monetizationGate.js';

const completeStock = {
  name: '학습용 종목',
  code: '000000',
  updatedAt: '2026-08-31',
  confidence: 72,
  indicatorStates: {
    ichimoku: { state: 'BULLISH', reasons: ['price_above_cloud'] },
    bollinger: { state: 'SQUEEZE', reasons: ['recent_squeeze'] },
    rsi: { state: 'NEUTRAL', reasons: ['rsi_crossed_above_50_with_signal'] },
  },
  raw: { confidenceReasons: ['price_above_cloud', 'recent_squeeze'] },
};

const adEnv = {
  VITE_ENABLE_PUBLIC_LIVE_DATA: 'true',
  VITE_PUBLIC_DATA_RIGHTS_CONFIRMED: 'true',
  VITE_PUBLIC_DATA_RIGHTS_APPROVAL_REFERENCE: 'rights-1',
  VITE_PUBLIC_DATA_RULES_RELEASE_REFERENCE: 'rules-1',
  VITE_ENABLE_ADSENSE: 'true',
  VITE_ENABLE_ANALYSIS_ADS: 'true',
  VITE_ADSENSE_LEGAL_REVIEW_CONFIRMED: 'true',
  VITE_ADSENSE_LEGAL_REVIEW_REFERENCE: 'legal-1',
  VITE_ADSENSE_ACCOUNT_APPROVED: 'true',
  VITE_ADSENSE_ADS_TXT_VERIFIED: 'true',
  VITE_ADSENSE_CMP_STATUS: 'certified_cmp_live',
  VITE_ADSENSE_CLIENT_ID: 'ca-pub-9876543210987654',
  VITE_ADSENSE_LEARNING_SLOT_ID: '11111111',
  VITE_ADSENSE_ANALYSIS_SLOT_ID: '22222222',
};

test('complete reports qualify for the narrow analysis content gate', () => {
  assert.equal(hasSubstantialAnalysisContent(completeStock), true);
});

test('missing or no-data reports stay ad-free', () => {
  assert.equal(hasSubstantialAnalysisContent(null), false);
  assert.equal(hasSubstantialAnalysisContent({ ...completeStock, updatedAt: '-' }), false);
  assert.equal(hasSubstantialAnalysisContent({
    ...completeStock,
    indicatorStates: Object.fromEntries(Object.keys(completeStock.indicatorStates).map((key) => [key, { state: 'NO_DATA', reasons: ['no_data'] }])),
  }), false);
});

test('both named placements require separate real slot IDs when enabled', () => {
  const gate = monetizationGate(adEnv);
  assert.equal(gate.adsensePlacementApproved, true);
  assert.deepEqual(gate.requestedPlacements, ['learning', 'analysis']);
  assert.equal(monetizationGate({ ...adEnv, VITE_ADSENSE_ANALYSIS_SLOT_ID: '' }).adsensePlacementApproved, false);
});

test('analysis placement can be disabled without disabling learning ads', () => {
  const gate = monetizationGate({ ...adEnv, VITE_ENABLE_ANALYSIS_ADS: 'false' });
  assert.equal(gate.adsensePlacementApproved, true);
  assert.deepEqual(gate.requestedPlacements, ['learning']);
});
