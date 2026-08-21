import { Fragment, useEffect, useMemo, useRef, useState } from 'react';
import { getRedirectResult, onAuthStateChanged, signInWithPopup, signInWithRedirect, signOut } from 'firebase/auth';
import { addDoc, collection, doc, getDoc, getDocs, onSnapshot, query, serverTimestamp, where } from 'firebase/firestore';
import {
  AlertTriangle,
  BarChart3,
  CandlestickChart,
  Cloud,
  Gauge,
  LogIn,
  LogOut,
  RefreshCw,
  Shield,
  WalletCards,
  ChevronDown,
  SlidersHorizontal,
  HelpCircle,
  X,
} from 'lucide-react';
import { auth, db, firebaseReady, googleProvider } from './firebase';
import { AdSenseSlot } from './AdSenseSlot';
import { monetizationGate } from './monetizationGate';
import { BRAND_FULL, BRAND_SHORT } from './brand';
import './research.css';

const mockHistory = Array.from({ length: 130 }, (_, index) => {
  const base = 69000 + index * 116;
  const wave = Math.sin(index / 6) * 1450;
  const close = Math.round(base + wave);
  const open = Math.round(close - Math.cos(index / 4) * 620);
  const high = Math.max(open, close) + 950;
  const low = Math.min(open, close) - 880;
  const ma20 = Math.round(close - 520 + Math.sin(index / 11) * 420);
  const ma60 = Math.round(close - 1700 + Math.cos(index / 15) * 680);
  return {
    date: `2026-04-${String((index % 30) + 1).padStart(2, '0')}`,
    open,
    high,
    low,
    close,
    volume: 900000 + index * 12000,
    upper: close + 3100,
    lower: close - 3300,
    bbMid: ma20,
    ma20,
    ma60,
    rsi: 44 + Math.sin(index / 8) * 10 + index * 0.08,
    rsiSignal: 43 + Math.sin(index / 9) * 8 + index * 0.07,
  };
});

const mockSignals = [
  {
    id: 'KR_005930',
    code: '005930',
    name: '삼성전자',
    market: 'KR',
    currentPrice: 78400,
    confidenceScore: 88,
    confidenceLabel: 'STRONG_BUY',
    status: 'STRONG_BUY',
    stopLoss: 72100,
    cashTargetPct: 0.12,
    riskState: 'normal',
    lastDate: '2026-05-17',
    componentScores: { bollinger: 80, maSupport: 86, ichimoku: 92, rsi: 78, volume: 74 },
    sortMetrics: {
      bollinger: { percentB: 0.82, bandwidth: 0.19, bandwidthRank: 0.72 },
      maSupport: { priceToMa20Pct: 2.3, priceToMa60Pct: 7.8, aboveMa60Ratio: 0.88 },
      ichimoku: { priceToCloudPct: 5.1, tenkanToKijunPct: 1.7, cloudSpreadPct: 2.5 },
      rsi: { rsi: 61.4, rsiChange: 2.2 },
    },
    indicatorStates: {
      bollinger: { state: 'SQUEEZE_RELEASE_UP', reasons: ['recent_squeeze', 'upper_band_release'] },
      maSupport: { state: 'LOWER_BAND_ABOVE_MA60', reasons: ['bollinger_lower_above_ma60'] },
      ichimoku: { state: 'BULLISH', reasons: ['price_above_cloud', 'tenkan_above_kijun'] },
      rsi: { state: 'BULLISH', reasons: ['rsi_crossed_above_50_with_signal'] }
    },
    riskFlags: [],
    history: mockHistory,
    marcap: 460000000000000,
  },
  {
    id: 'KR_000660',
    code: '000660',
    name: 'SK하이닉스',
    market: 'KR',
    currentPrice: 317750,
    confidenceScore: 74,
    confidenceLabel: 'WATCH',
    status: 'WATCH',
    stopLoss: 292000,
    cashTargetPct: 0.18,
    riskState: 'watch',
    lastDate: '2026-05-17',
    componentScores: { bollinger: 70, maSupport: 79, ichimoku: 72, rsi: 60, volume: 68 },
    sortMetrics: {
      bollinger: { percentB: 0.64, bandwidth: 0.16, bandwidthRank: 0.59 },
      maSupport: { priceToMa20Pct: 1.8, priceToMa60Pct: 5.2, aboveMa60Ratio: 0.81 },
      ichimoku: { priceToCloudPct: 3.6, tenkanToKijunPct: 0.8, cloudSpreadPct: 1.9 },
      rsi: { rsi: 56.8, rsiChange: 0.9 },
    },
    indicatorStates: {
      bollinger: { state: 'SQUEEZE', reasons: ['bandwidth_low_percentile'] },
      maSupport: { state: 'LOWER_BAND_ABOVE_MA60', reasons: ['bollinger_lower_above_ma60'] },
      ichimoku: { state: 'NEUTRAL', reasons: [] },
      rsi: { state: 'NEUTRAL', reasons: [] }
    },
    riskFlags: ['RSI_COOLING'],
    history: mockHistory.map((row) => ({
      ...row,
      open: row.open * 3.9,
      high: row.high * 3.9,
      low: row.low * 3.9,
      close: row.close * 3.9,
      upper: row.upper * 3.9,
      lower: row.lower * 3.9,
      bbMid: row.bbMid * 3.9,
      ma20: row.ma20 * 3.9,
      ma60: row.ma60 * 3.9,
    })),
    marcap: 231000000000000,
  },
];

const fallbackOrders = [
  { time: '10:19', code: '005930', action: 'BUY', reason: 'confidence_rebalance', amount: 203000, status: 'staged' },
];

const fallbackTradeLogs = [
  { time: '10:21', code: '005930', action: 'BUY', name: '삼성전자', amount: 784000, price: 78400, quantity: 10, reason: 'paper_rebalance', source: 'mock' },
];

const fallbackPortfolio = {
  mode: 'mock',
  source: 'mock',
  market: 'KR',
  holdingCount: 1,
  cash: 120000,
  initialCash: 1000000,
  totalEvalAmt: 784000,
  totalBuyAmt: 721000,
  totalEquity: 904000,
  realizedPnl: 0,
  unrealizedPnl: 63000,
  totalPnl: -96000,
  returnPct: -9.6,
  updatedAt: '2026-05-17T09:00:00+09:00',
  holdings: [{ code: '005930', name: '삼성전자', qty: 10, evalAmt: 784000, buyAmt: 721000, pnlPct: 8.74 }],
};

const emptyPaperPortfolio = {
  mode: 'paper',
  source: 'KIS_PAPER',
  market: 'KR',
  holdingCount: 0,
  cash: 0,
  initialCash: 0,
  totalEvalAmt: 0,
  totalBuyAmt: 0,
  totalEquity: 0,
  realizedPnl: 0,
  unrealizedPnl: 0,
  totalPnl: 0,
  returnPct: 0,
  updatedAt: null,
  holdings: [],
};

const componentMeta = {
  bollinger: { label: '볼린저밴드', max: 100, color: '#3b82f6' },
  maSupport: { label: '이동평균선', max: 100, color: '#f59e0b' },
  ichimoku: { label: '일목균형표', max: 100, color: '#8b5cf6' },
  rsi: { label: 'RSI', max: 100, color: '#ec4899' },
  valuation: { label: '가치 참고값', max: 100, color: '#14b8a6' },
  volume: { label: '거래량 확인', max: 100, color: '#22c55e' },
  penalty: { label: '리스크 감점', max: 100, color: '#ef4444' },
};

const componentWeights = { bollinger: 0.25, maSupport: 0.20, ichimoku: 0.20, rsi: 0.10, valuation: 0.15, volume: 0.10, penalty: -1 };

const sortGroups = [
  {
    label: '시장 정보',
    options: [
      { key: 'confidence', label: '차트 컨디션 점수', category: '종합 점수' },
      { key: 'marketCap', label: '시가총액 (KR 제공값만)', category: '시장 정보' },
      { key: 'cash', label: '방어 현금 비중', category: '시장 정보' },
      { key: 'market', label: '시장 / 코드', category: '시장 정보', text: true },
      { key: 'name', label: '종목명', category: '시장 정보', text: true },
    ],
  },
  {
    label: '점수 요소',
    options: [
      { key: 'score.bollinger', label: '볼린저밴드 점수', category: '볼린저밴드', color: componentMeta.bollinger.color },
      { key: 'score.maSupport', label: '이동평균선 점수', category: '이동평균선', color: componentMeta.maSupport.color },
      { key: 'score.ichimoku', label: '일목균형표 점수', category: '일목균형표', color: componentMeta.ichimoku.color },
      { key: 'score.rsi', label: 'RSI 점수', category: 'RSI', color: componentMeta.rsi.color },
    ],
  },
  {
    label: '점수 세부 수치',
    options: [
      { key: 'detail.bollinger.percentB', label: '%B', category: '볼린저밴드', color: componentMeta.bollinger.color },
      { key: 'detail.bollinger.bandwidth', label: '밴드폭', category: '볼린저밴드', color: componentMeta.bollinger.color },
      { key: 'detail.bollinger.bandwidthRank', label: '밴드폭 백분위', category: '볼린저밴드', color: componentMeta.bollinger.color },
      { key: 'detail.maSupport.priceToMa20Pct', label: 'MA20 괴리율', category: '이동평균선', color: componentMeta.maSupport.color },
      { key: 'detail.maSupport.priceToMa60Pct', label: 'MA60 괴리율', category: '이동평균선', color: componentMeta.maSupport.color },
      { key: 'detail.maSupport.aboveMa60Ratio', label: 'MA60 상회 비율', category: '이동평균선', color: componentMeta.maSupport.color },
      { key: 'detail.ichimoku.priceToCloudPct', label: '구름대 괴리율', category: '일목균형표', color: componentMeta.ichimoku.color },
      { key: 'detail.ichimoku.tenkanToKijunPct', label: '전환선/기준선 괴리율', category: '일목균형표', color: componentMeta.ichimoku.color },
      { key: 'detail.ichimoku.cloudSpreadPct', label: '구름대 폭', category: '일목균형표', color: componentMeta.ichimoku.color },
      { key: 'detail.rsi.rsi', label: 'RSI 값', category: 'RSI', color: componentMeta.rsi.color },
      { key: 'detail.rsi.rsiChange', label: 'RSI 변화량', category: 'RSI', color: componentMeta.rsi.color },
    ],
  },
];

const publicSortGroups = sortGroups
  .map((group) => ({
    ...group,
    options: group.options.filter((option) => option.key === 'name' || option.key === 'market' || option.key === 'confidence' || option.key.startsWith('score.')),
  }))
  .filter((group) => group.options.length > 0);

const sortOptions = sortGroups.flatMap((group) => group.options);
const sortOptionByKey = Object.fromEntries(sortOptions.map((option) => [option.key, option]));

const statusLabels = {
  STRONG_BUY: '강한 기술 조건',
  BUY_CANDIDATE: '관심 조건 충족',
  WATCH: '관찰',
  HOLD: '중립',
  DEFENSIVE: '방어 신호',
  AVOID: '리스크 신호',
  UNKNOWN: '분석 대기',
};

const actionLabels = {
  BUY: '가상 매수',
  SELL: '가상 매도',
  HOLD: '관찰 유지',
  REDUCE: '비중 축소 실험',
  EXIT: '청산 실험',
  BUY_CANDIDATE: '관심 조건 충족',
  WATCH: '관찰',
};

const reasonLabels = {
  confidence_rebalance: '조건 점수 기반 리밸런싱 실험',
  paper_rebalance: '모의 리밸런싱 체결',
  live_rebalance: '실시간 조건 재점검',
};

const themeOptions = [
  { key: 'light', label: '라이트' },
  { key: 'nightOwl', label: '나이트 아울' },
  { key: 'beigeOwl', label: '베이지 아울' }
];

const themeClassMap = { light: 'theme-light', nightOwl: 'theme-night-owl', beigeOwl: 'theme-beige-owl' };
// Public research and advertising are fail-closed. The same gate runs before build.
const { publicLiveDataApproved, adsensePlacementApproved } = monetizationGate(import.meta.env);

function numberAt(value, path) {
  const number = path.split('.').reduce((current, key) => current?.[key], value);
  return Number.isFinite(Number(number)) ? Number(number) : null;
}

function formatNumber(value, digits = 0) {
  const number = Number(value);
  if (!Number.isFinite(number)) return '-';
  return number.toLocaleString('ko-KR', { maximumFractionDigits: digits, minimumFractionDigits: digits });
}

function formatSigned(value, digits = 0) {
  const number = Number(value);
  if (!Number.isFinite(number)) return '-';
  return `${number > 0 ? '+' : ''}${formatNumber(number, digits)}`;
}

function formatTimestamp(value) {
  if (!value) return '-';
  if (value.toDate) return value.toDate().toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' });
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' });
}

function formatDateTime(value) {
  if (!value) return '-';
  if (value.toDate) return value.toDate().toLocaleString('ko-KR', { dateStyle: 'short', timeStyle: 'short' });
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString('ko-KR', { dateStyle: 'short', timeStyle: 'short' });
}

function compactDate(value) {
  const text = String(value || '');
  return text.length > 5 ? text.slice(5) : text;
}

function statusLabel(value) {
  const key = String(value || 'UNKNOWN').toUpperCase();
  return statusLabels[key] || key.replaceAll('_', ' ');
}

function actionLabel(value) {
  const key = String(value || 'HOLD').toUpperCase();
  return actionLabels[key] || key.replaceAll('_', ' ');
}

function reasonLabel(value) {
  return reasonLabels[value] || String(value || '-').replaceAll('_', ' ');
}

