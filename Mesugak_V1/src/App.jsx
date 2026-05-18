import React, { useState, useEffect, useRef } from 'react';
import { collection, getDocs, query, doc, getDoc, setDoc, orderBy, limit } from "firebase/firestore";
import { db, auth, googleProvider } from "./firebase"; 
import { signInWithEmailAndPassword, createUserWithEmailAndPassword, signOut, onAuthStateChanged, signInWithPopup, setPersistence, browserSessionPersistence } from "firebase/auth"; 

import {
  ComposedChart, Line, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, Brush
} from 'recharts';
import {
  TrendingUp, Activity, AlertCircle, ArrowRightCircle, ExternalLink, Info, Settings,
  Eye, EyeOff, Check, Search, Lock, LogOut, Wallet, RefreshCw, FileText
} from 'lucide-react';

// Landing page
import LandingPage from './LandingPage'; 

// Auth error messages
const getErrorMessage = (code) => {
    switch (code) {
        case 'auth/user-not-found':
        case 'auth/invalid-email':
            return '이메일 또는 비밀번호가 올바르지 않습니다.';
        case 'auth/wrong-password':
            return '비밀번호가 일치하지 않습니다.';
        case 'auth/email-already-in-use':
            return '이미 사용 중인 이메일입니다.';
        case 'auth/weak-password':
            return '비밀번호는 6자 이상이어야 합니다.';
        case 'auth/network-request-failed':
            return '네트워크 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.';
        case 'auth/too-many-requests':
            return '요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.';
        case 'auth/popup-closed-by-user':
            return '로그인 팝업이 닫혔습니다.';
        default:
            return '로그인 중 오류가 발생했습니다. (' + code + ')';
    }
};

// =================================================================
// [1] Shared helpers
// =================================================================
const getExternalLink = (id) => {
  if (/^\d+$/.test(id)) return `https://finance.naver.com/item/main.naver?code=${id}`;
  return `https://finance.yahoo.com/quote/${id}`;
};

const CustomTooltip = ({ active, payload, label, market }) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    // Ignore tooltip rows without OHLC data.
    if (!data || data.open === undefined) return null;

    const isUS = market === 'US';
    const currency = isUS ? '$' : '';
    const unit = isUS ? '' : '원';

    return (
      <div className="bg-white p-3 border border-gray-200 shadow-xl rounded-lg text-xs z-50 min-w-[180px]">
        <p className="font-bold text-gray-800 mb-2 border-b pb-1">{label}</p>
        <div className="grid grid-cols-2 gap-x-4 gap-y-1 mb-2">
          <p className="text-gray-500">시가:</p> <p className="text-right font-medium">{currency}{data.open.toLocaleString()}{unit}</p>
          <p className="text-gray-500">고가:</p> <p className="text-right font-medium text-red-500">{currency}{data.high.toLocaleString()}{unit}</p>
          <p className="text-gray-500">저가:</p> <p className="text-right font-medium text-blue-500">{currency}{data.low.toLocaleString()}{unit}</p>
          <p className="text-gray-800 font-bold">종가:</p> <p className="text-right font-bold">{currency}{data.close.toLocaleString()}{unit}</p>
        </div>
        <div className="border-t pt-2 space-y-1">
          <p className="flex justify-between text-gray-600"><span>상단 밴드</span> <span>{currency}{data.upper?.toLocaleString()}{unit}</span></p>
          <p className="flex justify-between text-orange-600 font-bold"><span>20일 이동평균</span> <span>{currency}{data.ma20?.toLocaleString()}{unit}</span></p>
          <p className="flex justify-between text-gray-600"><span>하단 밴드</span> <span>{currency}{data.lower?.toLocaleString()}{unit}</span></p>
          <p className="flex justify-between text-blue-600 mt-1 font-bold"><span>밴드폭</span> <span>{(data.bandwidth * 100).toFixed(2)}%</span></p>
        </div>
      </div>
    );
  }
  return null;
};

// =================================================================
// [2] Sidebar item
// =================================================================
const getStatusColor = (status) => {
  if (!status) return 'text-gray-500';
  const text = String(status);
  if (/매도|SELL|sell/i.test(text)) return 'text-red-600 font-bold';
  if (/관망|대기|주의|BUY|buy|watch/i.test(text)) return 'text-yellow-600 font-bold';
  if (/squeeze|응축|스퀴즈/i.test(text)) return 'text-violet-600 font-bold';
  if (/normal|일반/i.test(text)) return 'text-emerald-600 font-bold';
  if (/suspended|거래정지|suspend/i.test(text)) return 'text-slate-500 font-bold';
  if (/N\/A|데이터 없음|없음|insufficient/i.test(text)) {
    return 'text-slate-400 font-bold bg-slate-100 px-1 rounded';
  }
  return 'text-gray-500';
};

const normalizeStatusText = (status, type) => {
  const raw = String(status ?? '').trim();
  // Mojibake/깨진 문자열이면 타입 기반으로 안전한 라벨 사용
  if (!raw || /(\?\?|�|醫|嶺|β돦)/.test(raw)) {
    if (type === 'sell_signal') return '매도 신호';
    if (type === 'buy_signal') return '매수 후보';
    if (type === 'squeeze') return '스퀴즈 구간';
    if (type === 'suspended') return '거래정지';
    return '일반';
  }
  return raw;
};

const getStockMarket = (stock, fallbackMarket = null) => {
  const stockId = String(stock?.id ?? '').trim().toUpperCase();
  const rawId = stockId.replace(/^KR_|^US_/, '');

  if (stockId.startsWith('KR_')) return 'KR';
  if (stockId.startsWith('US_')) return 'US';
  if (/^\d{4,6}$/.test(rawId)) return 'KR';
  if (/^[A-Z][A-Z0-9.\-]*$/.test(rawId)) return 'US';

  const explicitMarket = String(stock?.market ?? '').toUpperCase();
  if (explicitMarket === 'KR' || explicitMarket === 'US') return explicitMarket;

  if (fallbackMarket === 'KR' || fallbackMarket === 'US') return fallbackMarket;

  return null;
};

const normalizeStock = (stock, fallbackMarket = null) => {
  const resolvedMarket = getStockMarket(stock, fallbackMarket);
  if (!resolvedMarket) return null;

  return {
    ...stock,
    resolvedMarket,
  };
};

const SidebarItem = React.memo(({ stock, isSelected, onClick, isLoggedIn }) => {
  // Non-admin users should not see sell-signal details.
  const isHidden = !isLoggedIn && stock.type === 'sell_signal';
  
  const displayType = isHidden ? 'squeeze' : stock.type;
  const displayStatus = isHidden ? '로그인 후 확인 가능' : normalizeStatusText(stock.status, stock.type);

  return (
    <div 
      onClick={() => onClick(stock)}
      className={`p-4 border-b border-gray-100 cursor-pointer hover:bg-slate-50 transition-all ${isSelected ? 'bg-slate-100 border-l-4 border-slate-800 pl-3' : 'border-l-4 border-transparent'}`}
    >
      <div className="flex justify-between items-start mb-1">
        <div>
          <span className="font-bold text-lg mr-2">{stock.name}</span>
          <span className="text-xs text-gray-400">{stock.id.replace('KR_', '').replace('US_', '')}</span>
        </div>
        <span
          className={`text-[10px] px-2 py-0.5 rounded-full border ${
            /매도|SELL|sell/i.test(String(displayStatus))
              ? 'bg-red-50 border-red-200 text-red-600'
              : /관망|대기|주의|watch|buy|BUY/i.test(String(displayStatus))
                ? 'bg-yellow-50 border-yellow-200 text-yellow-600'
                : /squeeze|응축|스퀴즈/i.test(String(displayStatus))
                  ? 'bg-violet-50 border-violet-200 text-violet-600'
                  : /normal|일반/i.test(String(displayStatus))
                    ? 'bg-emerald-50 border-emerald-200 text-emerald-600'
                    : /suspended|거래정지|suspend/i.test(String(displayStatus))
                      ? 'bg-slate-100 border-slate-300 text-slate-500'
                      : 'bg-gray-50 border-gray-200 text-gray-500'
          }`}
        >
          {displayType.toUpperCase()}
          {isHidden && <span className="ml-1 text-[8px] opacity-50">?</span>} 
        </span>
      </div>
      <div className="flex justify-between items-center mt-2">
        <span className={`text-xs font-medium ${getStatusColor(displayStatus)}`}>{displayStatus}</span>
        <div className="text-right">
            <span className="block text-sm font-bold">{stock.currentPrice.toLocaleString()}원</span>
            <span className="text-xs text-gray-400">B/W: {(stock.bandwidth * 100).toFixed(2)}%</span>
        </div>
      </div>
    </div>
  );
}, (prev, next) => {
  return prev.isSelected === next.isSelected && prev.stock === next.stock && prev.isLoggedIn === next.isLoggedIn;
});

