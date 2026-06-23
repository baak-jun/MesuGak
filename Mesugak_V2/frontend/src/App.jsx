import { useEffect, useMemo, useState } from 'react';
import { getRedirectResult, onAuthStateChanged, signInWithPopup, signInWithRedirect, signOut } from 'firebase/auth';
import { collection, doc, getDoc, getDocs, query, serverTimestamp, setDoc, where } from 'firebase/firestore';
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
  SlidersHorizontal,
  WalletCards,
} from 'lucide-react';
import { auth, db, firebaseReady, googleProvider } from './firebase';

const mockHistory = [
  70, 71, 70, 72, 73, 74, 73, 75, 77, 78, 79, 78, 80, 81, 82, 81, 83, 84, 83, 85,
].map((close, index, rows) => ({
  date: `2026-04-${String(index + 1).padStart(2, '0')}`,
  open: close - (index % 2 ? -0.6 : 0.7),
  high: close + 1.4,
  low: close - 1.5,
  close,
  volume: 1000000 + index * 35000,
  upper: close + 4.2,
  lower: close - 4.4,
  bbMid: close - 0.2,
  ma5: close - 0.1,
  ma20: close - 0.4,
  ma60: close - 1.5,
  ma120: close - 2.2,
  rsi: 45 + (index / rows.length) * 22,
  rsiSignal: 44 + (index / rows.length) * 18,
  tenkan: close - 0.8,
  kijun: close - 1.2,
  senkouA: close - 1.0,
  senkouB: close - 3.0 + (index % 4) * 0.3,
}));

const mockSignals = [
  {
    id: 'KR_005930',
    code: '005930',
    name: 'Samsung Electronics',
    market: 'KR',
    price: '78,400',
    confidence: 88,
    labelKey: 'STRONG_BUY',
    label: '강한 매수',
    signal: '매수 후보',
    stopLoss: '72,100',
    cashTarget: 12,
    riskState: 'normal',
    updatedAt: '2026-05-17',
    componentScores: {
      bollinger: 80,
      maSupport: 86,
      ichimoku: 92,
      rsi: 78,
    },
    sortMetrics: {
      bollinger: { percentB: 0.82, bandwidth: 0.19, bandwidthRank: 0.72 },
      maSupport: { priceToMa20Pct: 2.3, priceToMa60Pct: 7.8, aboveMa60Ratio: 0.88 },
      ichimoku: { priceToCloudPct: 5.1, tenkanToKijunPct: 1.7, cloudSpreadPct: 2.5 },
      rsi: { rsi: 61.4, rsiChange: 2.2 },
    },
    components: [
      { label: '일목균형표', score: 92, max: 100 },
      { label: '이동평균선', score: 86, max: 100 },
      { label: '볼린저밴드', score: 80, max: 100 },
      { label: 'RSI', score: 78, max: 100 },
      { label: '감점', score: 0, max: 100 },
    ],
    risks: [{ label: '리스크 상태', state: 'clear', value: 'NORMAL' }],
    raw: { history: mockHistory, marcap: 460000000000000 },
  },
];

const fallbackOrders = [
  { time: '10:19', code: '005930', action: 'BUY', reason: 'confidence_rebalance', amount: '203,000', status: 'staged' },
];

const fallbackTradeLogs = [
  {
    time: '10:21',
    code: '005930',
    action: 'BUY',
    name: 'Samsung Electronics',
    amount: '784,000',
    price: '78,400',
    quantity: 10,
    reason: 'paper_rebalance',
    source: 'mock',
  },
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
  cashTargetPct: 0.12,
  updatedAt: '2026-05-17',
  holdings: [
    {
      code: '005930',
      name: 'Samsung Electronics',
      qty: 10,
      evalAmt: 784000,
      buyAmt: 721000,
      pnlPct: 8.74,
    },
  ],
};

const componentMeta = {
  ichimoku: { label: '일목균형표', max: 100 },
  maSupport: { label: '이동평균선', max: 100 },
  bollinger: { label: '볼린저밴드', max: 100 },
  rsi: { label: 'RSI', max: 100 },
  valuation: { label: '가치판단', max: 100 },
  penalty: { label: '감점', max: 100 },
};

const componentWeights = {
  bollinger: 0.30,
  maSupport: 0.20,
  ichimoku: 0.15,
  rsi: 0.10,
  valuation: 0.25,
  penalty: -1,
};

const sortGroups = [
  {
    label: '?? ??',
    tone: 'market',
    options: [
      { key: 'confidence', label: '?? ??? ??', category: '?? ??' },
      { key: 'marketCap', label: '???? (KR? ??)', category: '?? ??', krOnly: true },
      { key: 'cash', label: '?? ?? ??', category: '?? ??' },
      { key: 'market', label: '?? / ??', category: '?? ??', text: true },
      { key: 'name', label: '???', category: '?? ??', text: true },
    ],
  },
  {
    label: '?? ??',
    tone: 'score',
    options: [
      { key: 'score.bollinger', label: '????? ??', category: '?????', color: '#3b82f6' },
      { key: 'score.maSupport', label: '????? ??', category: '?????', color: '#f59e0b' },
      { key: 'score.ichimoku', label: '????? ??', category: '?????', color: '#8b5cf6' },
      { key: 'score.rsi', label: 'RSI ??', category: 'RSI', color: '#ec4899' },
    ],
  },
  {
    label: '?? ?? ??',
    tone: 'detail',
    options: [
      { key: 'detail.bollinger.percentB', label: '%B', category: '?????', color: '#3b82f6' },
      { key: 'detail.bollinger.bandwidth', label: '???', category: '?????', color: '#3b82f6' },
      { key: 'detail.bollinger.bandwidthRank', label: '??? ???', category: '?????', color: '#3b82f6' },
      { key: 'detail.maSupport.priceToMa20Pct', label: 'MA20 ?? ???', category: '?????', color: '#f59e0b' },
      { key: 'detail.maSupport.priceToMa60Pct', label: 'MA60 ?? ???', category: '?????', color: '#f59e0b' },
      { key: 'detail.maSupport.aboveMa60Ratio', label: 'MA60 ?? ??', category: '?????', color: '#f59e0b' },
      { key: 'detail.ichimoku.priceToCloudPct', label: '??? ?? ???', category: '?????', color: '#8b5cf6' },
      { key: 'detail.ichimoku.tenkanToKijunPct', label: '???/??? ???', category: '?????', color: '#8b5cf6' },
      { key: 'detail.ichimoku.cloudSpreadPct', label: '??? ?', category: '?????', color: '#8b5cf6' },
      { key: 'detail.rsi.rsi', label: 'RSI ?', category: 'RSI', color: '#ec4899' },
      { key: 'detail.rsi.rsiChange', label: 'RSI ???', category: 'RSI', color: '#ec4899' },
    ],
  },
];

const sortOptions = sortGroups.flatMap((group) => group.options);
const sortOptionByKey = Object.fromEntries(sortOptions.map((option) => [option.key, option]));
const sortGroupLabels = ['\uC2DC\uC7A5 \uC815\uBCF4', '\uC0C1\uC704 \uC810\uC218', '\uC810\uC218 \uC138\uBD80 \uC218\uCE58'];
const sortText = {
  confidence: { label: '\uC885\uD569 \uC2E0\uB8B0\uB3C4 \uC810\uC218', category: '\uC885\uD569 \uC810\uC218' },
  marketCap: { label: '\uC2DC\uAC00\uCD1D\uC561 (KR\uB9CC \uC81C\uACF5)', category: '\uC2DC\uC7A5 \uC815\uBCF4' },
  cash: { label: '\uAD8C\uC7A5 \uD604\uAE08 \uBE44\uC911', category: '\uC2DC\uC7A5 \uC815\uBCF4' },
  market: { label: '\uC2DC\uC7A5 / \uCF54\uB4DC', category: '\uC2DC\uC7A5 \uC815\uBCF4' },
  name: { label: '\uC885\uBAA9\uBA85', category: '\uC2DC\uC7A5 \uC815\uBCF4' },
  'score.bollinger': { label: '\uBCFC\uB9B0\uC800\uBC34\uB4DC \uC810\uC218', category: '\uBCFC\uB9B0\uC800\uBC34\uB4DC' },
  'score.maSupport': { label: '\uC774\uB3D9\uD3C9\uADE0\uC120 \uC810\uC218', category: '\uC774\uB3D9\uD3C9\uADE0\uC120' },
  'score.ichimoku': { label: '\uC77C\uBAA9\uADE0\uD615\uD45C \uC810\uC218', category: '\uC77C\uBAA9\uADE0\uD615\uD45C' },
  'score.rsi': { label: 'RSI \uC810\uC218', category: 'RSI' },
  'detail.bollinger.percentB': { label: '%B', category: '\uBCFC\uB9B0\uC800\uBC34\uB4DC' },
  'detail.bollinger.bandwidth': { label: '\uBC34\uB4DC\uD3ED', category: '\uBCFC\uB9B0\uC800\uBC34\uB4DC' },
  'detail.bollinger.bandwidthRank': { label: '\uBC34\uB4DC\uD3ED \uBC31\uBD84\uC704', category: '\uBCFC\uB9B0\uC800\uBC34\uB4DC' },
  'detail.maSupport.priceToMa20Pct': { label: 'MA20 \uB300\uBE44 \uAD34\uB9AC\uC728', category: '\uC774\uB3D9\uD3C9\uADE0\uC120' },
  'detail.maSupport.priceToMa60Pct': { label: 'MA60 \uB300\uBE44 \uAD34\uB9AC\uC728', category: '\uC774\uB3D9\uD3C9\uADE0\uC120' },
  'detail.maSupport.aboveMa60Ratio': { label: 'MA60 \uC0C1\uD68C \uBE44\uC728', category: '\uC774\uB3D9\uD3C9\uADE0\uC120' },
  'detail.ichimoku.priceToCloudPct': { label: '\uAD6C\uB984\uB300 \uB300\uBE44 \uAD34\uB9AC\uC728', category: '\uC77C\uBAA9\uADE0\uD615\uD45C' },
  'detail.ichimoku.tenkanToKijunPct': { label: '\uC804\uD658\uC120 / \uAE30\uC900\uC120 \uAD34\uB9AC\uC728', category: '\uC77C\uBAA9\uADE0\uD615\uD45C' },
  'detail.ichimoku.cloudSpreadPct': { label: '\uAD6C\uB984\uB300 \uD3ED', category: '\uC77C\uBAA9\uADE0\uD615\uD45C' },
  'detail.rsi.rsi': { label: 'RSI \uAC12', category: 'RSI' },
  'detail.rsi.rsiChange': { label: 'RSI \uBCC0\uD654\uB7C9', category: 'RSI' },

};
sortGroups.forEach((group, index) => { group.label = sortGroupLabels[index]; });
sortOptions.forEach((option) => Object.assign(option, sortText[option.key] || {}));