const analysisReasonLabels = {
  ichimoku_price_above_cloud: '주가가 구름대 위에 위치', ichimoku_price_below_cloud: '주가가 구름대 아래에 위치', ichimoku_tenkan_above_kijun: '전환선이 기준선 위에 위치', ichimoku_tenkan_below_kijun: '전환선이 기준선 아래에 위치', ichimoku_forward_cloud_bullish: '선행 구름이 상승 방향', ichimoku_forward_cloud_bearish: '선행 구름이 하락 방향', bollinger_state_squeeze_release_up: '밴드 수축 뒤 상방 확장 조건', bollinger_state_squeeze: '밴드 수축 상태', bollinger_state_upper_band_release: '상단 밴드 확장 조건', bollinger_state_below_lower_band: '하단 밴드 이탈 주의', ma_support_lower_band_above_ma60: '하단 밴드가 장기 이동평균 위에 위치', ma_support_lower_band_cross_above_ma60: '하단 밴드가 장기 이동평균을 상향 통과', ma_support_lower_band_cross_below_ma60: '하단 밴드가 장기 이동평균을 하향 통과', rsi_crossed_above_50_with_signal: 'RSI가 기준선 위로 회복', rsi_oversold_recovery: 'RSI 과매도 구간 회복', rsi_breakdown: 'RSI 약화 신호', price_breakout_with_relative_volume: '가격 확장과 거래량 확인', squeeze_release_lacks_volume: '확장 조건 대비 거래량 확인 부족', below_bollinger_lower: '하단 밴드 이탈', downside_band_expansion: '하방 밴드 확장', below_ichimoku_cloud: '구름대 하단 이탈', failed_box_breakout: '박스권 돌파 실패', bollinger_lower_crossed_above_ma60: '하단 밴드가 장기 이평선을 상향 돌파', bollinger_lower_above_ma60: '하단 밴드가 장기 이평선 위에 위치', bollinger_lower_crossed_below_ma60: '하단 밴드가 장기 이평선을 하향 돌파', negative_or_zero_earnings: '적자 또는 이익 없음', low_per: '낮은 PER', reasonable_per: '적정 PER', elevated_but_positive_per: '다소 높은 PER', high_per: '높은 PER', low_pbr: '낮은 PBR', reasonable_pbr: '적정 PBR', high_pbr: '높은 PBR', high_roe: '높은 ROE', positive_roe: '양의 ROE', negative_roe: '음의 ROE', manageable_debt: '관리 가능한 부채비율', high_debt: '높은 부채비율', operating_profit_growing: '영업이익 성장', operating_profit_shrinking: '영업이익 감소', price_above_cloud: '주가가 구름대 위에 위치', price_below_cloud: '주가가 구름대 아래에 위치', tenkan_above_kijun: '전환선이 기준선 위에 위치', tenkan_below_kijun: '전환선이 기준선 아래에 위치', bullish_forward_cloud: '선행 구름이 상승 방향', bearish_forward_cloud: '선행 구름이 하락 방향', chikou_confirmed: '후행스팬이 추세 확인', chikou_below_past_price: '후행스팬이 과거 주가 하회', bearish_rsi_divergence: 'RSI 하락 다이버전스', penalty_below_lower_band: '하단 밴드 이탈', valuation_state_valued: '가치 참고 조건 충족',
};

function analysisReasonLabel(value) { const key = String(value || '').toLowerCase(); return analysisReasonLabels[key] || key.replaceAll('_', ' '); }

const publicReasonLabels = {
  ichimoku_bearish_forward_cloud: '선행 구름은 약세 방향',
  ichimoku_forward_cloud_bearish: '선행 구름은 약세 방향',
  ichimoku_chikou_confirmed: '후행스팬이 현재 추세를 확인',
  ma_state_neutral: '이동평균선은 뚜렷한 방향을 아직 만들지 않음',
  bollinger_recent_squeeze: '최근 변동성이 수축했던 구간',
  bollinger_bandwidth_expanding: '수축 뒤 밴드폭이 다시 넓어지는 중',
  bollinger_upper_band_release: '상단 밴드 쪽 확장 조건',
  volume_price_breakout_with_relative_volume: '가격 확장에 거래량 확인이 동반됨',
  valuation_state_valued: '가치 참고 조건이 기준을 충족함',
  valuation_low_per: '낮은 PER 참고 조건',
  valuation_low_pbr: '낮은 PBR 참고 조건',
  valuation_high_roe: '높은 ROE 참고 조건',
  valuation_operating_profit_growing: '영업이익 성장 참고 조건',
  price_above_cloud: '주가가 구름대 위에 위치',
  tenkan_above_kijun: '전환선이 기준선 위에 위치',
  bearish_forward_cloud: '선행 구름은 약세 방향',
  chikou_confirmed: '후행스팬이 현재 추세를 확인',
  recent_squeeze: '최근 변동성이 수축했던 구간',
  bandwidth_expanding: '수축 뒤 밴드폭이 다시 넓어지는 중',
  upper_band_release: '상단 밴드 쪽 확장 조건',
  price_breakout_with_relative_volume: '가격 확장에 거래량 확인이 동반됨',
  low_per: '낮은 PER 참고 조건',
  low_pbr: '낮은 PBR 참고 조건',
  high_roe: '높은 ROE 참고 조건',
  operating_profit_growing: '영업이익 성장 참고 조건',
};

function normalizedReasonKey(value) {
  return String(value || '').trim().toLowerCase().replaceAll('-', '_').replaceAll(' ', '_');
}

function publicReasonLabel(value) {
  const key = normalizedReasonKey(value);
  return publicReasonLabels[key] || analysisReasonLabel(key);
}

function publicStateLabel(state) {
  const normalized = String(state || 'NEUTRAL').toUpperCase();
  const labels = {
    BULLISH: '상승 조건 우세',
    BEARISH: '약세 조건 주의',
    NEUTRAL: '중립 · 추적',
    SQUEEZE_RELEASE_UP: '수축 후 상방 확장',
    SQUEEZE: '변동성 수축',
    BREAKOUT_CONFIRMED: '돌파 · 거래량 확인',
    VALUED: '가치 참고 조건 충족',
  };
  return labels[normalized] || normalized.replaceAll('_', ' ');
}

function publicStateExplanation(key, state) {
  const normalized = String(state || '').toUpperCase();
  if (key === 'ichimoku' && normalized === 'BULLISH') return '구름대 위 위치와 전환선·기준선 관계가 추세 환경을 뒷받침합니다. 다만 선행 구름 방향처럼 엇갈린 조건도 함께 확인합니다.';
  if (key === 'bollinger' && normalized === 'SQUEEZE_RELEASE_UP') return '변동성이 줄었던 뒤 밴드가 위쪽으로 넓어지는 모습입니다. 확장이 지속되는지는 다른 지표와 거래량 조건을 함께 봅니다.';
  if (key === 'volume' && normalized === 'BREAKOUT_CONFIRMED') return '가격 움직임에 상대 거래량 확인이 동반된 상태입니다. 거래량이 줄어들면 이 조건의 신뢰도도 다시 점검합니다.';
  if (key === 'valuation' && normalized === 'VALUED') return '가치 참고 조건은 기술지표 판단을 보조합니다. 단독으로 방향을 결정하지 않으며, 추세·모멘텀 조건과 함께 사용합니다.';
  if ((key === 'maSupport' || key === 'rsi') && normalized === 'NEUTRAL') return '현재는 뚜렷하게 한 방향을 지지하지 않아, 다음 분석 갱신에서 회복 또는 약화 여부를 추가 확인하는 상태입니다.';
  return publicStateNarrative(key, state);
}

function isCautionReason(value) {
  return /(below|bearish|breakdown|lacks|downside|risk|lower)/.test(normalizedReasonKey(value));
}

function AnalysisContentsRail({ sections }) {
  const moveToSection = (id) => document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  return (
    <nav className="analysis-contents-rail" aria-label="분석 목차">
      <div className="analysis-contents-drawer">
        <span className="analysis-contents-tab">목차</span>
        <div className="analysis-contents-menu">
          <p>분석 목차</p>
          {sections.map((section, index) => <button key={section.id} type="button" onClick={() => moveToSection(section.id)}><span>{String(index + 1).padStart(2, '0')}</span><strong>{section.label}</strong><small>{section.description}</small></button>)}
        </div>
      </div>
    </nav>
  );
}
const publicIndicatorGuides = {
  bollinger: { label: '볼린저밴드', focus: '최근 변동성의 수축·확장과 밴드 안팎의 위치를 함께 해석합니다.' },
  maSupport: { label: '이동평균선', focus: '중장기 추세선 위에서 지지되는지와 전환 여부를 해석합니다.' },
  ichimoku: { label: '일목균형표', focus: '구름대와 전환선·기준선의 상대적 위치로 추세 환경을 해석합니다.' },
  rsi: { label: 'RSI', focus: '힘의 회복·약화와 과열·침체 구간을 해석합니다.' },
  volume: { label: '거래량 확인', focus: '가격 움직임을 뒷받침하는 참여 강도를 확인합니다.' },
  valuation: { label: '가치 참고값', focus: '재무 참고값을 기술지표 판단의 보조 정보로만 사용합니다.' },
};

function publicStateNarrative(key, state) {
  const normalized = String(state || '').toUpperCase();
  if (key === 'bollinger' && normalized.includes('SQUEEZE_RELEASE_UP')) return '변동성이 좁아진 뒤 상방 확장 조건이 포착됐습니다. 다른 지표의 확인 여부를 함께 봅니다.';
  if (key === 'bollinger' && normalized.includes('SQUEEZE')) return '변동성은 줄었지만 아직 방향이 충분히 확정되지 않은 상태로 해석합니다.';
  if (key === 'bollinger' && normalized.includes('LOWER')) return '하단 밴드 쪽 압력이 감지되어 반등 확인 전까지는 방어적으로 해석합니다.';
  if (key === 'maSupport' && normalized.includes('ABOVE')) return '중장기 이동평균선 위의 지지 조건이 유지되는지 확인합니다.';
  if (key === 'maSupport' && normalized.includes('BELOW')) return '중장기 이동평균선 아래로 약화된 조건이어서 추세 회복을 추가 확인합니다.';
  if (key === 'ichimoku' && normalized.includes('ABOVE')) return '구름대 위 환경으로 분류되어 추세 조건에는 우호적인 신호로 해석합니다.';
  if (key === 'ichimoku' && normalized.includes('BELOW')) return '구름대 아래 환경으로 분류되어 반등보다 위험 관리 조건을 우선 확인합니다.';
  if (key === 'rsi' && (normalized.includes('RECOVERY') || normalized.includes('ABOVE'))) return '모멘텀이 회복되는지 확인하는 조건입니다. 단독 신호로 결론 내리지 않습니다.';
  if (key === 'rsi' && (normalized.includes('BREAK') || normalized.includes('WEAK'))) return '모멘텀이 약해지는 조건으로, 다른 지표의 방어 신호와 함께 해석합니다.';
  return publicIndicatorGuides[key]?.focus || '이 지표의 상태와 다른 기술 조건의 일치 여부를 함께 해석합니다.';
}

function publicConclusion(stock) {
  if (stock.riskState === 'defensive') return '방어 신호가 우세합니다. 상승 가능성을 단정하기보다 약화 요인과 추세 회복 여부를 우선 점검한 결과입니다.';
  if (stock.confidence >= 70) return '여러 기술 조건이 같은 방향을 가리켜 관심 조건으로 분류됐습니다. 이는 교육용 해석이며 매수 권유가 아닙니다.';
  if (stock.riskState === 'watch') return '긍정·주의 조건이 함께 나타나 관찰 대상으로 분류됐습니다. 추가 확인이 쌓일 때까지 방향을 단정하지 않습니다.';
  return '현재 조건은 뚜렷한 방향성을 확정하기보다 중립적으로 추적하는 구간으로 해석했습니다.';
}
function riskStateFromPayload(payload) {
  const state = String(payload.riskState || payload.status || '').toLowerCase();
  if (state.includes('defensive') || state.includes('avoid')) return 'defensive';
  if (state.includes('caution') || state.includes('watch')) return 'watch';
  return 'normal';
}

function normalizeHistory(history) {
  return (Array.isArray(history) ? history : [])
    .map((row) => ({
      date: row.date,
      open: Number(row.open),
      high: Number(row.high),
      low: Number(row.low),
      close: Number(row.close),
      volume: Number(row.volume || 0),
      upper: Number(row.upper ?? row.bbUpper),
      lower: Number(row.lower ?? row.bbLower),
      bbMid: Number(row.bbMid ?? row.mid),
      ma20: Number(row.ma20),
      ma60: Number(row.ma60),
      rsi: Number(row.rsi),
      rsiSignal: Number(row.rsiSignal),
    }))
    .filter((row) => [row.open, row.high, row.low, row.close].every(Number.isFinite));
}

function mapComponents(payload) {
  const scores = payload.componentScores || {};
  const order = ['bollinger', 'maSupport', 'ichimoku', 'rsi', 'volume', 'valuation', 'penalty'];
  return Object.entries(scores)
    .map(([key, value]) => ({
      key,
      label: componentMeta[key]?.label || key,
      color: componentMeta[key]?.color || '#64748b',
      score: Number(value || 0),
      max: componentMeta[key]?.max || 100,
      weight: componentWeights[key],
    }))
    .sort((a, b) => order.indexOf(a.key) - order.indexOf(b.key));
}

function mapStockPayload(payload) {
  const market = payload.market || 'KR';
  const code = payload.code || payload.symbol || '';
  const id = payload.id || `${market}_${code}`;
  const history = normalizeHistory(payload.history);
  const labelKey = String(payload.confidenceLabel || payload.status || 'UNKNOWN').toUpperCase();
  const riskState = riskStateFromPayload(payload);
  const riskFlags = payload.riskFlags || [];
  return {
    id,
    code,
    name: payload.name || code,
    market,
    price: Number(payload.currentPrice ?? payload.price ?? 0),
    confidence: Number(payload.confidenceScore ?? payload.confidence ?? 0),
    labelKey,
    label: statusLabel(labelKey),
    signal: actionLabel(payload.signal?.action || payload.status || labelKey),
    stopLoss: Number(payload.stopLoss || 0),
    cashTarget: Math.round(Number(payload.cashTargetPct || 0) * 100),
    riskState,
    updatedAt: payload.analysisDate || payload.lastDate || payload.updatedAt || '-',
    components: mapComponents(payload),
    componentScores: payload.componentScores || {},
    sortMetrics: payload.sortMetrics || {},
    risks: riskFlags.length
      ? riskFlags.map((flag) => ({ label: analysisReasonLabel(flag), state: riskState === 'defensive' ? 'danger' : 'watch', value: statusLabel(payload.status || labelKey) }))
      : [{ label: '특별 경고 없음', state: 'clear', value: riskState === 'normal' ? '정상 관찰' : '주의 관찰' }],
    indicatorStates: payload.indicatorStates || payload.signal?.indicatorStates || {},
    raw: { ...payload, history, hasFullHistory: history.length > 0, marcap: payload.marcap },
  };
}

function componentScore(signal, key) {
  const direct = numberAt(signal.componentScores, key);
  if (direct !== null) return direct;
  return Number(signal.components?.find((component) => component.key === key)?.score) || null;
}