// =================================================================
// [3] Ads and chart defaults
// =================================================================

// Ad placeholder
const AdBanner = ({ position, className }) => {
  return (
    <div className={`bg-gray-200 flex items-center justify-center text-gray-400 text-xs border border-gray-300 ${className}`}>
      {position} AD AREA
    </div>
  );
};

// Chart rendering defaults
const DEFAULT_CHART_CONFIG = {
  close: { show: true, color: '#334155', width: 2 },
  ma20: { show: true, color: '#f59e0b', width: 1.5 },
  upper: { show: true, color: '#64748b', width: 2 },
  lower: { show: true, color: '#64748b', width: 2 },
  rsi: { show: true, color: '#0f766e', width: 1.5 },
  rsiSignal: { show: true, color: '#f97316', width: 1.5 },
  candle: { show: true, upColor: '#16a34a', downColor: '#dc2626', wickWidth: 1, bodySize: 8 },
  highLow: { show: true },
  yAxis: { show: true, format: 'simple' }
};
const DEFAULT_PATTERNS = ['squeeze', 'buy_signal', 'sell_signal', 'normal', 'suspended'];
const SORT_PREFERENCE = {
  bandwidth: 'asc',  // 좁을수록 우선
  marcap: 'desc',    // 클수록 우선
  percentB: 'desc',  // 클수록 우선
  volume: 'desc',    // 클수록 우선
};

const getPreferredSortDirection = (key) => SORT_PREFERENCE[key] || 'asc';

const DEFAULT_SORT = { key: 'bandwidth', direction: getPreferredSortDirection('bandwidth') };
const DEFAULT_MARKET = 'KR';
const DEFAULT_ZOOM = 'ALL';