const sortUi = {
  heading: '\uC815\uB82C \uAE30\uC900',
  ascending: '\uC624\uB984\uCC28\uC21C',
  descending: '\uB0B4\uB9BC\uCC28\uC21C',
  separator: ' \u00B7 ',
};

function numberAt(value, path) {
  const number = path.split('.').reduce((current, key) => current?.[key], value);
  return Number.isFinite(Number(number)) ? Number(number) : null;
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
function formatNumber(value, digits = 0) {
  const number = Number(value);
  if (!Number.isFinite(number)) return '-';
  return number.toLocaleString(undefined, {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  });
}

function formatTimestamp(value) {
  if (!value) return '-';
  if (value.toDate) return value.toDate().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '-' : date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function compactDate(value) {
  if (!value) return '';
  const text = String(value);
  return text.length > 5 ? text.slice(5) : text;
}

function riskStateFromPayload(payload) {
  const state = String(payload.riskState || '').toLowerCase();
  if (state === 'defensive') return 'defensive';
  if (state === 'caution' || state === 'watch') return 'watch';
  return 'normal';
}

function labelFromPayload(payload) {
  const value = String(payload.confidenceLabel || payload.status || 'UNKNOWN').toUpperCase();
  if (value === 'STRONG_BUY') return '강한 매수';
  if (value === 'BUY_CANDIDATE') return '매수 후보';
  if (value === 'WATCH') return '관찰';
  if (value === 'AVOID') return '회피';
  if (value === 'DEFENSIVE') return '방어';
  return value.replaceAll('_', ' ');
}

function formatDateTime(value) {
  if (!value) return '-';
  if (value.toDate) return value.toDate().toLocaleString([], { dateStyle: 'short', timeStyle: 'short' });
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString([], { dateStyle: 'short', timeStyle: 'short' });
}

function actionFromPayload(payload) {
  const action = payload.signal?.action || payload.status || 'HOLD';
  const value = String(action).toUpperCase();
  if (value === 'BUY_CANDIDATE') return '매수 후보';
  if (value === 'WATCH') return '관찰';
  if (value === 'REDUCE') return '축소';
  if (value === 'EXIT') return '청산';
  if (value === 'HOLD') return '보류';
  return value.replaceAll('_', ' ');
}

function stateLabel(value) {
  const key = String(value || '').toUpperCase();
  const labels = {
    SQUEEZE_RELEASE_UP: '응축 후 상방 돌파',
    BAND_RIDE_UP: '상단 밴드 추세',
    HEALTHY_MID_UP: '중심선 위 상승',
    SQUEEZE: '응축',
    EXPANSION_CURL_NEUTRAL: '확장 후 꺾임',
    FAILED_RELEASE: '돌파 실패',
    DOWNSIDE_EXPANSION: '하방 확장',
    NO_DATA: '데이터 없음',
    NEUTRAL: '중립',
  };
  return labels[key] || String(value || '-').replaceAll('_', ' ');
}

function mapComponents(payload) {
  const scores = payload.componentScores || {};
  const order = ['bollinger', 'maSupport', 'ichimoku', 'rsi', 'valuation', 'penalty'];
  return Object.entries(scores)
    .map(([key, value]) => ({
      key,
      label: componentMeta[key]?.label || key,
      score: Number(value || 0),
      max: componentMeta[key]?.max || 100,
      weight: componentWeights[key],
    }))
    .sort((a, b) => order.indexOf(a.key) - order.indexOf(b.key));
}

function mapRisks(payload) {
  const flags = payload.riskFlags || [];
  if (!flags.length) {
    return [{ label: '리스크 상태', state: 'clear', value: payload.riskState || 'NORMAL' }];
  }
  return flags.map((flag) => ({
    label: String(flag).replaceAll('_', ' '),
    state: payload.riskState === 'DEFENSIVE' ? 'danger' : 'watch',
    value: payload.riskState || 'CAUTION',
  }));
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
      ma5: Number(row.ma5),
      ma60: Number(row.ma60),
      ma120: Number(row.ma120),
      rsi: Number(row.rsi),
      rsiSignal: Number(row.rsiSignal),
      tenkan: Number(row.tenkan),
      kijun: Number(row.kijun),
      senkouA: Number(row.senkouA),
      senkouB: Number(row.senkouB),
    }))
    .filter((row) => [row.open, row.high, row.low, row.close].every(Number.isFinite));
}

function mapStockPayload(payload) {
  const history = normalizeHistory(payload.history);
  return {
    id: payload.id,
    code: payload.code,
    name: payload.name || payload.code,
    market: payload.market,
    price: formatNumber(payload.currentPrice, payload.market === 'US' ? 2 : 0),
    confidence: Number(payload.confidenceScore || 0),
    labelKey: String(payload.confidenceLabel || payload.status || 'UNKNOWN').toUpperCase(),
    label: labelFromPayload(payload),
    signal: actionFromPayload(payload),
    stopLoss: formatNumber(payload.stopLoss, payload.market === 'US' ? 2 : 0),
    cashTarget: Math.round(Number(payload.cashTargetPct || 0) * 100),
    riskState: riskStateFromPayload(payload),
    updatedAt: payload.lastDate || '-',
    components: mapComponents(payload),
    componentScores: payload.componentScores || {},
    sortMetrics: payload.sortMetrics || {},
    risks: mapRisks(payload),
    indicatorStates: payload.indicatorStates || payload.signal?.indicatorStates || {},
    raw: { ...payload, history, hasFullHistory: history.length > 0 },
  };
}

async function loadSignalsFromFirestore() {
  if (!firebaseReady || !db) return [];
  const metaQuery = query(collection(db, 'meta_data'), where('market', 'in', ['KR', 'US']));
  const metaSnap = await getDocs(metaQuery);
  const chunks = [];
  metaSnap.forEach((item) => {
    const data = item.data();
    if (Array.isArray(data.list)) chunks.push({ id: item.id, ...data });
  });
  const v2Chunks = chunks.filter((chunk) => chunk.strategyVersion === 'V2' && String(chunk.id).startsWith('meta_v2_'));
  let rows = [];
  (v2Chunks.length > 0 ? v2Chunks : chunks).forEach((chunk) => {
    rows = rows.concat(chunk.list || []);
  });
  rows.sort((a, b) => Number(b.confidenceScore || 0) - Number(a.confidenceScore || 0));
  return rows.map(mapStockPayload);
}

async function loadOrdersFromFirestore() {
  if (!firebaseReady || !db) return [];
  const ordersQuery = query(collection(db, 'rebalance_orders'), where('market', 'in', ['KR', 'US']));
  const snap = await getDocs(ordersQuery);
  const rows = [];
  snap.forEach((item) => rows.push({ id: item.id, ...item.data() }));
  rows.sort((a, b) => Number(b.tradeAmount || 0) - Number(a.tradeAmount || 0));
  return rows.map((order) => ({
    time: formatTimestamp(order.updatedAt),
    code: order.code,
    action: order.side || 'HOLD',
    reason: order.reason || '-',
    amount: formatNumber(order.tradeAmount, 0),
    status: 'staged',
  }));
}

function buildLinePath(rows, key, xForIndex, yForValue) {
  return rows
    .map((row, index) => {
      const value = Number(row[key]);
      if (!Number.isFinite(value)) return null;
      return `${index === 0 ? 'M' : 'L'} ${xForIndex(index).toFixed(2)} ${yForValue(value).toFixed(2)}`;
    })
    .filter(Boolean)
    .join(' ');
}

