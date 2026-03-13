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

// ???샑???醫???
import LandingPage from './LandingPage'; 

// [?怨뺥넪??] ??醫롫윥??嶺뚮∥???낆?? ?뺢퀡?녻굢???醫???
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
// [1] ??ｋ걠??????醫???
// =================================================================
const getExternalLink = (id) => {
  if (/^\d+$/.test(id)) return `https://finance.naver.com/item/main.naver?code=${id}`;
  return `https://finance.yahoo.com/quote/${id}`;
};

const CustomTooltip = ({ active, payload, label, market }) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    // ??醫롫윪???醫롫짗?? ??醫????醫롫짗?? 嶺뚳퐢?얍칰?
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
// [2] ??醫롫윪???醫롫윥????醫롫윪???(React.memo 嶺뚣끉裕???
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

const SidebarItem = React.memo(({ stock, isSelected, onClick, isLoggedIn }) => {
  // [?곌랜?삯뇡? ?β돦裕????????롪퍔??? sell_signal??squeeze????醫롫윪??
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
// [3] 嶺뚮∥??????샑???醫???
// =================================================================

// [?怨뺥넪??] ??⑹탪???꾩룄?←몭????샑???醫???
const AdBanner = ({ position, className }) => {
  return (
    <div className={`bg-gray-200 flex items-center justify-center text-gray-400 text-xs border border-gray-300 ${className}`}>
      {position} AD AREA
    </div>
  );
};

// [?怨뺥넪??] ?リ옇?????醫롫윪????醫롫윪??
const DEFAULT_CHART_CONFIG = {
  close: { show: true, color: '#334155', width: 2 },
  ma20: { show: true, color: '#f59e0b', width: 1.5 },
  upper: { show: true, color: '#64748b', width: 2 },
  lower: { show: true, color: '#64748b', width: 2 },
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
  const [loading, setLoading] = useState(false); // [??醫롫윪?? ?貫?껆뵳寃쇰쐻?false (?β돦裕??????β돦裕녽???醫롫윪??

  // [?怨뺥넪??] ??醫롫윪凉???醫?繹?
  const [user, setUser] = useState(null);
  const [userRole, setUserRole] = useState(null); // 'member', 'user', 'admin'
  // derived state for convenience
  const isAdmin = userRole === 'admin';
  const isApproved = ['user', 'admin'].includes(userRole);
  
  const [showLoginModal, setShowLoginModal] = useState(false);
  const [isSignup, setIsSignup] = useState(false); // [?怨뺥넪??] ??醫롫윪???쾸???嶺뚮ㅄ維獄?
  const [loginEmail, setLoginEmail] = useState("");
  const [loginPassword, setLoginPassword] = useState("");

  // [?怨뺥넪??] 嶺뚢뼰維????醫롫윪????醫?繹?
  const [showSettings, setShowSettings] = useState(false);
  const [chartConfig, setChartConfig] = useState(DEFAULT_CHART_CONFIG);
  const [priceView, setPriceView] = useState('candle'); // 'candle' | 'line'

  // [?怨뺥넪??] ????醫롫윪?????醫??묕퐛?? ??醫?繹?
  const [zoomRange, setZoomRange] = useState(DEFAULT_ZOOM); // '1M', '3M', '6M', 'ALL'
  const [visualData, setVisualData] = useState([]);

  // [?怨뺥넪??] ??醫?????醫?繹?
  const [selectedMarket, setSelectedMarket] = useState(DEFAULT_MARKET); // 'KR' | 'US'
  const [selectedPatterns, setSelectedPatterns] = useState(DEFAULT_PATTERNS);
  const [sortConfig, setSortConfig] = useState(DEFAULT_SORT);

  // [?怨뺥넪??] Y???뺢퀡???domain) ??醫?繹?(??醫롫짗?? ??????μ쪠???
  const [yDomain, setYDomain] = useState(['auto', 'auto']);
  const [yTicks, setYTicks] = useState([]); // [?怨뺥넪??] ??ｌ뫒亦??Y????醫롫윞??

  // [?怨뺥넪??] 嶺뚢뼰維????醫롫윥?臾덈쐻?繞벿뮻????醫?繹?(Layout Thrashing ?꾩렮維??)
  const [chartReady, setChartReady] = useState(false);
  const [botAccount, setBotAccount] = useState(null);
  const [botTradeLogs, setBotTradeLogs] = useState([]);
  const [botLoading, setBotLoading] = useState(false);
  const [botPermissionDenied, setBotPermissionDenied] = useState(false);
  const [adminView, setAdminView] = useState('scanner');
  const candleDebugLoggedRef = useRef(false);
  const chartHostRef = useRef(null);
  const [chartWidth, setChartWidth] = useState(0);

  // selectedStock/zoomRange changes update visualData and chart-ready state.
  useEffect(() => {
    console.log("Selected Stock Updated:", selectedStock);
    setChartReady(false); // ??醫롫윪????꾩룆????????醫롫윥??嶺뚢뼰維????醫롫짗??
    
    if (selectedStock?.history) {
      console.log("History found, applying zoom...", selectedStock.history.length);
      applyZoom(selectedStock.history, zoomRange);
      // DOM ??醫롫윪???醫롫윪?????醫?????醫롫윞?????(Recharts width error ?꾩렮維??)
      setTimeout(() => {
          console.log("Setting chartReady to true");
          setChartReady(true);
      }, 200); 
    } else {
      console.warn("No history found for selected stock");
      setVisualData([]); // fallback when selected stock has no history
    }
  }, [selectedStock, zoomRange]);



  // Recompute Y-axis domain/ticks from currently visible chart data.
  useEffect(() => {
    if (!visualData || visualData.length === 0) return;

    let min = Infinity;
    let max = -Infinity;

    visualData.forEach(d => {
      // 嶺뚮ㅄ維獄??낅슣???嶺뚯솘???醫롫짗?? ??μ쪚???醫롫윪??嶺뚣끉裕??嶺뚣끉裕??????醫롫윪??
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

    // [??醫롫윪?? "Nice Number" ??醫롫윞??逾?凉???醫롫윪??(50, 100, 500 ??醫롫윪??껊쐻???醫롫윪?됯퉵彛???
    const padding = (max - min) * 0.05;
    const roughMin = min - padding;
    const roughMax = max + padding;

    const ticks = calculateNiceTicks(roughMin, roughMax, 8);
    setYTicks(ticks);
    setYDomain([ticks[0], ticks[ticks.length - 1]]);
  }, [visualData]);

  // [?怨뺥넪??] Nice Ticks ??ｌ뫒亦???醫롫윪??
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

  // [?怨뺥넪??] Y????醫롫윥?????醫롫윪??
  const formatYAxis = (value) => {
    if (chartConfig.yAxis.format === 'full') {
        const isUS = selectedStock?.market === 'US';
        return isUS ? `$${value.toLocaleString()}` : value.toLocaleString();
    }
    
    // 亦껋꼶????낅슣?????'?? ??醫롫윪????醫롫윪??????(??醫롫윥????醫롫윪??
    if (selectedStock?.market === 'US') {
        return `$${value.toLocaleString()}`;
    }

    // ??醫롫윞???낅슣??? '?? ??醫롫윪????醫롫윪??
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
    
    // ... (rest of applyZoom remains same, just ensuring context match)
    
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
  
// ... (rest of configuration functions)

// ...

                         {chartConfig.yAxis.show && (
                            <YAxis 
                                domain={yDomain} 
                                tickCount={8} // ???띠룇裕??嶺뚯빘鍮??
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


  // Load account role/settings on auth state changes.
  useEffect(() => {
      const unsubscribe = onAuthStateChanged(auth, async (currentUser) => {
          setUser(currentUser);
          if (currentUser) {
              console.log("Logged in:", currentUser.email);
              // Firestore??醫롫윪????醫롫윪????雅?굝??뇡??釉띾쐞???醫롫윞??
              try {
                  // 1. 雅?굝??뇡?Role) ??醫롫윪??('users' ??롫맩???
                  const userDocRef = doc(db, "users", currentUser.uid);
                  const userDocSnap = await getDoc(userDocRef);
                  
                  if (userDocSnap.exists()) {
                      const data = userDocSnap.data();
                      if (data.role) setUserRole(data.role || 'member');
                      setBotPermissionDenied(false);
                  } else {
                      // ??쒖굣?묐슗泥? ??醫롫윪???쐻??リ옇?????醫롫윪??(member)
                      await setDoc(userDocRef, {
                          email: currentUser.email,
                          role: 'member',
                          createdAt: new Date()
                      });
                      setUserRole('member');
                      setBotPermissionDenied(false);
                  }

                  // 2. ??醫롫윪???釉띾쐞???醫롫윞??('users/{uid}/settings/mesugak')
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

  // 2. ??醫롫윪????醫롫윥??????(Debounce ??醫롫윪???띠룄????醫롫윞???곌떠?????醫롫윥壤??????- ??醫롫윪?遺룹쾸? 嶺뚮씭??? ??醫롫윪??뀁쾵???
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
      
      // ?곌떠????띠룆??? ??????(??醫롫윥甸???? ?????꾩렮維??????醫???1????醫롫윥???醫롫윪????醫롫윪??雅?굝????醫롫윥?? ??醫롫윞????β돦裕뉐퐲???醫롫윪???
      const timeout = setTimeout(saveSettings, 500);
      return () => clearTimeout(timeout);
  }, [user, selectedMarket, selectedPatterns, sortConfig, chartConfig, zoomRange, priceView]);

  // 3. Login/signup submit handler.
  const handleAuthSubmit = async (e) => {
      e.preventDefault();
      try {
          if (isSignup) {
              // ??醫롫윪???쾸?????醫롫윪?????醫롫윪??嶺뚯솘???醫롫윪????醫롫윪??(??醫?繹??醫????醫롫윥????醫롫짗????醫롫윪????醫???
              await setPersistence(auth, browserSessionPersistence);
              const userCredential = await createUserWithEmailAndPassword(auth, loginEmail, loginPassword);
              // ??醫롫윪???쾸??????リ옇???雅?굝??뇡?먰떊??ㅲ뵛 (role: 'member')
              await setDoc(doc(db, "users", userCredential.user.uid), {
                  email: loginEmail,
                  role: 'member',
                  createdAt: new Date()
              });
              alert("회원가입이 완료되었습니다. 로그인해 주세요.");
          } else {
              // ?β돦裕?????嶺뚯솘???醫롫윪????醫롫윪??
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

  // Google login handler.
  const handleGoogleLogin = async () => {
      try {
          await setPersistence(auth, browserSessionPersistence);
          const result = await signInWithPopup(auth, googleProvider);
          const user = result.user;
          
          // ??醫롫윪?????쒖굣????醫롫윪??????醫롫윪??
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

  // ResizeObserver ?β돦裕뉐퐲???醫롫윞??(??醫롫윪???


  useEffect(() => {
    // Skip data fetch when logged out.
    if (!user) {
        setStocks([]);
        return;
    }

    const fetchData = async () => {
      try {
        setLoading(true);
        // [嶺뚣끉裕??? ??醫롫윪???洹먮봾裕??醫롫윥壤??釉띾쐞???醫롫윞??(Read ?????99.9% ??醫롫윞??
        const q = query(collection(db, "meta_data")); 
        const querySnapshot = await getDocs(q);
        
        let allStocks = [];
        querySnapshot.forEach(doc => {
            const data = doc.data();
            if (data.list && Array.isArray(data.list)) {
                allStocks = [...allStocks, ...data.list];
            }
        });

        // ?꾩룆?獄????る궡?? ??醫롫윪????醫롫윥??(?? 濾곌쑨????醫롫짗????????醫롫윥餓?
        allStocks.sort((a, b) => {
          const aStatus = normalizeStatusText(a.status, a.type);
          const bStatus = normalizeStatusText(b.status, b.type);
          const aSuspended = a.type === 'suspended' || /거래정지|suspend/i.test(aStatus) ? 1 : 0;
          const bSuspended = b.type === 'suspended' || /거래정지|suspend/i.test(bStatus) ? 1 : 0;
            if (aSuspended !== bSuspended) return aSuspended - bSuspended;
            
            return a.bandwidth - b.bandwidth;
        });
        setStocks(allStocks);
        
        // ???뺢퀡?????リ턁????醫롫윥????醫?繹?(??醫롫윪???β돦裕녽?
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

  // [?怨뺥넪??] ??リ턁????醫롫윥????醫롫윥獄??(??醫롫윪????醫롫윪???Lazy Loading)
  const handleStockClick = async (summaryStock) => {
      // 1. ??醫롫짗?? ??醫롫윪???醫롫윥????醫롫윪???띠럾? ??醫롫윥???롪퍔??????꾩룆?餓???醫?繹?
      if (summaryStock.history) {
          setSelectedStock(summaryStock);
          return;
      }

      // 2. Lazy-load detail payload from Firestore.
      try {
          console.log("Fetching details for:", summaryStock.id);
          // ?β돦裕녽???醫?繹???醫롫윪??띕쐻???醫?????醫롫윪????醫롫윪??(嶺뚢뼰維???β돦裕녽???醫??????醫롫윥??
          setSelectedStock({ ...summaryStock, history: null }); 

          const docRef = doc(db, "stock_analysis", summaryStock.id);
          const docSnap = await getDoc(docRef);

          if (docSnap.exists()) {
              const fullData = docSnap.data();
              console.log("Fetched Data:", fullData);
              const mergedData = { ...summaryStock, ...fullData };
              
              setSelectedStock(mergedData);
              
              // Keep the list pane in sync with the fetched full detail.
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

  // [??醫롫윪?? ??醫??묕퐛??& ??醫롫윥???β돦裕뉐퐲?(useMemo??嶺뚣끉裕???
  const filteredStocks = React.useMemo(() => {
      // 1. Base filtering
      let result = stocks.filter(stock => {
          // 嶺뚮씭?????醫???
          const market = stock.id.startsWith('KR_') ? 'KR' : 'US';
          if (market !== selectedMarket) return false;
          // Non-admin users should treat sell signals as squeeze for visibility/filtering.
          let effectiveType = stock.type;
          if (!isAdmin && stock.type === 'sell_signal') {
              effectiveType = 'squeeze';
          }
          
          if (!selectedPatterns.includes(effectiveType)) return false;
          return true;
      });

      // 2. ??醫롫윥??
      result.sort((a, b) => {
          const aStatus = normalizeStatusText(a.status, a.type);
          const bStatus = normalizeStatusText(b.status, b.type);
          const aSuspended = a.type === 'suspended' || /거래정지|suspend/i.test(aStatus) ? 1 : 0;
          const bSuspended = b.type === 'suspended' || /거래정지|suspend/i.test(bStatus) ? 1 : 0;
          if (aSuspended !== bSuspended) return aSuspended - bSuspended;

          let valA, valB;

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
  }, [stocks, selectedMarket, selectedPatterns, sortConfig, isAdmin]);

  // ??醫롫윥獄?? ??醫?????醫롫짗??
  const togglePattern = (type) => {
      setSelectedPatterns(prev => {
          if (type === 'ALL') {
              // ??醫롫윪????醫?繹???醫롫윪????醫롫짗??
              const all = ['squeeze', 'buy_signal', 'normal', 'suspended'];
              if (isAdmin) all.push('sell_signal'); // ??㉱?洹먮봿???嶺뚮씞?뉒뙴袁?쐻???醫???
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

  // [?怨뺥넪??] ?β돦裕?????醫롫윪?議얜쐻???醫롫윥????醫롫윪?醫묒?? ??醫롫윪??
  if (!user) {
      return (
          <>
            <LandingPage onLogin={() => setShowLoginModal(true)} />
             {/* ?β돦裕???嶺뚮ㅄ維??(??醫롫윥????醫롫윪?醫묒????醫롫윪?????醫롫윪??????醫롫윪????? */}
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


  // [?怨뺥넪??] ?β돦裕?????醫롫윪?????醫롫윪???醫롫짗?? ??醫롫짗?? ?롪퍔???(member) - ??醫롫윪????醫롫짗????醫롫윥??
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
      
      {/* 嶺뚮∥?????醫롫윪??(??レ뒩?쒌깺苑닺눧濡걔?+ ??醫롫윪???醫롫윥??+ ???쳜??λ쐻?+ ??醫롫윪?쒌깺苑닺눧濡걔? */}
      <div className="flex flex-1 overflow-hidden">
        
        {/* ??レ뒩????⑹탪??(??㉱?洹먮봿????醫롫윪????醫롫윪?? */}
        {!isAdmin && <AdBanner position="LEFT" className="hidden 2xl:flex w-[160px] flex-shrink-0 border-r" />}

        {/* ??醫롫윪???醫롫윥??*/}
        <div className="w-1/3 min-w-[320px] bg-white border-r border-gray-200 flex flex-col shadow-lg z-10">
        <div className="p-6 border-b border-gray-200 bg-slate-900 text-white">
          <h1 className="text-xl font-bold flex items-center gap-2">
            <Activity className="text-yellow-400" />
            MESUGAK
          </h1>
          <div className="mt-2 flex justify-between items-end">
            <p className="text-xs text-slate-400">AI 스캐너 결과 ({stocks.length})</p>
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
        
        {/* [?怨뺥넪??] ??醫???UI */}
        <div className="p-3 bg-white border-b border-gray-200 space-y-3">
            {/* 嶺뚮씭?????醫?繹?*/}
            <div className="flex rounded-md bg-gray-100 p-1">
                {['KR', 'US'].map(m => (
                    <button 
                        key={m}
                        onClick={() => setSelectedMarket(m)}
                        className={`flex-1 text-sm py-1.5 rounded font-medium transition-all ${selectedMarket === m ? 'bg-white shadow text-slate-900' : 'text-gray-400 hover:text-gray-600'}`}
                    >
                        {m === 'KR' ? '한국 시장' : '미국 시장'}
                    </button>
                ))}
            </div>

            {/* [??醫롫윪?? ??醫???嶺뚳퐢?얍칰類좎낯筌먦끇裕?(??醫롫윥?? */}
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
                    // [?곌랜?삯뇡? 嶺뚮씞?뉒뙴袁?쾸?⑥궡?? ??㉱?洹먮봿?????醫롫윪??
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

            {/* [?怨뺥넪??] ??醫롫윥????醫롫윪??(??醫롫윥?? */}
            <div className="flex gap-1 items-stretch h-8">
                 {/* ??醫롫윥???リ옇??? ??醫?繹?*/}
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
                 
                 {/* ?꾩렮維싧젆???醫롫짗?? */}
                 <button 
                    onClick={() => setSortConfig(prev => ({ ...prev, direction: prev.direction === 'asc' ? 'desc' : 'asc' }))}
                    className="w-8 flex items-center justify-center border border-gray-200 rounded bg-white text-gray-500 hover:text-slate-800"
                    title={sortConfig.direction === 'asc' ? 'Ascending' : 'Descending'}
                 >
                     {sortConfig.direction === 'asc' ? '↑' : '↓'}
                 </button>
            </div>
        </div>

        <div className="flex-1 overflow-y-auto">
          {filteredStocks.length === 0 ? (
            <div className="p-10 text-center text-gray-400">조건에 맞는 종목이 없습니다.</div>
          ) : (
            filteredStocks.map((stock) => (
              <SidebarItem 
                key={stock.id}
                stock={stock}
                isSelected={selectedStock?.id === stock.id}
                onClick={handleStockClick}
                isLoggedIn={isAdmin} // [?곌랜?삯뇡? SideItem????㉱?洹먮봿????醫롫짗?? ??醫롫윥??(?????β돦裕뉐퐲??
                getStatusColor={getStatusColor}
              />
            ))
          )}
        </div>
      </div>

      {/* 嶺뚮∥?????醫롫윥??*/}
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
        {/* ??醫롫윪????⑹탪??(??㉱?洹먮봿????醫롫윪????醫롫윪?? */}
        {!isAdmin && <AdBanner position="RIGHT" className="hidden 2xl:flex w-[160px] flex-shrink-0 border-l" />}
      </div>

      {/* ??醫롫윥????⑹탪??(???醫롫짗????醫롫윪??/ ??㉱?洹먮봿????醫롫윪?? */}
      {!isAdmin && <AdBanner position="BOTTOM" className="h-[90px] w-full flex-shrink-0 border-t z-20" />}

      {/* ?β돦裕???嶺뚮ㅄ維??*/}
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