export default function BollingerScanner() {
  const [selectedStock, setSelectedStock] = useState(null);
  const [stocks, setStocks] = useState([]);
  const detailRequestRef = useRef(0);
  const [loading, setLoading] = useState(false);

  // Auth/user state
  const [user, setUser] = useState(null);
  const [userRole, setUserRole] = useState(null); // 'member', 'user', 'admin'
  // derived state for convenience
  const isAdmin = userRole === 'admin';
  const isApproved = ['user', 'admin'].includes(userRole);
  
  const [showLoginModal, setShowLoginModal] = useState(false);
  const [isSignup, setIsSignup] = useState(false);
  const [loginEmail, setLoginEmail] = useState("");
  const [loginPassword, setLoginPassword] = useState("");

  // Chart settings
  const [showSettings, setShowSettings] = useState(false);
  const [chartConfig, setChartConfig] = useState(DEFAULT_CHART_CONFIG);
  const [priceView, setPriceView] = useState('candle'); // 'candle' | 'line'

  // Chart range and prepared data
  const [zoomRange, setZoomRange] = useState(DEFAULT_ZOOM); // '1M', '3M', '6M', 'ALL'
  const [visualData, setVisualData] = useState([]);

  // Filters and sorting
  const [selectedMarket, setSelectedMarket] = useState(DEFAULT_MARKET); // 'KR' | 'US'
  const [selectedPatterns, setSelectedPatterns] = useState(DEFAULT_PATTERNS);
  const [sortConfig, setSortConfig] = useState(DEFAULT_SORT);

  // Y-axis display state
  const [yDomain, setYDomain] = useState(['auto', 'auto']);
  const [yTicks, setYTicks] = useState([]);

  // Chart layout/runtime state
  const [chartReady, setChartReady] = useState(false);
  const [botAccount, setBotAccount] = useState(null);
  const [botTradeLogs, setBotTradeLogs] = useState([]);
  const [botLoading, setBotLoading] = useState(false);
  const [botPermissionDenied, setBotPermissionDenied] = useState(false);
  const [adminView, setAdminView] = useState('scanner');
  const candleDebugLoggedRef = useRef(false);
  const chartHostRef = useRef(null);
  const [chartWidth, setChartWidth] = useState(0);

  // 선택 종목이나 확대 범위가 바뀌면 차트 데이터를 다시 준비합니다.
  useEffect(() => {
    console.log("Selected Stock Updated:", selectedStock);
    setChartReady(false);
    
    if (selectedStock?.history) {
      console.log("History found, applying zoom...", selectedStock.history.length);
      applyZoom(selectedStock.history, zoomRange);
      // 차트 컨테이너의 폭이 잡힌 뒤 렌더링되도록 잠시 대기합니다.
      setTimeout(() => {
          console.log("Setting chartReady to true");
          setChartReady(true);
      }, 200); 
    } else {
      console.warn("No history found for selected stock");
      setVisualData([]); // 히스토리가 없으면 빈 차트로 처리
    }
  }, [selectedStock, zoomRange]);



  // 현재 보이는 데이터 기준으로 Y축 범위와 눈금을 다시 계산합니다.
  useEffect(() => {
    if (!visualData || visualData.length === 0) return;

    let min = Infinity;
    let max = -Infinity;

    visualData.forEach(d => {
      // 종가, 고가/저가, 밴드 값을 모두 포함해 표시 범위를 계산합니다.
      const values = [d.close, d.high, d.low, d.upper, d.lower, d.ma20];
      values.forEach(v => {
        if (v !== undefined && v !== null && !isNaN(v)) {
            if (v < min) min = v;
            if (v > max) max = v;
        }
      });
    });

    if (min === Infinity || max === -Infinity) {
        setYTicks([]);
        setYDomain(['auto', 'auto']);
        return;
    }

    // 최소/최대값에 약간의 여유를 두고 보기 좋은 눈금을 만듭니다.
    const padding = (max - min) * 0.05;
    const roughMin = min - padding;
    const roughMax = max + padding;

    const ticks = calculateNiceTicks(roughMin, roughMax, 8);
    setYTicks(ticks);
    setYDomain([ticks[0], ticks[ticks.length - 1]]);
  }, [visualData]);

  // 보기 좋은 간격의 눈금을 만드는 유틸리티입니다.
  const calculateNiceTicks = (min, max, tickCount) => {
    const range = niceNum(max - min, false);
    const tickSpacing = niceNum(range / (tickCount - 1), true);
    const niceMin = Math.floor(min / tickSpacing) * tickSpacing;
    const niceMax = Math.ceil(max / tickSpacing) * tickSpacing;

    const ticks = [];
    for (let t = niceMin; t <= niceMax + 0.5 * tickSpacing; t += tickSpacing) {
        ticks.push(t);
    }
    return ticks;
  };

  const niceNum = (range, round) => {
    const exponent = Math.floor(Math.log10(range));
    const fraction = range / Math.pow(10, exponent);
    let niceFraction;

    if (round) {
        if (fraction < 1.5) niceFraction = 1;
        else if (fraction < 3) niceFraction = 2;
        else if (fraction < 7) niceFraction = 5;
        else niceFraction = 10;
    } else {
        if (fraction <= 1) niceFraction = 1;
        else if (fraction <= 2) niceFraction = 2;
        else if (fraction <= 5) niceFraction = 5;
        else niceFraction = 10;
    }
    return niceFraction * Math.pow(10, exponent);
  };

  // Y축 라벨 포맷터
  const formatYAxis = (value) => {
    if (chartConfig.yAxis.format === 'full') {
        const isUS = selectedStock?.market === 'US';
        return isUS ? `$${value.toLocaleString()}` : value.toLocaleString();
    }
    
    // 미국 주식은 축약 표시에서도 달러 기호를 유지합니다.
    if (selectedStock?.market === 'US') {
        return `$${value.toLocaleString()}`;
    }

    // 한국 주식은 축약 표시에서 만원 단위를 사용합니다.
    if (value >= 10000) {
        return `${(value / 10000).toFixed(2)}만`;
    }
    return value.toLocaleString();
  };

  const applyZoom = (data, range) => {
    if (!data || data.length === 0) {
        setVisualData([]);
        return;
    }
    if (range === 'ALL') {
      setVisualData(data);
      return;
    }
    
    // 선택된 기간만 남기도록 마지막 날짜 기준으로 필터링합니다.
    
    const lastDate = new Date(data[data.length - 1].date);
    let subtractDays = 0;
    if (range === '1M') subtractDays = 30;
    else if (range === '3M') subtractDays = 90;
    else if (range === '6M') subtractDays = 180;

    const startDate = new Date(lastDate);
    startDate.setDate(lastDate.getDate() - subtractDays);

    const filtered = data.filter(d => new Date(d.date) >= startDate);
    setVisualData(filtered);
  };
  
                         {chartConfig.yAxis.show && (
                            <YAxis 
                                domain={yDomain} 
                                tickCount={8} // 눈금 수 고정
                                tick={{fontSize: 11, fill: '#94a3b8'}} 
                                tickFormatter={formatYAxis} 
                                axisLine={false} tickLine={false} width={60} 
                            />
                         )}
  
  const toggleConfig = (key) => {
      setChartConfig(prev => ({ ...prev, [key]: { ...prev[key], show: !prev[key].show } }));
  };

  const updateConfig = (key, field, value) => {
    setChartConfig(prev => ({ ...prev, [key]: { ...prev[key], [field]: value } }));
  };

  const candleData = React.useMemo(() => {
    const rows = (visualData || []).map((d) => {
      const open = Number(d.open);
      const close = Number(d.close);
      const high = Number(d.high);
      const low = Number(d.low);
      if ([open, close, high, low].some((v) => Number.isNaN(v))) return null;
      const up = close >= open;
      return {
        ...d,
        candleUp: up,
        candleBase: Math.min(open, close),
        candleBody: Math.max(Math.abs(close - open), 0.1),
        wickBase: low,
        wickBody: Math.max(high - low, 0.1),
      };
    }).filter(Boolean);

    if (!candleDebugLoggedRef.current && rows.length > 0) {
      candleDebugLoggedRef.current = true;
      console.log('candle-data-sample', rows[0]);
    }
    return rows;
  }, [visualData]);

  const rsiData = React.useMemo(() => {
    const period = 14;
    const signalPeriod = 9;
    const rows = (visualData || []).map((d) => ({
      ...d,
      rsi: null,
      rsiSignal: null,
      rsiUpper: 70,
      rsiMid: 50,
      rsiLower: 30,
    }));

    if (rows.length <= period) return rows;

    let gains = 0;
    let losses = 0;

    for (let i = 1; i <= period; i += 1) {
      const change = Number(rows[i].close) - Number(rows[i - 1].close);
      if (Number.isNaN(change)) continue;
      if (change >= 0) gains += change;
      else losses += Math.abs(change);
    }

    let avgGain = gains / period;
    let avgLoss = losses / period;
    rows[period].rsi = avgLoss === 0 ? 100 : 100 - (100 / (1 + (avgGain / avgLoss)));

    for (let i = period + 1; i < rows.length; i += 1) {
      const change = Number(rows[i].close) - Number(rows[i - 1].close);
      const gain = Number.isNaN(change) ? 0 : Math.max(change, 0);
      const loss = Number.isNaN(change) ? 0 : Math.max(-change, 0);

      avgGain = ((avgGain * (period - 1)) + gain) / period;
      avgLoss = ((avgLoss * (period - 1)) + loss) / period;

      rows[i].rsi = avgLoss === 0 ? 100 : 100 - (100 / (1 + (avgGain / avgLoss)));
    }

    for (let i = 0; i < rows.length; i += 1) {
      if (i < period + signalPeriod - 1) continue;

      const window = rows
        .slice(i - signalPeriod + 1, i + 1)
        .map((row) => row.rsi)
        .filter((value) => value !== null && value !== undefined && !Number.isNaN(value));

      if (window.length === signalPeriod) {
        rows[i].rsiSignal = window.reduce((sum, value) => sum + value, 0) / signalPeriod;
      }
    }

    return rows;
  }, [visualData]);

  const formatMoney = (value) => {
    if (value === undefined || value === null || isNaN(value)) return '-';
    return Number(value).toLocaleString();
  };

  const formatLogTime = (value) => {
    if (!value) return '-';
    if (value?.toDate) return value.toDate().toLocaleString();
    const d = new Date(value);
    return isNaN(d.getTime()) ? '-' : d.toLocaleString();
  };


  const fetchAdminBotData = async () => {
    if (!user || !isAdmin || botPermissionDenied) return;

    try {
      setBotLoading(true);
      const accountSnap = await getDoc(doc(db, 'bot_account_snapshot', 'latest'));
      if (accountSnap.exists()) {
        setBotAccount(accountSnap.data());
      } else {
        setBotAccount(null);
      }

      const logsQ = query(collection(db, 'bot_trade_logs'), orderBy('createdAt', 'desc'), limit(100));
      const logsSnap = await getDocs(logsQ);
      const logs = [];
      logsSnap.forEach((d) => logs.push({ id: d.id, ...d.data() }));
      setBotTradeLogs(logs);
    } catch (e) {
      if (e?.code === 'permission-denied') {
        setBotAccount(null);
        setBotTradeLogs([]);
        setBotPermissionDenied(true);
        console.warn('봇 관리자 데이터 조회 권한이 없습니다.');
      } else {
        console.error('Error loading bot admin data:', e);
      }
    } finally {
      setBotLoading(false);
    }
  };

  useEffect(() => {
    if (!user || !isAdmin || botPermissionDenied) {
      setBotAccount(null);
      setBotTradeLogs([]);
      return;
    }

    fetchAdminBotData();
    const interval = setInterval(fetchAdminBotData, 15000);
    return () => clearInterval(interval);
  }, [user, isAdmin, botPermissionDenied]);

  useEffect(() => {
    const el = chartHostRef.current;
    if (!el) return;

    const update = () => setChartWidth(Math.max(320, Math.floor(el.clientWidth || 0) - 8));
    update();

    let ro;
    if (typeof ResizeObserver !== 'undefined') {
      ro = new ResizeObserver(update);
      ro.observe(el);
    }
    window.addEventListener('resize', update);
    return () => {
      window.removeEventListener('resize', update);
      if (ro) ro.disconnect();
    };
  }, [selectedStock, showSettings]);


  // 인증 상태가 바뀌면 사용자 권한과 저장된 설정을 불러옵니다.
  useEffect(() => {
      const unsubscribe = onAuthStateChanged(auth, async (currentUser) => {
          setUser(currentUser);
          if (currentUser) {
              console.log("Logged in:", currentUser.email);
              // Firestore에서 역할과 저장된 설정을 조회합니다.
              try {
                  // 1. 기본 사용자 문서: users/{uid}
                  const userDocRef = doc(db, "users", currentUser.uid);
                  const userDocSnap = await getDoc(userDocRef);
                  
                  if (userDocSnap.exists()) {
                      const data = userDocSnap.data();
                      if (data.role) setUserRole(data.role || 'member');
                      setBotPermissionDenied(false);
                  } else {
                      // 첫 로그인 사용자면 기본 프로필을 생성합니다.
                      await setDoc(userDocRef, {
                          email: currentUser.email,
                          role: 'member',
                          createdAt: new Date()
                      });
                      setUserRole('member');
                      setBotPermissionDenied(false);
                  }

                  // 2. 사용자별 스캐너 설정
                  const settingsDocRef = doc(db, "users", currentUser.uid, "settings", "mesugak");
                  const settingsDocSnap = await getDoc(settingsDocRef);
                  if (settingsDocSnap.exists()) {
                      const data = settingsDocSnap.data();
                      if (data.selectedMarket) setSelectedMarket(data.selectedMarket);
                      if (data.selectedPatterns) setSelectedPatterns(data.selectedPatterns);
                      if (data.sortConfig) setSortConfig(data.sortConfig);
                      if (data.chartConfig) {
                        setChartConfig(prev => ({
                          ...DEFAULT_CHART_CONFIG,
                          ...prev,
                          ...data.chartConfig,
                          close: { ...DEFAULT_CHART_CONFIG.close, ...(data.chartConfig.close || {}) },
                          ma20: { ...DEFAULT_CHART_CONFIG.ma20, ...(data.chartConfig.ma20 || {}) },
                          upper: { ...DEFAULT_CHART_CONFIG.upper, ...(data.chartConfig.upper || {}) },
                          lower: { ...DEFAULT_CHART_CONFIG.lower, ...(data.chartConfig.lower || {}) },
                          rsi: { ...DEFAULT_CHART_CONFIG.rsi, ...(data.chartConfig.rsi || {}) },
                          rsiSignal: { ...DEFAULT_CHART_CONFIG.rsiSignal, ...(data.chartConfig.rsiSignal || {}) },
                          candle: { ...DEFAULT_CHART_CONFIG.candle, ...(data.chartConfig.candle || {}) },
                          highLow: { ...DEFAULT_CHART_CONFIG.highLow, ...(data.chartConfig.highLow || {}) },
                          yAxis: { ...DEFAULT_CHART_CONFIG.yAxis, ...(data.chartConfig.yAxis || {}) },
                        }));
                      }
                      if (data.zoomRange) setZoomRange(data.zoomRange);
                      if (data.priceView) setPriceView(data.priceView);
                      console.log("Settings loaded from Firestore");
                  }
              } catch (e) {
                  console.error("Error loading user data:", e);
              }

          } else {
              console.log("Logged out, resetting settings to defaults");
              setUserRole(null);
              setBotPermissionDenied(false);
              setChartConfig(DEFAULT_CHART_CONFIG);
              setSelectedPatterns(DEFAULT_PATTERNS);
              setSortConfig(DEFAULT_SORT);
              setSelectedMarket(DEFAULT_MARKET);
              setZoomRange(DEFAULT_ZOOM);
          }
      });
      return () => unsubscribe();
  }, []);

  // 쓰기 횟수를 줄이기 위해 설정 저장은 짧게 디바운스합니다.
  useEffect(() => {
      if (!user) return;
      
      const saveSettings = async () => {
          try {
             await setDoc(doc(db, "users", user.uid, "settings", "mesugak"), {
                 selectedMarket,
                 selectedPatterns,
                 sortConfig,
                 chartConfig,
                 zoomRange,
                 priceView,
                 updatedAt: new Date()
             }, { merge: true });
             // console.log("Settings saved");
          } catch (e) {
             console.error("Error saving settings:", e);
          }
      };
      
      const timeout = setTimeout(saveSettings, 500);
      return () => clearTimeout(timeout);
  }, [user, selectedMarket, selectedPatterns, sortConfig, chartConfig, zoomRange, priceView]);

  // 이메일 로그인/회원가입 제출 처리
  const handleAuthSubmit = async (e) => {
      e.preventDefault();
      try {
          if (isSignup) {
              // 브라우저 세션이 끝나면 인증도 종료되도록 세션 지속성을 사용합니다.
              await setPersistence(auth, browserSessionPersistence);
              const userCredential = await createUserWithEmailAndPassword(auth, loginEmail, loginPassword);
              // 신규 사용자는 기본적으로 member 권한입니다.
              await setDoc(doc(db, "users", userCredential.user.uid), {
                  email: loginEmail,
                  role: 'member',
                  createdAt: new Date()
              });
              alert("회원가입이 완료되었습니다. 로그인해 주세요.");
          } else {
              // 이메일 로그인도 동일하게 세션 지속성을 사용합니다.
              await setPersistence(auth, browserSessionPersistence);
              await signInWithEmailAndPassword(auth, loginEmail, loginPassword);
          }
          setShowLoginModal(false);
          setLoginEmail("");
          setLoginPassword("");
      } catch (error) {
          console.error(error);
          alert(getErrorMessage(error.code));
      }
  };

  // Google 로그인 처리
  const handleGoogleLogin = async () => {
      try {
          await setPersistence(auth, browserSessionPersistence);
          const result = await signInWithPopup(auth, googleProvider);
          const user = result.user;
          
          // Google 첫 로그인 시 사용자 문서를 생성합니다.
          const userDocRef = doc(db, "users", user.uid);
          const userDocSnap = await getDoc(userDocRef);
          
          if (!userDocSnap.exists()) {
              await setDoc(userDocRef, {
                  email: user.email,
                  role: 'member',
                  createdAt: new Date(),
                  provider: 'google'
              });
          }
          
          setShowLoginModal(false);
      } catch (error) {
          console.error(error);
          alert(getErrorMessage(error.code));
      }
  };

  const handleLogout = async () => {
      if (window.confirm("로그아웃 하시겠습니까?")) {
          await signOut(auth);
      }
  };

  // 차트 영역 폭을 컨테이너 크기에 맞춰 동기화합니다.


  useEffect(() => {
    // 로그아웃 상태에서는 목록을 비웁니다.
    if (!user) {
        setStocks([]);
        return;
    }

    const fetchData = async () => {
      try {
        setLoading(true);
        // meta_data 컬렉션에서 목록용 요약 데이터를 읽어옵니다.
        const q = query(collection(db, "meta_data")); 
        const querySnapshot = await getDocs(q);
        
        let allStocks = [];
        querySnapshot.forEach(doc => {
            const data = doc.data();
            if (data.list && Array.isArray(data.list)) {
                allStocks = [...allStocks, ...data.list];
            }
        });

        allStocks = allStocks
          .map(normalizeStock)
          .filter(Boolean);

        // 거래정지 종목은 뒤로 보내고, 그다음 밴드폭으로 정렬합니다.
        allStocks.sort((a, b) => {
          const aStatus = normalizeStatusText(a.status, a.type);
          const bStatus = normalizeStatusText(b.status, b.type);
          const aSuspended = a.type === 'suspended' || /거래정지|suspend/i.test(aStatus) ? 1 : 0;
          const bSuspended = b.type === 'suspended' || /거래정지|suspend/i.test(bStatus) ? 1 : 0;
            if (aSuspended !== bSuspended) return aSuspended - bSuspended;
            
            return a.bandwidth - b.bandwidth;
        });
        setStocks(allStocks);
        
        // 최초 로드 후 첫 종목을 기본 선택합니다.
        if (allStocks.length > 0) {
             handleStockClick(allStocks[0]);
        }
      } catch (error) {
        console.error("Error fetching data:", error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [user]);

  // 종목 선택 시 상세 데이터는 지연 로딩합니다.
  const handleStockClick = async (summaryStock) => {
      const requestId = ++detailRequestRef.current;

      // 이미 history가 있으면 그대로 사용합니다.
      if (summaryStock.history) {
          setSelectedStock(summaryStock);
          return;
      }

      // Firestore에서 상세 payload를 지연 로딩합니다.
      try {
          console.log("Fetching details for:", summaryStock.id);
          // 상세 로딩 중에도 요약 정보는 즉시 화면에 보여줍니다.
          setSelectedStock({ ...summaryStock, history: null }); 

          const docRef = doc(db, "stock_analysis", summaryStock.id);
          const docSnap = await getDoc(docRef);

          if (requestId !== detailRequestRef.current) {
              return;
          }

          if (docSnap.exists()) {
              const fullData = docSnap.data();
              console.log("Fetched Data:", fullData);
              const mergedData = normalizeStock(
                { ...summaryStock, ...fullData },
                summaryStock.resolvedMarket
              ) || {
                ...summaryStock,
                ...fullData,
                resolvedMarket: summaryStock.resolvedMarket,
              };
              
              setSelectedStock(mergedData);
              
              // 상세 데이터를 받아오면 리스트 캐시도 함께 갱신합니다.
              setStocks(prev => prev.map(s => s.id === summaryStock.id ? mergedData : s));
          } else {
              console.error("No such document!");
          }
      } catch (e) {
          console.error("Detail fetching error:", e);
      }
  };

    const getStatusColor = (status) => {
    if (!status) return 'text-gray-500';
    const text = String(status);
    if (/매도|SELL|sell/i.test(text)) return 'text-red-600 font-bold';
    if (/관망|대기|주의|BUY|buy|watch/i.test(text)) return 'text-yellow-600 font-bold';
    if (/squeeze|응축|스퀴즈/i.test(text)) return 'text-violet-600 font-bold';
    if (/normal|일반/i.test(text)) return 'text-emerald-600 font-bold';
    if (/suspended|거래정지|suspend/i.test(text)) return 'text-slate-500 font-bold';
    if (/N\/A|데이터 없음|없음|insufficient/i.test(text)) return 'text-blue-600 font-bold';
    return 'text-gray-500';
  };

  const handleOpenExternal = (stock) => {
    const url = getExternalLink(stock.id.replace('KR_', '').replace('US_', ''));
    window.open(url, '_blank');
  };

  const sortStocks = (items) => {
      const result = [...items];
      result.sort((a, b) => {
          const aStatus = normalizeStatusText(a.status, a.type);
          const bStatus = normalizeStatusText(b.status, b.type);
          const aSuspended = a.type === 'suspended' || /거래정지|suspend/i.test(aStatus) ? 1 : 0;
          const bSuspended = b.type === 'suspended' || /거래정지|suspend/i.test(bStatus) ? 1 : 0;
          if (aSuspended !== bSuspended) return aSuspended - bSuspended;

          let valA = 0;
          let valB = 0;

          if (sortConfig.key === 'bandwidth') {
              valA = a.bandwidth;
              valB = b.bandwidth;
          } else if (sortConfig.key === 'marcap') {
              valA = a.marcap || 0;
              valB = b.marcap || 0;
          } else if (sortConfig.key === 'percentB') {
              valA = a.percentB || 0;
              valB = b.percentB || 0;
          } else if (sortConfig.key === 'volume') {
              valA = a.volume || 0;
              valB = b.volume || 0;
          }

          if (valA < valB) return sortConfig.direction === 'asc' ? -1 : 1;
          if (valA > valB) return sortConfig.direction === 'asc' ? 1 : -1;
          return 0;
      });
      return result;
  };

  // 사이드바 목록을 시장별로 분리해 관리합니다.
  const marketStocks = React.useMemo(() => {
      const buckets = { KR: [], US: [] };

      stocks.forEach(stock => {
          const market = stock.resolvedMarket;
          if (market !== 'KR' && market !== 'US') return;

          let effectiveType = stock.type;
          if (!isAdmin && stock.type === 'sell_signal') {
              effectiveType = 'squeeze';
          }

          if (!selectedPatterns.includes(effectiveType)) return;
          buckets[market].push(stock);
      });

      return {
          KR: sortStocks(buckets.KR),
          US: sortStocks(buckets.US),
      };
  }, [stocks, selectedPatterns, sortConfig, isAdmin]);

  const filteredStocks = marketStocks[selectedMarket] || [];

  useEffect(() => {
      const selectedStockMarket = selectedStock?.resolvedMarket ?? getStockMarket(selectedStock);
      const nextSelectedStock = filteredStocks.find(stock => stock.id === selectedStock?.id) ?? null;

      if (filteredStocks.length === 0) {
          if (selectedStock && selectedStockMarket !== selectedMarket) {
              detailRequestRef.current += 1;
              setSelectedStock(null);
          }
          return;
      }

      if (!selectedStock || selectedStockMarket !== selectedMarket || !nextSelectedStock) {
          handleStockClick(filteredStocks[0]);
          return;
      }

      if (nextSelectedStock !== selectedStock) {
          setSelectedStock(nextSelectedStock);
      }
  }, [filteredStocks, selectedMarket, selectedStock]);

  // 패턴 필터 칩 토글
  const togglePattern = (type) => {
      setSelectedPatterns(prev => {
          if (type === 'ALL') {
              const all = ['squeeze', 'buy_signal', 'normal', 'suspended'];
              if (isAdmin) all.push('sell_signal');
              return all;
          }
          if (prev.includes(type)) return prev.filter(p => p !== type);
          else return [...prev, type];
      });
  };

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center flex-col gap-4">
        <Activity className="w-10 h-10 text-slate-800 animate-bounce" />
        <div className="text-xl font-bold text-slate-700">데이터를 불러오는 중입니다...</div>
      </div>
    );
  }

  // 로그인 전 화면
  if (!user) {
      return (
          <>
            <LandingPage onLogin={() => setShowLoginModal(true)} />
             {/* 로그인 모달 */}
            {showLoginModal && (
              <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 animate-fade-in">
                <div className="bg-white p-6 rounded-lg shadow-xl w-80">
                  <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                    <Lock className="w-5 h-5 text-slate-700" /> {isSignup ? "회원가입" : "로그인"}
                  </h3>
                  <form onSubmit={handleAuthSubmit} className="space-y-3">
                    <input
                      type="email"
                      placeholder="이메일"
                      autoComplete="username"
                      value={loginEmail}
                      onChange={(e) => setLoginEmail(e.target.value)}
                      className="w-full text-sm p-2 border rounded focus:outline-none focus:border-slate-500"
                      required
                    />
                    <input
                      type="password"
                      placeholder="비밀번호 (최소 6자)"
                      autoComplete={isSignup ? "new-password" : "current-password"}
                      value={loginPassword}
                      onChange={(e) => setLoginPassword(e.target.value)}
                      className="w-full text-sm p-2 border rounded focus:outline-none focus:border-slate-500"
                      required
                    />
                    <div className="flex gap-2 pt-2">
                      <button type="button" onClick={() => setShowLoginModal(false)} className="flex-1 py-2 text-sm text-gray-500 hover:bg-gray-100 rounded">취소</button>
                      <button type="submit" className="flex-1 py-2 text-sm bg-slate-800 text-white rounded hover:bg-slate-700 font-bold">{isSignup ? "가입하기" : "로그인"}</button>
                    </div>
                  </form>

                  <div className="relative my-4">
                    <div className="absolute inset-0 flex items-center">
                      <span className="w-full border-t border-gray-300" />
                    </div>
                    <div className="relative flex justify-center text-xs uppercase">
                      <span className="bg-white px-2 text-gray-500">또는</span>
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={handleGoogleLogin}
                    className="w-full flex items-center justify-center gap-2 bg-white border border-gray-300 text-slate-700 py-2 rounded text-sm font-bold hover:bg-gray-50 transition-all"
                  >
                    <svg className="w-4 h-4" viewBox="0 0 24 24">
                      <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
                      <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
                      <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
                      <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
                    </svg>
                    Google로 로그인
                  </button>

                  <div className="mt-4 text-center">
                    <button onClick={() => setIsSignup(!isSignup)} className="text-xs text-blue-500 hover:underline">
                      {isSignup ? "이미 계정이 있나요? 로그인" : "계정이 없나요? 회원가입"}
                    </button>
                  </div>
                </div>
              </div>
            )}
          </>
      );
  }


  // 로그인했지만 승인되지 않은 사용자 화면
  if (user && !isApproved) {
      return (
        <div className="flex h-screen items-center justify-center flex-col gap-6 bg-slate-50 p-6 text-center">
          <div className="bg-white p-8 rounded-2xl shadow-xl max-w-md w-full border border-gray-100">
            <div className="w-16 h-16 bg-yellow-100 rounded-full flex items-center justify-center mx-auto mb-6">
              <Lock className="w-8 h-8 text-yellow-600" />
            </div>
            <h2 className="text-2xl font-bold text-slate-800 mb-3">접근 권한이 필요합니다</h2>
            <p className="text-slate-500 mb-6 text-sm leading-relaxed">
              현재 로그인 계정: <strong>{user?.email}</strong>
              <br />
              이 계정은 관리자 화면 접근 권한이 없습니다.
            </p>
            <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 mb-6 text-sm">
              <p className="text-slate-600 font-medium mb-1">문의</p>
              <a href="mailto:or_not_official@naver.com" className="text-blue-600 hover:underline font-bold text-lg">
                or_not_official@naver.com
              </a>
            </div>
            <button
              onClick={handleLogout}
              className="w-full py-3 bg-white border border-slate-300 text-slate-600 font-bold rounded-xl hover:bg-slate-50 transition-all flex items-center justify-center gap-2"
            >
              <LogOut className="w-4 h-4" /> 로그아웃
            </button>
          </div>
        </div>
      );
  }

  return (
    <div className="flex flex-col h-screen bg-gray-50 overflow-hidden font-sans text-slate-800">
      
      {/* 메인 앱 레이아웃 */}
      <div className="flex flex-1 overflow-hidden">
        
        {/* 좌측 배너 영역 */}
        {!isAdmin && <AdBanner position="LEFT" className="hidden 2xl:flex w-[160px] flex-shrink-0 border-r" />}

        {/* 사이드바 */}
        <div className="w-1/3 min-w-[320px] bg-white border-r border-gray-200 flex flex-col shadow-lg z-10">
        <div className="p-6 border-b border-gray-200 bg-slate-900 text-white">
          <h1 className="text-xl font-bold flex items-center gap-2">
            <Activity className="text-yellow-400" />
            MESUGAK
          </h1>
          <div className="mt-2 flex justify-between items-end">
            <p className="text-xs text-slate-400">AI 스캐너 결과 ({filteredStocks.length})</p>
            {user ? (
              <button onClick={handleLogout} className="text-xs text-slate-400 hover:text-white flex items-center gap-1">
                <LogOut className="w-3 h-3" /> 로그아웃
              </button>
            ) : (
              <button onClick={() => setShowLoginModal(true)} className="text-xs text-slate-400 hover:text-white flex items-center gap-1">
                <Lock className="w-3 h-3" /> 로그인
              </button>
            )}
          </div>
        </div>
        {isAdmin && (
          <div className="mt-3 flex gap-2">
            <button
              onClick={() => setAdminView('scanner')}
              className={
                'flex-1 text-xs py-1.5 rounded border transition-all ' +
                (adminView === 'scanner'
                  ? 'bg-white text-slate-900 border-slate-200 font-bold'
                  : 'bg-slate-800 text-slate-300 border-slate-700')
              }
            >
              SCANNER
            </button>
            <button
              onClick={() => setAdminView('log')}
              className={
                'flex-1 text-xs py-1.5 rounded border transition-all flex items-center justify-center gap-1 ' +
                (adminView === 'log'
                  ? 'bg-white text-slate-900 border-slate-200 font-bold'
                  : 'bg-slate-800 text-slate-300 border-slate-700')
              }
            >
              <FileText className="w-3 h-3" /> LOG
            </button>
          </div>
        )}
        <div className="p-3 bg-yellow-50 border-b border-yellow-100 text-xs text-yellow-800 flex items-start gap-2">
          <Info className="w-4 h-4 mt-0.5 flex-shrink-0" />
          <p><strong>밴드폭(Bandwidth)</strong>이 낮을수록 수렴 구간 가능성이 큽니다.</p>
        </div>
        
        {/* 필터 컨트롤 */}
        <div className="p-3 bg-white border-b border-gray-200 space-y-3">
            {/* 시장 선택 */}
            <div className="flex rounded-md bg-gray-100 p-1">
                {['KR', 'US'].map(m => (
                    <button 
                        key={m}
                        onClick={() => {
                          detailRequestRef.current += 1;
                          setSelectedStock(null);
                          setSelectedMarket(m);
                        }}
                        className={`flex-1 text-sm py-1.5 rounded font-medium transition-all ${selectedMarket === m ? 'bg-white shadow text-slate-900' : 'text-gray-400 hover:text-gray-600'}`}
                    >
                        {m === 'KR' ? '한국 시장' : '미국 시장'}
                    </button>
                ))}
            </div>

            {/* 패턴 필터 */}
            <div className="flex gap-1 mb-2">
                <button
                    onClick={() => togglePattern('ALL')}
                    className="flex-1 text-xs py-1.5 rounded border border-slate-300 bg-white hover:bg-slate-50 font-bold text-slate-700"
                >
                    전체
                </button>
                {[
                    { id: 'squeeze', label: 'Squeeze' },
                    { id: 'buy_signal', label: 'Buy Signal' },
                    { id: 'sell_signal', label: 'Sell Signal' },
                    { id: 'normal', label: 'Normal' },
                    { id: 'suspended', label: 'Suspended' }
                ].map(p => {
                    // 비관리자에게는 sell_signal 필터를 숨깁니다.
                    if (p.id === 'sell_signal' && !isAdmin) return null;
                    const isActive = selectedPatterns.includes(p.id);
                    return (
                        <button
                            key={p.id}
                            onClick={() => togglePattern(p.id)}
                            className={`flex-1 text-xs py-1.5 rounded border transition-all flex items-center justify-center gap-1 ${
                                isActive
                                ? 'bg-slate-800 text-white border-slate-800 font-bold' 
                                : 'bg-white text-gray-400 border-gray-200'
                            }`}
                        >   
                            {isActive && <Check className="w-3 h-3" />}
                            {p.label}
                        </button>
                    );
                })}
            </div>

            {/* 정렬 컨트롤 */}
            <div className="flex gap-1 items-stretch h-8">
                 {/* 정렬 기준 버튼 */}
                 {[
                    { id: 'bandwidth', label: 'Bandwidth' },
                    { id: 'marcap', label: 'Market Cap' },
                    { id: 'percentB', label: '%B' },
                    { id: 'volume', label: 'Volume' }
                 ].map(s => (
                    <button
                        key={s.id}
                        onClick={() =>
                          setSortConfig(prev => ({
                            ...prev,
                            key: s.id,
                            direction: getPreferredSortDirection(s.id),
                          }))
                        }
                        className={`flex-1 text-[10px] rounded border transition-all ${
                            sortConfig.key === s.id
                            ? 'bg-blue-50 text-blue-600 border-blue-200 font-bold'
                            : 'bg-white text-gray-500 border-gray-200'
                        }`}
                    >
                        {s.label}
                    </button>
                 ))}
                 
                 {/* 정렬 방향 */}
                 <button 
                    onClick={() => setSortConfig(prev => ({ ...prev, direction: prev.direction === 'asc' ? 'desc' : 'asc' }))}
                    className="w-8 flex items-center justify-center border border-gray-200 rounded bg-white text-gray-500 hover:text-slate-800"
                    title={sortConfig.direction === 'asc' ? 'Ascending' : 'Descending'}
                 >
                     {sortConfig.direction === 'asc' ? '↑' : '↓'}
                 </button>
            </div>
        </div>

        <div key={selectedMarket} className="flex-1 overflow-y-auto">
          {filteredStocks.length === 0 ? (
            <div className="p-10 text-center text-gray-400">조건에 맞는 종목이 없습니다.</div>
          ) : (
            filteredStocks.map((stock) => (
              <SidebarItem 
                key={stock.id}
                stock={stock}
                isSelected={selectedStock?.id === stock.id}
                onClick={handleStockClick}
                isLoggedIn={isAdmin}
                getStatusColor={getStatusColor}
              />
            ))
          )}
        </div>
      </div>

      {/* 상세 패널 */}
      <div className="flex-1 min-w-0 min-h-0 flex flex-col h-full overflow-hidden bg-slate-50/50">
        {isAdmin && adminView === 'log' ? (
          <div className="flex-1 p-6 overflow-y-auto">
            <div className="bg-white p-5 rounded-2xl shadow-sm border border-gray-200 mb-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-bold text-slate-700 flex items-center gap-2">
                  <FileText className="w-4 h-4" /> 자동매매 로그 (최근 100건)
                </h3>
                <button
                  onClick={fetchAdminBotData}
                  className="text-xs bg-slate-800 text-white border border-slate-700 px-2 py-1 rounded flex items-center gap-1 hover:bg-slate-700"
                >
                  <RefreshCw className="w-3 h-3" /> 새로고침
                </button>
              </div>
              <div className="overflow-auto max-h-[70vh] border border-gray-200 rounded-lg">
                <table className="w-full text-xs">
                  <thead className="bg-slate-50 text-slate-500 sticky top-0">
                    <tr>
                      <th className="text-left px-3 py-2">Time</th>
                      <th className="text-left px-3 py-2">Type</th>
                      <th className="text-left px-3 py-2">Symbol</th>
                      <th className="text-right px-3 py-2">Qty</th>
                      <th className="text-right px-3 py-2">Price</th>
                      <th className="text-right px-3 py-2">PnL%</th>
                      <th className="text-left px-3 py-2">Reason</th>
                    </tr>
                  </thead>
                  <tbody>
                    {botTradeLogs.length === 0 ? (
                      <tr>
                        <td colSpan={7} className="px-3 py-6 text-center text-gray-400">로그가 없습니다.</td>
                      </tr>
                    ) : (
                      botTradeLogs.map((log) => (
                        <tr key={log.id} className="border-t border-gray-100">
                          <td className="px-3 py-2 text-gray-500">{formatLogTime(log.createdAt)}</td>
                          <td className={`px-3 py-2 font-bold ${log.action === 'BUY' ? 'text-emerald-600' : 'text-red-600'}`}>{log.action}</td>
                          <td className="px-3 py-2">{log.name} ({log.code})</td>
                          <td className="px-3 py-2 text-right">{log.quantity ?? '-'}</td>
                          <td className="px-3 py-2 text-right">{formatMoney(log.price)}</td>
                          <td className={`px-3 py-2 text-right ${Number(log.pnlPct || 0) >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>{log.pnlPct !== undefined ? `${Number(log.pnlPct).toFixed(2)}%` : '-'}</td>
                          <td className="px-3 py-2 text-gray-500">{log.reason || '-'}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        ) : selectedStock ? (
          <div className="flex-1 p-6 overflow-y-auto">
            <div className="bg-white p-6 rounded-2xl border border-gray-200 shadow-sm">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-2xl font-bold text-slate-800">{selectedStock.name}</h2>
                  <p className="text-sm text-gray-500 mt-1">{selectedStock.id}</p>
                </div>
                <div className="text-right mr-3">
                  <p className="text-[11px] text-slate-400">현재가</p>
                  <p className="text-xl font-extrabold text-slate-800">
                    {selectedStock.currentPrice?.toLocaleString?.() ?? '-'}
                  </p>
                </div>
                <button
                  onClick={() => handleOpenExternal(selectedStock)}
                  className="bg-green-500 hover:bg-green-600 text-white px-4 py-2 rounded-lg text-sm font-bold transition-all flex items-center gap-2"
                >
                  외부 차트 열기 <ExternalLink className="w-4 h-4" />
                </button>
              </div>
              <div className="mt-6 flex items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <div className="flex bg-gray-100 rounded-md p-1">
                    {['candle', 'line'].map((mode) => (
                      <button
                        key={mode}
                        onClick={() => setPriceView(mode)}
                        className={`px-3 py-1 text-xs font-bold rounded-md transition-all ${
                          priceView === mode ? 'bg-white text-slate-800 shadow' : 'text-gray-500 hover:text-slate-700'
                        }`}
                      >
                        {mode === 'candle' ? '캔들' : '선'}
                      </button>
                    ))}
                  </div>
                  <div className="flex bg-gray-100 rounded-md p-1">
                    {['1M', '3M', '6M', 'ALL'].map((range) => (
                      <button
                        key={range}
                        onClick={() => setZoomRange(range)}
                        className={`px-3 py-1 text-xs font-bold rounded-md transition-all ${
                          zoomRange === range ? 'bg-white text-slate-800 shadow' : 'text-gray-500 hover:text-slate-700'
                        }`}
                      >
                        {range}
                      </button>
                    ))}
                  </div>
                </div>
                <button
                  onClick={() => setShowSettings((v) => !v)}
                  className={`p-2 rounded-lg transition-all ${showSettings ? 'bg-slate-800 text-white' : 'bg-gray-100 text-gray-500 hover:bg-gray-200'}`}
                >
                  <Settings className="w-4 h-4" />
                </button>
              </div>

              {showSettings && (
                <div className="mt-3 p-3 rounded-xl border border-gray-200 bg-slate-50 grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                  {[
                    { key: 'close', label: '종가선' },
                    { key: 'ma20', label: 'MA20' },
                    { key: 'upper', label: '상단밴드' },
                    { key: 'lower', label: '하단밴드' },
                    { key: 'rsi', label: 'RSI' },
                    { key: 'rsiSignal', label: 'RSI Signal' },
                  ].map((cfg) => (
                    <div key={cfg.key} className="flex items-center justify-between gap-2 bg-white border border-gray-200 rounded-lg p-2">
                      <button onClick={() => toggleConfig(cfg.key)} className={chartConfig[cfg.key].show ? 'text-slate-800' : 'text-gray-300'}>
                        {chartConfig[cfg.key].show ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
                      </button>
                      <span className="font-bold text-slate-600">{cfg.label}</span>
                      <input type="color" value={chartConfig[cfg.key].color} onChange={(e) => updateConfig(cfg.key, 'color', e.target.value)} />
                      <input
                        type="range"
                        min="1"
                        max="4"
                        step="0.5"
                        value={chartConfig[cfg.key].width}
                        onChange={(e) => updateConfig(cfg.key, 'width', Number(e.target.value))}
                      />
                    </div>
                  ))}
                  <div className="flex items-center justify-between gap-2 bg-white border border-gray-200 rounded-lg p-2">
                    <button onClick={() => toggleConfig('candle')} className={chartConfig.candle.show ? 'text-slate-800' : 'text-gray-300'}>
                      {chartConfig.candle.show ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
                    </button>
                    <span className="font-bold text-slate-600">캔들</span>
                    <div className="flex items-center gap-1">
                      <span className="text-[10px] text-gray-500">양봉</span>
                      <input type="color" value={chartConfig.candle.upColor} onChange={(e) => updateConfig('candle', 'upColor', e.target.value)} />
                    </div>
                    <div className="flex items-center gap-1">
                      <span className="text-[10px] text-gray-500">음봉</span>
                      <input type="color" value={chartConfig.candle.downColor} onChange={(e) => updateConfig('candle', 'downColor', e.target.value)} />
                    </div>
                    <input
                      type="range"
                      min="1"
                      max="4"
                      step="1"
                      value={chartConfig.candle.wickWidth}
                      onChange={(e) => updateConfig('candle', 'wickWidth', Number(e.target.value))}
                    />
                    <input
                      type="range"
                      min="4"
                      max="14"
                      step="1"
                      value={chartConfig.candle.bodySize}
                      onChange={(e) => updateConfig('candle', 'bodySize', Number(e.target.value))}
                    />
                  </div>
                </div>
              )}

              <div ref={chartHostRef} className="mt-3 h-[420px] rounded-xl border border-gray-200 bg-white p-3">
                {chartReady && visualData?.length > 0 && chartWidth > 0 ? (
                    <ComposedChart width={chartWidth} height={392} data={priceView === 'candle' ? candleData : visualData} margin={{ top: 8, right: 8, left: 4, bottom: 8 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
                      <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#94a3b8' }} />
                      <YAxis
                        domain={yDomain}
                        tickCount={8}
                        tick={{ fontSize: 11, fill: '#94a3b8' }}
                        tickFormatter={formatYAxis}
                        width={70}
                      />
                      <Tooltip content={<CustomTooltip market={selectedStock?.market} />} />
                      {chartConfig.close.show && priceView === 'line' && (
                        <Line type="monotone" dataKey="close" name="종가" stroke={chartConfig.close.color} dot={false} strokeWidth={chartConfig.close.width} />
                      )}
                      {priceView === 'candle' && chartConfig.candle.show && (
                        <>
                          <Bar dataKey="wickBase" stackId="wick" fill="transparent" isAnimationActive={false} />
                          <Bar dataKey="wickBody" stackId="wick" barSize={Math.max(1, Number(chartConfig.candle.wickWidth) || 1)} isAnimationActive={false}>
                            {candleData.map((d, i) => (
                              <Cell key={`wick-${i}`} fill={d.candleUp ? chartConfig.candle.upColor : chartConfig.candle.downColor} />
                            ))}
                          </Bar>
                          <Bar dataKey="candleBase" stackId="body" fill="transparent" isAnimationActive={false} />
                          <Bar dataKey="candleBody" stackId="body" barSize={Math.max(4, Number(chartConfig.candle.bodySize) || 8)} isAnimationActive={false}>
                            {candleData.map((d, i) => (
                              <Cell
                                key={`body-${i}`}
                                fill={d.candleUp ? chartConfig.candle.upColor : chartConfig.candle.downColor}
                                fillOpacity={0.25}
                                stroke={d.candleUp ? chartConfig.candle.upColor : chartConfig.candle.downColor}
                              />
                            ))}
                          </Bar>
                        </>
                      )}
                      {chartConfig.ma20.show && (
                        <Line type="monotone" dataKey="ma20" name="MA20" stroke={chartConfig.ma20.color} dot={false} strokeWidth={chartConfig.ma20.width} />
                      )}
                      {chartConfig.upper.show && (
                        <Line type="monotone" dataKey="upper" name="상단밴드" stroke={chartConfig.upper.color} dot={false} strokeWidth={chartConfig.upper.width} />
                      )}
                      {chartConfig.lower.show && (
                        <Line type="monotone" dataKey="lower" name="하단밴드" stroke={chartConfig.lower.color} dot={false} strokeWidth={chartConfig.lower.width} />
                      )}
                      <Brush dataKey="date" height={20} stroke="#64748b" travellerWidth={8} />
                    </ComposedChart>
                ) : (
                  <div className="h-full flex items-center justify-center text-gray-400 text-sm">
                    차트 데이터 준비 중입니다. 현재가 {selectedStock.currentPrice?.toLocaleString?.() ?? '-'}
                  </div>
                )}
              </div>
              <div className="mt-3 h-[120px] rounded-xl border border-gray-200 bg-white p-3">
                {visualData?.length > 0 && chartWidth > 0 ? (
                    <ComposedChart width={chartWidth} height={96} data={visualData} margin={{ top: 4, right: 8, left: 4, bottom: 4 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
                      <XAxis dataKey="date" hide />
                      <YAxis domain={[0, 1]} tick={{ fontSize: 10, fill: '#94a3b8' }} width={36} />
                      <Tooltip />
                      <Line type="monotone" dataKey="percentB" name="%B" stroke="#8b5cf6" dot={false} strokeWidth={1.5} />
                    </ComposedChart>
                ) : null}
              </div>
              <div className="mt-3 h-[120px] rounded-xl border border-gray-200 bg-white p-3">
                {visualData?.length > 0 && chartWidth > 0 ? (
                    <ComposedChart width={chartWidth} height={96} data={visualData} margin={{ top: 4, right: 8, left: 4, bottom: 4 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
                      <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#94a3b8' }} />
                      <YAxis tick={{ fontSize: 10, fill: '#94a3b8' }} width={50} />
                      <Tooltip />
                      <Bar dataKey="volume" name="거래량" fill="#cbd5e1" />
                    </ComposedChart>
                ) : null}
              </div>
              <div className="mt-3 h-[120px] rounded-xl border border-gray-200 bg-white p-3">
                {rsiData?.length > 0 && chartWidth > 0 ? (
                    <ComposedChart width={chartWidth} height={96} data={rsiData} margin={{ top: 4, right: 8, left: 4, bottom: 4 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
                      <XAxis dataKey="date" hide />
                      <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: '#94a3b8' }} width={36} />
                      <Tooltip />
                      <Line type="monotone" dataKey="rsiUpper" name="과매수 70" stroke="#ef4444" dot={false} strokeDasharray="4 4" strokeWidth={1} />
                      <Line type="monotone" dataKey="rsiMid" name="중립 50" stroke="#cbd5e1" dot={false} strokeDasharray="3 3" strokeWidth={1} />
                      <Line type="monotone" dataKey="rsiLower" name="과매도 30" stroke="#2563eb" dot={false} strokeDasharray="4 4" strokeWidth={1} />
                      {chartConfig.rsi.show && (
                        <Line
                          type="monotone"
                          dataKey="rsi"
                          name="RSI(14)"
                          stroke={chartConfig.rsi.color}
                          dot={false}
                          connectNulls={false}
                          strokeWidth={chartConfig.rsi.width}
                        />
                      )}
                      {chartConfig.rsiSignal.show && (
                        <Line
                          type="monotone"
                          dataKey="rsiSignal"
                          name="RSI Signal(9)"
                          stroke={chartConfig.rsiSignal.color}
                          dot={false}
                          connectNulls={false}
                          strokeWidth={chartConfig.rsiSignal.width}
                        />
                      )}
                    </ComposedChart>
                ) : null}
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
                <div className="p-4 bg-slate-50 rounded-xl">
                  <p className="text-xs text-slate-500">상태</p>
                  <p className={`text-base font-bold ${getStatusColor(normalizeStatusText(selectedStock.status, selectedStock.type))}`}>
                    {normalizeStatusText(selectedStock.status, selectedStock.type)}
                  </p>
                </div>
                <div className="p-4 bg-slate-50 rounded-xl">
                  <p className="text-xs text-slate-500">현재가</p>
                  <p className="text-base font-bold text-slate-800">{selectedStock.currentPrice?.toLocaleString?.() ?? "-"}</p>
                </div>
                <div className="p-4 bg-slate-50 rounded-xl">
                  <p className="text-xs text-slate-500">밴드폭</p>
                  <p className="text-base font-bold text-slate-800">{selectedStock.bandwidth !== undefined ? `${(selectedStock.bandwidth * 100).toFixed(2)}%` : "-"}</p>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-gray-400 bg-slate-50">
            <Activity className="w-16 h-16 text-gray-200 mb-4" />
            <p>종목을 선택하면 상세 정보가 표시됩니다.</p>
          </div>
        )}

      </div>
        {/* 우측 배너 */}
        {!isAdmin && <AdBanner position="RIGHT" className="hidden 2xl:flex w-[160px] flex-shrink-0 border-l" />}
      </div>

      {/* 모바일 하단 배너 */}
      {!isAdmin && <AdBanner position="BOTTOM" className="h-[90px] w-full flex-shrink-0 border-t z-20" />}

      {/* 전역 모달 영역 */}
      {showLoginModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-lg shadow-xl w-80">
            <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
              <Lock className="w-5 h-5 text-slate-700" /> {isSignup ? "회원가입" : "로그인"}
            </h3>
            <form onSubmit={handleAuthSubmit} className="space-y-3">
              <input
                type="email"
                placeholder="이메일"
                autoComplete="username"
                value={loginEmail}
                onChange={(e) => setLoginEmail(e.target.value)}
                className="w-full text-sm p-2 border rounded focus:outline-none focus:border-slate-500"
                required
              />
              <input
                type="password"
                placeholder="비밀번호 (최소 6자)"
                autoComplete={isSignup ? "new-password" : "current-password"}
                value={loginPassword}
                onChange={(e) => setLoginPassword(e.target.value)}
                className="w-full text-sm p-2 border rounded focus:outline-none focus:border-slate-500"
                required
              />
              <div className="flex gap-2 pt-2">
                <button type="button" onClick={() => setShowLoginModal(false)} className="flex-1 py-2 text-sm text-gray-500 hover:bg-gray-100 rounded">취소</button>
                <button type="submit" className="flex-1 py-2 text-sm bg-slate-800 text-white rounded hover:bg-slate-700 font-bold">{isSignup ? "가입하기" : "로그인"}</button>
              </div>
            </form>
            <div className="relative my-4">
              <div className="absolute inset-0 flex items-center">
                <span className="w-full border-t border-gray-300" />
              </div>
              <div className="relative flex justify-center text-xs uppercase">
                <span className="bg-white px-2 text-gray-500">또는</span>
              </div>
            </div>
            <button
              type="button"
              onClick={handleGoogleLogin}
              className="w-full flex items-center justify-center gap-2 bg-white border border-gray-300 text-slate-700 py-2 rounded text-sm font-bold hover:bg-gray-50 transition-all"
            >
              <svg className="w-4 h-4" viewBox="0 0 24 24">
                <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
                <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
                <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
                <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
              </svg>
              Google로 로그인
            </button>
            <div className="mt-4 text-center">
              <button onClick={() => setIsSignup(!isSignup)} className="text-xs text-blue-500 hover:underline">
                {isSignup ? "이미 계정이 있나요? 로그인" : "계정이 없나요? 회원가입"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}