function sortValue(signal, mode) {
  if (mode === 'confidence') return Number(signal.confidence);
  if (mode === 'cash') return Number(signal.cashTarget);
  if (mode === 'marketCap') {
    const marcap = numberAt(signal.raw, 'marcap');
    return signal.market === 'KR' && marcap && marcap > 0 ? marcap : null;
  }
  if (mode.startsWith('score.')) return componentScore(signal, mode.slice('score.'.length));
  if (mode.startsWith('detail.')) {
    const path = mode.slice('detail.'.length);
    const metric = numberAt(signal.sortMetrics, path);
    if (metric !== null) return metric;
    if (path === 'bollinger.percentB') return numberAt(signal.raw, 'percentB');
    if (path === 'bollinger.bandwidth') return numberAt(signal.raw, 'bandwidth');
    return numberAt(signal.indicatorStates, path);
  }
  return null;
}

async function loadSignalsFromFirestore({ admin = false } = {}) {
  if (!firebaseReady || !db) return [];
  if (!admin && !publicLiveDataApproved) return [];
  const sourceCollection = admin ? 'meta_data' : 'public_analysis_meta';
  const expectedPrefix = admin ? 'meta_v2_' : 'public_meta_v2_';
  const metaQuery = query(collection(db, sourceCollection), where('market', 'in', ['KR', 'US']));
  const metaSnap = await getDocs(metaQuery);
  const chunks = [];
  metaSnap.forEach((item) => { const data = item.data(); if (Array.isArray(data.list) && String(item.id).startsWith(expectedPrefix)) chunks.push({ id: item.id, ...data }); });
  const expectedVersion = admin ? 'V2' : 'V2_PUBLIC';
  const v2Chunks = chunks.filter((chunk) => chunk.strategyVersion === expectedVersion);
  let rows = [];
  (v2Chunks.length > 0 ? v2Chunks : chunks).forEach((chunk) => { rows = rows.concat(chunk.list || []); });
  rows.sort((a, b) => Number(b.confidenceScore || 0) - Number(a.confidenceScore || 0));
  return rows.map(mapStockPayload);
}
async function loadOrdersFromFirestore(allowLiveData = false) {
  if (!allowLiveData || !firebaseReady || !db) return [];
  const ordersQuery = query(collection(db, 'rebalance_orders'), where('market', 'in', ['KR', 'US']));
  const snap = await getDocs(ordersQuery);
  const rows = [];
  snap.forEach((item) => rows.push({ id: item.id, ...item.data() }));
  rows.sort((a, b) => Number(b.tradeAmount || 0) - Number(a.tradeAmount || 0));
  return rows.map((order) => ({
    time: formatTimestamp(order.updatedAt),
    code: order.code,
    name: order.name || order.code,
    action: order.side || 'HOLD',
    reason: order.reason || '-',
    amount: Number(order.tradeAmount || order.targetAmount || 0),
    status: 'staged',
  }));
}

async function loadTradeLogsFromFirestore() {
  if (!firebaseReady || !db) return [];
  const snap = await getDocs(collection(db, 'bot_trade_logs'));
  const rows = [];
  snap.forEach((item) => rows.push({ id: item.id, ...item.data() }));
  rows.sort((a, b) => {
    const aDate = a.createdAt?.toDate ? a.createdAt.toDate() : new Date(a.createdAt || 0);
    const bDate = b.createdAt?.toDate ? b.createdAt.toDate() : new Date(b.createdAt || 0);
    return bDate.getTime() - aDate.getTime();
  });
  return rows.slice(0, 120).map((log) => ({
    time: formatTimestamp(log.createdAt),
    code: log.code,
    name: log.name || log.code,
    action: log.action || '-',
    amount: Number(log.amount || 0),
    price: Number(log.price || 0),
    quantity: Number(log.quantity || 0),
    reason: log.reason || '-',
    pnlPct: log.pnlPct,
    pnl: log.pnl,
    source: log.source || 'legacy',
    brokerOrderNo: log.brokerOrderNo || '',
  }));
}

function mapPortfolioPosition(payload, fallbackCode = '') {
  const code = payload.code || payload.pdno || fallbackCode;
  return {
    code,
    name: payload.name || payload.prdt_name || code,
    qty: Number(payload.qty ?? payload.quantity ?? payload.hldg_qty ?? 0),
    evalAmt: Number(payload.evalAmt ?? payload.marketValue ?? payload.value ?? payload.evlu_amt ?? 0),
    buyAmt: Number(payload.buyAmt ?? payload.buyAmount ?? payload.pchs_amt ?? 0),
    pnlPct: Number(payload.pnlPct ?? payload.fltt_rt ?? 0),
  };
}

async function loadPortfolioFromFirestore() {
  if (!firebaseReady || !db) return null;
  const snapshotSnap = await getDoc(doc(db, 'bot_account_snapshot', 'latest'));
  const portfolioSnap = await getDocs(collection(db, 'bot_portfolio'));
  const positions = [];
  portfolioSnap.forEach((item) => positions.push(mapPortfolioPosition({ id: item.id, ...item.data() }, item.id)));
  if (!snapshotSnap.exists() && positions.length === 0) return null;
  const snapshot = snapshotSnap.exists() ? snapshotSnap.data() : {};
  const holdings = Array.isArray(snapshot.holdings) && snapshot.holdings.length > 0
    ? snapshot.holdings.map((item) => mapPortfolioPosition(item))
    : positions;
  const totalEvalAmt = Number(snapshot.totalEvalAmt ?? holdings.reduce((sum, item) => sum + Number(item.evalAmt || 0), 0));
  const totalBuyAmt = Number(snapshot.totalBuyAmt ?? holdings.reduce((sum, item) => sum + Number(item.buyAmt || 0), 0));
  const cash = Number(snapshot.cash ?? 0);
  const totalEquity = Number(snapshot.totalEquity ?? cash + totalEvalAmt);
  const initialCash = Number(snapshot.initialCash ?? totalEquity);
  const totalPnl = Number(snapshot.totalPnl ?? totalEquity - initialCash);
  const returnPct = Number(snapshot.returnPct ?? (initialCash > 0 ? (totalPnl / initialCash) * 100 : 0));
  return {
    ...snapshot,
    mode: snapshot.mode || 'paper',
    source: snapshot.source || BRAND_SHORT,
    market: snapshot.market || 'KR',
    holdingCount: Number(snapshot.holdingCount ?? holdings.length),
    cash,
    initialCash,
    totalEvalAmt,
    totalBuyAmt,
    totalEquity,
    totalPnl,
    returnPct,
    holdings,
  };
}

async function loadPrivatePerformanceFromFirestore() {
  if (!firebaseReady || !db) return null;
  const snapshot = await getDoc(doc(db, 'paper_performance_private', 'latest'));
  return snapshot.exists() ? snapshot.data() : null;
}
function linePath(rows, key, xForIndex, yForValue) {
  return rows.map((row, index) => {
    const value = Number(row[key]);
    if (!Number.isFinite(value)) return null;
    return `${index === 0 ? 'M' : 'L'} ${xForIndex(index).toFixed(2)} ${yForValue(value).toFixed(2)}`;
  }).filter(Boolean).join(' ');
}

function areaPath(rows, topKey, bottomKey, xForIndex, yForValue) {
  const top = [];
  const bottom = [];
  rows.forEach((row, index) => {
    const topValue = Number(row[topKey]);
    const bottomValue = Number(row[bottomKey]);
    if (!Number.isFinite(topValue) || !Number.isFinite(bottomValue)) return;
    top.push(`${xForIndex(index).toFixed(2)} ${yForValue(topValue).toFixed(2)}`);
    bottom.unshift(`${xForIndex(index).toFixed(2)} ${yForValue(bottomValue).toFixed(2)}`);
  });
  if (top.length < 2) return '';
  return `M ${top.join(' L ')} L ${bottom.join(' L ')} Z`;
}

function WatchlistAd() {
  return <AdSenseSlot title="목록 광고" compact className="watchlist-ad-slot adsense-watchlist-slot" />;
}
function IndicatorToggle({ active, label, onClick }) {
  return (
    <button type="button" className={`tool-toggle ${active ? 'active' : ''}`} onClick={onClick}>
      <span>{label}</span>
    </button>
  );
}

function TechnicalChart({ stock }) {
  const [range, setRange] = useState(120);
  const [layers, setLayers] = useState({ candles: true, bollinger: true, ma: true, rsi: true });
  const history = useMemo(() => (stock.raw?.history?.length ? stock.raw.history : []), [stock.raw]);
  const rows = useMemo(() => (range === 'ALL' ? history : history.slice(-Number(range))), [history, range]);

  if (!rows.length) {
    return (
      <section className="chart-workspace">
        <div className="chart-header">
          <div>
            <span className="quote-symbol">{stock.market}:{stock.code}</span>
            <h2>{stock.name}</h2>
            <p>상세 차트 데이터가 아직 로드되지 않았습니다.</p>
          </div>
          <span className={`risk-chip risk-${stock.riskState}`}>{stock.label}</span>
        </div>
        <div className="chart-empty">
          <RefreshCw size={20} />
          <strong>종목을 선택하면 Firestore 상세 분석을 불러옵니다.</strong>
          <span>이 화면은 기술지표 학습용이며 매수·매도 권유가 아닙니다.</span>
        </div>
      </section>
    );
  }

  const width = 920;
  const height = layers.rsi ? 520 : 390;
  const margin = { top: 24, right: 72, bottom: 36, left: 18 };
  const priceHeight = layers.rsi ? 330 : 310;
  const rsiTop = margin.top + priceHeight + 38;
  const values = rows.flatMap((row) => [row.high, row.low, layers.bollinger ? row.upper : null, layers.bollinger ? row.lower : null, layers.ma ? row.ma20 : null, layers.ma ? row.ma60 : null]).filter(Number.isFinite);
  const minPrice = Math.min(...values);
  const maxPrice = Math.max(...values);
  const pad = (maxPrice - minPrice || 1) * 0.08;
  const domainMin = minPrice - pad;
  const domainMax = maxPrice + pad;
  const candleGap = (width - margin.left - margin.right) / Math.max(rows.length - 1, 1);
  const candleWidth = Math.max(3, Math.min(10, candleGap * 0.58));
  const xForIndex = (index) => margin.left + candleGap * index;
  const yForPrice = (value) => margin.top + ((domainMax - value) / (domainMax - domainMin || 1)) * priceHeight;
  const yForRsi = (value) => rsiTop + ((100 - Number(value || 0)) / 100) * 118;
  const latest = rows[rows.length - 1];

  return (
    <section className="chart-workspace">
      <div className="chart-header">
        <div className="quote-stack">
          <span className="quote-symbol">{stock.market}:{stock.code}</span>
          <h2>{stock.name}</h2>
          <div className="quote-line">
            <strong>{formatNumber(stock.price || latest.close, stock.market === 'US' ? 2 : 0)}</strong>
            <span>분석일 {stock.updatedAt || latest.date}</span>
            <span className={`risk-chip risk-${stock.riskState}`}>{stock.label}</span>
          </div>
        </div>
        <div className="chart-tools">
          <div className="range-tabs" aria-label="차트 기간">
            {[60, 120, 240, 'ALL'].map((item) => (
              <button key={item} type="button" className={range === item ? 'active' : ''} onClick={() => setRange(item)}>
                {item === 'ALL' ? '전체' : `${item}일`}
              </button>
            ))}
          </div>
          <div className="layer-toggles" aria-label="지표 레이어">
            <IndicatorToggle active={layers.candles} label="캔들" onClick={() => setLayers((current) => ({ ...current, candles: !current.candles }))} />
            <IndicatorToggle active={layers.bollinger} label="볼린저" onClick={() => setLayers((current) => ({ ...current, bollinger: !current.bollinger }))} />
            <IndicatorToggle active={layers.ma} label="이평선" onClick={() => setLayers((current) => ({ ...current, ma: !current.ma }))} />
            <IndicatorToggle active={layers.rsi} label="RSI" onClick={() => setLayers((current) => ({ ...current, rsi: !current.rsi }))} />
          </div>
        </div>
      </div>

      <div className="chart-frame">
        <svg className="technical-chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`${stock.name} 기술지표 차트`}>
          <rect x="0" y="0" width={width} height={height} className="chart-bg" />
          {[0, 0.25, 0.5, 0.75, 1].map((ratio) => {
            const y = margin.top + ratio * priceHeight;
            const value = domainMax - ratio * (domainMax - domainMin);
            return (
              <g key={ratio}>
                <line x1={margin.left} x2={width - margin.right} y1={y} y2={y} className="grid-line" />
                <text x={width - 60} y={y - 5} className="axis-label">{formatNumber(value, stock.market === 'US' ? 2 : 0)}</text>
              </g>
            );
          })}
          {layers.bollinger && (
            <>
              <path d={areaPath(rows, 'upper', 'lower', xForIndex, yForPrice)} className="bb-area" />
              <path d={linePath(rows, 'upper', xForIndex, yForPrice)} className="line bb-upper" />
              <path d={linePath(rows, 'bbMid', xForIndex, yForPrice)} className="line bb-mid" />
              <path d={linePath(rows, 'lower', xForIndex, yForPrice)} className="line bb-lower" />
            </>
          )}
          {layers.ma && (
            <>
              <path d={linePath(rows, 'ma20', xForIndex, yForPrice)} className="line ma20" />
              <path d={linePath(rows, 'ma60', xForIndex, yForPrice)} className="line ma60" />
            </>
          )}
          <path d={linePath(rows, 'close', xForIndex, yForPrice)} className="line close-line" />
          {layers.candles && rows.map((row, index) => {
            const x = xForIndex(index);
            const up = row.close >= row.open;
            const top = yForPrice(Math.max(row.open, row.close));
            const bottom = yForPrice(Math.min(row.open, row.close));
            return (
              <g key={`${row.date}-${index}`}>
                <line x1={x} x2={x} y1={yForPrice(row.high)} y2={yForPrice(row.low)} className={`wick ${up ? 'up' : 'down'}`} />
                <rect x={x - candleWidth / 2} y={top} width={candleWidth} height={Math.max(2, bottom - top)} className={`candle ${up ? 'up' : 'down'}`} />
              </g>
            );
          })}
          {layers.rsi && (
            <>
              <line x1={margin.left} x2={width - margin.right} y1={rsiTop} y2={rsiTop} className="section-line" />
              {[70, 50, 30].map((tick) => (
                <g key={tick}>
                  <line x1={margin.left} x2={width - margin.right} y1={yForRsi(tick)} y2={yForRsi(tick)} className={tick === 50 ? 'grid-line' : 'rsi-band'} />
                  <text x={width - 54} y={yForRsi(tick) - 5} className="axis-label">{tick}</text>
                </g>
              ))}
              <path d={linePath(rows, 'rsi', xForIndex, yForRsi)} className="line rsi-line" />
              <path d={linePath(rows, 'rsiSignal', xForIndex, yForRsi)} className="line rsi-signal" />
              <text x={margin.left + 4} y={rsiTop + 16} className="panel-label">RSI</text>
            </>
          )}
          {rows.filter((_, index) => index % Math.ceil(rows.length / 5) === 0 || index === rows.length - 1).map((row, index) => {
            const realIndex = rows.indexOf(row);
            return <text key={`${row.date}-${index}`} x={xForIndex(realIndex)} y={height - 12} className="date-label">{compactDate(row.date)}</text>;
          })}
        </svg>
      </div>

      <div className="legend-strip">
        <span><i className="swatch candle-up" /> 상승 캔들</span>
        <span><i className="swatch bb" /> 볼린저밴드</span>
        <span><i className="swatch ma" /> MA20 / MA60</span>
        <span><i className="swatch rsi" /> RSI / 시그널</span>
      </div>
    </section>
  );
}

