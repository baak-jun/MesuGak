import { useEffect, useMemo, useRef, useState } from 'react';
import { getRedirectResult, onAuthStateChanged, signInWithPopup, signOut } from 'firebase/auth';
import { addDoc, collection, doc, getDoc, getDocs, limit, onSnapshot, orderBy, query, serverTimestamp, where } from 'firebase/firestore';
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
import { hasSubstantialAnalysisContent } from './contentPolicy';
import { ComplianceDock } from './LegalPages.jsx';
import { BRAND_FULL, BRAND_SHORT } from './brand';
import {
  AnalysisContentsRail,
  analysisReasonLabel,
  educationUiCopy,
  educationalGuides,
  getReasonGraphic,
  getReasonLesson,
  isCautionReason,
  publicIndicatorGuides,
  publicReasonLabel,
  publicStateExplanation,
  publicStateLabel,
} from './analysisEducationContent.jsx';
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

const publicSortGroups = [{
  label: '공개 요약',
  options: sortGroups[0].options.filter((option) => ['name', 'market', 'confidence'].includes(option.key)),
}];

const sortOptions = sortGroups.flatMap((group) => group.options);
const sortOptionByKey = Object.fromEntries(sortOptions.map((option) => [option.key, option]));

const themeOptions = [
  { key: 'light', label: '라이트' },
  { key: 'nightOwl', label: '나이트 아울' },
  { key: 'beigeOwl', label: '베이지 아울' },
];

const themeClassMap = { light: 'theme-light', nightOwl: 'theme-night-owl', beigeOwl: 'theme-beige-owl' };




