const blue = '#2563eb';
const teal = '#0f766e';
const amber = '#b45309';
const gray = '#64748b';

const illustrations = {
  cloudRsi: {
    label: '가격은 구름대 위에 있지만 RSI는 67에서 58로 낮아진 예시',
    caption: '가격의 위치와 상승 힘은 서로 다른 질문이에요.',
    art: <>
      <path d="M18 55 L115 61 L205 65 L340 70 L340 93 L205 86 L115 83 L18 76Z" fill="#d7f1eb" />
      <path d="M18 42 L100 36 L180 34 L260 43 L340 39" fill="none" stroke={blue} strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
      <text x="20" y="24" fill={blue}>종가 102</text><text x="264" y="87" fill={teal}>구름대 상단 98</text>
      <line x1="18" y1="128" x2="340" y2="128" stroke={gray} strokeDasharray="4 4" />
      <path d="M40 107 L118 101 L203 113 L282 132" fill="none" stroke={amber} strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="282" cy="132" r="4" fill={amber} /><text x="20" y="156" fill={gray}>RSI 67 → 58</text><text x="247" y="151" fill={gray}>신호선 60</text>
    </>,
  },
  bandVolume: {
    label: '종가가 볼린저 상단을 넘었지만 거래량은 최근 평균의 0.8배인 예시',
    caption: '선은 넘었는데, 거래 참여는 아직 조용하네요.',
    art: <>
      <path d="M20 78 Q150 70 240 57 L340 50 M20 103 Q150 98 240 96 L340 93" fill="none" stroke={gray} strokeWidth="2" strokeDasharray="5 4" />
      <path d="M20 91 L88 88 L158 80 L228 72 L296 40 L340 37" fill="none" stroke={blue} strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="296" cy="40" r="4" fill={blue} /><text x="20" y="25" fill={blue}>종가 100.8 &gt; 상단 100</text>
      <text x="22" y="120" fill={gray}>거래량</text><line x1="95" y1="135" x2="340" y2="135" stroke={amber} strokeDasharray="4 4" />
      <rect x="116" y="132" width="24" height="29" rx="3" fill="#bfdbfe" /><rect x="163" y="125" width="24" height="36" rx="3" fill="#bfdbfe" />
      <rect x="210" y="130" width="24" height="31" rx="3" fill="#bfdbfe" /><rect x="257" y="140" width="24" height="21" rx="3" fill={blue} />
      <text x="286" y="151" fill={amber}>평균의 0.8배</text>
    </>,
  },
  movingAverage: {
    label: '종가는 60일선 위에 있지만 볼린저 하단은 60일선 아래로 내려간 예시',
    caption: '종가만 보면 회복, 하단 밴드까지 보면 다른 장면이에요.',
    art: <>
      <text x="27" y="27" fill={gray}>어제</text><text x="249" y="27" fill={gray}>오늘</text>
      <path d="M45 79 L235 87" fill="none" stroke={gray} strokeWidth="3" strokeLinecap="round" />
      <path d="M45 70 L235 128" fill="none" stroke={amber} strokeWidth="3" strokeLinecap="round" />
      <circle cx="235" cy="48" r="6" fill={blue} /><text x="248" y="52" fill={blue}>종가 101</text>
      <text x="248" y="91" fill={gray}>60일선 100</text><text x="248" y="132" fill={amber}>하단 98.8</text>
      <line x1="45" y1="145" x2="275" y2="145" stroke="#cbd5e1" /><text x="113" y="165" fill={gray}>하단 밴드가 아래로 교차</text>
    </>,
  },
  pbrPeers: {
    label: '두 기업의 PBR은 0.8배로 같지만 업종 중앙값은 각각 0.6배와 1.2배인 예시',
    caption: '같은 0.8배라도 비교 대상이 바뀌면 위치가 달라져요.',
    art: <>
      <text x="31" y="26" fill={gray}>A은행</text><text x="216" y="26" fill={gray}>B제조사</text>
      <line x1="20" y1="137" x2="170" y2="137" stroke="#cbd5e1" /><line x1="196" y1="137" x2="346" y2="137" stroke="#cbd5e1" />
      <rect x="40" y="56" width="36" height="81" rx="4" fill={blue} /><rect x="92" y="76" width="36" height="61" rx="4" fill="#99a9b9" />
      <rect x="216" y="56" width="36" height="81" rx="4" fill={blue} /><rect x="268" y="16" width="36" height="121" rx="4" fill="#99a9b9" />
      <text x="45" y="51" fill={blue}>0.8</text><text x="97" y="71" fill={gray}>0.6</text>
      <text x="221" y="51" fill={blue}>0.8</text><text x="273" y="13" fill={gray}>1.2</text>
      <text x="34" y="158" fill={blue}>기업</text><text x="85" y="158" fill={gray}>업종</text><text x="210" y="158" fill={blue}>기업</text><text x="261" y="158" fill={gray}>업종</text>
    </>,
  },
  sharedPrice: {
    label: '하나의 종가 105를 구름대 100, 60일선 103, 볼린저 중심선 104.5와 비교한 예시',
    caption: '기준선은 셋이어도 출발점은 같은 종가 105예요.',
    art: <>
      <text x="18" y="28" fill={blue}>종가 105</text><line x1="120" y1="24" x2="340" y2="24" stroke={blue} strokeWidth="4" />
      <text x="18" y="66" fill={teal}>중심선 104.5</text><line x1="120" y1="62" x2="340" y2="62" stroke={teal} strokeWidth="2" />
      <text x="18" y="105" fill={gray}>60일선 103</text><line x1="120" y1="101" x2="340" y2="101" stroke={gray} strokeWidth="2" />
      <text x="18" y="144" fill={amber}>구름대 100</text><line x1="120" y1="140" x2="340" y2="140" stroke={amber} strokeWidth="2" />
    </>,
  },
  rsiBelowCloud: {
    label: 'RSI는 28에서 34로 30선을 회복했지만 종가 92는 구름대 하단 97 아래인 예시',
    caption: '단기 힘은 돌아와도 가격은 아직 구름대 아래예요.',
    art: <>
      <text x="18" y="28" fill={teal}>RSI 28 → 34</text><line x1="153" y1="63" x2="339" y2="63" stroke={gray} strokeDasharray="4 4" />
      <path d="M160 76 L216 81 L280 48 L337 38" fill="none" stroke={teal} strokeWidth="3" strokeLinecap="round" /><text x="20" y="67" fill={gray}>기준 30</text>
      <path d="M154 105 L340 108 L340 133 L154 127Z" fill="#d7f1eb" /><text x="18" y="120" fill={teal}>구름대 하단 97</text>
      <path d="M154 146 L216 151 L280 145 L337 155" fill="none" stroke={blue} strokeWidth="3" strokeLinecap="round" /><text x="20" y="158" fill={blue}>종가 92</text>
    </>,
  },
  freshness: {
    label: '화면 분석 기준일은 T−2 거래일이고 제공기관의 확인 가능한 최신 자료는 T인 예시',
    caption: '분석을 읽기 전에 기준일이 어디에 멈췄는지 보세요.',
    art: <>
      <line x1="54" y1="95" x2="313" y2="95" stroke="#cbd5e1" strokeWidth="4" />
      <circle cx="54" cy="95" r="9" fill={amber} /><circle cx="184" cy="95" r="7" fill="#cbd5e1" /><circle cx="313" cy="95" r="9" fill={teal} />
      <text x="35" y="63" fill={amber}>화면 기준일</text><text x="275" y="63" fill={teal}>최신 자료</text>
      <text x="41" y="132" fill={gray}>T−2</text><text x="174" y="132" fill={gray}>T−1</text><text x="308" y="132" fill={gray}>T</text>
      <text x="113" y="160" fill={amber}>두 거래일의 입력 차이</text>
    </>,
  },
  missingData: {
    label: '80개 일봉은 최소 120행에 못 미쳐 분석을 보류하고, 120행 이상에서 RSI만 없으면 해당 가중치만 제외하는 예시',
    caption: '전체 입력 부족과 지표 하나의 누락은 다르게 다뤄요.',
    art: <>
      <text x="18" y="28" fill={gray}>입력 A · 일봉 80행</text><rect x="18" y="40" width="250" height="18" rx="9" fill="#e2e8f0" />
      <rect x="18" y="40" width="167" height="18" rx="9" fill={amber} /><text x="278" y="54" fill={amber}>분석 보류</text>
      <text x="18" y="99" fill={gray}>입력 B · 120행 이상</text><rect x="18" y="111" width="250" height="18" rx="9" fill="#e2e8f0" />
      <rect x="18" y="111" width="250" height="18" rx="9" fill={teal} /><text x="278" y="125" fill={teal}>계산 진행</text>
      <text x="18" y="159" fill={gray}>RSI 값만 없으면 RSI 가중치를 빼고 다시 계산</text>
    </>,
  },
};

export default function CaseStudyVisual({ visual }) {
  const illustration = illustrations[visual];
  if (!illustration) return null;

  return (
    <figure className="case-study-visual">
      <svg viewBox="0 0 360 180" role="img" aria-label={illustration.label} preserveAspectRatio="xMidYMid meet">
        {illustration.art}
      </svg>
      <figcaption>{illustration.caption}</figcaption>
    </figure>
  );
}