function ScoreDock({ stock }) {
  const bollinger = stock.indicatorStates?.bollinger || stock.sortMetrics?.bollinger || {};
  const detailRows = [
    ['%B', numberAt(stock.sortMetrics, 'bollinger.percentB'), 2, componentMeta.bollinger.color],
    ['밴드폭', numberAt(stock.sortMetrics, 'bollinger.bandwidth'), 3, componentMeta.bollinger.color],
    ['MA20 괴리율', numberAt(stock.sortMetrics, 'maSupport.priceToMa20Pct'), 2, componentMeta.maSupport.color],
    ['구름대 괴리율', numberAt(stock.sortMetrics, 'ichimoku.priceToCloudPct'), 2, componentMeta.ichimoku.color],
    ['RSI 값', numberAt(stock.sortMetrics, 'rsi.rsi'), 1, componentMeta.rsi.color],
  ];

  return (
    <aside className="score-dock">
      <section className="dock-section headline-score">
        <span>차트 컨디션 점수</span>
        <strong className="glow-text">{formatNumber(stock.confidence, 1)}</strong>
        <small>{stock.label}</small>
        <p>여러 기술지표가 같은 방향을 가리키는 정도를 교육용 점수로 표현합니다.</p>
      </section>
      <section className="dock-section compact-stats">
        <div><span>리스크 기준가</span><strong>{stock.stopLoss ? formatNumber(stock.stopLoss, stock.market === 'US' ? 2 : 0) : '-'}</strong></div>
        <div><span>방어 현금 비중</span><strong>{stock.cashTarget}%</strong></div>
        <div><span>볼린저 상태</span><strong className="state-text">{String(bollinger.state || '중립').replaceAll('_', ' ')}</strong></div>
        <div><span>밴드폭 백분위</span><strong>{bollinger.bandwidthRank !== undefined ? `${formatNumber(Number(bollinger.bandwidthRank) * 100, 1)}%` : '-'}</strong></div>
      </section>
      <section className="dock-section">
        <div className="dock-title"><Gauge size={16} /><span>점수 요소</span></div>
        <div className="score-bars">
          {stock.components.length === 0 && <div className="empty-watch">세부 점수 데이터가 아직 없습니다.</div>}
          {stock.components.map((component) => (
            <div key={component.key} className="score-bar">
              <div>
                <span style={{ color: component.color }}>{component.label}</span>
                <strong>{component.weight === -1 ? `감점 ${formatNumber(component.score, 1)}` : `${formatNumber(component.score, 1)} × ${formatNumber(Number(component.weight || 0) * 100, 0)}%`}</strong>
              </div>
              <meter min="0" max={component.max || 100} value={component.score || 0} style={{ '--meter-color': component.color }} />
            </div>
          ))}
        </div>
      </section>
      <section className="dock-section">
        <div className="dock-title"><BarChart3 size={16} /><span>세부 수치</span></div>
        <div className="metric-grid">
          {detailRows.map(([label, value, digits, color]) => <div key={label}><span style={{ color }}>{label}</span><strong>{value === null ? '-' : formatNumber(value, digits)}</strong></div>)}
        </div>
      </section>
      <section className="dock-section">
        <div className="dock-title"><Shield size={16} /><span>리스크 신호</span></div>
        <div className="risk-list">
          {stock.risks.map((risk) => <div key={`${risk.label}-${risk.value}`} className={`risk-row risk-${risk.state}`}><span>{risk.label}</span><strong>{risk.value}</strong></div>)}
        </div>
      </section>
    </aside>
  );
}

const Candle = ({ x, o, c, h, l }) => {
  const isUp = c <= o; // Y axis is inverted, so smaller Y means higher price
  const color = isUp ? '#ef4444' : '#3b82f6';
  const top = Math.min(o, c);
  const bottom = Math.max(o, c);
  const height = Math.max(bottom - top, 2);
  return (
    <g stroke={color}>
      <line x1={x} y1={h} x2={x} y2={l} strokeWidth="1.5" />
      <rect x={x - 3} y={top} width="6" height={height} fill={color} strokeWidth="1" stroke="none" />
    </g>
  );
};

const educationalGuides = {
  bollinger: {
    title: '볼린저 밴드 (Bollinger Bands)',
    points: [
      { 
        label: '스퀴즈 돌파 (+90점)', 
        desc: '밴드가 좁게 횡보(힘 응축)하다가, 상단 밴드를 강하게 뚫고 밴드가 상하로 넓어지는(발산) 강력한 상승 신호입니다.',
        graphic: (
          <svg viewBox="0 0 300 120" width="100%" height="100%" preserveAspectRatio="xMidYMid meet">
            <path d="M 10,70 L 120,70 Q 180,70 280,40" fill="none" stroke="var(--text-muted)" strokeWidth="1.5" strokeDasharray="3,3" />
            <path d="M 10,50 L 120,50 Q 180,50 280,10" fill="none" stroke="var(--text-soft)" strokeWidth="1.5" />
            <path d="M 10,90 L 120,90 Q 180,90 280,110" fill="none" stroke="var(--text-soft)" strokeWidth="1.5" />
            <Candle x={30} h={55} l={85} o={75} c={65} />
            <Candle x={60} h={60} l={80} o={65} c={75} />
            <Candle x={90} h={50} l={80} o={75} c={55} />
            <Candle x={120} h={45} l={60} o={55} c={48} />
            <Candle x={150} h={25} l={50} o={48} c={32} />
            <Candle x={180} h={10} l={40} o={32} c={15} />
            <Candle x={210} h={5} l={30} o={20} c={10} />
            <Candle x={240} h={10} l={25} o={12} c={22} />
            <text x="160" y="25" fontSize="12" fill="#ef4444" fontWeight="bold">상단선 돌파(발산)</text>
            <text x="10" y="45" fontSize="11" fill="var(--text-soft)">상단밴드</text>
            <text x="10" y="65" fontSize="11" fill="var(--text-soft)">중심선(MA20)</text>
            <text x="10" y="105" fontSize="11" fill="var(--text-soft)">하단밴드</text>
          </svg>
        )
      },
      { 
        label: '단순 수축 (+35점)', 
        desc: '볼린저 밴드의 상단과 하단 폭이 좁아지며 가격이 중심선 부근에서 횡보하는 상태입니다. 곧 큰 변동이 올 수 있습니다.',
        graphic: (
          <svg viewBox="0 0 300 120" width="100%" height="100%" preserveAspectRatio="xMidYMid meet">
            <path d="M 10,40 Q 150,60 280,60" fill="none" stroke="var(--text-soft)" strokeWidth="1.5" />
            <path d="M 10,60 Q 150,70 280,70" fill="none" stroke="var(--text-muted)" strokeWidth="1.5" strokeDasharray="3,3" />
            <path d="M 10,80 Q 150,80 280,80" fill="none" stroke="var(--text-soft)" strokeWidth="1.5" />
            <Candle x={40} h={30} l={70} o={45} c={65} />
            <Candle x={80} h={40} l={75} o={65} c={50} />
            <Candle x={120} h={50} l={80} o={50} c={70} />
            <Candle x={160} h={55} l={85} o={70} c={65} />
            <Candle x={200} h={60} l={80} o={65} c={75} />
            <Candle x={240} h={62} l={78} o={75} c={68} />
            <text x="150" y="45" fontSize="12" fill="var(--text)" fontWeight="bold">밴드폭 축소(수축)</text>
          </svg>
        )
      },
      { 
        label: '하단 붕괴 (-45점)', 
        desc: '하단 밴드를 깨고 내려가며 밴드가 넓어지는 패턴입니다. 강한 하락 추세가 시작될 수 있어 주의해야 합니다.',
        graphic: (
          <svg viewBox="0 0 300 120" width="100%" height="100%" preserveAspectRatio="xMidYMid meet">
            <path d="M 10,50 L 120,50 Q 180,50 280,20" fill="none" stroke="var(--text-soft)" strokeWidth="1.5" />
            <path d="M 10,70 L 120,70 Q 180,70 280,85" fill="none" stroke="var(--text-muted)" strokeWidth="1.5" strokeDasharray="3,3" />
            <path d="M 10,90 L 120,90 Q 180,90 280,115" fill="none" stroke="var(--text-soft)" strokeWidth="1.5" />
            <Candle x={40} h={55} l={85} o={75} c={65} />
            <Candle x={80} h={50} l={80} o={65} c={75} />
            <Candle x={120} h={65} l={85} o={75} c={82} />
            <Candle x={160} h={75} l={100} o={82} c={95} />
            <Candle x={200} h={85} l={110} o={95} c={105} />
            <Candle x={240} h={95} l={115} o={105} c={110} />
            <text x="160" y="112" fontSize="12" fill="#3b82f6" fontWeight="bold">하단선 이탈(폭락)</text>
          </svg>
        )
      },
      { 
        label: '돌파 실패 (-25점)', 
        desc: '상단 밴드를 넘었다가 안착하지 못하고 다시 밴드 안쪽(중심선 방향)으로 밀려나는 패턴입니다.',
        graphic: (
          <svg viewBox="0 0 300 120" width="100%" height="100%" preserveAspectRatio="xMidYMid meet">
            <path d="M 10,50 Q 80,45 150,50 Q 220,55 280,50" fill="none" stroke="var(--text-soft)" strokeWidth="1.5" />
            <path d="M 10,70 Q 150,70 280,70" fill="none" stroke="var(--text-muted)" strokeWidth="1.5" strokeDasharray="3,3" />
            <path d="M 10,90 Q 150,90 280,90" fill="none" stroke="var(--text-soft)" strokeWidth="1.5" />
            <Candle x={40} h={55} l={85} o={75} c={60} />
            <Candle x={80} h={35} l={70} o={60} c={40} />
            <Candle x={120} h={25} l={50} o={40} c={30} />
            <Candle x={160} h={30} l={65} o={30} c={60} />
            <Candle x={200} h={45} l={75} o={60} c={70} />
            <Candle x={240} h={65} l={85} o={70} c={80} />
            <text x="150" y="25" fontSize="12" fill="#3b82f6" fontWeight="bold">돌파 후 밴드 안으로 하락</text>
          </svg>
        )
      }
    ]
  },
  maSupport: {
    title: '이동평균선 지지 (MA Support)',
    points: [
      { 
        label: '골든크로스 안착 (+90점)', 
        desc: '단기 이동평균선(또는 주가)이 60일 장기 추세선을 강하게 뚫고 올라가(골든크로스) 지지를 받는 상태입니다.',
        graphic: (
          <svg viewBox="0 0 300 120" width="100%" height="100%" preserveAspectRatio="xMidYMid meet">
            <path d="M 10,90 L 280,50" fill="none" stroke="var(--accent-purple, #8b5cf6)" strokeWidth="2.5" />
            <path d="M 10,110 Q 120,100 160,40 Q 200,60 280,20" fill="none" stroke="var(--text-muted)" strokeWidth="1.5" strokeDasharray="3,3" />
            <Candle x={40} h={100} l={115} o={110} c={105} />
            <Candle x={80} h={80} l={110} o={105} c={85} />
            <Candle x={120} h={50} l={90} o={85} c={60} />
            <Candle x={160} h={40} l={65} o={60} c={45} />
            <Candle x={200} h={40} l={60} o={45} c={55} />
            <Candle x={240} h={20} l={55} o={55} c={25} />
            <text x="180" y="80" fontSize="12" fill="#ef4444" fontWeight="bold">장기선 위 안착(지지)</text>
            <text x="10" y="80" fontSize="11" fill="var(--accent-purple, #8b5cf6)">60일선(장기)</text>
            <text x="10" y="105" fontSize="11" fill="var(--text-soft)">20일선(단기)</text>
          </svg>
        )
      },
      { 
        label: '장기선 위 유지 (+70점)', 
        desc: '주가가 장기선 위에서 꾸준히 지지를 받으며 추세가 꺾이지 않고 편안하게 상승하는 상태입니다.',
        graphic: (
          <svg viewBox="0 0 300 120" width="100%" height="100%" preserveAspectRatio="xMidYMid meet">
            <path d="M 10,100 L 280,70" fill="none" stroke="var(--accent-purple, #8b5cf6)" strokeWidth="2.5" />
            <Candle x={40} h={40} l={75} o={50} c={65} />
            <Candle x={80} h={55} l={85} o={65} c={75} />
            <Candle x={120} h={70} l={95} o={75} c={90} />
            <Candle x={160} h={55} l={90} o={90} c={65} />
            <Candle x={200} h={35} l={75} o={65} c={45} />
            <Candle x={240} h={25} l={60} o={45} c={30} />
            <text x="10" y="90" fontSize="11" fill="var(--accent-purple, #8b5cf6)">60일선(장기)</text>
            <text x="100" y="110" fontSize="12" fill="#ef4444" fontWeight="bold">장기선 터치 후 반등</text>
          </svg>
        )
      },
      { 
        label: '데드크로스 붕괴 (-35점)', 
        desc: '지켜주던 장기 지지선이 뚫려 아래로 내려간 위험 상태입니다. 추세가 하락으로 꺾일 수 있습니다.',
        graphic: (
          <svg viewBox="0 0 300 120" width="100%" height="100%" preserveAspectRatio="xMidYMid meet">
            <path d="M 10,70 L 280,60" fill="none" stroke="var(--accent-purple, #8b5cf6)" strokeWidth="2.5" />
            <Candle x={40} h={30} l={65} o={50} c={40} />
            <Candle x={80} h={35} l={70} o={40} c={55} />
            <Candle x={120} h={50} l={85} o={55} c={75} />
            <Candle x={160} h={70} l={100} o={75} c={90} />
            <Candle x={200} h={85} l={110} o={90} c={105} />
            <text x="10" y="60" fontSize="11" fill="var(--accent-purple, #8b5cf6)">60일선(장기)</text>
            <text x="140" y="45" fontSize="12" fill="#3b82f6" fontWeight="bold">지지선 붕괴(하락)</text>
          </svg>
        )
      }
    ]
  },
  ichimoku: {
    title: '일목균형표 (Ichimoku Cloud)',
    points: [
      { 
        label: '구름대 위 (+35점)', 
        desc: '두꺼운 저항대인 구름을 뚫고 올라가 주가 상승에 방해물이 적은 편안한 상승 구간입니다.',
        graphic: (
          <svg viewBox="0 0 300 120" width="100%" height="100%" preserveAspectRatio="xMidYMid meet">
            <path d="M 10,80 Q 150,70 280,60 L 280,110 Q 150,100 10,120 Z" fill="rgba(16,185,129,0.15)" stroke="rgba(16,185,129,0.5)" strokeWidth="1" />
            <Candle x={40} h={40} l={70} o={60} c={45} />
            <Candle x={90} h={45} l={65} o={45} c={55} />
            <Candle x={140} h={30} l={60} o={55} c={35} />
            <Candle x={190} h={20} l={50} o={35} c={25} />
            <Candle x={240} h={15} l={40} o={25} c={30} />
            <text x="110" y="30" fontSize="12" fill="#ef4444" fontWeight="bold">구름 저항대 위 (상승 추세)</text>
            <text x="10" y="100" fontSize="11" fill="#10b981">양운(지지구름)</text>
          </svg>
        )
      },
      { 
        label: '구름대 아래 (-35점)', 
        desc: '두꺼운 구름이 머리 위에서 짓누르고 있어 돌파하기 힘든 하락/정체 구간입니다.',
        graphic: (
          <svg viewBox="0 0 300 120" width="100%" height="100%" preserveAspectRatio="xMidYMid meet">
            <path d="M 10,20 Q 150,40 280,30 L 280,70 Q 150,80 10,60 Z" fill="rgba(239,68,68,0.15)" stroke="rgba(239,68,68,0.5)" strokeWidth="1" />
            <Candle x={40} h={70} l={90} o={75} c={85} />
            <Candle x={90} h={65} l={100} o={85} c={70} />
            <Candle x={140} h={70} l={95} o={70} c={85} />
            <Candle x={190} h={80} l={110} o={85} c={100} />
            <Candle x={240} h={95} l={120} o={100} c={110} />
            <text x="120" y="100" fontSize="12" fill="#3b82f6" fontWeight="bold">두꺼운 저항(구름)에 막힘</text>
            <text x="10" y="45" fontSize="11" fill="#ef4444">음운(저항구름)</text>
          </svg>
        )
      },
      { 
        label: '전환선 호전 (+25점)', 
        desc: '주가 흐름에 가장 민감한 전환선(단기선)이 기준선(중기선)을 뚫고 올라가 단기 상승 에너지가 강해진 상태입니다.',
        graphic: (
          <svg viewBox="0 0 300 120" width="100%" height="100%" preserveAspectRatio="xMidYMid meet">
            <path d="M 10,80 L 280,60" fill="none" stroke="var(--text-soft)" strokeWidth="2" strokeDasharray="3,3" />
            <path d="M 10,100 Q 100,90 140,50 L 280,30" fill="none" stroke="var(--accent)" strokeWidth="2" />
            <Candle x={40} h={80} l={105} o={95} c={85} />
            <Candle x={100} h={50} l={85} o={85} c={60} />
            <Candle x={160} h={30} l={60} o={60} c={40} />
            <Candle x={220} h={25} l={45} o={40} c={35} />
            <text x="10" y="75" fontSize="11" fill="var(--text-soft)">기준선(중기선)</text>
            <text x="160" y="25" fontSize="12" fill="#ef4444" fontWeight="bold">전환선(단기) 돌파</text>
          </svg>
        )
      }
    ]
  },
  rsi: {
    title: 'RSI (상대강도지수)',
    points: [
      { 
        label: '기준선 50 돌파 (+55점)', 
        desc: '50을 넘었다는 것은 매도세보다 매수세가 강해졌음을 의미하며, 중요한 상승 추세 전환 신호입니다.',
        graphic: (
          <svg viewBox="0 0 300 120" width="100%" height="100%" preserveAspectRatio="xMidYMid meet">
            <line x1="0" y1="20" x2="300" y2="20" stroke="var(--negative-muted)" strokeWidth="1" strokeDasharray="3,3" />
            <line x1="0" y1="60" x2="300" y2="60" stroke="var(--text-soft)" strokeWidth="1.5" strokeDasharray="4,4" />
            <line x1="0" y1="100" x2="300" y2="100" stroke="var(--positive-muted)" strokeWidth="1" strokeDasharray="3,3" />
            <path d="M 10,90 Q 70,80 120,60 Q 180,30 280,40" fill="none" stroke="#ef4444" strokeWidth="2.5" />
            <circle cx="120" cy="60" r="5" fill="#ef4444" />
            <text x="10" y="55" fontSize="11" fill="var(--text-soft)">50 (기준선)</text>
            <text x="130" y="80" fontSize="12" fill="#ef4444" fontWeight="bold">50 상향 돌파 (매수 우위)</text>
          </svg>
        )
      },
      { 
        label: '과매도권 회복 (+35점)', 
        desc: '주가가 지나치게 빠져 RSI가 30 이하로 내려갔다가, 다시 30을 회복할 때 나오는 단기 반등 신호입니다.',
        graphic: (
          <svg viewBox="0 0 300 120" width="100%" height="100%" preserveAspectRatio="xMidYMid meet">
            <line x1="0" y1="20" x2="300" y2="20" stroke="var(--negative-muted)" strokeWidth="1" strokeDasharray="3,3" />
            <line x1="0" y1="60" x2="300" y2="60" stroke="var(--text-soft)" strokeWidth="1" strokeDasharray="4,4" />
            <line x1="0" y1="100" x2="300" y2="100" stroke="var(--positive-muted)" strokeWidth="2" strokeDasharray="3,3" />
            <path d="M 10,80 L 80,115 L 140,95 L 200,80 L 280,65" fill="none" stroke="#ef4444" strokeWidth="2.5" />
            <circle cx="140" cy="95" r="5" fill="#ef4444" />
            <text x="10" y="95" fontSize="11" fill="var(--text-soft)">30 (침체)</text>
            <text x="150" y="110" fontSize="12" fill="#ef4444" fontWeight="bold">30선 회복 (과매도 탈출)</text>
          </svg>
        )
      },
      { 
        label: '추세 이탈 (-35점)', 
        desc: '매수세가 꺾이며 RSI가 50 아래로 내려갈 때 나타나는 하락 전환 신호입니다.',
        graphic: (
          <svg viewBox="0 0 300 120" width="100%" height="100%" preserveAspectRatio="xMidYMid meet">
            <line x1="0" y1="20" x2="300" y2="20" stroke="var(--negative-muted)" strokeWidth="1" strokeDasharray="3,3" />
            <line x1="0" y1="60" x2="300" y2="60" stroke="var(--text-soft)" strokeWidth="2" strokeDasharray="4,4" />
            <line x1="0" y1="100" x2="300" y2="100" stroke="var(--positive-muted)" strokeWidth="1" strokeDasharray="3,3" />
            <path d="M 10,40 Q 80,45 130,60 Q 200,80 280,105" fill="none" stroke="#3b82f6" strokeWidth="2.5" />
            <circle cx="130" cy="60" r="5" fill="#3b82f6" />
            <text x="140" y="55" fontSize="12" fill="#3b82f6" fontWeight="bold">50 하향 돌파 (추세 꺾임)</text>
          </svg>
        )
      }
    ]
  }
};