const statusLabels = {
  HIGH_ALIGNMENT: '조건 일치 높음',
  MODERATE_ALIGNMENT: '조건 일치 보통',
  LIMITED_ALIGNMENT: '조건 일치 제한적',
  CAUTION: '주의 조건 우세',
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


// Public research and advertising are fail-closed. The same gate runs before build.
const { publicLiveDataApproved, analysisAdsRequested } = monetizationGate(import.meta.env);

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


function publicConclusion(stock) {
  if (stock.riskState === 'defensive') return '주의 조건의 비중이 높습니다. 이후 방향을 단정하지 않고 약화 요인과 다음 확정 일봉의 변화를 함께 확인해야 합니다.';
  if (stock.confidence >= 70) return '여러 기술 조건의 일치도가 상대적으로 높게 계산됐습니다. 이는 과거·현재 조건의 요약이며 미래 가격 방향이나 수익을 예측하지 않습니다.';
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
  if (!firebaseReady || !db) return { signals: [], manifests: {}, loadedPages: [] };
  if (!admin && !publicLiveDataApproved) return { signals: [], manifests: {}, loadedPages: [] };
  if (admin) {
    const metaQuery = query(collection(db, 'meta_data'), where('market', '==', 'KR'));
    const metaSnap = await getDocs(metaQuery);
    let rows = [];
    metaSnap.forEach((item) => {
      const data = item.data();
      if (data.strategyVersion === 'V2' && Array.isArray(data.list) && item.id.startsWith('meta_v2_')) rows = rows.concat(data.list);
    });
    rows.sort((a, b) => Number(b.confidenceScore || 0) - Number(a.confidenceScore || 0));
    return { signals: rows.map(mapStockPayload), manifests: {}, loadedPages: [] };
  }

  const markets = ['KR'];
  const manifestSnapshots = await Promise.all(markets.map((market) => getDoc(doc(db, 'public_analysis_meta', `public_meta_v2_${market}_manifest`))));
  const manifests = {};
  manifestSnapshots.forEach((snapshot, index) => {
    if (snapshot.exists() && snapshot.data()?.strategyVersion === 'V2_PUBLIC_MANIFEST') manifests[markets[index]] = snapshot.data();
  });
  const pageKeys = Object.keys(manifests).map((market) => `${market}:0`);
  return {
    signals: await loadPublicPageKeys(pageKeys),
    manifests,
    loadedPages: pageKeys,
  };
}

const developmentSignals = import.meta.env.DEV ? mockSignals.map(mapStockPayload) : [];

async function loadPublicPageKeys(pageKeys) {
  if (!firebaseReady || !db || !publicLiveDataApproved || pageKeys.length === 0) return [];
  const snapshots = await Promise.all(pageKeys.map((key) => {
    const [market, page] = key.split(':');
    return getDoc(doc(db, 'public_analysis_meta', `public_meta_v2_${market}_${page}`));
  }));
  const rows = [];
  snapshots.forEach((snapshot) => {
    const data = snapshot.exists() ? snapshot.data() : null;
    if (data?.strategyVersion === 'V2_PUBLIC' && Array.isArray(data.list)) rows.push(...data.list);
  });
  return rows.map(mapStockPayload);
}

function mergeSignals(current, incoming) {
  const merged = new Map(current.map((signal) => [signal.id, signal]));
  incoming.forEach((signal) => merged.set(signal.id, signal));
  return [...merged.values()];
}
async function loadOrdersFromFirestore(allowLiveData = false) {
  if (!allowLiveData || !firebaseReady || !db) return [];
  const ordersQuery = query(collection(db, 'rebalance_orders'), orderBy('updatedAt', 'desc'), limit(200));
  const snap = await getDocs(ordersQuery);
  const rows = [];
  snap.forEach((item) => {
    const data = item.data();
    if (data.market === 'KR') rows.push({ id: item.id, ...data });
  });
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
  const logsQuery = query(collection(db, 'bot_trade_logs'), orderBy('createdAt', 'desc'), limit(120));
  const snap = await getDocs(logsQuery);
  const rows = [];
  snap.forEach((item) => rows.push({ id: item.id, ...item.data() }));
  return rows.map((log) => ({
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

function SupportCard() {
  const configuredUrl = String(import.meta.env.VITE_SUPPORT_URL || '').trim();
  const supportUrl = configuredUrl.startsWith('https://') ? configuredUrl : '';

  return (
    <aside className="support-card" aria-label="자발적 사이트 운영 후원">
      <div className="support-card-copy">
        <Coffee size={22} aria-hidden="true" />
        <div>
          <span>자발적 운영 후원</span>
          <strong>사이트가 도움이 됐다면 커피 한 잔으로 응원할 수 있어요.</strong>
          <small>후원 여부와 관계없이 공개 정보는 동일하며, 개별 상담·추가 분석·우선 열람은 제공하지 않습니다.</small>
        </div>
      </div>
      {supportUrl ? (
        <a className="support-card-button" href={supportUrl} target="_blank" rel="noopener noreferrer">
          커피 한 잔 후원하기 <ExternalLink size={14} aria-hidden="true" />
        </a>
      ) : (
        <span className="support-card-button disabled" aria-disabled="true">후원 링크 준비 중</span>
      )}
    </aside>
  );
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
  const [helpKey, setHelpKey] = useState(null);
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
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ color: component.color }}>{component.label}</span>
                  {educationalGuides[component.key] && (
                    <button type="button" onClick={(e) => { e.stopPropagation(); setHelpKey(component.key); }} style={{background: 'none', border: 'none', cursor: 'pointer', padding: 0, color: 'var(--text-muted)', display: 'flex', alignItems: 'center'}} title="패턴 기준 보기">
                      <HelpCircle size={13} />
                    </button>
                  )}
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
    {helpKey && <EducationalGuideModal guideKey={helpKey} onClose={() => setHelpKey(null)} />}
      </aside>
    );
  }


function useModalBehavior(onClose) {
  useEffect(() => {
    const previousOverflow = document.body.style.overflow;
    const onKeyDown = (event) => {
      if (event.key === 'Escape') onClose();
    };
    document.body.style.overflow = 'hidden';
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener('keydown', onKeyDown);
    };
  }, [onClose]);
}

function DisclaimerModal({ onClose }) {
  useModalBehavior(onClose);
  return (
    <div className="modal-backdrop" role="presentation" onClick={onClose}>
      <div className="modal-content modal-content--disclaimer" role="dialog" aria-modal="true" aria-labelledby="disclaimer-modal-title" onClick={e => e.stopPropagation()}>
        <div className="modal-header"><h3 id="disclaimer-modal-title">서비스 이용 안내</h3></div>
        <div className="modal-body"><p>
          이 서비스는 기술지표를 이해하기 위한 학습 정보를 제공하며, 개인별 투자 상담이나 특정 종목의 매수·매도·보유 권유를 제공하지 않습니다.<br/><br/>
          화면의 점수와 해설은 최근 거래일의 확정 일봉에서 계산한 기술적 조건을 정리한 결과이며, 미래 가격이나 수익을 보장하지 않습니다.<br/><br/>
          이 정보를 실제 투자에 활용할지는 이용자가 스스로 판단해야 합니다.
        </p></div>
        <div className="modal-actions"><button type="button" onClick={onClose} className="auth-button">확인</button></div>
      </div>
    </div>
  );
}

function EducationalGuideModal({ guideKey, onClose }) {
  const guide = educationalGuides[guideKey];
  useModalBehavior(onClose);
  if (!guide) return null;
  return (
    <div className="modal-backdrop" role="presentation" onClick={onClose}>
      <div className="modal-content modal-content--guide" role="dialog" aria-modal="true" aria-labelledby="guide-modal-title" onClick={e => e.stopPropagation()}>
        <div className="modal-header"><h3 id="guide-modal-title">{guide.title} {educationUiCopy.guideTitleSuffix}</h3><button type="button" onClick={onClose} className="modal-close" aria-label="설명 닫기"><X size={20} /></button></div>
        <div className="modal-body"><p>{educationUiCopy.guideIntro}</p>
          <div className="guide-points">
            {guide.points.map((pt, i) => (
              <div key={i} className="guide-point">
                <strong>{pt.label}</strong>
                <p>{pt.desc}</p>
                <div className="guide-graphic">{pt.graphic}</div>
              </div>
            ))}
          </div>
          <small className="modal-education-disclaimer"><strong>{educationUiCopy.disclaimerTitle}</strong>{educationUiCopy.disclaimerText}</small>
        </div>
      </div>
    </div>
  );
}

function ReasonExplanationModal({ reasonKey, onClose }) {
  const label = publicReasonLabel(reasonKey);
  const lesson = getReasonLesson(reasonKey);
  const visual = getReasonGraphic(reasonKey);
  useModalBehavior(onClose);

  return (
    <div className="modal-backdrop" role="presentation" onClick={onClose}>
      <div className="modal-content modal-content--reason" role="dialog" aria-modal="true" aria-labelledby="reason-modal-title" onClick={e => e.stopPropagation()}>
        <div className="modal-header"><h3 id="reason-modal-title"><HelpCircle size={18} color="var(--accent, #3b82f6)" />{educationUiCopy.reasonModalTitle}</h3><button type="button" onClick={onClose} className="modal-close" aria-label="해설 닫기"><X size={20} /></button></div>
        <div className="modal-body"><div className="reason-lesson">
          <strong className="reason-lesson-title">{label}</strong>
          {visual && (
            <figure className="reason-lesson-graphic">
              <figcaption>그림으로 읽어보기 · {visual.label}</figcaption>
              <div className="reason-lesson-graphic-canvas" role="img" aria-label={`${label} 설명 그림`}>{visual.graphic}</div>
            </figure>
          )}
          <section className="reason-lesson-section reason-lesson-section--meaning"><span>{educationUiCopy.reasonMeaningLabel}</span><p>{lesson.meaning}</p></section>
          <section className="reason-lesson-section reason-lesson-section--interpretation"><span>{educationUiCopy.reasonInterpretationLabel}</span><p>{lesson.interpretation}</p></section>
          <section className="reason-lesson-section reason-lesson-section--check"><span>{educationUiCopy.reasonCheckLabel}</span><p>{lesson.check}</p></section>
          <small className="modal-education-disclaimer"><strong>{educationUiCopy.disclaimerTitle}</strong>{educationUiCopy.disclaimerText}</small>
        </div></div>
        <div className="modal-actions"><button type="button" onClick={onClose} className="auth-button">확인</button></div>
      </div>
    </div>
  );
}

function PublicAnalysisUnavailable({ message }) {
  return (<section className="public-analysis-panel public-analysis-unavailable"><p>공공데이터 기반 기술지표 분석</p><h3>공개 분석을 준비 중입니다.</h3><span>{message || '다음 분석 결과가 게시되면 이곳에 지표별 해설이 표시됩니다.'}</span></section>);
}

function PublicAnalysisPanel({ stock, compact = false }) {
  const [helpKey, setHelpKey] = useState(null);
  const [reasonKey, setReasonKey] = useState(null);
  const [expandedIndicators, setExpandedIndicators] = useState(() => new Set());
  const reasons = Array.from(new Set([...(stock.raw?.confidenceReasons || stock.raw?.signal?.reasons || []), ...Object.values(stock.indicatorStates || {}).flatMap((state) => state?.reasons || [])].filter(Boolean))).slice(0, 16);
  const states = Object.entries(stock.indicatorStates || {}).filter(([, state]) => state?.state || (state?.reasons || []).length);
  const supportingReasons = reasons.filter((reason) => !isCautionReason(reason));
  const cautionReasons = reasons.filter(isCautionReason);
  const baseId = 'public-analysis-' + String(stock.id || stock.code || 'stock').replace(/[^a-zA-Z0-9_-]/g, '-');
  const sectionId = (suffix) => baseId + '-' + suffix;
  const sections = [
    { id: sectionId('overview'), label: '종합 해석', description: '현재 분류와 읽는 방법' },
    { id: sectionId('evidence'), label: '반영한 조건', description: '긍정·주의 근거' },
    { id: sectionId('indicators'), label: '지표별 해설', description: '상태와 추가 확인점' },
  ];

  return (
    <section className="public-analysis-panel">
      <AnalysisContentsRail sections={sections} />
      <div className="public-analysis-header">
        <div><p>공공데이터 기반 기술지표 분석</p><h3>{stock.name}</h3><span>{stock.market}:{stock.code} · 확정 일봉 기준 {stock.updatedAt}</span></div>
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
        <p className="public-analysis-note">최근 거래일의 확정 일봉을 분석한 결과입니다. 가격·차트·지표 원수치는 공개하지 않고, 분석에 반영된 조건과 해설만 보여드립니다.</p>
      </section>

      <section id={sectionId('evidence')} className="public-analysis-section public-evidence-section">
        <div className="public-section-heading"><span>02 · 반영한 조건</span><h4>뒷받침 조건과 주의 조건을 나눠 확인하세요</h4><p>같은 종목 안에서도 서로 다른 방향의 근거가 함께 존재할 수 있습니다.</p></div>
        <div className="public-evidence-columns">
          <article className="public-evidence-card supportive"><header><strong>해석을 뒷받침한 조건</strong><span>{supportingReasons.length}개</span></header><div>{supportingReasons.length ? supportingReasons.map((reason) => <span key={reason} onClick={() => setReasonKey(reason)} style={{cursor: 'pointer'}} title="클릭하여 설명 보기" className="clickable-reason">{publicReasonLabel(reason)} <HelpCircle size={11} style={{display:'inline', marginLeft:'2px', opacity:0.6}}/></span>) : <small>현재 공개된 뒷받침 조건이 없습니다.</small>}</div></article>
          <article className="public-evidence-card caution"><header><strong>함께 확인할 조건</strong><span>{cautionReasons.length}개</span></header><div>{cautionReasons.length ? cautionReasons.map((reason) => <span key={reason} onClick={() => setReasonKey(reason)} style={{cursor: 'pointer'}} title="클릭하여 설명 보기" className="clickable-reason">{publicReasonLabel(reason)} <HelpCircle size={11} style={{display:'inline', marginLeft:'2px', opacity:0.6}}/></span>) : <small>현재 뚜렷한 경고 조건이 없습니다.</small>}</div></article>
        </div>
        {stock.raw?.riskFlags?.length > 0 && <div className="public-risk-note"><Shield size={16} /><span><strong>추가 주의 신호:</strong> {stock.raw.riskFlags.map(publicReasonLabel).join(' · ')}</span></div>}
      </section>

      <section id={sectionId('indicators')} className="public-analysis-section public-state-detail">
        <div className="public-section-heading"><span>03 · 지표별 상태 해설</span><h4>각 지표를 어떤 조건으로 분류했나요?</h4><p>실제 입력값은 공개하지 않고, 분석 코드가 판정한 상태와 조건 설명만 제공합니다.</p></div>
        {states.length ? states.map(([key, state]) => {
          const stateReasons = (state.reasons || []).slice(0, 6);
          return (
            <details
              key={key}
              className="public-indicator-explainer"
              open={!compact || expandedIndicators.has(key)}
              onToggle={(event) => {
                if (!compact) return;
                const isOpen = event.currentTarget.open;
                setExpandedIndicators((current) => {
                  const next = new Set(current);
                  if (isOpen) next.add(key);
                  else next.delete(key);
                  return next;
                });
              }}
            >
              <summary>
                <div style={{display: 'flex', flexDirection: 'column'}}>
                  <div style={{display: 'flex', alignItems: 'center', gap: '6px'}}>
                    <span>{publicIndicatorGuides[key]?.label || componentMeta[key]?.label || key}</span>
                  </div>
                  <h5>{publicStateLabel(state.state)}</h5>
                </div>
                <strong>상태 요약</strong>
              </summary>
              <div className="public-indicator-body">
                {educationalGuides[key] && (
                  <button type="button" onClick={() => setHelpKey(key)} className="public-guide-button" title="패턴 기준 보기">
                    <HelpCircle size={14} /> 지표 읽는 법
                  </button>
                )}
                <p>{publicStateExplanation(key, state.state)}</p>
                <div className="public-explainer-prompt">
                  <span>이번 분석에서 확인한 이유</span>
                  <div>{stateReasons.length ? stateReasons.map((reason) => <button type="button" key={reason} onClick={() => setReasonKey(reason)} title="클릭하여 설명 보기" className="public-reason-detail-button">{publicReasonLabel(reason)} <HelpCircle size={11} /></button>) : <small>세부 근거를 다음 분석 갱신에서 보완합니다.</small>}</div>
                </div>
              </div>
            </details>
          );
        }) : <div className="public-empty-detail">현재 종목의 지표별 해설을 준비 중입니다.</div>}
      </section>
      {helpKey && <EducationalGuideModal guideKey={helpKey} onClose={() => setHelpKey(null)} />}
      {reasonKey && <ReasonExplanationModal reasonKey={reasonKey} onClose={() => setReasonKey(null)} />}
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
        <div><p>관리자 전용 · KIS 모의계좌</p><h3>모의투자 성과와 시장 비교</h3></div>
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
        <p className="private-performance-note">KIS 모의계좌의 조회값을 같은 기준일의 시장지수와 비교한 결과입니다. 실제 투자 성과나 수익을 보장하지 않으며, 표시된 기간 안에서만 비교해 주세요.</p>
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
        <div><p>관리자 전용 모의계좌 · {BRAND_SHORT}</p><h3>가상 계좌 현황</h3></div>
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
        <div><span>{isExamplePortfolio ? '예시 포트폴리오 수익률' : '누적 계좌 수익률'}</span><strong className={isUp ? 'pnl-up' : 'pnl-down'}>{formatSigned(returnPct, 2)}%</strong><p>{isExamplePortfolio ? '개발 환경에서만 사용하는 예시 수치입니다.' : 'KIS 모의계좌의 초기 잔고와 현재 평가자산을 비교한 값입니다.'}</p></div>
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
      <p className="section-note portfolio-legal-note">이 화면은 모의투자 기록입니다. 실제 투자 성과를 의미하지 않으며 세금, 수수료, 체결 오차와 거래 제한을 모두 반영하지 않을 수 있습니다.</p>
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
                <td data-label="시간">{log.time}</td>
                <td data-label="구분"><span className={`side side-${String(log.action).toLowerCase()}`}>{actionLabel(log.action)}</span></td>
                <td data-label="종목"><span className="symbol-cell"><strong>{log.name}</strong><small>{log.code} · {log.source}</small></span></td>
                <td data-label="수량">{formatNumber(log.quantity, 0)}</td>
                <td data-label="가격">{formatNumber(log.price, 0)}</td>
                <td data-label="금액">{formatNumber(log.amount, 0)}</td>
                <td data-label="손익" className={Number(log.pnl || 0) >= 0 ? 'pnl-up' : 'pnl-down'}>{log.pnl === undefined ? '-' : formatSigned(log.pnl, 0)}</td>
                <td data-label="사유">{reasonLabel(log.reason)}</td>
                <td data-label="브로커 주문">{log.brokerOrderNo || '-'}</td>
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
      <p className="section-note">아래 항목은 모의투자와 백테스트를 확인하기 위해 전략 엔진이 만든 가상 주문 후보입니다. 실제 매매 권유가 아닙니다.</p>
      <div className="order-table">
        <table>
          <thead><tr><th>시간</th><th>코드</th><th>구분</th><th>금액</th><th>사유</th></tr></thead>
          <tbody>
            {orders.length === 0 && <tr><td colSpan="5" className="empty-table-cell">현재 가상 주문 후보가 없습니다.</td></tr>}
            {orders.map((order, index) => <tr key={`${order.code}-${order.action}-${order.amount}-${index}`}><td data-label="시간">{order.time}</td><td data-label="코드">{order.code}</td><td data-label="구분"><span className={`side side-${String(order.action).toLowerCase()}`}>{actionLabel(order.action)}</span></td><td data-label="금액">{formatNumber(order.amount, 0)}</td><td data-label="사유">{reasonLabel(order.reason)}</td></tr>)}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export default function ResearchApp() {
  const [signals, setSignals] = useState([]);
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
  const [publicManifests, setPublicManifests] = useState({});
  const [publicLoadedPages, setPublicLoadedPages] = useState([]);
  const [visibleCount, setVisibleCount] = useState(30);
  const [marketFilter, setMarketFilter] = useState('ALL');
  const [labelFilter, setLabelFilter] = useState('ALL');
  const [sortMode, setSortMode] = useState('confidence');
  const [sortDirection, setSortDirection] = useState('desc');
  const [workspaceView, setWorkspaceView] = useState('console');
  const [mobilePane, setMobilePane] = useState('list');
  const [isCompactLayout, setIsCompactLayout] = useState(() => typeof window !== 'undefined' && window.matchMedia('(max-width: 920px)').matches);
  const [theme, setTheme] = useState(() => localStorage.getItem('mesugak_theme') || 'beigeOwl');

  useEffect(() => {
    localStorage.setItem('mesugak_theme', theme);
  }, [theme]);
  useEffect(() => {
    const media = window.matchMedia('(max-width: 920px)');
    const updateLayout = () => setIsCompactLayout(media.matches);
    updateLayout();
    media.addEventListener?.('change', updateLayout);
    return () => media.removeEventListener?.('change', updateLayout);
  }, []);
  const [showDisclaimerModal, setShowDisclaimerModal] = useState(false);
  const [user, setUser] = useState(null);
  const [isAdmin, setIsAdmin] = useState(false);
  const [adminViewActive, setAdminViewActive] = useState(false);
  const [adminChecking, setAdminChecking] = useState(false);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [settingsStatus, setSettingsStatus] = useState('');
  const [paperRefreshBusy, setPaperRefreshBusy] = useState(false);
  const publicRefreshInFlightRef = useRef(false);
  const lastPublicRefreshAtRef = useRef(0);
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

  const displayedSignals = adminViewActive ? filteredSignals : filteredSignals.slice(0, visibleCount);
  const publicTotalCount = Object.values(publicManifests).reduce((total, manifest) => total + Number(manifest.totalCount || 0), 0);
  const publicChunkCount = Object.entries(publicManifests).reduce((total, [, manifest]) => total + Number(manifest.chunkCount || 0), 0);
  const hasMorePublic = !adminViewActive && (
    visibleCount < filteredSignals.length || publicLoadedPages.length < publicChunkCount
  );

  // With no manual selection, the report always starts from the first visible row
  // after the current search, filters, and sort order are applied.
  const selected = useMemo(() => (
    displayedSignals.find((signal) => signal.id === selectedId) ?? displayedSignals[0] ?? signals[0]
  ), [displayedSignals, selectedId, signals]);

  // The analysis placement is intentionally narrow: it never appears on
  // loading, error, empty, administrator, or low-information reports.
  const publicAnalysisAdReady = analysisAdsRequested
    && publicLiveDataApproved
    && hasLoaded
    && !loading
    && !adminViewActive
    && !loadError
    && hasSubstantialAnalysisContent(selected);

  useEffect(() => {
    if (adminViewActive || searchText.trim().length < 2 || Object.keys(publicManifests).length === 0) return undefined;
    const timer = window.setTimeout(() => {
      const queryText = searchText.trim().toLowerCase();
      const loaded = new Set(publicLoadedPages);
      const missingPages = [];
      Object.entries(publicManifests).forEach(([market, manifest]) => {
        if (marketFilter !== 'ALL' && marketFilter !== market) return;
        (manifest.searchIndex || []).forEach((entry) => {
          const code = Array.isArray(entry) ? entry[1] : entry?.code;
          const name = Array.isArray(entry) ? entry[2] : entry?.name;
          const page = Array.isArray(entry) ? entry[3] : entry?.page;
          if ([code, name].join(' ').toLowerCase().includes(queryText)) {
            const key = `${market}:${page}`;
            if (!loaded.has(key) && !missingPages.includes(key) && missingPages.length < 8) missingPages.push(key);
          }
        });
      });
      if (missingPages.length === 0) return;
      void loadPublicPageKeys(missingPages).then((incoming) => {
        setSignals((current) => mergeSignals(current, incoming));
        setPublicLoadedPages((current) => [...new Set([...current, ...missingPages])]);
        setVisibleCount(30);
      }).catch(() => setLoadError('검색 결과 일부를 불러오지 못했습니다. 잠시 뒤 다시 시도해 주세요.'));
    }, 250);
    return () => window.clearTimeout(timer);
  }, [adminViewActive, searchText, marketFilter, publicManifests, publicLoadedPages]);

  const loadMorePublic = async () => {
    if (visibleCount < filteredSignals.length) {
      setVisibleCount((count) => count + 30);
      return;
    }
    const loaded = new Set(publicLoadedPages);
    let nextKey = '';
    for (const [market, manifest] of Object.entries(publicManifests)) {
      if (marketFilter !== 'ALL' && marketFilter !== market) continue;
      for (let page = 0; page < Number(manifest.chunkCount || 0); page += 1) {
        const key = `${market}:${page}`;
        if (!loaded.has(key)) {
          nextKey = key;
          break;
        }
      }
      if (nextKey) break;
    }
    if (!nextKey) return;
    setLoading(true);
    try {
      const incoming = await loadPublicPageKeys([nextKey]);
      setSignals((current) => mergeSignals(current, incoming));
      setPublicLoadedPages((current) => [...new Set([...current, nextKey])]);
      setVisibleCount((count) => count + 30);
    } catch {
      setLoadError('다음 30개 종목을 불러오지 못했습니다. 잠시 뒤 다시 시도해 주세요.');
    } finally {
      setLoading(false);
    }
  };

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
    if (!adminAccess) {
      const recentlyLoaded = Date.now() - lastPublicRefreshAtRef.current < 5_000;
      if (publicRefreshInFlightRef.current || recentlyLoaded) return;
      publicRefreshInFlightRef.current = true;
    }
    setLoading(true); setLoadError('');
    try {
      const result = await loadSignalsFromFirestore({ admin: adminAccess });
      const loaded = result.signals;
      setPublicManifests(result.manifests);
      setPublicLoadedPages(result.loadedPages);
      setVisibleCount(30);
      if (loaded.length > 0) {
        const nextSelectedId = adminAccess && loaded.some((signal) => signal.id === selectedId) ? selectedId : '';
        const selectedIndex = Math.max(0, loaded.findIndex((signal) => signal.id === nextSelectedId));
        const selectedSignal = loaded[selectedIndex];
        if (adminAccess && firebaseReady && db && !selectedSignal.raw?.hasFullHistory) { const snap = await getDoc(doc(db, 'stock_analysis', selectedSignal.id)); if (snap.exists()) loaded[selectedIndex] = mapStockPayload({ ...selectedSignal.raw, ...snap.data(), id: selectedSignal.id }); }
        setSignals(loaded); setSelectedId(nextSelectedId);
      } else if (adminAccess && developmentSignals.length > 0) { setSignals(developmentSignals); setSelectedId(developmentSignals[0]?.id || ''); setLoadError('개발 환경 예시 데이터입니다. Firestore V2 분석 목록은 아직 없습니다.'); }
      else { setSignals([]); setSelectedId(''); setLoadError(adminAccess ? 'Firestore에 V2 분석 목록이 아직 없습니다.' : '공개 분석 결과가 아직 발행되지 않았습니다.'); }
      if (adminAccess) { const loadedOrders = await loadOrdersFromFirestore(true).catch(() => []); setOrders(loadedOrders.length > 0 ? loadedOrders : fallbackOrders); } else { setOrders([]); }
    } catch (error) { setSignals([]); setSelectedId(''); setOrders([]); setLoadError(adminAccess ? `Firestore 조회에 실패했습니다: ${error?.message || '알 수 없는 오류'}` : `공개 분석 결과를 불러오지 못했습니다: ${error?.message || '알 수 없는 오류'}`); }
    finally {
      if (!adminAccess) {
        publicRefreshInFlightRef.current = false;
        lastPublicRefreshAtRef.current = Date.now();
      }
      setLoading(false);
      setHasLoaded(true);
    }
  };

  const enterAdminAnalysis = () => {
    if (!isAdmin) return;
    setAdminViewActive(true);
    setWorkspaceView('console');
    setMobilePane('list');
    setSettingsStatus('관리자 분석 화면을 불러오는 중입니다.');
    void refreshSignals(true);
    void refreshPrivatePaperAccount(user);
  };

  const exitAdminAnalysis = () => {
    setAdminViewActive(false);
    setWorkspaceView('console');
    setMobilePane('list');
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
    setFiltersOpen(false);
    setMobilePane('detail');
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
          setSettingsStatus('관리자 권한이 없어 공개 분석 결과만 표시합니다.');
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
    <main className={`terminal-shell ${themeClassMap[theme] || themeClassMap.light} mobile-pane-${mobilePane}`}>
      <aside className={`watchlist ${mobilePane === 'detail' ? 'mobile-pane-hidden' : ''}`}>
        <div className="brand-block"><span>{BRAND_FULL}</span><h1>{BRAND_SHORT}</h1><p>종목별 기술지표가 무엇을 보여주는지 쉽게 살펴보세요.</p></div>
        <div className="watchlist-meta"><span>{displayedSignals.length} / {adminViewActive ? summary.observed : publicTotalCount || summary.observed} 종목</span><button type="button" className="icon-button" onClick={() => refreshSignals(adminViewActive)} aria-label="데이터 새로고침"><RefreshCw size={16} className={loading ? 'spin' : ''} /></button></div>
        <div className="watch-filters" aria-label="종목 필터">

          <button type="button" className="filter-toggle" onClick={() => setFiltersOpen((open) => !open)} aria-expanded={filtersOpen} aria-controls="watch-filter-controls">
            <span><SlidersHorizontal size={15} /> {filtersOpen ? '필터·정렬 접기' : '필터·정렬 펼치기'}</span><ChevronDown size={16} className={filtersOpen ? 'open' : ''} />
          </button>
          {filtersOpen && <div id="watch-filter-controls" className="filter-controls">
          <input type="search" value={searchText} onChange={(event) => { setSearchText(event.target.value); setSelectedId(''); }} placeholder="종목명 또는 코드 검색" />
            <div className="filter-grid">
              <select value={marketFilter} onChange={(event) => { setMarketFilter(event.target.value); setSelectedId(''); }} aria-label="시장 필터"><option value="ALL">전체 시장</option><option value="KR">KR</option></select>
              <select value={labelFilter} onChange={(event) => { setLabelFilter(event.target.value); setSelectedId(''); }} aria-label="조건 필터">
                <option value="ALL">전체 조건</option>
                {adminViewActive ? <>
                  <option value="STRONG_BUY">강한 기술 조건</option><option value="BUY_CANDIDATE">관심 조건 충족</option><option value="WATCH">관찰</option><option value="HOLD">중립</option><option value="DEFENSIVE">방어 신호</option><option value="AVOID">리스크 신호</option>
                </> : <>
                  <option value="HIGH_ALIGNMENT">조건 일치 높음</option><option value="MODERATE_ALIGNMENT">조건 일치 보통</option><option value="LIMITED_ALIGNMENT">조건 일치 제한적</option><option value="CAUTION">주의 조건 우세</option>
                </>}
              </select>
            </div>
            <div className="sort-heading"><span>정렬 기준</span><strong style={{ color: activeSort.color }}>{activeSort.category}</strong></div>
            <div className="sort-direction" aria-label="정렬 방향"><button type="button" className={sortDirection === 'desc' ? 'active' : ''} onClick={() => { setSortDirection('desc'); setSelectedId(''); }}>높은 순</button><button type="button" className={sortDirection === 'asc' ? 'active' : ''} onClick={() => { setSortDirection('asc'); setSelectedId(''); }}>낮은 순</button></div>
            <select className="sort-select" value={sortMode} onChange={(event) => { setSortMode(event.target.value); setSelectedId(''); }} aria-label="종목 정렬">{(adminViewActive ? sortGroups : publicSortGroups).map((group) => <optgroup key={group.label} label={group.label}>{group.options.map((option) => <option key={option.key} value={option.key}>{option.category} · {option.label}</option>)}</optgroup>)}</select>
            <select value={theme} onChange={(event) => setTheme(event.target.value)} aria-label="테마">{themeOptions.map((option) => <option key={option.key} value={option.key}>{option.label} 테마</option>)}</select>
          </div>}
        </div>
        <div className="market-summary"><div><span>조건 강함</span><strong>{summary.strong}</strong></div><div><span>주의 신호</span><strong>{summary.defensive}</strong></div><div><span>{adminViewActive ? '실험 큐' : '표시 종목'}</span><strong>{adminViewActive ? summary.staged : displayedSignals.length}</strong></div></div>
        <div className="signal-stack">
          {filteredSignals.length === 0 && <div className="empty-watch">조건에 맞는 종목이 없습니다.</div>}
          {displayedSignals.map((signal) => <button key={signal.id} type="button" className={`watch-row ${selected?.id === signal.id ? 'selected' : ''}`} aria-current={selected?.id === signal.id ? 'true' : undefined} onClick={() => selectSignal(signal)}><span className="watch-main"><strong>{signal.name}</strong><span>{signal.market}:{signal.code} · {signal.label}</span></span><span className={`watch-score score-${signal.riskState}`}>{formatNumber(signal.confidence, 1)}</span></button>)}
          {hasMorePublic && <button type="button" className="auth-button ghost" onClick={loadMorePublic} disabled={loading} style={{ margin: '12px', justifyContent: 'center' }}>{loading ? '불러오는 중...' : '다음 30개 불러오기'}</button>}
        </div>
      </aside>

      <section className={`chart-column ${mobilePane === 'list' ? 'mobile-pane-hidden' : ''}`}>
        <div className="mobile-detail-bar">
          <button type="button" onClick={() => setMobilePane('list')} aria-label="종목 목록으로 돌아가기">← 목록</button>
          {selected && <span><strong>{selected.name}</strong><small>{selected.market}:{selected.code}</small></span>}
        </div>
        <header className="desk-topbar">
          <div><p>{loadError || (adminViewActive ? '관리자 분석 화면 · 상세 지표 확인' : publicLiveDataApproved ? '금융위원회 공공데이터 기반 · 최근 거래일 분석' : '공개 분석을 준비 중입니다')}</p><h2>{BRAND_SHORT}</h2>{!user && <button type="button" className="topbar-disclaimer" onClick={() => setShowDisclaimerModal(true)}>기술지표 학습 정보이며 투자 권유가 아닙니다. (자세히)</button>}</div>
          <div className="topbar-actions">
            <a className="auth-button ghost research-learning-link" href="/">지표 학습</a>
            <div className="workspace-tabs" aria-label="작업 화면"><button type="button" className={workspaceView === 'console' ? 'active' : ''} onClick={() => setWorkspaceView('console')}>종목 분석</button>{adminViewActive && <button type="button" className={workspaceView === 'executions' ? 'active' : ''} onClick={() => setWorkspaceView('executions')}>모의투자 성과</button>}</div>
            {adminViewActive ? <div className="topbar-pills"><span><CandlestickChart size={14} /> 캔들</span><span><Cloud size={14} /> 이평·구름</span><span><Gauge size={14} /> RSI</span></div> : <div className="topbar-pills"><span><Shield size={14} /> 분석 근거와 해설</span></div>}
            <div className="auth-block"><span>{user ? (settingsStatus || (adminChecking ? '관리자 권한 확인 중...' : adminViewActive ? '관리자 분석 화면 · 상세 지표 확인 중' : isAdmin ? '관리자 권한 확인됨 · 공개 분석 화면 사용 중' : '로그인됨 · 공개 분석 화면 사용 중')) : '로그인 없이 공개 분석을 볼 수 있습니다.'}</span><div className="auth-buttons">{isAdmin && <button type="button" className="auth-button ghost" onClick={adminViewActive ? exitAdminAnalysis : enterAdminAnalysis}><span>{adminViewActive ? '공개 분석 보기' : '관리자 분석 보기'}</span></button>}<button type="button" className="auth-button" onClick={user ? () => signOut(auth) : loginWithGoogle}>{user ? <LogOut size={14} /> : <LogIn size={14} />}<span>{user ? '로그아웃' : '구글 로그인'}</span></button></div></div>
          </div>
        </header>
        <section className="notice-panel"><Shield size={18} /><p>최근 거래일의 확정 일봉을 바탕으로 기술지표가 어떤 상태인지 설명하는 학습 서비스입니다. 화면의 점수와 해설은 기술지표를 공부하기 위한 참고자료이며, 특정 종목의 거래나 수익을 보장하지 않습니다.</p></section>
        <section className="notice-panel data-rights-panel"><AlertTriangle size={18} /><p>{adminViewActive ? '관리자 화면에서는 금융위원회 공공데이터로 계산한 차트와 상세 지표를 확인할 수 있습니다.' : publicLiveDataApproved ? '금융위원회 공공데이터에서 제공하는 최근 거래일의 확정 일봉을 분석해 종목별 종합점수와 지표 해설을 보여드립니다. 현재가, 가격 차트와 지표 원수치는 공개하지 않습니다.' : '공개 분석을 준비하고 있습니다. 데이터 확인이 끝나면 종목별 점수와 지표 해설을 보여드립니다.'}</p></section>
        {workspaceView === 'console' && <>{adminViewActive ? selected ? <><div className="analysis-layout"><TechnicalChart stock={selected} loading={detailLoadingId === selected?.id} /><ScoreDock stock={selected} /></div><PublicAnalysisPanel stock={selected} compact={isCompactLayout} /></> : <PublicAnalysisUnavailable message="관리자 분석 목록을 아직 불러오지 못했습니다. 잠시 후 새로고침해 주세요." /> : selected ? <PublicAnalysisPanel stock={selected} compact={isCompactLayout} /> : <PublicAnalysisUnavailable message={publicLiveDataApproved ? loadError : '공개 분석 데이터를 준비하고 있습니다. 잠시 후 다시 확인해 주세요.'} />}{publicAnalysisAdReady && <AdSenseSlot title="분석 본문 광고" placement="analysis" />}</>}
        {workspaceView === 'executions' && adminViewActive && <div className="execution-page"><PortfolioSnapshot portfolio={portfolio} onRefresh={requestPaperAccountRefresh} refreshBusy={paperRefreshBusy} refreshMessage={paperAccountMessage} canRefresh={Boolean(adminViewActive && firebaseReady && db)} /><PrivatePerformancePanel performance={privatePerformance} /><TradeLogPanel logs={tradeLogs} /><OrdersPanel orders={orders} /></div>}

      </section>
      {showDisclaimerModal && <DisclaimerModal onClose={() => setShowDisclaimerModal(false)} />}
    {!user && <ComplianceDock />}
    </main>
  );
}