function buildAreaPath(rows, topKey, bottomKey, xForIndex, yForValue) {
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

function buildIndexedLinePath(rows, valueKey, xForIndex, yForValue) {
  return rows
    .map((row, index) => {
      const value = Number(row[valueKey]);
      if (!Number.isFinite(value)) return null;
      return `${index === 0 ? 'M' : 'L'} ${xForIndex(row.plotIndex).toFixed(2)} ${yForValue(value).toFixed(2)}`;
    })
    .filter(Boolean)
    .join(' ');
}

function buildIndexedAreaPath(rows, topKey, bottomKey, xForIndex, yForValue) {
  const top = [];
  const bottom = [];
  rows.forEach((row) => {
    const topValue = Number(row[topKey]);
    const bottomValue = Number(row[bottomKey]);
    if (!Number.isFinite(topValue) || !Number.isFinite(bottomValue)) return;
    top.push(`${xForIndex(row.plotIndex).toFixed(2)} ${yForValue(topValue).toFixed(2)}`);
    bottom.unshift(`${xForIndex(row.plotIndex).toFixed(2)} ${yForValue(bottomValue).toFixed(2)}`);
  });
  if (top.length < 2) return '';
  return `M ${top.join(' L ')} L ${bottom.join(' L ')} Z`;
}

function rollingMidpoint(rows, endIndex, windowSize) {
  const start = Math.max(0, endIndex - windowSize + 1);
  const windowRows = rows.slice(start, endIndex + 1);
  if (windowRows.length < windowSize) return null;
  const highs = windowRows.map((row) => row.high).filter(Number.isFinite);
  const lows = windowRows.map((row) => row.low).filter(Number.isFinite);
  if (highs.length < windowSize || lows.length < windowSize) return null;
  return (Math.max(...highs) + Math.min(...lows)) / 2;
}

function buildForwardCloudRows(history, startIndex, endIndex, futureSlots) {
  const cloudRows = [];
  const visibleCount = endIndex - startIndex;
  const maxPlotIndex = visibleCount + futureSlots - 1;
  for (let sourceIndex = Math.max(0, startIndex - futureSlots); sourceIndex < endIndex; sourceIndex += 1) {
    const row = history[sourceIndex];
    const plotIndex = sourceIndex - startIndex + futureSlots;
    if (plotIndex < 0 || plotIndex > maxPlotIndex) continue;
    const tenkan = Number(row.tenkan);
    const kijun = Number(row.kijun);
    const spanA = Number.isFinite(tenkan) && Number.isFinite(kijun) ? (tenkan + kijun) / 2 : null;
    const spanB = rollingMidpoint(history, sourceIndex, 52);
    if (!Number.isFinite(spanA) || !Number.isFinite(spanB)) continue;
    cloudRows.push({ plotIndex, senkouA: spanA, senkouB: spanB });
  }
  return cloudRows;
}

function axisTicks(min, max, count = 5) {
  const spread = max - min || 1;
  return Array.from({ length: count }, (_, index) => min + (spread * index) / (count - 1));
}

function IndicatorToggle({ active, icon: Icon, label, onClick }) {
  return (
    <button type="button" className={`tool-toggle ${active ? 'active' : ''}`} onClick={onClick}>
      <Icon size={15} />
      <span>{label}</span>
    </button>
  );
}

const indicatorStylePresets = {
  light: {
    candleUp: { color: '#089981', width: 1.5 },
    candleDown: { color: '#f23645', width: 1.5 },
    bbUpper: { color: '#2962ff', width: 2.2 },
    bbMid: { color: '#ff9800', width: 1.8 },
    bbLower: { color: '#2962ff', width: 2.2 },
    cloudA: { color: '#00a884', width: 1.8 },
    cloudB: { color: '#e05260', width: 1.8 },
    tenkan: { color: '#7c4dff', width: 2.0 },
    kijun: { color: '#455a64', width: 2.0 },
    ma5: { color: '#00bcd4', width: 1.8 },
    ma20: { color: '#ffb300', width: 2.1 },
    ma60: { color: '#e040fb', width: 2.2 },
    ma120: { color: '#607d8b', width: 1.9 },
    rsi: { color: '#00a884', width: 2.3 },
    rsiSignal: { color: '#ff8f00', width: 1.9 },
  },
  nightOwl: {
    candleUp: { color: '#7fdbca', width: 1.5 },
    candleDown: { color: '#ef5350', width: 1.5 },
    bbUpper: { color: '#82aaff', width: 2.2 },
    bbMid: { color: '#ffeb95', width: 2.0 },
    bbLower: { color: '#82aaff', width: 2.2 },
    cloudA: { color: '#c3e88d', width: 1.8 },
    cloudB: { color: '#ff869a', width: 1.8 },
    tenkan: { color: '#c792ea', width: 2.0 },
    kijun: { color: '#ecc48d', width: 2.0 },
    ma5: { color: '#7fdbca', width: 1.9 },
    ma20: { color: '#ffcb8b', width: 2.2 },
    ma60: { color: '#c792ea', width: 2.2 },
    ma120: { color: '#5f7e97', width: 1.9 },
    rsi: { color: '#c5e478', width: 2.3 },
    rsiSignal: { color: '#f78c6c', width: 1.9 },
  },
  beigeOwl: {
    candleUp: { color: '#2f8f6b', width: 1.5 },
    candleDown: { color: '#c94f45', width: 1.5 },
    bbUpper: { color: '#4f79b8', width: 2.2 },
    bbMid: { color: '#b1782a', width: 2.0 },
    bbLower: { color: '#4f79b8', width: 2.2 },
    cloudA: { color: '#75a65b', width: 1.8 },
    cloudB: { color: '#c76f61', width: 1.8 },
    tenkan: { color: '#8a66b8', width: 2.0 },
    kijun: { color: '#9b6a2d', width: 2.0 },
    ma5: { color: '#2f94a8', width: 1.9 },
    ma20: { color: '#c48a2c', width: 2.2 },
    ma60: { color: '#8d62b4', width: 2.2 },
    ma120: { color: '#6f6b5d', width: 1.9 },
    rsi: { color: '#5d8f45', width: 2.3 },
    rsiSignal: { color: '#c16c2d', width: 1.9 },
  },
  black: {
    candleUp: { color: '#00ff9c', width: 1.5 },
    candleDown: { color: '#ff3b5c', width: 1.5 },
    bbUpper: { color: '#00a3ff', width: 2.3 },
    bbMid: { color: '#ffd60a', width: 2.0 },
    bbLower: { color: '#00a3ff', width: 2.3 },
    cloudA: { color: '#00e676', width: 1.9 },
    cloudB: { color: '#ff5252', width: 1.9 },
    tenkan: { color: '#b388ff', width: 2.1 },
    kijun: { color: '#40c4ff', width: 2.1 },
    ma5: { color: '#18ffff', width: 1.9 },
    ma20: { color: '#ffea00', width: 2.2 },
    ma60: { color: '#ff00ff', width: 2.2 },
    ma120: { color: '#b0bec5', width: 1.9 },
    rsi: { color: '#00e676', width: 2.4 },
    rsiSignal: { color: '#ff9100', width: 2.0 },
  },
};

const defaultIndicatorStyles = indicatorStylePresets.light;

const themeOptions = [
  { key: 'light', label: '화이트' },
  { key: 'nightOwl', label: '나이트 아울' },
  { key: 'beigeOwl', label: '베이지 아울' },
  { key: 'black', label: '블랙' },
];

const themeClassMap = {
  light: 'theme-light',
  nightOwl: 'theme-night-owl',
  beigeOwl: 'theme-beige-owl',
  black: 'theme-black',
};

const themeLabels = Object.fromEntries(themeOptions.map((item) => [item.key, item.label]));
const defaultTheme = 'light';

const defaultIndicatorVisibility = {
  bbUpper: true,
  bbMid: true,
  bbLower: true,
  cloudA: true,
  cloudB: true,
  tenkan: true,
  kijun: true,
  ma5: true,
  ma20: true,
  ma60: true,
  ma120: true,
  rsi: true,
  rsiSignal: true,
};

const styleSections = [
  { title: '이동평균선', items: [['ma5', 'MA 5'], ['ma20', 'MA 20'], ['ma60', 'MA 60'], ['ma120', 'MA 120']] },
  { title: '볼린저밴드', items: [['bbUpper', '상단 밴드'], ['bbMid', '중심선'], ['bbLower', '하단 밴드']] },
  { title: '일목균형표', items: [['cloudA', '선행스팬 A'], ['cloudB', '선행스팬 B'], ['tenkan', '전환선'], ['kijun', '기준선']] },
  { title: '모멘텀', items: [['rsi', 'RSI'], ['rsiSignal', 'RSI 신호선']] },
  { title: '캔들', items: [['candleUp', '상승 캔들'], ['candleDown', '하락 캔들']] },
];

const styleKeys = Object.keys(defaultIndicatorStyles);
const visibilityKeys = Object.keys(defaultIndicatorVisibility);

function cloneIndicatorStyles(source = defaultIndicatorStyles) {
  return Object.fromEntries(styleKeys.map((key) => [key, { ...defaultIndicatorStyles[key], ...(source[key] || {}) }]));
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
  return rows.slice(0, 100).map((log) => ({
    time: formatTimestamp(log.createdAt),
    code: log.code,
    name: log.name || log.code,
    action: log.action || '-',
    amount: formatNumber(log.amount, 0),
    price: formatNumber(log.price, 0),
    quantity: Number(log.quantity || 0),
    reason: log.reason || '-',
    pnlPct: log.pnlPct,
    pnl: log.pnl,
    source: log.source || 'legacy',
  }));
}

function mapPortfolioPosition(payload, fallbackCode = '') {
  const code = payload.code || payload.pdno || fallbackCode;
  const qty = Number(payload.qty ?? payload.quantity ?? payload.hldg_qty ?? 0);
  const evalAmt = Number(payload.evalAmt ?? payload.marketValue ?? payload.value ?? payload.evlu_amt ?? 0);
  const buyAmt = Number(payload.buyAmt ?? payload.buyAmount ?? payload.pchs_amt ?? 0);
  const pnlPct = Number(payload.pnlPct ?? payload.fltt_rt ?? 0);
  return {
    code,
    name: payload.name || payload.prdt_name || code,
    qty,
    evalAmt,
    buyAmt,
    pnlPct,
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
  return {
    mode: snapshot.mode || 'paper',
    market: snapshot.market || 'KR',
    holdingCount: Number(snapshot.holdingCount ?? holdings.length),
    totalEvalAmt,
    totalBuyAmt,
    cashTargetPct: Number(snapshot.cashTargetPct ?? 0),
    updatedAt: snapshot.updatedAt,
    holdings,
  };
}

function indicatorStylesForTheme(themeKey) {
  return cloneIndicatorStyles(indicatorStylePresets[themeKey] || indicatorStylePresets.light);
}

function normalizeIndicatorVisibility(source = defaultIndicatorVisibility) {
  return Object.fromEntries(visibilityKeys.map((key) => [key, source[key] !== false]));
}

function ChartLoadingPanel({ stock, loading }) {
  return (
    <section className="chart-workspace">
      <div className="chart-header">
        <div>
          <span>{stock.market}:{stock.code}</span>
          <h2>{stock.name}</h2>
          <p>
            <strong>{formatNumber(stock.confidence, 1)}</strong>
            <small>{stock.updatedAt}</small>
          </p>
        </div>
        <span className={`risk-chip risk-${stock.riskState}`}>{stock.label}</span>
      </div>
      <div className="chart-frame chart-loading-frame">
        <div className="chart-loading-panel">
          <RefreshCw size={20} className={loading ? 'spin' : ''} />
          <span>{loading ? '차트 데이터 불러오는 중' : '차트 데이터가 없습니다'}</span>
          <strong>{stock.name}</strong>
        </div>
      </div>
    </section>
  );
}

function TechnicalChartBody({
  stock,
  range,
  layers,
  indicatorStyles,
  indicatorVisibility,
  onRangeChange,
  onToggleLayer,
  onStyleChange,
  onVisibilityChange,
}) {
  const [hoverIndex, setHoverIndex] = useState(null);
  const [showStylePanel, setShowStylePanel] = useState(false);
  const fullHistory = useMemo(() => {
    return stock.raw?.history?.length ? stock.raw.history : mockHistory;
  }, [stock]);
  const [viewEnd, setViewEnd] = useState(fullHistory.length);
  const cloudShift = 26;
  const effectiveRange = range === 'ALL' ? fullHistory.length : Math.min(Number(range), fullHistory.length);
  const safeViewEnd = Math.max(effectiveRange, Math.min(viewEnd || fullHistory.length, fullHistory.length));
  const startIndex = Math.max(0, safeViewEnd - effectiveRange);
  const endIndex = safeViewEnd;
  const rows = useMemo(() => fullHistory.slice(startIndex, endIndex), [fullHistory, startIndex, endIndex]);
  const cloudRows = useMemo(
    () => buildForwardCloudRows(fullHistory, startIndex, endIndex, cloudShift),
    [fullHistory, startIndex, endIndex],
  );

  useEffect(() => {
    setViewEnd(fullHistory.length);
    setHoverIndex(null);
  }, [stock.id, fullHistory.length, range]);

  const latest = rows[rows.length - 1] || {};
  const priceValues = rows.flatMap((row) => [
    row.high,
    row.low,
    layers.bollinger && indicatorVisibility.bbUpper ? row.upper : null,
    layers.bollinger && indicatorVisibility.bbLower ? row.lower : null,
    layers.ma && indicatorVisibility.ma5 ? row.ma5 : null,
    layers.ma && indicatorVisibility.ma20 ? row.ma20 : null,
    layers.ma && indicatorVisibility.ma60 ? row.ma60 : null,
    layers.ma && indicatorVisibility.ma120 ? row.ma120 : null,
  ]).concat(layers.ichimoku ? cloudRows.flatMap((row) => [
    indicatorVisibility.cloudA ? row.senkouA : null,
    indicatorVisibility.cloudB ? row.senkouB : null,
  ]) : []).filter(Number.isFinite);

  const minPrice = Math.min(...priceValues);
  const maxPrice = Math.max(...priceValues);
  const pad = (maxPrice - minPrice || 1) * 0.08;
  const domainMin = minPrice - pad;
  const domainMax = maxPrice + pad;

  const width = 1120;
  const priceHeight = 520;
  const volumeHeight = 76;
  const rsiHeight = 164;
  const gap = 18;
  const margin = { top: 18, right: 72, bottom: 28, left: 10 };
  const innerWidth = width - margin.left - margin.right;
  const totalHeight = priceHeight + volumeHeight + rsiHeight + gap * 2 + margin.top + margin.bottom;
  const plotSlots = Math.max(rows.length + (layers.ichimoku ? cloudShift : 0), 1);
  const candleGap = innerWidth / plotSlots;
  const candleWidth = Math.max(4, Math.min(12, candleGap * 0.82));
  const maxVolume = Math.max(...rows.map((row) => Number(row.volume || 0)), 1);
  const activeIndex = hoverIndex ?? rows.length - 1;
  const activeRow = rows[activeIndex] || latest;

  const xForIndex = (index) => margin.left + candleGap * index + candleGap / 2;
  const yForPrice = (value) => margin.top + ((domainMax - value) / (domainMax - domainMin || 1)) * priceHeight;
  const volumeTop = margin.top + priceHeight + gap;
  const yForVolume = (value) => volumeTop + volumeHeight - (Number(value || 0) / maxVolume) * volumeHeight;
  const rsiTop = volumeTop + volumeHeight + gap;
  const yForRsi = (value) => rsiTop + ((100 - value) / 100) * rsiHeight;

  const hoverX = xForIndex(activeIndex);
  const activeCloud = cloudRows.find((row) => row.plotIndex === activeIndex) || cloudRows[cloudRows.length - 1] || {};
  const cloudBullish = Number(activeCloud.senkouA) >= Number(activeCloud.senkouB);
  const canPanLeft = startIndex > 0;
  const canPanRight = endIndex < fullHistory.length;
  const panStep = Math.max(10, Math.round(effectiveRange * 0.35));
  const pan = (amount) => {
    setViewEnd((current) => Math.max(effectiveRange, Math.min(fullHistory.length, (current || fullHistory.length) + amount)));
    setHoverIndex(null);
  };

  return (
    <section className="chart-workspace">
      <div className="chart-header">
        <div className="quote-stack">
          <span className="quote-symbol">{stock.market}:{stock.code}</span>
          <h2>{stock.name}</h2>
          <div className="quote-line">
            <strong>{formatNumber(activeRow.close, stock.market === 'US' ? 2 : 0)}</strong>
            <span>{activeRow.date || stock.updatedAt}</span>
            <span className={`risk-chip risk-${stock.riskState}`}>{stock.label}</span>
          </div>
        </div>
          <div className="chart-tools">
          <div className="ma-ribbon" aria-label="Moving average colors">
            {[
              ['ma5', '5'],
              ['ma20', '20'],
              ['ma60', '60'],
              ['ma120', '120'],
            ].map(([key, label]) => (
              <span key={key} style={{ color: indicatorStyles[key].color, opacity: indicatorVisibility[key] ? 1 : 0.35 }}>{label}</span>
            ))}
          </div>
          <div className="range-tabs" aria-label="Chart range">
            {[60, 120, 160, 240, 'ALL'].map((item) => (
              <button key={item} type="button" className={range === item ? 'active' : ''} onClick={() => onRangeChange(item)}>
                {item === 'ALL' ? '전체' : `${item}일`}
              </button>
            ))}
          </div>
          <div className="pan-controls" aria-label="Move chart window">
            <button type="button" onClick={() => pan(-effectiveRange)} disabled={!canPanLeft}>-기간</button>
            <button type="button" onClick={() => pan(-panStep)} disabled={!canPanLeft}>-이동</button>
            <button type="button" onClick={() => setViewEnd(fullHistory.length)} disabled={!canPanRight}>최신</button>
            <button type="button" onClick={() => pan(panStep)} disabled={!canPanRight}>+이동</button>
            <button type="button" onClick={() => pan(effectiveRange)} disabled={!canPanRight}>+기간</button>
          </div>
          <div className="layer-toggles" aria-label="Indicator layers">
            <IndicatorToggle active={layers.candles} icon={CandlestickChart} label="캔들" onClick={() => onToggleLayer('candles')} />
            <IndicatorToggle active={layers.bollinger} icon={BarChart3} label="볼린저" onClick={() => onToggleLayer('bollinger')} />
            <IndicatorToggle active={layers.ichimoku} icon={Cloud} label="구름" onClick={() => onToggleLayer('ichimoku')} />
            <IndicatorToggle active={layers.rsi} icon={Gauge} label="RSI" onClick={() => onToggleLayer('rsi')} />
            <button type="button" className={`tool-toggle ${showStylePanel ? 'active' : ''}`} onClick={() => setShowStylePanel((value) => !value)}>
              <SlidersHorizontal size={15} />
              <span>스타일</span>
            </button>
          </div>
        </div>
      </div>

      {showStylePanel && (
        <div className="style-panel" aria-label="Indicator style controls">
          {styleSections.map((section) => (
            <section key={section.title} className="style-section">
              <h3>{section.title}</h3>
              <div className="style-section-grid">
                {section.items.map(([key, label]) => (
                  <label key={key} className="style-control">
                    {key in indicatorVisibility ? (
                      <input
                        type="checkbox"
                        checked={indicatorVisibility[key]}
                        onChange={(event) => onVisibilityChange(key, event.target.checked)}
                        aria-label={`${label} visibility`}
                      />
                    ) : (
                      <span className="style-lock" />
                    )}
                    <span className="style-name">{label}</span>
                    <span className="color-preview" style={{ background: indicatorStyles[key].color }} />
                    <input
                      type="color"
                      value={indicatorStyles[key].color}
                      onChange={(event) => onStyleChange(key, 'color', event.target.value)}
                      aria-label={`${label} color`}
                    />
                    <input
                      type="range"
                      min="1"
                      max="4"
                      step="0.25"
                      value={indicatorStyles[key].width}
                      onChange={(event) => onStyleChange(key, 'width', Number(event.target.value))}
                      aria-label={`${label} width`}
                    />
                    <strong>{Number(indicatorStyles[key].width).toFixed(2)}</strong>
                  </label>
                ))}
              </div>
            </section>
          ))}
        </div>
      )}

      <div className="chart-frame">
        <svg
          className="technical-chart"
          viewBox={`0 0 ${width} ${totalHeight}`}
          role="img"
          aria-label={`${stock.name} technical chart`}
          onMouseLeave={() => setHoverIndex(null)}
          onMouseMove={(event) => {
            const rect = event.currentTarget.getBoundingClientRect();
            const x = ((event.clientX - rect.left) / rect.width) * width;
            const index = Math.max(0, Math.min(rows.length - 1, Math.floor((x - margin.left) / candleGap)));
            setHoverIndex(index);
          }}
        >
          <rect x="0" y="0" width={width} height={totalHeight} className="chart-bg" />

          {axisTicks(domainMin, domainMax).map((tick) => (
            <g key={`price-${tick}`}>
              <line x1={margin.left} x2={width - margin.right} y1={yForPrice(tick)} y2={yForPrice(tick)} className="grid-line" />
              <text x={width - 60} y={yForPrice(tick) - 5} className="axis-label">{formatNumber(tick, stock.market === 'US' ? 2 : 0)}</text>
            </g>
          ))}

          {layers.ichimoku && (
            <>
              {indicatorVisibility.cloudA && indicatorVisibility.cloudB && (
                <path
                  d={buildIndexedAreaPath(cloudRows, 'senkouA', 'senkouB', xForIndex, yForPrice)}
                  className={cloudBullish ? 'cloud-area bullish' : 'cloud-area bearish'}
                />
              )}
              {indicatorVisibility.cloudA && <path d={buildIndexedLinePath(cloudRows, 'senkouA', xForIndex, yForPrice)} className="line" style={{ stroke: indicatorStyles.cloudA.color, strokeWidth: indicatorStyles.cloudA.width }} />}
              {indicatorVisibility.cloudB && <path d={buildIndexedLinePath(cloudRows, 'senkouB', xForIndex, yForPrice)} className="line" style={{ stroke: indicatorStyles.cloudB.color, strokeWidth: indicatorStyles.cloudB.width }} />}
              {indicatorVisibility.tenkan && <path d={buildLinePath(rows, 'tenkan', xForIndex, yForPrice)} className="line" style={{ stroke: indicatorStyles.tenkan.color, strokeWidth: indicatorStyles.tenkan.width }} />}
              {indicatorVisibility.kijun && <path d={buildLinePath(rows, 'kijun', xForIndex, yForPrice)} className="line" style={{ stroke: indicatorStyles.kijun.color, strokeWidth: indicatorStyles.kijun.width }} />}
            </>
          )}

          {layers.bollinger && (
            <>
              {indicatorVisibility.bbUpper && indicatorVisibility.bbLower && <path d={buildAreaPath(rows, 'upper', 'lower', xForIndex, yForPrice)} className="bb-area" />}
              {indicatorVisibility.bbUpper && <path d={buildLinePath(rows, 'upper', xForIndex, yForPrice)} className="line" style={{ stroke: indicatorStyles.bbUpper.color, strokeWidth: indicatorStyles.bbUpper.width }} />}
              {indicatorVisibility.bbMid && <path d={buildLinePath(rows, 'bbMid', xForIndex, yForPrice)} className="line" style={{ stroke: indicatorStyles.bbMid.color, strokeWidth: indicatorStyles.bbMid.width }} />}
              {indicatorVisibility.bbLower && <path d={buildLinePath(rows, 'lower', xForIndex, yForPrice)} className="line" style={{ stroke: indicatorStyles.bbLower.color, strokeWidth: indicatorStyles.bbLower.width }} />}
            </>
          )}

          {layers.ma && (
            <>
              {indicatorVisibility.ma5 && <path d={buildLinePath(rows, 'ma5', xForIndex, yForPrice)} className="line" style={{ stroke: indicatorStyles.ma5.color, strokeWidth: indicatorStyles.ma5.width }} />}
              {indicatorVisibility.ma20 && <path d={buildLinePath(rows, 'ma20', xForIndex, yForPrice)} className="line" style={{ stroke: indicatorStyles.ma20.color, strokeWidth: indicatorStyles.ma20.width }} />}
              {indicatorVisibility.ma60 && <path d={buildLinePath(rows, 'ma60', xForIndex, yForPrice)} className="line" style={{ stroke: indicatorStyles.ma60.color, strokeWidth: indicatorStyles.ma60.width }} />}
              {indicatorVisibility.ma120 && <path d={buildLinePath(rows, 'ma120', xForIndex, yForPrice)} className="line" style={{ stroke: indicatorStyles.ma120.color, strokeWidth: indicatorStyles.ma120.width }} />}
            </>
          )}

          {rows.map((row, index) => {
            const x = xForIndex(index);
            const up = row.close >= row.open;
            const top = yForPrice(Math.max(row.open, row.close));
            const bottom = yForPrice(Math.min(row.open, row.close));
            const bodyHeight = Math.max(2, bottom - top);
            return (
              <g key={`${row.date}-${index}`}>
                <rect
                  x={x - candleWidth / 2}
                  y={yForVolume(row.volume)}
                  width={Math.max(1.5, candleWidth * 0.62)}
                  height={volumeTop + volumeHeight - yForVolume(row.volume)}
                  className={up ? 'volume up' : 'volume down'}
                />
                {layers.candles ? (
                  <>
                    <line
                      x1={x}
                      x2={x}
                      y1={yForPrice(row.high)}
                      y2={yForPrice(row.low)}
                      className="wick"
                      style={{ stroke: up ? indicatorStyles.candleUp.color : indicatorStyles.candleDown.color, strokeWidth: up ? indicatorStyles.candleUp.width : indicatorStyles.candleDown.width }}
                    />
                    <rect
                      x={x - candleWidth / 2}
                      y={top}
                      width={candleWidth}
                      height={bodyHeight}
                      className={up ? 'candle up' : 'candle down'}
                      style={{ stroke: up ? indicatorStyles.candleUp.color : indicatorStyles.candleDown.color }}
                    />
                  </>
                ) : (
                  <circle cx={x} cy={yForPrice(row.close)} r="2.3" className="close-dot" />
                )}
              </g>
            );
          })}

          <line x1={margin.left} x2={width - margin.right} y1={volumeTop} y2={volumeTop} className="section-line" />
          <text x={margin.left + 4} y={volumeTop + 15} className="panel-label">거래량</text>

          {layers.rsi && (
            <>
              <line x1={margin.left} x2={width - margin.right} y1={rsiTop} y2={rsiTop} className="section-line" />
              {[70, 50, 30].map((tick) => (
                <g key={`rsi-${tick}`}>
                  <line x1={margin.left} x2={width - margin.right} y1={yForRsi(tick)} y2={yForRsi(tick)} className={tick === 50 ? 'grid-line' : 'rsi-band'} />
                  <text x={width - 54} y={yForRsi(tick) - 5} className="axis-label">{tick}</text>
                </g>
              ))}
              {indicatorVisibility.rsi && <path d={buildLinePath(rows, 'rsi', xForIndex, yForRsi)} className="line" style={{ stroke: indicatorStyles.rsi.color, strokeWidth: indicatorStyles.rsi.width }} />}
              {indicatorVisibility.rsiSignal && <path d={buildLinePath(rows, 'rsiSignal', xForIndex, yForRsi)} className="line" style={{ stroke: indicatorStyles.rsiSignal.color, strokeWidth: indicatorStyles.rsiSignal.width }} />}
              <text x={margin.left + 4} y={rsiTop + 15} className="panel-label">RSI</text>
            </>
          )}

          {hoverIndex !== null && (
            <>
              <line x1={hoverX} x2={hoverX} y1={margin.top} y2={rsiTop + rsiHeight} className="crosshair" />
              <circle cx={hoverX} cy={yForPrice(activeRow.close)} r="4" className="active-point" />
              <g transform={`translate(${Math.min(hoverX + 12, width - 250)}, ${margin.top + 10})`}>
                <rect width="224" height="126" rx="7" className="tooltip-box" />
                <text x="12" y="22" className="tooltip-title">{activeRow.date || '-'}</text>
                <text x="12" y="46" className="tooltip-text">시 {formatNumber(activeRow.open, stock.market === 'US' ? 2 : 0)}</text>
                <text x="82" y="46" className="tooltip-text">고 {formatNumber(activeRow.high, stock.market === 'US' ? 2 : 0)}</text>
                <text x="12" y="68" className="tooltip-text">저 {formatNumber(activeRow.low, stock.market === 'US' ? 2 : 0)}</text>
                <text x="82" y="68" className="tooltip-text">종 {formatNumber(activeRow.close, stock.market === 'US' ? 2 : 0)}</text>
                <text x="12" y="92" className="tooltip-text">RSI {formatNumber(activeRow.rsi, 1)}</text>
                <text x="82" y="92" className="tooltip-text">%B {formatNumber((activeRow.close - activeRow.lower) / ((activeRow.upper - activeRow.lower) || 1), 2)}</text>
                <text x="12" y="114" className="tooltip-text">거래량 {formatNumber(activeRow.volume, 0)}</text>
              </g>
            </>
          )}

          {layers.ichimoku && cloudRows.length > 0 && (
            <text x={xForIndex(rows.length + cloudShift - 1)} y={margin.top + 14} className="future-label">+26 구름</text>
          )}

          {rows.filter((_, index) => index % Math.ceil(rows.length / 6) === 0 || index === rows.length - 1).map((row, index) => {
            const realIndex = rows.indexOf(row);
            return (
              <text key={`${row.date}-${index}`} x={xForIndex(realIndex)} y={totalHeight - 8} className="date-label">
                {compactDate(row.date)}
              </text>
            );
          })}
        </svg>
      </div>

      <div className="legend-strip">
        <span><i className="swatch candle-up" /> 상승 캔들</span>
        <span><i className="swatch bb" /> 볼린저밴드</span>
        <span><i className="swatch cloud" /> 일목 구름</span>
        <span><i className="swatch rsi" /> RSI / 신호선</span>
      </div>
    </section>
  );
}

function TechnicalChart({
  stock,
  range,
  layers,
  indicatorStyles,
  indicatorVisibility,
  onRangeChange,
  onToggleLayer,
  onStyleChange,
  onVisibilityChange,
  isLoading,
}) {
  const hasChartHistory = Boolean(stock.raw?.history?.length);
  if (isLoading || !hasChartHistory) {
    return <ChartLoadingPanel stock={stock} loading={isLoading} />;
  }

  return (
    <TechnicalChartBody
      stock={stock}
      range={range}
      layers={layers}
      indicatorStyles={indicatorStyles}
      indicatorVisibility={indicatorVisibility}
      onRangeChange={onRangeChange}
      onToggleLayer={onToggleLayer}
      onStyleChange={onStyleChange}
      onVisibilityChange={onVisibilityChange}
    />
  );
}

function ScoreDock({ stock }) {
  const bollinger = stock.indicatorStates?.bollinger || {};
  return (
    <aside className="score-dock">
      <section className="dock-section headline-score">
        <span>종합 점수</span>
        <strong>{formatNumber(stock.confidence, 1)}</strong>
        <small>{stock.signal}</small>
      </section>

      <section className="dock-section compact-stats">
        <div>
          <span>손절 기준</span>
          <strong>{stock.stopLoss}</strong>
        </div>
        <div>
          <span>현금 비중</span>
          <strong>{stock.cashTarget}%</strong>
        </div>
        <div>
          <span>볼린저 상태</span>
          <strong className="state-text">{stateLabel(bollinger.state)}</strong>
        </div>
        <div>
          <span>밴드폭 위치</span>
          <strong>{bollinger.bandwidthRank !== undefined ? `${formatNumber(Number(bollinger.bandwidthRank) * 100, 1)}%` : '-'}</strong>
        </div>
      </section>

      <section className="dock-section">
        <div className="dock-title">
          <Gauge size={16} />
          <span>점수 비율</span>
        </div>
        <div className="score-bars">
          {stock.components.map((component) => (
            <div key={component.label} className="score-bar">
              <div>
                <span>{component.label}</span>
                <strong>
                  {component.weight === -1
                    ? `감점 ${formatNumber(component.score, 1)}`
                    : `${formatNumber(component.score, 1)} x ${formatNumber(Number(component.weight || 0) * 100, 0)}% = ${formatNumber(component.score * Number(component.weight || 0), 1)}`}
                </strong>
              </div>
              <meter min="0" max={component.max || 100} value={component.score || 0} />
            </div>
          ))}
        </div>
      </section>

      <section className="dock-section">
        <div className="dock-title">
          <Shield size={16} />
          <span>리스크</span>
        </div>
        <div className="risk-list">
          {stock.risks.map((risk) => (
            <div key={risk.label} className={`risk-row risk-${risk.state}`}>
              <span>{risk.label}</span>
              <strong>{risk.value}</strong>
            </div>
          ))}
        </div>
      </section>
    </aside>
  );
}

function PortfolioSnapshot({ portfolio }) {
  const totalEval = Number(portfolio.totalEvalAmt || 0);
  const totalBuy = Number(portfolio.totalBuyAmt || 0);
  const cash = Number(portfolio.cash || 0);
  const totalEquity = Number(portfolio.totalEquity || cash + totalEval);
  const realizedPnl = Number(portfolio.realizedPnl || 0);
  const pnlPct = totalBuy > 0 ? ((totalEval - totalBuy) / totalBuy) * 100 : 0;
  const holdings = Array.isArray(portfolio.holdings) ? portfolio.holdings : [];

  return (
    <section className="portfolio-strip">
      <div className="orders-header">
        <div>
          <p>Paper portfolio · {portfolio.source || 'legacy'} · {portfolio.mode || 'paper'}</p>
          <h3>Account snapshot</h3>
        </div>
        <WalletCards size={18} />
      </div>

      <div className="portfolio-grid">
        <div>
          <span>총자산</span>
          <strong>{formatNumber(totalEquity, 0)}</strong>
        </div>
        <div>
          <span>현금</span>
          <strong>{formatNumber(cash, 0)}</strong>
        </div>
        <div>
          <span>평가금액</span>
          <strong>{formatNumber(totalEval, 0)}</strong>
        </div>
        <div>
          <span>수익률</span>
          <strong className={pnlPct >= 0 ? 'pnl-up' : 'pnl-down'}>{formatNumber(pnlPct, 2)}%</strong>
        </div>
        <div>
          <span>실현손익</span>
          <strong className={realizedPnl >= 0 ? 'pnl-up' : 'pnl-down'}>{formatNumber(realizedPnl, 0)}</strong>
        </div>
        <div>
          <span>보유</span>
          <strong>{formatNumber(portfolio.holdingCount ?? holdings.length, 0)}</strong>
        </div>
        <div>
          <span>업데이트</span>
          <strong>{formatDateTime(portfolio.updatedAt)}</strong>
        </div>
      </div>

      <div className="portfolio-holdings">
        {holdings.length === 0 && <div className="empty-watch">보유 종목이 없습니다</div>}
        {holdings.slice(0, 5).map((holding) => (
          <div key={holding.code} className="holding-row">
            <span>
              <strong>{holding.name}</strong>
              <small>{holding.code} · {formatNumber(holding.qty, 0)}주</small>
            </span>
            <span>
              <strong>{formatNumber(holding.evalAmt, 0)}</strong>
              <small className={Number(holding.pnlPct || 0) >= 0 ? 'pnl-up' : 'pnl-down'}>
                {formatNumber(Number(holding.pnlPct || 0), 2)}%
              </small>
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}

function TradeLogPanel({ logs }) {
  const [actionFilter, setActionFilter] = useState('ALL');
  const [sourceFilter, setSourceFilter] = useState('ALL');
  const sources = useMemo(() => {
    const unique = Array.from(new Set(logs.map((log) => log.source || 'legacy')));
    return ['ALL', ...unique.sort()];
  }, [logs]);
  const filteredLogs = useMemo(() => logs.filter((log) => {
    const matchesAction = actionFilter === 'ALL' || String(log.action).toUpperCase() === actionFilter;
    const matchesSource = sourceFilter === 'ALL' || String(log.source || 'legacy') === sourceFilter;
    return matchesAction && matchesSource;
  }), [logs, actionFilter, sourceFilter]);
  const executionSummary = useMemo(() => ({
    buyCount: filteredLogs.filter((log) => String(log.action).toUpperCase() === 'BUY').length,
    sellCount: filteredLogs.filter((log) => String(log.action).toUpperCase() === 'SELL').length,
    tradedAmount: filteredLogs.reduce((sum, log) => sum + Number(String(log.amount || '0').replaceAll(',', '')), 0),
    realizedPnl: filteredLogs.reduce((sum, log) => sum + Number(log.pnl || 0), 0),
  }), [filteredLogs]);

  return (
    <section className="execution-history">
      <div className="orders-header">
        <div>
          <p>Paper execution</p>
          <h3>Execution history</h3>
        </div>
        <div className="execution-filters">
          <select value={actionFilter} onChange={(event) => setActionFilter(event.target.value)} aria-label="Execution action filter">
            <option value="ALL">전체 체결</option>
            <option value="BUY">매수</option>
            <option value="SELL">매도</option>
          </select>
          <select value={sourceFilter} onChange={(event) => setSourceFilter(event.target.value)} aria-label="Execution source filter">
            {sources.map((source) => (
              <option key={source} value={source}>{source === 'ALL' ? '전체 소스' : source}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="execution-summary">
        <div>
          <span>체결</span>
          <strong>{filteredLogs.length}</strong>
        </div>
        <div>
          <span>매수 / 매도</span>
          <strong>{executionSummary.buyCount} / {executionSummary.sellCount}</strong>
        </div>
        <div>
          <span>거래금액</span>
          <strong>{formatNumber(executionSummary.tradedAmount, 0)}</strong>
        </div>
        <div>
          <span>실현손익</span>
          <strong className={executionSummary.realizedPnl >= 0 ? 'pnl-up' : 'pnl-down'}>
            {formatNumber(executionSummary.realizedPnl, 0)}
          </strong>
        </div>
      </div>

      <div className="execution-table">
        <table>
          <thead>
            <tr>
              <th>Time</th>
              <th>Side</th>
              <th>Symbol</th>
              <th>Qty</th>
              <th>Price</th>
              <th>Amount</th>
              <th>PnL</th>
              <th>Reason</th>
            </tr>
          </thead>
          <tbody>
            {filteredLogs.length === 0 && (
              <tr>
                <td colSpan={8} className="empty-table-cell">최근 체결 로그가 없습니다</td>
              </tr>
            )}
            {filteredLogs.map((log) => (
              <tr key={`${log.time}-${log.code}-${log.action}-${log.amount}-${log.reason}`}>
                <td>{log.time}</td>
                <td><span className={`side side-${String(log.action).toLowerCase()}`}>{log.action}</span></td>
                <td>
                  <span className="symbol-cell">
                    <strong>{log.name || log.code}</strong>
                    <small>{log.code} · {log.source || 'legacy'}</small>
                  </span>
                </td>
                <td>{formatNumber(log.quantity, 0)}</td>
                <td>{log.price || '-'}</td>
                <td>{log.amount}</td>
                <td className={Number(log.pnl || log.pnlPct || 0) >= 0 ? 'pnl-up' : 'pnl-down'}>
                  {log.pnl !== undefined ? formatNumber(Number(log.pnl || 0), 0) : '-'}
                  {log.pnlPct !== undefined ? ` (${formatNumber(Number(log.pnlPct || 0), 2)}%)` : ''}
                </td>
                <td>{log.reason}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export default function App() {
  const [signals, setSignals] = useState(mockSignals);
  const [orders, setOrders] = useState(fallbackOrders);
  const [tradeLogs, setTradeLogs] = useState(fallbackTradeLogs);
  const [portfolio, setPortfolio] = useState(fallbackPortfolio);
  const [selectedId, setSelectedId] = useState(mockSignals[0].id);
  const [loading, setLoading] = useState(true);
  const [detailLoadingId, setDetailLoadingId] = useState('');
  const [hasLoaded, setHasLoaded] = useState(false);
  const [loadError, setLoadError] = useState('');
  const [range, setRange] = useState(240);
  const [theme, setTheme] = useState(defaultTheme);
  const [layers, setLayers] = useState({
    candles: true,
    bollinger: true,
    ichimoku: true,
    rsi: true,
    ma: true,
  });
  const [indicatorStyles, setIndicatorStyles] = useState(() => indicatorStylesForTheme(defaultTheme));
  const [indicatorVisibility, setIndicatorVisibility] = useState(() => normalizeIndicatorVisibility());
  const [searchText, setSearchText] = useState('');
  const [marketFilter, setMarketFilter] = useState('ALL');
  const [labelFilter, setLabelFilter] = useState('ALL');
  const [sortMode, setSortMode] = useState('confidence');
  const [sortDirection, setSortDirection] = useState('desc');
  const [workspaceView, setWorkspaceView] = useState('console');
  const [user, setUser] = useState(null);
  const [settingsReady, setSettingsReady] = useState(false);
  const [settingsStatus, setSettingsStatus] = useState('');
  const activeSort = sortOptionByKey[sortMode] || sortOptionByKey.confidence;


  const selected = useMemo(
    () => signals.find((signal) => signal.id === selectedId) ?? signals[0],
    [signals, selectedId],
  );

  const summary = useMemo(() => ({
    candidates: signals.length,
    highConfidence: signals.filter((signal) => signal.confidence >= 80).length,
    maxCash: Math.max(...signals.map((signal) => Number(signal.cashTarget || 0)), 0),
    staged: orders.filter((order) => order.status === 'staged').length,
  }), [signals, orders]);

  const filteredSignals = useMemo(() => {
    const queryText = searchText.trim().toLowerCase();
    const rows = signals.filter((signal) => {
      const matchesSearch = !queryText || [signal.name, signal.code, signal.market, signal.label]
        .join(' ')
        .toLowerCase()
        .includes(queryText);
      const matchesMarket = marketFilter === 'ALL' || signal.market === marketFilter;
      const labelKey = signal.labelKey || signal.label.toUpperCase().replaceAll(' ', '_');
      const matchesLabel = labelFilter === 'ALL' || labelKey === labelFilter;
      return matchesSearch && matchesMarket && matchesLabel;
    });

    return [...rows].sort((a, b) => {
      if (sortMode === 'name') {
        return sortDirection === 'asc' ? a.name.localeCompare(b.name) : b.name.localeCompare(a.name);
      }
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

  const refreshSignals = async () => {
    setLoading(true);
    setLoadError('');
    try {
      const loaded = await loadSignalsFromFirestore();
      if (loaded.length > 0) {
        const nextSelectedId = hasLoaded && loaded.some((signal) => signal.id === selectedId)
          ? selectedId
          : loaded[0].id;
        const selectedIndex = Math.max(0, loaded.findIndex((signal) => signal.id === nextSelectedId));
        const selectedSignal = loaded[selectedIndex];
        if (firebaseReady && db && !selectedSignal.raw?.hasFullHistory) {
          const snap = await getDoc(doc(db, 'stock_analysis', selectedSignal.id));
          if (snap.exists()) {
            loaded[selectedIndex] = mapStockPayload({ ...selectedSignal.raw, ...snap.data(), id: selectedSignal.id });
          }
        }
        setSignals(loaded);
        setSelectedId(nextSelectedId);
      } else {
        setSignals(mockSignals);
        setLoadError(firebaseReady ? 'Firestore 분석 데이터가 아직 없습니다' : 'Firebase 환경 설정이 없습니다');
      }
      try {
        const loadedOrders = await loadOrdersFromFirestore();
        setOrders(loadedOrders.length > 0 ? loadedOrders : fallbackOrders);
      } catch {
        setOrders(fallbackOrders);
      }
      try {
        const loadedPortfolio = await loadPortfolioFromFirestore();
        setPortfolio(loadedPortfolio || fallbackPortfolio);
      } catch {
        setPortfolio(fallbackPortfolio);
      }
      try {
        const loadedLogs = await loadTradeLogsFromFirestore();
        setTradeLogs(loadedLogs.length > 0 ? loadedLogs : fallbackTradeLogs);
      } catch {
        setTradeLogs(fallbackTradeLogs);
      }
    } catch (error) {
      setSignals(mockSignals);
      setOrders(fallbackOrders);
      setPortfolio(fallbackPortfolio);
      setTradeLogs(fallbackTradeLogs);
      setLoadError(error?.message || 'Firestore 불러오기 실패');
    } finally {
      setLoading(false);
      setHasLoaded(true);
    }
  };

  const loadSignalDetail = async (signal) => {
    if (!firebaseReady || !db || signal.raw?.hasFullHistory) return;
    setDetailLoadingId(signal.id);
    try {
      const snap = await getDoc(doc(db, 'stock_analysis', signal.id));
      if (!snap.exists()) return;
      const enriched = mapStockPayload({ ...signal.raw, ...snap.data(), id: signal.id });
      setSignals((prev) => prev.map((item) => (item.id === signal.id ? enriched : item)));
    } catch (error) {
      setLoadError(error?.message || '상세 데이터 불러오기 실패');
    } finally {
      setDetailLoadingId((current) => (current === signal.id ? '' : current));
    }
  };

  const selectSignal = async (signal) => {
    setSelectedId(signal.id);
    if (!signal.raw?.hasFullHistory) {
      setDetailLoadingId(signal.id);
    }
    await loadSignalDetail(signal);
  };

  const toggleLayer = (key) => {
    setLayers((current) => ({ ...current, [key]: !current[key] }));
  };

  const updateIndicatorStyle = (key, field, value) => {
    setIndicatorStyles((current) => ({
      ...current,
      [key]: {
        ...current[key],
        [field]: value,
      },
    }));
  };

  const updateIndicatorVisibility = (key, value) => {
    setIndicatorVisibility((current) => ({ ...current, [key]: value }));
  };

  const applyTheme = (nextTheme) => {
    setTheme(nextTheme);
    setIndicatorStyles(indicatorStylesForTheme(nextTheme));
  };

  const loginWithGoogle = async () => {
    if (!auth || !googleProvider) {
      setSettingsStatus('Firebase 로그인이 설정되지 않았습니다');
      return;
    }
    setSettingsStatus('로그인 중');
    try {
      await signInWithPopup(auth, googleProvider);
    } catch (error) {
      const code = error?.code || 'auth/error';
      if (code === 'auth/popup-closed-by-user') {
        setSettingsStatus('팝업이 로그인 완료 전에 닫혔습니다. 이동 로그인을 시도하세요.');
      } else if (code === 'auth/operation-not-allowed') {
        setSettingsStatus('Firebase Auth에서 Google 로그인이 활성화되지 않았습니다.');
      } else if (code === 'auth/unauthorized-domain') {
        setSettingsStatus('Firebase Auth에서 허용되지 않은 도메인입니다.');
      } else {
        setSettingsStatus(`${code}: ${error?.message || '로그인 실패'}`);
      }
    }
  };

  const loginWithRedirect = async () => {
    if (!auth || !googleProvider) {
      setSettingsStatus('Firebase 로그인이 설정되지 않았습니다');
      return;
    }
    setSettingsStatus('Google 로그인으로 이동합니다');
    try {
      await signInWithRedirect(auth, googleProvider);
    } catch (error) {
      setSettingsStatus(`${error?.code || 'auth/error'}: ${error?.message || '이동 로그인 실패'}`);
    }
  };

  const logout = async () => {
    if (!auth) return;
    await signOut(auth);
  };

  useEffect(() => {
    refreshSignals();
  }, []);

  useEffect(() => {
    if (!auth || !db) {
      setSettingsReady(true);
      return undefined;
    }

    getRedirectResult(auth).catch((error) => {
      setSettingsStatus(`${error?.code || 'auth/error'}: ${error?.message || '이동 로그인 실패'}`);
    });

    return onAuthStateChanged(auth, async (nextUser) => {
      setUser(nextUser);
      setSettingsReady(false);
      if (!nextUser) {
        setSettingsReady(true);
        setSettingsStatus('');
        return;
      }

          setSettingsStatus('설정 불러오는 중');
      try {
        const snap = await getDoc(doc(db, 'users', nextUser.uid, 'settings', 'chart'));
        if (snap.exists()) {
          const data = snap.data();
          setRange(data.range ?? 240);
          setTheme(data.theme || defaultTheme);
          setLayers((current) => ({ ...current, ...(data.layers || {}) }));
          setIndicatorStyles(cloneIndicatorStyles(data.indicatorStyles || indicatorStylePresets[data.theme || defaultTheme]));
          setIndicatorVisibility(normalizeIndicatorVisibility(data.indicatorVisibility));
          setMarketFilter(data.marketFilter || 'ALL');
          setLabelFilter(data.labelFilter || 'ALL');
          setSortMode(data.sortMode || 'confidence');
          setSortDirection(data.sortDirection || 'desc');
        }
        setSettingsStatus('설정 불러옴');
      } catch (error) {
        setSettingsStatus(error?.message || '설정 불러오기 실패');
      } finally {
        setSettingsReady(true);
      }
    });
  }, []);

  useEffect(() => {
    if (!user || !db || !settingsReady) return undefined;

    setSettingsStatus('설정 저장 중');
    const timer = window.setTimeout(async () => {
      try {
        await setDoc(doc(db, 'users', user.uid, 'settings', 'chart'), {
          range,
          theme,
          layers,
          indicatorStyles,
          indicatorVisibility,
          marketFilter,
          labelFilter,
          sortMode,
          sortDirection,
          updatedAt: serverTimestamp(),
        }, { merge: true });
        setSettingsStatus('설정 저장됨');
      } catch (error) {
        setSettingsStatus(error?.message || '설정 저장 실패');
      }
    }, 500);

    return () => window.clearTimeout(timer);
  }, [user?.uid, settingsReady, range, theme, layers, indicatorStyles, indicatorVisibility, marketFilter, labelFilter, sortMode, sortDirection]);

  useEffect(() => {
    if (!selected || selected.raw?.hasFullHistory) return;
    loadSignalDetail(selected);
  }, [selected?.id]);

  if (!hasLoaded && loading) {
    return (
      <main className={`loading-screen ${themeClassMap[theme] || themeClassMap.light}`}>
        <div className="loading-panel">
          <RefreshCw size={22} className="spin" />
          <span>전략 데이터 불러오는 중</span>
          <strong>Mesugak V2</strong>
        </div>
      </main>
    );
  }

  return (
    <main className={`terminal-shell ${themeClassMap[theme] || themeClassMap.light}`}>
      <aside className="watchlist">
        <div className="brand-block">
          <span>Mesugak V2</span>
          <h1>기술 분석</h1>
        </div>

        <div className="watchlist-meta">
          <span>{filteredSignals.length} / {summary.candidates} 종목</span>
          <button type="button" className="icon-button" onClick={refreshSignals} aria-label="Refresh data">
            <RefreshCw size={16} className={loading ? 'spin' : ''} />
          </button>
        </div>

        <div className="watch-filters" aria-label="Stock filters">
          <input
            type="search"
            value={searchText}
            onChange={(event) => setSearchText(event.target.value)}
            placeholder="종목명 또는 코드 검색"
          />
          <div className="filter-grid">
            <select value={marketFilter} onChange={(event) => setMarketFilter(event.target.value)} aria-label="Market filter">
              <option value="ALL">전체 시장</option>
              <option value="KR">KR</option>
              <option value="US">US</option>
            </select>
            <select value={labelFilter} onChange={(event) => setLabelFilter(event.target.value)} aria-label="Signal filter">
              <option value="ALL">전체 신호</option>
              <option value="STRONG_BUY">강한 매수</option>
              <option value="BUY_CANDIDATE">매수 후보</option>
              <option value="WATCH">관찰</option>
              <option value="AVOID">회피</option>
            </select>
          </div>
          <div className="sort-heading">
            <span>{sortUi.heading}</span>
            <strong style={{ color: activeSort.color }}>{activeSort.category}</strong>
          </div>
          <div className="sort-direction" aria-label="Sort direction">
            <button type="button" className={sortDirection === 'asc' ? 'active' : ''} onClick={() => setSortDirection('asc')}>{sortUi.descending}</button>
            <button type="button" className={sortDirection === 'desc' ? 'active' : ''} onClick={() => setSortDirection('desc')}>{sortUi.ascending}</button>
          </div>
          <select className="sort-select" value={sortMode} onChange={(event) => setSortMode(event.target.value)} aria-label="Sort stocks">
            {sortGroups.map((group) => (
              <optgroup key={group.label} label={group.label}>
                {group.options.map((option) => (
                  <option key={option.key} value={option.key} style={{ color: option.color }}>
                    {option.category}{sortUi.separator}{option.label}
                  </option>
                ))}
              </optgroup>
            ))}
            <option value="confidence">점수순</option>
            <option value="cash">현금 비중순</option>
            <option value="market">시장/코드순</option>
            <option value="name">종목명순</option>
          </select>
          <select value={theme} onChange={(event) => applyTheme(event.target.value)} aria-label="Theme">
            {themeOptions.map((option) => (
              <option key={option.key} value={option.key}>{option.label} 테마</option>
            ))}
          </select>
        </div>

        <div className="market-summary">
          <div>
            <span>고점수</span>
            <strong>{summary.highConfidence}</strong>
          </div>
          <div>
            <span>최대 현금</span>
            <strong>{summary.maxCash}%</strong>
          </div>
          <div>
            <span>주문</span>
            <strong>{summary.staged}</strong>
          </div>
        </div>

        <div className="signal-stack">
          {filteredSignals.length === 0 && (
            <div className="empty-watch">조건에 맞는 종목이 없습니다</div>
          )}
          {filteredSignals.map((signal) => (
            <button
              key={signal.id}
              type="button"
              className={`watch-row ${selected.id === signal.id ? 'selected' : ''}`}
              onClick={() => selectSignal(signal)}
            >
              <span className="watch-main">
                <strong>{signal.name}</strong>
                <span>{signal.market}:{signal.code}</span>
              </span>
              <span className={`watch-score score-${signal.riskState}`}>{formatNumber(signal.confidence, 1)}</span>
            </button>
          ))}
        </div>
      </aside>

      <section className="chart-column">
        <header className="desk-topbar">
          <div>
            <p>{loadError ? `대체 데이터: ${loadError}` : 'Firestore 실시간 데이터'}</p>
            <h2>차트 중심 다중 지표 스캐너</h2>
          </div>
          <div className="topbar-actions">
            <div className="workspace-tabs" aria-label="Workspace view">
              <button
                type="button"
                className={workspaceView === 'console' ? 'active' : ''}
                onClick={() => setWorkspaceView('console')}
              >
                Console
              </button>
              <button
                type="button"
                className={workspaceView === 'executions' ? 'active' : ''}
                onClick={() => setWorkspaceView('executions')}
              >
                Executions
              </button>
            </div>
            <div className="topbar-pills">
              <span><CandlestickChart size={14} /> 캔들</span>
              <span><Cloud size={14} /> 일목</span>
              <span><Gauge size={14} /> RSI</span>
            </div>
            <div className="auth-block">
              <span>{user ? (settingsStatus || user.displayName || user.email) : '로그인 전에는 설정이 이 브라우저에만 남습니다'}</span>
              <div className="auth-buttons">
                <button type="button" className="auth-button" onClick={user ? logout : loginWithGoogle}>
                  {user ? <LogOut size={14} /> : <LogIn size={14} />}
                  <span>{user ? '로그아웃' : '로그인'}</span>
                </button>
                {!user && (
                  <button type="button" className="auth-button ghost" onClick={loginWithRedirect}>
                    <span>이동 로그인</span>
                  </button>
                )}
              </div>
            </div>
          </div>
        </header>

        {workspaceView === 'console' && (
          <>
            <div className="analysis-layout">
              <TechnicalChart
                stock={selected}
                range={range}
                layers={layers}
                indicatorStyles={indicatorStyles}
                indicatorVisibility={indicatorVisibility}
                onRangeChange={setRange}
                onToggleLayer={toggleLayer}
                onStyleChange={updateIndicatorStyle}
                onVisibilityChange={updateIndicatorVisibility}
                isLoading={detailLoadingId === selected.id}
              />
              <ScoreDock stock={selected} />
            </div>

            <PortfolioSnapshot portfolio={portfolio} />
          </>
        )}

        {workspaceView === 'executions' && (
          <div className="execution-page">
            <PortfolioSnapshot portfolio={portfolio} />
            <TradeLogPanel logs={tradeLogs} />
          </div>
        )}

        <section className="orders-strip">
          <div className="orders-header">
            <div>
              <p>Rebalance simulation</p>
              <h3>Staged orders</h3>
            </div>
            <AlertTriangle size={18} />
          </div>
          <div className="order-table">
            <table>
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Code</th>
                  <th>Side</th>
                  <th>Amount</th>
                  <th>Reason</th>
                </tr>
              </thead>
              <tbody>
                {orders.map((order) => (
                  <tr key={`${order.code}-${order.action}-${order.amount}`}>
                    <td>{order.time}</td>
                    <td>{order.code}</td>
                    <td><span className={`side side-${String(order.action).toLowerCase()}`}>{order.action}</span></td>
                    <td>{order.amount}</td>
                    <td>{order.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </section>
    </main>
  );
}