function DisclaimerModal({ onClose }) {
  return (
    <div className="modal-backdrop" onClick={onClose} style={{position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.5)', zIndex: 9999, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
      <div className="modal-content" onClick={e => e.stopPropagation()} style={{background: 'var(--panel-bg, #ffffff)', padding: '28px', borderRadius: '16px', maxWidth: '520px', width: '90%', maxHeight: '90vh', overflowY: 'auto', boxShadow: '0 10px 25px rgba(0,0,0,0.1)'}}>
        <h3 style={{marginTop: 0, fontSize: '18px'}}>서비스 이용 면책 조항</h3>
        <p style={{fontSize: '13px', lineHeight: '1.6', color: 'var(--text-soft)'}}>
          본 웹사이트는 정식 금융투자업자나 유사투자자문업자가 아니며, 특정 종목의 매수·매도·보유를 권유하지 않습니다.<br/><br/>
          제공되는 모든 지표와 스코어는 자동화된 알고리즘에 의한 객관적 산출물로 미래의 수익을 보장하지 않으며, 어떠한 1:1 투자 자문도 제공하지 않습니다.<br/><br/>
          제공된 정보는 참고용일 뿐이며, 모든 투자 판단과 그에 따른 최종적인 책임은 전적으로 투자자 본인에게 있습니다.
        </p>
        <button onClick={onClose} style={{marginTop: '16px', padding: '10px 16px', background: 'var(--accent)', color: '#fff', border: 'none', borderRadius: '8px', cursor: 'pointer', width: '100%'}}>확인</button>
      </div>
    </div>
  );
}

function EducationalGuideModal({ guideKey, onClose }) {
  const guide = educationalGuides[guideKey];
  if (!guide) return null;
  return (
    <div className="modal-backdrop" onClick={onClose} style={{position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.5)', zIndex: 9999, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
      <div className="modal-content" onClick={e => e.stopPropagation()} style={{background: 'var(--panel-bg, #ffffff)', padding: '28px', borderRadius: '16px', maxWidth: '520px', width: '90%', maxHeight: '90vh', overflowY: 'auto', boxShadow: '0 10px 25px rgba(0,0,0,0.1)'}}>
        <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px'}}>
          <h3 style={{margin: 0, fontSize: '18px', color: 'var(--text)'}}>{guide.title} 읽는 법</h3>
          <button onClick={onClose} style={{background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', display: 'flex'}}><X size={20} /></button>
        </div>
        <p style={{fontSize: '13.5px', color: 'var(--text-soft)', marginBottom: '24px', lineHeight: '1.5'}}>이 지표에서 자주 나타나는 패턴과 기준 점수입니다. 캔들과 지표 선의 움직임을 자세히 확인해 보세요.</p>
        <div style={{display: 'flex', flexDirection: 'column', gap: '20px'}}>
          {guide.points.map((pt, i) => (
            <div key={i} style={{background: 'var(--surface-sunken, #f8fafc)', padding: '20px', borderRadius: '12px', border: '1px solid var(--border)'}}>
              <strong style={{display: 'block', fontSize: '16px', marginBottom: '8px', color: 'var(--text)'}}>{pt.label}</strong>
              <p style={{margin: '0 0 16px 0', fontSize: '13.5px', color: 'var(--text-soft)', lineHeight: '1.5'}}>{pt.desc}</p>
              <div style={{width: '100%', height: '140px', background: 'var(--app-bg, #ffffff)', borderRadius: '8px', border: '1px solid var(--border)', padding: '10px', boxSizing: 'border-box'}}>
                {pt.graphic}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function PublicAnalysisUnavailable({ message }) {
  return (<section className="public-analysis-panel public-analysis-unavailable"><p>PUBLIC ANALYSIS FEED</p><h3>공개 분석 결과를 준비 중입니다.</h3><span>{message || '서버에서 가격 없는 분석 결과가 발행되면 이곳에 지표별 해석이 표시됩니다.'}</span></section>);
}

function PublicAnalysisPanel({ stock }) {
  const [helpKey, setHelpKey] = useState(null);
  const reasons = Array.from(new Set([...(stock.raw?.confidenceReasons || stock.raw?.signal?.reasons || []), ...Object.values(stock.indicatorStates || {}).flatMap((state) => state?.reasons || [])].filter(Boolean))).slice(0, 16);
  const states = Object.entries(stock.indicatorStates || {}).filter(([, state]) => state?.state || (state?.reasons || []).length);
  const components = stock.components.filter((component) => component.key !== 'penalty');
  const componentByKey = Object.fromEntries(components.map((component) => [component.key, component]));
  const supportingReasons = reasons.filter((reason) => !isCautionReason(reason));
  const cautionReasons = reasons.filter(isCautionReason);
  const baseId = 'public-analysis-' + String(stock.id || stock.code || 'stock').replace(/[^a-zA-Z0-9_-]/g, '-');
  const sectionId = (suffix) => baseId + '-' + suffix;
  const sections = [
    { id: sectionId('overview'), label: '종합 해석', description: '현재 분류와 읽는 방법' },
    { id: sectionId('scores'), label: '점수 구성', description: '지표별 기여도' },
    { id: sectionId('evidence'), label: '반영한 조건', description: '긍정·주의 근거' },
    { id: sectionId('indicators'), label: '지표별 해설', description: '상태와 추가 확인점' },
  ];

  return (
    <section className="public-analysis-panel">
      <AnalysisContentsRail sections={sections} />
      <div className="public-analysis-header">
        <div><p>REAL ANALYSIS · PRICE-FREE VIEW</p><h3>{stock.name}</h3><span>{stock.market}:{stock.code} · 분석 기준일 {stock.updatedAt}</span></div>
        <div className="public-status-stack"><strong className="glow-text">{formatNumber(stock.confidence, 1)}점</strong><span className={'risk-chip risk-' + stock.riskState}>{stock.label}</span></div>
      </div>

      <section id={sectionId('overview')} className="public-analysis-section public-overview-section">
        <div className="public-section-heading"><span>01 · 종합 해석</span><h4>이 결과를 이렇게 읽어보세요</h4></div>
        <div className="public-conclusion"><span>현재 분류</span><p>{publicConclusion(stock)}</p></div>
        <div className="public-reading-grid">
          <article><span>점수가 말하는 것</span><strong>{formatNumber(stock.confidence, 1)}점 · {stock.label}</strong><p>여러 기술 조건이 같은 방향을 가리키는 정도를 교육용 점수로 묶었습니다. 한 개 지표만으로 결론을 내리지 않습니다.</p></article>
          <article><span>뒷받침 조건</span><strong>{supportingReasons.length}개</strong><p>추세·변동성·거래량처럼 현재 해석을 지지하는 조건의 수입니다. 아래 근거에서 항목별 의미를 확인할 수 있습니다.</p></article>
          <article><span>추가 확인 조건</span><strong>{cautionReasons.length}개</strong><p>엇갈리거나 약화될 수 있는 조건입니다. 숫자가 적어도 방향을 단정하지 않고 함께 살펴봐야 합니다.</p></article>
        </div>
        <p className="public-analysis-note">실제 차트 입력값을 바탕으로 만든 결과입니다. 가격·캔들·가상 차트·원시 지표 수치는 공개하지 않고, 분석에 사용된 조건과 해석만 제공합니다.</p>
      </section>

      <section id={sectionId('scores')} className="public-analysis-section">
        <div className="public-section-heading"><span>02 · 점수 구성</span><h4>어떤 지표가 이번 해석에 반영됐나요?</h4><p>점수가 높을수록 해당 기술 조건이 현재 상태를 더 뒷받침한다는 뜻이며, 매수·매도 지시가 아닙니다.</p></div>
        <div className="public-component-grid">{components.map((component) => <article key={component.key} className="public-component-card" style={{ '--component-color': component.color }}><span>{component.label}</span><strong>{formatNumber(component.score, 1)}점</strong><small>{publicIndicatorGuides[component.key]?.focus || '조건 일치 정도를 교육용 점수로 정리했습니다.'}</small><meter min="0" max={component.max || 100} value={Math.max(0, component.score || 0)} /></article>)}</div>
      </section>

      {adsensePlacementApproved && <div style={{ margin: '24px 0' }}><AdSenseSlot title="분석 패널 중간 광고" /></div>}

      <section id={sectionId('evidence')} className="public-analysis-section public-evidence-section">
        <div className="public-section-heading"><span>03 · 반영한 조건</span><h4>긍정 조건과 주의 조건을 나눠 확인하세요</h4><p>같은 종목 안에서도 상승 쪽 근거와 주의할 근거가 함께 존재할 수 있습니다.</p></div>
        <div className="public-evidence-columns">
          <article className="public-evidence-card supportive"><header><strong>해석을 뒷받침한 조건</strong><span>{supportingReasons.length}개</span></header><div>{supportingReasons.length ? supportingReasons.map((reason) => <span key={reason}>{publicReasonLabel(reason)}</span>) : <small>현재 공개된 뒷받침 조건이 없습니다.</small>}</div></article>
          <article className="public-evidence-card caution"><header><strong>함께 확인할 조건</strong><span>{cautionReasons.length}개</span></header><div>{cautionReasons.length ? cautionReasons.map((reason) => <span key={reason}>{publicReasonLabel(reason)}</span>) : <small>현재 뚜렷한 경고 조건이 없습니다.</small>}</div></article>
        </div>
        {stock.raw?.riskFlags?.length > 0 && <div className="public-risk-note"><Shield size={16} /><span><strong>추가 주의 신호:</strong> {stock.raw.riskFlags.map(publicReasonLabel).join(' · ')}</span></div>}
      </section>

      <section id={sectionId('indicators')} className="public-analysis-section public-state-detail">
        <div className="public-section-heading"><span>04 · 지표별 해설 (교육용 수치)</span><h4>각 지표가 말하는 현재 상태</h4><p>각 항목의 수치는 학습용으로 제공되며, 가격 차트 없이 기술적 지표의 상태만을 나타냅니다.</p></div>
        {states.length ? states.map(([key, state]) => {
          const component = componentByKey[key];
          const stateReasons = (state.reasons || []).slice(0, 6);
          const metrics = stock.sortMetrics?.[key];
          return (
            <article key={key} className="public-indicator-explainer">
              <header>
                <div style={{display: 'flex', flexDirection: 'column'}}>
                  <div style={{display: 'flex', alignItems: 'center', gap: '6px'}}>
                    <span>{publicIndicatorGuides[key]?.label || componentMeta[key]?.label || key}</span>
                    {educationalGuides[key] && (
                      <button onClick={() => setHelpKey(key)} style={{background: 'none', border: 'none', cursor: 'pointer', padding: 0, color: 'var(--text-muted)', display: 'flex', alignItems: 'center'}} title="패턴 기준 보기">
                        <HelpCircle size={14} />
                      </button>
                    )}
                  </div>
                  <h5>{publicStateLabel(state.state)}</h5>
                </div>
                <strong>{component ? formatNumber(component.score, 1) + '점' : '상태 확인'}</strong>
              </header>
              <p>{publicStateExplanation(key, state.state)}</p>
              
              {metrics && Object.keys(metrics).length > 0 && (
                <div className="public-metric-summary" style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', margin: '12px 0', padding: '12px', background: 'var(--surface-sunken)', borderRadius: '6px' }}>
                  {Object.entries(metrics).map(([mKey, mVal]) => mVal !== undefined && mVal !== null ? (
                    <div key={mKey} className="metric-badge" style={{ display: 'flex', flexDirection: 'column' }}>
                      <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{sortOptionByKey[`detail.${key}.${mKey}`]?.label || mKey}</span>
                      <strong style={{ fontSize: '14px' }}>{typeof mVal === 'number' ? formatNumber(mVal, 4) : mVal}</strong>
                    </div>
                  ) : null)}
                </div>
              )}

              <div className="public-explainer-prompt">
                <span>이번 분석에서 확인한 이유</span>
                <div>{stateReasons.length ? stateReasons.map((reason) => <span key={reason}>{publicReasonLabel(reason)}</span>) : <small>세부 근거를 다음 분석 갱신에서 보완합니다.</small>}</div>
              </div>
            </article>
          );
        }) : <div className="public-empty-detail">현재 종목의 지표별 해설을 준비 중입니다.</div>}
      </section>
      {helpKey && <EducationalGuideModal guideKey={helpKey} onClose={() => setHelpKey(null)} />}
    </section>
  );
}
function PrivatePerformancePanel({ performance }) {
  const benchmarks = Object.entries(performance?.benchmarks || {});
  const comparisonStatus = performance?.benchmarkStatus === 'complete'
    ? '동일 기준일 · 마지막 확정 종가 비교'
    : '일부 기준지수 데이터를 준비 중입니다.';

  return (
    <section className="private-performance-panel">
      <div className="orders-header">
        <div><p>ADMIN ONLY · KIS PAPER RESEARCH</p><h3>모의투자 · 시장 기준 비교</h3></div>
        <Shield size={18} />
      </div>
      {!performance ? <div className="private-performance-empty">서버가 비교 기준일을 설정한 뒤, 관리자 전용 성과 비교가 이곳에 표시됩니다.</div> : <>
        <div className="private-performance-summary">
          <article><span>모의계좌 누적 수익률</span><strong className={Number(performance.returnPct || 0) >= 0 ? 'pnl-up' : 'pnl-down'}>{formatSigned(performance.returnPct, 2)}%</strong><small>기준일 {performance.baselineDate || '-'} · 총 평가자산 {formatNumber(performance.totalEquity, 0)}</small></article>
          <article><span>비교 기준</span><strong>{comparisonStatus}</strong><small>기준지수의 원시 값은 표시하지 않고, 동일 시작일 대비 변동률만 비교합니다.</small></article>
        </div>
        <div className="private-benchmark-grid">
          {benchmarks.map(([key, benchmark]) => <article key={key}>
            <span>{benchmark.label || key}</span>
            <strong className={Number(benchmark.returnPct || 0) >= 0 ? 'pnl-up' : 'pnl-down'}>{formatSigned(benchmark.returnPct, 2)}%</strong>
            <p>계좌와의 수익률 차이 <b className={Number(benchmark.gapPctPoints || 0) >= 0 ? 'pnl-up' : 'pnl-down'}>{formatSigned(benchmark.gapPctPoints, 2)}%p</b></p>
            <small>기준일 {benchmark.baselineDate || performance.baselineDate || '-'} · 기준시각 {benchmark.asOfDate || '-'}</small>
          </article>)}
        </div>
        <p className="private-performance-note">운영자 KIS 모의투자 실험의 사실형 비교값입니다. 실제 투자 성과·수익 보장·매매 권유가 아니며, 비교 기준과 기간은 위에 표시된 값으로 한정됩니다.</p>
      </>}
    </section>
  );
}
function PortfolioSnapshot({ portfolio, onRefresh, refreshBusy, refreshMessage, canRefresh }) {
  const totalEval = Number(portfolio.totalEvalAmt || 0);
  const reportedCash = Number(portfolio.cash || 0);
  const totalEquity = Number(portfolio.totalEquity || reportedCash + totalEval);
  const derivedCash = totalEquity - totalEval;
  const cash = totalEquity > 0 && derivedCash >= 0 ? derivedCash : reportedCash;
  const initialCash = Number(portfolio.initialCash || totalEquity);
  // Always derive these from the same account basis so old snapshots cannot
  // display a positive P&L beside a lower total asset value.
  const totalPnl = totalEquity - initialCash;
  const unrealizedPnl = Number(portfolio.unrealizedPnl || 0);
  const realizedPnl = totalPnl - unrealizedPnl;
  const returnPct = initialCash > 0 ? (totalPnl / initialCash) * 100 : 0;
  const holdings = Array.isArray(portfolio.holdings) ? portfolio.holdings : [];
  const isUp = totalPnl >= 0;
  const isExamplePortfolio = String(portfolio.source || '').toLowerCase() === 'mock';
  const refreshLabel = refreshBusy ? '모의투자 새로고침 중...' : canRefresh ? '모의투자 새로고침' : '관리자 권한 필요';

  return (
    <section className="portfolio-strip">
      <div className="orders-header">
        <div><p>모의투자 성과 실험 · {BRAND_SHORT} · {portfolio.mode || 'paper'}</p><h3>가상 계좌 스냅샷</h3></div>
        <div className="portfolio-header-actions">
          <span className="portfolio-refresh-message" aria-live="polite">{refreshMessage}</span>
          <button type="button" className="paper-refresh-button" onClick={onRefresh} disabled={refreshBusy || !onRefresh}>
            <RefreshCw size={15} className={refreshBusy ? 'spin' : ''} />
            <span>{refreshLabel}</span>
          </button>
          <WalletCards size={18} />
        </div>
      </div>
      <div className="portfolio-hero">
        <div><span>{isExamplePortfolio ? '예시 포트폴리오 수익률' : '누적 계좌 수익률'}</span><strong className={isUp ? 'pnl-up' : 'pnl-down'}>{formatSigned(returnPct, 2)}%</strong><p>{isExamplePortfolio ? '공개 화면용 예시 수치입니다. 관리자 로그인 후 실제 모의투자 계좌를 확인할 수 있습니다.' : '초기 실험금 대비 현재 KIS 모의투자 계좌 전체 가치 기준입니다.'}</p></div>
        <div className="equity-card"><span>총 평가 자산</span><strong>{formatNumber(totalEquity, 0)}</strong><small>업데이트 {formatDateTime(portfolio.updatedAt)}</small></div>
      </div>
      <div className="portfolio-grid">
        <div><span>초기 실험금</span><strong>{formatNumber(initialCash, 0)}</strong></div>
        <div><span>현금</span><strong>{formatNumber(cash, 0)}</strong></div>
        <div><span>평가금액</span><strong>{formatNumber(totalEval, 0)}</strong></div>
        <div><span>계좌 기준 손익</span><strong className={isUp ? 'pnl-up' : 'pnl-down'}>{formatSigned(totalPnl, 0)}</strong></div>
        <div><span>현금·체결 반영</span><strong className={realizedPnl >= 0 ? 'pnl-up' : 'pnl-down'}>{formatSigned(realizedPnl, 0)}</strong></div>
        <div><span>평가손익</span><strong className={unrealizedPnl >= 0 ? 'pnl-up' : 'pnl-down'}>{formatSigned(unrealizedPnl, 0)}</strong></div>
        <div><span>보유 종목</span><strong>{formatNumber(portfolio.holdingCount ?? holdings.length, 0)}</strong></div>
      </div>
      <p className="section-note portfolio-legal-note">이 가상 계좌는 모의투자 실험 기록입니다. 실제 계좌 수익, 세금, 수수료, 슬리피지, 거래 제한을 보장하거나 대체하지 않습니다.</p>
      <div className="portfolio-holdings">
        {holdings.length === 0 && <div className="empty-watch">현재 가상 보유 종목이 없습니다.</div>}
        {holdings.slice(0, 6).map((holding) => (
          <div key={holding.code} className="holding-row">
            <span><strong>{holding.name}</strong><small>{holding.code} · {formatNumber(holding.qty, 0)}주</small></span>
            <span><strong>{formatNumber(holding.evalAmt, 0)}</strong><small className={Number(holding.pnlPct || 0) >= 0 ? 'pnl-up' : 'pnl-down'}>{formatSigned(Number(holding.pnlPct || 0), 2)}%</small></span>
          </div>
        ))}
      </div>
    </section>
  );
}

function TradeLogPanel({ logs }) {
  const [actionFilter, setActionFilter] = useState('ALL');
  const [sourceFilter, setSourceFilter] = useState('ALL');
  const sources = useMemo(() => ['ALL', ...Array.from(new Set(logs.map((log) => log.source || 'legacy'))).sort()], [logs]);
  const filteredLogs = useMemo(() => logs.filter((log) => (actionFilter === 'ALL' || String(log.action).toUpperCase() === actionFilter) && (sourceFilter === 'ALL' || String(log.source || 'legacy') === sourceFilter)), [logs, actionFilter, sourceFilter]);
  const executionSummary = useMemo(() => ({
    buyCount: filteredLogs.filter((log) => String(log.action).toUpperCase() === 'BUY').length,
    sellCount: filteredLogs.filter((log) => String(log.action).toUpperCase() === 'SELL').length,
    tradedAmount: filteredLogs.reduce((sum, log) => sum + Number(log.amount || 0), 0),
    realizedPnl: filteredLogs.reduce((sum, log) => sum + Number(log.pnl || 0), 0),
  }), [filteredLogs]);

  return (
    <section className="execution-history">
      <div className="orders-header">
        <div><p>모의 체결 기록</p><h3>가상 매매 로그</h3></div>
        <div className="execution-filters">
          <select value={actionFilter} onChange={(event) => setActionFilter(event.target.value)} aria-label="체결 구분 필터"><option value="ALL">전체 체결</option><option value="BUY">가상 매수</option><option value="SELL">가상 매도</option></select>
          <select value={sourceFilter} onChange={(event) => setSourceFilter(event.target.value)} aria-label="소스 필터">{sources.map((source) => <option key={source} value={source}>{source === 'ALL' ? '전체 소스' : source}</option>)}</select>
        </div>
      </div>
      <div className="execution-summary">
        <div><span>체결</span><strong>{filteredLogs.length}</strong></div>
        <div><span>가상 매수 / 매도</span><strong>{executionSummary.buyCount} / {executionSummary.sellCount}</strong></div>
        <div><span>실험 거래금액</span><strong>{formatNumber(executionSummary.tradedAmount, 0)}</strong></div>
        <div><span>실현손익</span><strong className={executionSummary.realizedPnl >= 0 ? 'pnl-up' : 'pnl-down'}>{formatSigned(executionSummary.realizedPnl, 0)}</strong></div>
      </div>
      <div className="execution-table">
        <table>
          <thead><tr><th>시간</th><th>구분</th><th>종목</th><th>수량</th><th>가격</th><th>금액</th><th>손익</th><th>사유</th><th>브로커 주문</th></tr></thead>
          <tbody>
            {filteredLogs.length === 0 && <tr><td colSpan="9" className="empty-table-cell">조건에 맞는 가상 체결 기록이 없습니다.</td></tr>}
            {filteredLogs.map((log, index) => (
              <tr key={`${log.code}-${log.time}-${index}`}>
                <td>{log.time}</td>
                <td><span className={`side side-${String(log.action).toLowerCase()}`}>{actionLabel(log.action)}</span></td>
                <td><span className="symbol-cell"><strong>{log.name}</strong><small>{log.code} · {log.source}</small></span></td>
                <td>{formatNumber(log.quantity, 0)}</td>
                <td>{formatNumber(log.price, 0)}</td>
                <td>{formatNumber(log.amount, 0)}</td>
                <td className={Number(log.pnl || 0) >= 0 ? 'pnl-up' : 'pnl-down'}>{log.pnl === undefined ? '-' : formatSigned(log.pnl, 0)}</td>
                <td>{reasonLabel(log.reason)}</td>
                <td>{log.brokerOrderNo || '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function OrdersPanel({ orders }) {
  return (
    <section className="orders-strip">
      <div className="orders-header"><div><p>리밸런싱 실험 후보</p><h3>다음 가상 주문 큐</h3></div><AlertTriangle size={18} /></div>
      <p className="section-note">아래 항목은 전략 엔진이 만든 실험 후보입니다. 실제 매매 권유가 아니라, 모의투자·백테스트 검증을 위한 기록입니다.</p>
      <div className="order-table">
        <table>
          <thead><tr><th>시간</th><th>코드</th><th>구분</th><th>금액</th><th>사유</th></tr></thead>
          <tbody>
            {orders.length === 0 && <tr><td colSpan="5" className="empty-table-cell">현재 가상 주문 후보가 없습니다.</td></tr>}
            {orders.map((order, index) => <tr key={`${order.code}-${order.action}-${order.amount}-${index}`}><td>{order.time}</td><td>{order.code}</td><td><span className={`side side-${String(order.action).toLowerCase()}`}>{actionLabel(order.action)}</span></td><td>{formatNumber(order.amount, 0)}</td><td>{reasonLabel(order.reason)}</td></tr>)}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export default function ResearchApp() {
  const [signals, setSignals] = useState(() => mockSignals.map(mapStockPayload));
  const [orders, setOrders] = useState(fallbackOrders);
  const [portfolio, setPortfolio] = useState(fallbackPortfolio);
  const [tradeLogs, setTradeLogs] = useState(fallbackTradeLogs);
  const [privatePerformance, setPrivatePerformance] = useState(null);
  const [selectedId, setSelectedId] = useState('');
  const [loading, setLoading] = useState(true);
  const [detailLoadingId, setDetailLoadingId] = useState('');
  const [hasLoaded, setHasLoaded] = useState(false);
  const [loadError, setLoadError] = useState('');
  const [searchText, setSearchText] = useState('');
  const [marketFilter, setMarketFilter] = useState('ALL');
  const [labelFilter, setLabelFilter] = useState('ALL');
  const [sortMode, setSortMode] = useState('confidence');
  const [sortDirection, setSortDirection] = useState('desc');
  const [workspaceView, setWorkspaceView] = useState('console');
  const [theme, setTheme] = useState(() => localStorage.getItem('mesugak_theme') || 'beigeOwl');

  useEffect(() => {
    localStorage.setItem('mesugak_theme', theme);
  }, [theme]);
  const [showDisclaimerModal, setShowDisclaimerModal] = useState(false);
  const [user, setUser] = useState(null);
  const [isAdmin, setIsAdmin] = useState(false);
  const [adminViewActive, setAdminViewActive] = useState(false);
  const [adminChecking, setAdminChecking] = useState(false);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [settingsStatus, setSettingsStatus] = useState('');
  const [paperRefreshBusy, setPaperRefreshBusy] = useState(false);
  const [paperAccountMessage, setPaperAccountMessage] = useState('개인 모의투자 계좌는 관리자 로그인 후 확인할 수 있습니다.');
  const paperRefreshSubscriptionRef = useRef(null);
  const liveDataAccessEnabled = isAdmin && adminViewActive;
  const activeSort = sortOptionByKey[sortMode] || sortOptionByKey.confidence;

  const summary = useMemo(() => ({
    observed: signals.length,
    strong: signals.filter((signal) => signal.confidence >= 70).length,
    defensive: signals.filter((signal) => signal.riskState === 'defensive').length,
    staged: orders.filter((order) => order.status === 'staged').length,
  }), [signals, orders]);

  const filteredSignals = useMemo(() => {
    const queryText = searchText.trim().toLowerCase();
    const rows = signals.filter((signal) => {
      const matchesSearch = !queryText || [signal.name, signal.code, signal.market, signal.label].join(' ').toLowerCase().includes(queryText);
      return matchesSearch && (marketFilter === 'ALL' || signal.market === marketFilter) && (labelFilter === 'ALL' || signal.labelKey === labelFilter);
    });
    return [...rows].sort((a, b) => {
      if (sortMode === 'name') return sortDirection === 'asc' ? a.name.localeCompare(b.name) : b.name.localeCompare(a.name);
      if (sortMode === 'market') {
        const compared = `${a.market}:${a.code}`.localeCompare(`${b.market}:${b.code}`);
        return sortDirection === 'asc' ? compared : -compared;
      }
      const aValue = sortValue(a, sortMode);
      const bValue = sortValue(b, sortMode);
      if (aValue === null && bValue === null) return a.name.localeCompare(b.name);
      if (aValue === null) return 1;
      if (bValue === null) return -1;
      const compared = aValue - bValue;
      return sortDirection === 'asc' ? compared : -compared;
    });
  }, [signals, searchText, marketFilter, labelFilter, sortMode, sortDirection]);

  // With no manual selection, the report always starts from the first visible row
  // after the current search, filters, and sort order are applied.
  const selected = useMemo(() => (
    filteredSignals.find((signal) => signal.id === selectedId) ?? filteredSignals[0] ?? signals[0]
  ), [filteredSignals, selectedId, signals]);

  const refreshPrivatePaperAccount = async (activeUser = user) => {
    if (!activeUser || !firebaseReady || !db) {
      setPaperAccountMessage('개인 모의투자 계좌는 관리자 로그인 후 확인할 수 있습니다.');
      return false;
    }
    try {
      const [loadedPortfolio, loadedLogs, loadedPrivatePerformance] = await Promise.all([
        loadPortfolioFromFirestore(),
        loadTradeLogsFromFirestore(),
        loadPrivatePerformanceFromFirestore(),
      ]);
      if (loadedPortfolio) {
        setPortfolio(loadedPortfolio);
        setPaperAccountMessage('Firestore에 저장된 최신 모의투자 계좌를 불러왔습니다.');
      } else {
        setPortfolio(emptyPaperPortfolio);
        setPaperAccountMessage('저장된 모의투자 계좌 스냅샷이 아직 없습니다. 새로고침을 요청해 주세요.');
      }
      setTradeLogs(loadedLogs);
      setPrivatePerformance(loadedPrivatePerformance);
      return Boolean(loadedPortfolio);
    } catch (error) {
      const denied = error?.code === 'permission-denied';
      setPaperAccountMessage(
        denied
          ? '계좌 조회 권한이 없습니다. 관리자 Google 계정으로 로그인한 뒤 다시 시도하세요.'
          : `모의투자 계좌를 불러오지 못했습니다: ${error?.message || '알 수 없는 오류'}`,
      );
      return false;
    }
  };

  const stopPaperRefreshListener = () => {
    if (paperRefreshSubscriptionRef.current) {
      paperRefreshSubscriptionRef.current();
      paperRefreshSubscriptionRef.current = null;
    }
  };

  const requestPaperAccountRefresh = async () => {
    if (!user || !isAdmin) {
      setPaperAccountMessage('관리자 Google 계정으로 로그인한 뒤 새로고침할 수 있습니다.');
      return;
    }
    if (!firebaseReady || !db) {
      setPaperAccountMessage('Firebase 환경이 설정되지 않아 모의투자 계좌를 요청할 수 없습니다.');
      return;
    }
    if (paperRefreshBusy) return;

    stopPaperRefreshListener();
    setPaperRefreshBusy(true);
    setPaperAccountMessage('학교 서버에 KIS 모의투자 계좌 새로고침을 요청하는 중입니다...');
    try {
      const requestRef = await addDoc(collection(db, 'paper_refresh_requests'), {
        status: 'pending',
        market: 'KR',
        requestedAt: serverTimestamp(),
        requestedByUid: user.uid,
        source: 'web',
      });
      setPaperAccountMessage('요청을 보냈습니다. 학교 서버가 KIS 잔고를 조회해 반영할 때까지 기다리는 중입니다.');
      paperRefreshSubscriptionRef.current = onSnapshot(
        requestRef,
        (snapshot) => {
          if (!snapshot.exists()) {
            stopPaperRefreshListener();
            setPaperRefreshBusy(false);
            setPaperAccountMessage('새로고침 요청 상태를 찾을 수 없습니다. 다시 시도해 주세요.');
            return;
          }
          const request = snapshot.data() || {};
          if (request.status === 'completed') {
            stopPaperRefreshListener();
            setPaperAccountMessage('KIS 잔고 조회가 끝났습니다. 최신 평가금액을 불러오는 중입니다...');
            void refreshPrivatePaperAccount(user).then((loaded) => {
              setPaperRefreshBusy(false);
              if (loaded) setPaperAccountMessage('누른 시점에 학교 서버가 조회한 KIS 모의투자 계좌 값으로 갱신했습니다.');
            });
          } else if (request.status === 'failed') {
            stopPaperRefreshListener();
            setPaperRefreshBusy(false);
            setPaperAccountMessage('학교 서버가 모의투자 계좌를 갱신하지 못했습니다. 잠시 뒤 다시 시도해 주세요.');
          }
        },
        () => {
          stopPaperRefreshListener();
          setPaperRefreshBusy(false);
          setPaperAccountMessage('새로고침 상태를 확인하지 못했습니다. 페이지를 새로 열거나 다시 시도해 주세요.');
        },
      );
    } catch (error) {
      setPaperRefreshBusy(false);
      setPaperAccountMessage(
        error?.code === 'permission-denied'
          ? '계좌 새로고침 권한이 없습니다. 관리자 Google 계정으로 로그인해 주세요.'
          : `새로고침 요청을 만들지 못했습니다: ${error?.message || '알 수 없는 오류'}`,
      );
    }
  };
  const refreshSignals = async (adminAccess = adminViewActive) => {
    setLoading(true); setLoadError('');
    try {
      const loaded = await loadSignalsFromFirestore({ admin: adminAccess });
      if (loaded.length > 0) {
        const nextSelectedId = adminAccess && loaded.some((signal) => signal.id === selectedId) ? selectedId : '';
        const selectedIndex = Math.max(0, loaded.findIndex((signal) => signal.id === nextSelectedId));
        const selectedSignal = loaded[selectedIndex];
        if (adminAccess && firebaseReady && db && !selectedSignal.raw?.hasFullHistory) { const snap = await getDoc(doc(db, 'stock_analysis', selectedSignal.id)); if (snap.exists()) loaded[selectedIndex] = mapStockPayload({ ...selectedSignal.raw, ...snap.data(), id: selectedSignal.id }); }
        setSignals(loaded); setSelectedId(nextSelectedId);
      } else { const mock = mockSignals.map(mapStockPayload); setSignals(mock); setSelectedId(mock[0]?.id || ''); setLoadError(adminAccess ? 'Firestore에 V2 분석 목록이 아직 없습니다. 예시 데이터로 표시 중입니다.' : '공개 분석 결과가 없어 로컬 테스트용 예시 데이터를 표시합니다.'); }
      if (adminAccess) { const loadedOrders = await loadOrdersFromFirestore(true).catch(() => []); setOrders(loadedOrders.length > 0 ? loadedOrders : fallbackOrders); } else { setOrders([]); }
    } catch (error) { const mock = mockSignals.map(mapStockPayload); setSignals(mock); setSelectedId(mock[0]?.id || ''); setOrders([]); setLoadError(adminAccess ? `Firestore 조회에 실패해 예시 데이터로 전환했습니다: ${error?.message || '알 수 없는 오류'}` : '공개 분석 결과가 없어 로컬 테스트용 예시 데이터를 표시합니다.'); }
    finally { setLoading(false); setHasLoaded(true); }
  };

  const enterAdminAnalysis = () => {
    if (!isAdmin) return;
    setAdminViewActive(true);
    setWorkspaceView('console');
    setSettingsStatus('관리자 분석 화면을 불러오는 중입니다.');
    void refreshSignals(true);
    void refreshPrivatePaperAccount(user);
  };

  const exitAdminAnalysis = () => {
    setAdminViewActive(false);
    setWorkspaceView('console');
    setSettingsStatus('공개 분석 화면으로 전환했습니다.');
    stopPaperRefreshListener();
    setPaperRefreshBusy(false);
    setPortfolio(fallbackPortfolio);
    setTradeLogs(fallbackTradeLogs);
    setPrivatePerformance(null);
    setPaperAccountMessage('개인 모의투자 계좌는 관리자 분석 화면에서만 확인할 수 있습니다.');
    void refreshSignals(false);
  };

  const loadSignalDetail = async (signal) => {
    if (!liveDataAccessEnabled || !firebaseReady || !db || signal.raw?.hasFullHistory) return;
    setDetailLoadingId(signal.id);
    try {
      const snap = await getDoc(doc(db, 'stock_analysis', signal.id));
      if (!snap.exists()) return;
      const enriched = mapStockPayload({ ...signal.raw, ...snap.data(), id: signal.id });
      setSignals((prev) => prev.map((item) => (item.id === signal.id ? enriched : item)));
    } catch (error) {
      setLoadError(error?.message || '상세 분석 데이터를 불러오지 못했습니다.');
    } finally {
      setDetailLoadingId((current) => (current === signal.id ? '' : current));
    }
  };

  const selectSignal = async (signal) => {
    setSelectedId(signal.id);
    await loadSignalDetail(signal);
  };

  const loginWithGoogle = async () => {
    if (!auth || !googleProvider) {
      setSettingsStatus('Firebase 로그인 환경이 설정되지 않았습니다.');
      return;
    }
    setSettingsStatus('로그인 중...');
    try {
      await signInWithPopup(auth, googleProvider);
    } catch (error) {
      setSettingsStatus(`${error?.code || 'auth/error'}: ${error?.message || '로그인 실패'}`);
    }
  };

  const loginWithRedirect = async () => {
    if (!auth || !googleProvider) {
      setSettingsStatus('Firebase 로그인 환경이 설정되지 않았습니다.');
      return;
    }
    setSettingsStatus('Google 로그인으로 이동합니다.');
    try {
      await signInWithRedirect(auth, googleProvider);
    } catch (error) {
      setSettingsStatus(`${error?.code || 'auth/error'}: ${error?.message || '이동 로그인 실패'}`);
    }
  };

  // Firestore initial sync is intentionally kicked off once on mount.
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { refreshSignals(); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => () => { stopPaperRefreshListener(); }, []);
  // Firestore itself decides administrator access. Public users never request
  // live analysis data; they remain in the explicit no-live-data education view.
  useEffect(() => {
    if (!auth) return undefined;
    let cancelled = false;
    getRedirectResult(auth).catch((error) => setSettingsStatus(`${error?.code || 'auth/error'}: ${error?.message || '이동 로그인 실패'}`));
    const unsubscribe = onAuthStateChanged(auth, (nextUser) => {
      setUser(nextUser);
      setSettingsStatus('');
      if (!nextUser) {
        setIsAdmin(false);
        setAdminViewActive(false);
        setAdminChecking(false);
        setWorkspaceView('console');
        setSortMode('confidence');
        stopPaperRefreshListener();
        setPaperRefreshBusy(false);
        setPortfolio(fallbackPortfolio);
        setTradeLogs(fallbackTradeLogs);
        setPrivatePerformance(null);
        setPaperAccountMessage('개인 모의투자 계좌는 관리자 로그인 후 확인할 수 있습니다.');
        void refreshSignals(false);
        return;
      }
      setAdminChecking(true);
      setIsAdmin(false);
      setAdminViewActive(false);
      setPaperAccountMessage('관리자 권한을 확인하는 중입니다...');
      void (async () => {
        let granted = false;
        try {
          const email = String(nextUser.email || '').trim();
          if (firebaseReady && db && email) {
            const adminSnapshot = await getDoc(doc(db, 'admins', email));
            granted = adminSnapshot.exists();
          }
        } catch { granted = false; }
        if (cancelled) return;
        setIsAdmin(granted);
        setAdminViewActive(false);
        setAdminChecking(false);
        if (granted) {
          setSettingsStatus('관리자 권한 확인됨 · 기본 공개 분석 화면을 표시합니다.');
          void refreshSignals(false);
        } else {
          setSettingsStatus('관리자 권한이 없어 가격 없는 공개 분석 결과만 표시합니다.');
          setWorkspaceView('console');
          setSortMode('confidence');
          setPortfolio(fallbackPortfolio);
          setTradeLogs(fallbackTradeLogs);
        setPrivatePerformance(null);
          setPaperAccountMessage('개인 모의투자 계좌는 관리자 계정에서만 확인할 수 있습니다.');
          void refreshSignals(false);
        }
      })();
    });
    return () => { cancelled = true; unsubscribe(); };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
  // Detail hydration follows the selected symbol and writes into local UI state.
  // eslint-disable-next-line react-hooks/set-state-in-effect, react-hooks/exhaustive-deps
  useEffect(() => { if (selected && !selected.raw?.hasFullHistory) loadSignalDetail(selected); }, [selected?.id]);

  if (!hasLoaded && loading) {
    return (
      <main className={`loading-screen ${themeClassMap[theme] || themeClassMap.light}`}>
        <div className="loading-panel"><RefreshCw size={22} className="spin" /><span>기술지표 데이터를 불러오는 중</span><strong>{BRAND_SHORT}</strong></div>
      </main>
    );
  }

  return (
    <main className={`terminal-shell ${themeClassMap[theme] || themeClassMap.light}`}>
      <aside className="watchlist">
        <div className="brand-block"><span>{BRAND_FULL}</span><h1>{BRAND_SHORT}</h1><p>기술지표를 읽고, 모의투자 실험으로 전략 아이디어를 검토합니다.</p></div>
        <div className="watchlist-meta"><span>{filteredSignals.length} / {summary.observed} 종목</span><button type="button" className="icon-button" onClick={() => refreshSignals(adminViewActive)} aria-label="데이터 새로고침"><RefreshCw size={16} className={loading ? 'spin' : ''} /></button></div>
        <div className="watch-filters" aria-label="종목 필터">

          <button type="button" className="filter-toggle" onClick={() => setFiltersOpen((open) => !open)} aria-expanded={filtersOpen} aria-controls="watch-filter-controls">
            <span><SlidersHorizontal size={15} /> {filtersOpen ? '필터·정렬 접기' : '필터·정렬 펼치기'}</span><ChevronDown size={16} className={filtersOpen ? 'open' : ''} />
          </button>
          {filtersOpen && <div id="watch-filter-controls" className="filter-controls">
          <input type="search" value={searchText} onChange={(event) => { setSearchText(event.target.value); setSelectedId(''); }} placeholder="종목명 또는 코드 검색" />
            <div className="filter-grid">
              <select value={marketFilter} onChange={(event) => { setMarketFilter(event.target.value); setSelectedId(''); }} aria-label="시장 필터"><option value="ALL">전체 시장</option><option value="KR">KR</option><option value="US">US</option></select>
              <select value={labelFilter} onChange={(event) => { setLabelFilter(event.target.value); setSelectedId(''); }} aria-label="조건 필터"><option value="ALL">전체 조건</option><option value="STRONG_BUY">강한 기술 조건</option><option value="BUY_CANDIDATE">관심 조건 충족</option><option value="WATCH">관찰</option><option value="HOLD">중립</option><option value="DEFENSIVE">방어 신호</option><option value="AVOID">리스크 신호</option></select>
            </div>
            <div className="sort-heading"><span>정렬 기준</span><strong style={{ color: activeSort.color }}>{activeSort.category}</strong></div>
            <div className="sort-direction" aria-label="정렬 방향"><button type="button" className={sortDirection === 'desc' ? 'active' : ''} onClick={() => { setSortDirection('desc'); setSelectedId(''); }}>높은 순</button><button type="button" className={sortDirection === 'asc' ? 'active' : ''} onClick={() => { setSortDirection('asc'); setSelectedId(''); }}>낮은 순</button></div>
            <select className="sort-select" value={sortMode} onChange={(event) => { setSortMode(event.target.value); setSelectedId(''); }} aria-label="종목 정렬">{(adminViewActive ? sortGroups : publicSortGroups).map((group) => <optgroup key={group.label} label={group.label}>{group.options.map((option) => <option key={option.key} value={option.key}>{option.category} · {option.label}</option>)}</optgroup>)}</select>
            <select value={theme} onChange={(event) => setTheme(event.target.value)} aria-label="테마">{themeOptions.map((option) => <option key={option.key} value={option.key}>{option.label} 테마</option>)}</select>
          </div>}
        </div>
        <div className="market-summary"><div><span>조건 강함</span><strong>{summary.strong}</strong></div><div><span>방어 신호</span><strong>{summary.defensive}</strong></div><div><span>실험 큐</span><strong>{summary.staged}</strong></div></div>
        <div className="signal-stack">
          {filteredSignals.length === 0 && <div className="empty-watch">조건에 맞는 종목이 없습니다.</div>}
          {filteredSignals.map((signal, index) => <Fragment key={signal.id}><button type="button" className={`watch-row ${selected.id === signal.id ? 'selected' : ''}`} onClick={() => selectSignal(signal)}><span className="watch-main"><strong>{signal.name}</strong><span>{signal.market}:{signal.code} · {signal.label}</span></span><span className={`watch-score score-${signal.riskState}`}>{formatNumber(signal.confidence, 1)}</span></button>{adsensePlacementApproved && (index + 1) % 5 === 0 && <WatchlistAd />}</Fragment>)}
        </div>
      </aside>

      <section className="chart-column">
        <header className="desk-topbar">
          <div><p>{loadError || (adminViewActive ? '관리자 Firestore 분석 데이터 · 교육/연구용 표시' : publicLiveDataApproved ? '권리 확인된 가격 없는 공개 분석 결과 · 교육/연구용 표시' : '공개 데이터 이용권 검토 중 · 교육/연구용 표시')}</p><h2>{BRAND_SHORT}</h2>{!user && <span className="topbar-disclaimer" onClick={() => setShowDisclaimerModal(true)} style={{cursor: 'pointer', textDecoration: 'underline'}}>특정 종목의 매수·매도·보유를 권유하지 않습니다. (상세보기)</span>}</div>
          <div className="topbar-actions">
            <div className="workspace-tabs" aria-label="작업 화면"><button type="button" className={workspaceView === 'console' ? 'active' : ''} onClick={() => setWorkspaceView('console')}>연구 콘솔</button>{adminViewActive && <button type="button" className={workspaceView === 'executions' ? 'active' : ''} onClick={() => setWorkspaceView('executions')}>모의투자 성과</button>}</div>
            {adminViewActive ? <div className="topbar-pills"><span><CandlestickChart size={14} /> 캔들</span><span><Cloud size={14} /> 이평·구름</span><span><Gauge size={14} /> RSI</span></div> : <div className="topbar-pills"><span><Shield size={14} /> 가격 없는 분석 근거</span></div>}
            <div className="auth-block"><span>{user ? (settingsStatus || (adminChecking ? '관리자 권한 확인 중...' : adminViewActive ? '관리자 분석 화면 · 실시간 분석 데이터 사용 중' : isAdmin ? '관리자 권한 확인됨 · 공개 분석 화면 사용 중' : '로그인됨 · 가격 없는 공개 분석 결과 사용 중')) : '로그인하지 않아도 가격 없는 분석 결과를 볼 수 있습니다.'}</span><div className="auth-buttons">{isAdmin && <button type="button" className="auth-button ghost" onClick={adminViewActive ? exitAdminAnalysis : enterAdminAnalysis}><span>{adminViewActive ? '공개 분석 보기' : '관리자 분석 보기'}</span></button>}<button type="button" className="auth-button" onClick={user ? () => signOut(auth) : loginWithGoogle}>{user ? <LogOut size={14} /> : <LogIn size={14} />}<span>{user ? '로그아웃' : '구글 로그인'}</span></button></div></div>
          </div>
        </header>
        <section className="notice-panel"><Shield size={18} /><p>이 서비스는 기술지표 학습 및 차트 분석 보조 도구입니다. 점수와 모의투자 결과는 연구용 참고값이며, 실제 수익을 보장하지 않습니다.</p></section>
        <section className="notice-panel data-rights-panel"><AlertTriangle size={18} /><p>{adminViewActive ? '관리자 분석 화면입니다. 원시 시세와 기술 차트를 포함한 최신 분석 데이터를 연구·운영 목적으로 표시합니다.' : publicLiveDataApproved ? '시장 데이터는 출처별 이용 조건이 다릅니다. 공개 화면은 확인된 범위에서만 가격·차트·세부 수치 없이 분석 결과와 해석 근거를 표시합니다.' : '공개 실데이터는 이용권과 공개 범위가 서면으로 확인될 때까지 비활성화합니다. 로그인한 관리자만 연구용 원시 분석과 모의투자 비교를 확인할 수 있습니다.'}</p></section>
        {workspaceView === 'console' && <>{adminViewActive ? selected ? <><div className="analysis-layout"><TechnicalChart stock={selected} loading={detailLoadingId === selected?.id} /><ScoreDock stock={selected} /></div><PublicAnalysisPanel stock={selected} /></> : <PublicAnalysisUnavailable message="관리자 분석 목록을 아직 불러오지 못했습니다. 잠시 후 새로고침해 주세요." /> : selected ? <PublicAnalysisPanel stock={selected} /> : <PublicAnalysisUnavailable message={publicLiveDataApproved ? loadError : '실제 종목 분석 데이터는 데이터 이용권과 공개 범위를 서면으로 확인한 뒤에만 공개합니다. 현재는 기술지표 교육·연구 안내만 제공합니다.'} />}{adsensePlacementApproved && <AdSenseSlot title="본문 광고" />}</>}
        {workspaceView === 'executions' && adminViewActive && <div className="execution-page"><PortfolioSnapshot portfolio={portfolio} onRefresh={requestPaperAccountRefresh} refreshBusy={paperRefreshBusy} refreshMessage={paperAccountMessage} canRefresh={Boolean(adminViewActive && firebaseReady && db)} /><PrivatePerformancePanel performance={privatePerformance} /><TradeLogPanel logs={tradeLogs} /><OrdersPanel orders={orders} />{adsensePlacementApproved && <AdSenseSlot title="성과 화면 광고" />}</div>}

      </section>
      {showDisclaimerModal && <DisclaimerModal onClose={() => setShowDisclaimerModal(false)} />}
    </main>
  );
}
