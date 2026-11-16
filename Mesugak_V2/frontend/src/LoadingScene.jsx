import { BRAND_FULL, BRAND_SHORT } from './brand';

const loadingCandles = [
  { x: 20, wickTop: 74, wickBottom: 126, bodyY: 91, bodyHeight: 22, tone: 'down' },
  { x: 44, wickTop: 66, wickBottom: 116, bodyY: 78, bodyHeight: 23, tone: 'up' },
  { x: 68, wickTop: 59, wickBottom: 108, bodyY: 68, bodyHeight: 22, tone: 'up' },
  { x: 92, wickTop: 70, wickBottom: 112, bodyY: 80, bodyHeight: 19, tone: 'down' },
  { x: 116, wickTop: 50, wickBottom: 101, bodyY: 61, bodyHeight: 24, tone: 'up' },
  { x: 140, wickTop: 41, wickBottom: 91, bodyY: 50, bodyHeight: 23, tone: 'up' },
  { x: 164, wickTop: 29, wickBottom: 78, bodyY: 37, bodyHeight: 24, tone: 'up' },
];

export function AnalysisLoadingScene({ themeClass = 'theme-light', message = '기술지표 데이터를 불러오는 중' }) {
  return (
    <main className={`loading-screen ${themeClass}`} aria-busy="true" aria-live="polite">
      <div className="loading-panel">
        <p className="loading-kicker">{BRAND_FULL}</p>
        <div className="loading-board" aria-hidden="true">
          <div className="loading-board-top">
            <span className="loading-board-label">MARKET CLASSROOM</span>
            <span className="loading-board-status">STUDY MODE</span>
          </div>
          <svg className="loading-board-chart" viewBox="0 0 220 150" role="presentation">
            <defs>
              <linearGradient id="loading-trend-fill" x1="0" x2="0" y1="0" y2="1">
                <stop offset="0" stopColor="#ffcc67" stopOpacity="0.24" />
                <stop offset="1" stopColor="#ffcc67" stopOpacity="0" />
              </linearGradient>
            </defs>
            <path className="loading-grid" d="M12 34H208M12 63H208M12 92H208M12 121H208M36 18V132M76 18V132M116 18V132M156 18V132M196 18V132" />
            <g className="loading-candles">
              {loadingCandles.map((candle) => (
                <g className={`loading-candle loading-candle-${candle.tone}`} key={candle.x}>
                  <line className="loading-candle-wick" x1={candle.x} x2={candle.x} y1={candle.wickTop} y2={candle.wickBottom} />
                  <rect className="loading-candle-body" x={candle.x - 6} y={candle.bodyY} width="12" height={candle.bodyHeight} rx="2" />
                </g>
              ))}
            </g>
            <path className="loading-trend-fill" d="M12 126C35 121 44 109 64 112C83 115 91 91 108 94C128 97 135 67 151 71C169 76 176 39 208 22V132H12Z" />
            <path className="loading-trend-path" pathLength="1" d="M12 126C35 121 44 109 64 112C83 115 91 91 108 94C128 97 135 67 151 71C169 76 176 39 208 22" />
            <circle className="loading-trend-dot" cx="208" cy="22" r="4" />
            <path className="loading-arrow" d="M194 23L208 22L204 35" />
          </svg>
          <span className="loading-board-caption">조건을 읽고 상승·하락 흐름을 정리해요</span>
        </div>
        <div className="loading-copy">
          <strong>{BRAND_SHORT}</strong>
          <span className="loading-message" role="status">{message}</span>
          <span className="loading-hint">차트와 지표를 준비하고 있어요</span>
        </div>
        <div className="loading-meter" aria-hidden="true"><span /></div>
      </div>
    </main>
  );
}
