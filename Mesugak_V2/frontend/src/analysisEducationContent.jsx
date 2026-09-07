/* eslint-disable react-refresh/only-export-components */
/*
 * 기술지표분석교실의 공개 교육 문구를 모아 둔 파일입니다.
 *
 * 문구를 고치거나 조건·패턴을 추가/삭제할 때는 이 파일만 수정하면 됩니다.
 * - reasonExplanations: 조건 상세창의 뜻·해석 이유·같이 볼 항목
 * - reasonGraphicMap: 조건 상세창에 연결할 설명 그림
 * - publicStateLabel / publicStateExplanation: 지표별 상태 제목과 요약
 * - educationalGuides: '패턴 기준 보기'의 제목·항목·그림
 *
 * reasonExplanations의 키는 백엔드 reason 키에서 접두사를 뺀 이름을 사용합니다.
 * 해석 문장의 마지막 격식체는 화면에서 자연스러운 교실 말투로 자동 보정됩니다.
 */

export const educationUiCopy = {
  reasonModalTitle: '조건 상세 설명',
  reasonMeaningLabel: '조건의 뜻',
  reasonInterpretationLabel: '볼 수 있는 이유',
  reasonCheckLabel: '확인하면 좋을 것',
  guideTitleSuffix: '읽는 법',
  guideIntro: '이 지표에서 자주 나타나는 패턴과 기준 점수입니다. 캔들과 지표 선의 움직임을 자세히 확인해 보세요.',
  disclaimerTitle: '교육용 해설 안내',
  disclaimerText: '이 내용은 기술지표를 읽는 방법을 설명해요. 하나의 조건만으로 매수·매도·보유 판단을 확정하지 말고, 다른 지표와 시장 상황을 함께 살펴보세요.',
};

const analysisReasonLabels = {
  ichimoku_price_above_cloud: '주가가 구름대 위에 위치', ichimoku_price_below_cloud: '주가가 구름대 아래에 위치', ichimoku_tenkan_above_kijun: '전환선이 기준선 위에 위치', ichimoku_tenkan_below_kijun: '전환선이 기준선 아래에 위치', ichimoku_forward_cloud_bullish: '선행 구름이 상승 방향', ichimoku_forward_cloud_bearish: '선행 구름이 하락 방향', bollinger_state_squeeze_release_up: '밴드 수축 뒤 상방 확장 조건', bollinger_state_squeeze: '밴드 수축 상태', bollinger_state_upper_band_release: '상단 밴드 확장 조건', bollinger_state_below_lower_band: '하단 밴드 이탈 주의', ma_support_lower_band_above_ma60: '하단 밴드가 장기 이동평균 위에 위치', ma_support_lower_band_cross_above_ma60: '하단 밴드가 장기 이동평균을 상향 통과', ma_support_lower_band_cross_below_ma60: '하단 밴드가 장기 이동평균을 하향 통과', rsi_crossed_above_50_with_signal: 'RSI가 기준선 위로 회복', rsi_oversold_recovery: 'RSI 과매도 구간 회복', rsi_breakdown: 'RSI 약화 신호', price_breakout_with_relative_volume: '가격 확장과 거래량 확인', squeeze_release_lacks_volume: '확장 조건 대비 거래량 확인 부족', below_bollinger_lower: '하단 밴드 이탈', downside_band_expansion: '하방 밴드 확장', below_ichimoku_cloud: '구름대 하단 이탈', failed_box_breakout: '박스권 돌파 실패', bollinger_lower_crossed_above_ma60: '하단 밴드가 장기 이평선을 상향 돌파', bollinger_lower_above_ma60: '하단 밴드가 장기 이평선 위에 위치', bollinger_lower_crossed_below_ma60: '하단 밴드가 장기 이평선을 하향 돌파', negative_or_zero_earnings: '적자 또는 이익 없음', low_per: '낮은 PER', reasonable_per: '적정 PER', elevated_but_positive_per: '다소 높은 PER', high_per: '높은 PER', low_pbr: '낮은 PBR', reasonable_pbr: '적정 PBR', high_pbr: '높은 PBR', high_roe: '높은 ROE', positive_roe: '양의 ROE', negative_roe: '음의 ROE', manageable_debt: '관리 가능한 부채비율', high_debt: '높은 부채비율', operating_profit_growing: '영업이익 성장', operating_profit_shrinking: '영업이익 감소', price_above_cloud: '주가가 구름대 위에 위치', price_below_cloud: '주가가 구름대 아래에 위치', tenkan_above_kijun: '전환선이 기준선 위에 위치', tenkan_below_kijun: '전환선이 기준선 아래에 위치', bullish_forward_cloud: '선행 구름이 상승 방향', bearish_forward_cloud: '선행 구름이 하락 방향', chikou_confirmed: '후행스팬이 추세 확인', chikou_below_past_price: '후행스팬이 과거 주가 하회', bearish_rsi_divergence: 'RSI 하락 다이버전스', penalty_below_lower_band: '하단 밴드 이탈', valuation_state_valued: '가치 참고 조건 충족',
};

export function analysisReasonLabel(value) { const key = String(value || '').toLowerCase(); return analysisReasonLabels[key] || key.replaceAll('_', ' '); }

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

export function normalizedReasonKey(value) {
  return String(value || '').trim().toLowerCase().replaceAll('-', '_').replaceAll(' ', '_');
}

const reasonKeyPrefixes = ['ichimoku_', 'bollinger_', 'ma_support_', 'ma_', 'rsi_', 'volume_', 'valuation_', 'penalty_'];

function reasonKeyCandidates(value) {
  const candidates = [normalizedReasonKey(value)];
  for (let index = 0; index < candidates.length; index += 1) {
    const candidate = candidates[index];
    reasonKeyPrefixes.forEach((prefix) => {
      if (candidate.startsWith(prefix)) candidates.push(candidate.slice(prefix.length));
    });
    if (candidate.startsWith('state_')) candidates.push(candidate.slice('state_'.length));
  }
  return [...new Set(candidates.filter(Boolean))];
}

export function publicReasonLabel(value) {
  const candidates = reasonKeyCandidates(value);
  for (const candidate of candidates) {
    if (reasonExplanations[candidate]?.label) return reasonExplanations[candidate].label;
  }
  for (const candidate of candidates) {
    if (publicReasonLabels[candidate]) return publicReasonLabels[candidate];
    if (analysisReasonLabels[candidate]) return analysisReasonLabels[candidate];
  }
  return '추가 해설을 준비 중인 조건';
}

function friendlyInterpretation(value) {
  const text = String(value || '');
  const endings = [
    [/사용할 수 있습니다\.$/, '활용할 수도 있어요.'],
    [/해석할 수 있습니다\.$/, '해석할 수도 있어요.'],
    [/볼 수 있습니다\.$/, '볼 수도 있어요.'],
    [/될 수 있습니다\.$/, '될 수도 있어요.'],
    [/할 수 있습니다\.$/, '할 수도 있어요.'],
    [/해석합니다\.$/, '해석할 수도 있어요.'],
    [/경고로 봅니다\.$/, '경고로 읽을 수도 있어요.'],
    [/로 봅니다\.$/, '로 볼 수도 있어요.'],
    [/경계합니다\.$/, '주의해서 살펴볼 수도 있어요.'],
    [/경고합니다\.$/, '주의 신호로 읽을 수도 있어요.'],
    [/근거가 됩니다\.$/, '근거가 될 수도 있어요.'],
    [/근거입니다\.$/, '근거로 볼 수도 있어요.'],
    [/보조합니다\.$/, '보조할 수도 있어요.'],
    [/반영합니다\.$/, '반영할 수도 있어요.'],
    [/사용합니다\.$/, '활용할 수도 있어요.'],
    [/높입니다\.$/, '높여 볼 수도 있어요.'],
    [/둡니다\.$/, '볼 수도 있어요.'],
    [/필요합니다\.$/, '필요할 수도 있어요.'],
    [/제외합니다\.$/, '제외해요.'],
    [/되지 않습니다\.$/, '되지 않아요.'],
    [/하지 않습니다\.$/, '하지 않아요.'],
    [/있습니다\.$/, '있어요.'],
    [/없습니다\.$/, '없어요.'],
    [/뜻입니다\.$/, '뜻이에요.'],
    [/의미입니다\.$/, '의미예요.'],
    [/상태입니다\.$/, '상태예요.'],
    [/조건입니다\.$/, '조건이에요.'],
    [/안전장치입니다\.$/, '안전장치예요.'],
    [/했습니다\.$/, '했어요.'],
    [/됐습니다\.$/, '됐어요.'],
    [/됩니다\.$/, '될 수도 있어요.'],
    [/합니다\.$/, '해요.'],
    [/봅니다\.$/, '볼 수도 있어요.'],
  ];
  const ending = endings.find(([pattern]) => pattern.test(text));
  return ending ? text.replace(ending[0], ending[1]) : text;
}

const reasonLesson = (label, meaning, interpretation, check) => ({
  label,
  meaning,
  interpretation: friendlyInterpretation(interpretation),
  check,
});

const reasonExplanations = {
  no_data: reasonLesson('계산 데이터 부족', '해당 지표를 계산하는 데 필요한 일봉 수나 유효값이 부족한 상태입니다.', '점수가 낮다는 뜻이 아니라 판단을 보류했다는 뜻입니다. 데이터가 부족한 종목을 부정적으로 해석하지 않도록 종합점수의 해당 비중도 제외합니다.', '신규 상장 여부, 거래정지 구간, 누락된 일봉이 있는지 확인하고 데이터가 쌓인 뒤 다시 판단해야 합니다.'),
  bollinger_no_data: reasonLesson('볼린저 밴드 계산 데이터 부족', '최근 변동성과 밴드폭을 계산할 유효한 일봉이 충분하지 않습니다.', '밴드가 약하거나 강하다는 의미가 아니라 볼린저 조건을 아직 평가할 수 없다는 뜻입니다.', '상장 이력과 일봉 연속성을 확인하고 다른 지표도 데이터 부족 상태인지 함께 살펴보세요.'),
  ma_no_data: reasonLesson('이동평균 지지 조건 계산 불가', '60일 이동평균과 볼린저 하단 밴드의 관계를 계산할 자료가 부족합니다.', '장기 추세 지지 여부를 보류한 상태이며 긍정·부정 신호로 점수에 사용하지 않습니다.', '최소 계산 기간이 확보된 뒤 장기 이동평균의 방향과 가격 위치를 다시 확인해야 합니다.'),
  ichimoku_no_data: reasonLesson('일목균형표 계산 데이터 부족', '구름대와 선행·후행 조건을 만들 만큼 유효한 일봉이 충분하지 않습니다.', '일목균형표가 약세라는 뜻이 아니라 추세 환경을 판정하지 않았다는 의미입니다.', '구름대가 정상적으로 생성되는 시점까지 이동평균이나 거래량 같은 다른 조건만 참고하세요.'),
  rsi_no_data: reasonLesson('RSI 계산 데이터 부족', 'RSI와 RSI 시그널의 현재·이전 값을 안정적으로 비교할 자료가 부족합니다.', '모멘텀을 중립으로 본 것이 아니라 모멘텀 판단 자체를 보류한 상태입니다.', '일봉 누락 여부를 확인하고 충분한 기간이 쌓인 뒤 과열·침체와 기준선 회복 여부를 다시 보세요.'),
  volume_no_data: reasonLesson('거래량 비교 데이터 부족', '현재 거래량을 최근 평균과 비교하거나 직전 고점을 계산할 자료가 부족합니다.', '가격 움직임의 참여 강도를 확인하지 못했으므로 돌파를 확인하거나 부정할 수 없습니다.', '거래량 데이터가 정상인지 확인하고 가격 조건만으로 돌파를 단정하지 마세요.'),
  valuation_data_missing: reasonLesson('가치 참고자료 없음', '분석 데이터에 PER·PBR·ROE·부채비율·영업이익 증가율 중 사용할 값이 없었습니다.', '재무상태가 나쁘다는 뜻이 아니라 가치 참고 항목을 종합점수에서 제외했다는 의미입니다.', '사업보고서나 신뢰할 수 있는 재무자료에서 업종·성장률·일회성 손익까지 별도로 확인하세요.'),

  bullish: reasonLesson('긍정 조건 우세', '해당 지표 안에서 긍정 가점의 합이 주의 감점보다 큰 상태입니다.', '여러 하위 조건이 현재 추세나 모멘텀을 상대적으로 긍정적으로 설명한다는 뜻입니다.', '미래 상승을 보장하지 않으므로 반대 방향 조건과 거래량, 다음 일봉에서의 유지 여부를 함께 확인하세요.'),
  bearish: reasonLesson('주의 조건 우세', '해당 지표 안에서 주의 감점의 합이 긍정 가점보다 큰 상태입니다.', '추세나 모멘텀이 약해졌을 가능성을 먼저 살펴보라는 경고로 해석합니다.', '이미 하락이 많이 진행된 뒤 나타날 수도 있으므로 지지 구간과 반전 조건을 함께 확인하세요.'),
  neutral: reasonLesson('뚜렷한 방향 없음', '해당 지표의 긍정·주의 조건이 없거나 서로 상쇄된 상태입니다.', '방향성이 약하거나 전환 과정일 수 있어 성급하게 한쪽으로 해석하지 않습니다.', '다음 분석에서 어느 조건이 먼저 강화되는지와 다른 지표가 방향을 보완하는지 확인하세요.'),

  squeeze_release_up: reasonLesson('변동성 수축 뒤 상방 확장', '최근 밴드가 좁아졌던 구간 뒤에 밴드폭이 연속으로 넓어지고 종가가 상단 밴드 위로 나온 상태입니다.', '에너지가 모인 수축 구간을 위쪽으로 벗어나며 변동성과 방향이 동시에 커졌다는 점에서 긍정적인 추세 시작 후보로 해석할 수 있습니다.', '수축 자체는 방향을 말하지 않습니다. 거래량 증가, 상단 밴드 위 유지, 중심선 재이탈 여부를 확인해야 거짓 돌파 위험을 줄일 수 있습니다.'),
  squeeze: reasonLesson('변동성 수축 상태', '현재 볼린저 밴드폭이 최근 범위에서 매우 좁아 가격 변동성이 압축된 상태입니다.', '수축 뒤에는 변동성이 다시 커질 가능성이 있어 새로운 추세를 준비하는 관찰 구간으로 볼 수 있습니다.', '상승과 하락 어느 쪽으로도 확장될 수 있으므로 수축만으로 긍정 신호라고 보지 말고 돌파 방향과 거래량을 기다리세요.'),
  downside_expansion: reasonLesson('하방 변동성 확장', '종가가 하단 밴드 아래로 내려간 동시에 밴드폭이 넓어진 상태입니다.', '가격 하락과 변동성 확대가 함께 나타나 매도 압력이 커지는 국면일 가능성이 있어 주의 조건으로 해석합니다.', '과매도 반등도 가능하므로 하단 밴드 안으로 복귀하는지, 거래량과 중기 지지선이 어떻게 반응하는지 확인하세요.'),
  failed_release: reasonLesson('상단 돌파 유지 실패', '최근 상단 밴드를 돌파했던 가격이 다시 밴드 안쪽으로 깊게 돌아온 상태입니다.', '돌파 이후 매수세가 가격을 유지하지 못했다는 뜻일 수 있어 단기 추세의 힘이 약해졌다는 경고로 봅니다.', '정상적인 되돌림일 수도 있으므로 중심선 지지, 거래량 감소 여부, 이전 고점 재돌파를 함께 확인하세요.'),
  expansion_curl_neutral: reasonLesson('확장세 둔화', '밴드폭은 아직 넓지만 확장 속도나 상단 방향 조건 중 일부가 약해진 상태입니다.', '강한 움직임이 성숙 단계에 들어가거나 잠시 쉬어갈 수 있어 추가 추격보다 경과 관찰이 필요한 구간으로 해석합니다.', '둔화가 곧 반전을 뜻하지는 않습니다. 중심선과 추세선 유지, 거래량 변화, 밴드 재확장 여부를 보세요.'),
  recent_squeeze: reasonLesson('최근 변동성 수축 이력', '최근 일봉 구간에 밴드폭이 평소보다 매우 좁았던 시점이 존재합니다.', '변동성이 오랫동안 줄었다면 이후 가격 움직임이 커질 준비 구간일 수 있어 돌파 조건의 배경으로 사용합니다.', '수축은 방향을 알려주지 않으므로 상·하단 어느 쪽으로 이탈하는지와 거래량을 반드시 함께 확인하세요.'),
  bandwidth_expanding: reasonLesson('밴드폭 연속 확대', '볼린저 밴드폭이 하루만 넓어진 것이 아니라 최근 며칠 연속 확대되는 조건입니다.', '일시적인 흔들림보다 실제 변동성 국면 전환일 가능성을 높여 돌파 방향의 힘을 보조하는 근거가 됩니다.', '밴드폭 확대는 하락에서도 나타납니다. 가격이 중심선 어느 쪽에 있는지와 상·하단 밴드 방향을 같이 보세요.'),
  upper_band_release: reasonLesson('상단 밴드 위로 확장', '종가가 볼린저 상단 밴드 위에 있고 중심선보다도 높은 위치에 있습니다.', '상대적으로 높은 가격 영역을 매수세가 밀어 올렸다는 뜻이어서 추세가 위로 확장되는 후보로 해석할 수 있습니다.', '상단 밴드 접촉만으로 과매수나 매수를 단정할 수 없습니다. 다음 일봉의 유지, 거래량, 수축 선행 여부를 확인하세요.'),
  bandwidth_low_percentile: reasonLesson('밴드폭이 최근 최저권', '현재 밴드폭이 최근 관찰 기간의 최소 수준에 매우 가까운 상태입니다.', '시장 참여자 간 가격 합의 범위가 좁아졌고, 이후 균형이 깨질 때 변동성이 커질 가능성이 있는 준비 구간으로 봅니다.', '오랫동안 좁은 상태가 지속될 수 있으며 방향은 알 수 없습니다. 가격 이탈이 확인되기 전에는 중립적으로 읽으세요.'),
  volatility_compression: reasonLesson('가격 변동성 압축', '최근 가격의 표준편차가 줄면서 상단과 하단 밴드가 서로 가까워진 상태입니다.', '추세가 잠시 쉬거나 새로운 방향을 탐색하는 구간일 수 있어 이후 변동성 확대를 관찰할 이유가 됩니다.', '수축 기간이 길다고 큰 상승이 보장되지는 않습니다. 하방 이탈 가능성도 같은 비중으로 확인하세요.'),
  below_lower_band: reasonLesson('하단 밴드 아래로 이탈', '종가가 최근 평균과 변동성을 기준으로 만든 볼린저 하단 밴드보다 낮습니다.', '평소 범위를 벗어난 약한 가격 움직임이 나타났다는 뜻이어서 하락 압력이나 변동성 확대를 경계합니다.', '급락 뒤 과매도 반등일 수도 있습니다. 밴드 안 복귀, 거래량, 지지선과 RSI 회복을 함께 확인하세요.'),
  below_bollinger_lower: reasonLesson('볼린저 하단 이탈 위험', '종가가 볼린저 하단 밴드 아래에 있어 별도의 위험 플래그가 추가된 상태입니다.', '단순히 낮은 가격이 아니라 최근 변동 범위를 벗어난 하락이라는 점에서 위험 관리 비중을 높이는 신호로 사용합니다.', '하단 이탈이 하루짜리인지 지속되는지, 밴드폭이 확대되는지, 다음 종가가 밴드 안으로 복귀하는지 보세요.'),
  downside_band_expansion: reasonLesson('하방 밴드 확장', '밴드폭이 넓어지는 가운데 20일 이동평균도 하락하고 있습니다.', '변동성 확대와 중기 평균의 하향이 동시에 나타나 하락 흐름이 구조적으로 커질 가능성을 경고합니다.', '후행 지표 특성상 이미 하락한 뒤 잡힐 수 있습니다. 지지선 반응과 RSI·거래량의 반전 단서를 함께 확인하세요.'),
  failed_upper_band_release: reasonLesson('최근 상단 돌파 실패 가능성', '최근 며칠 안에 상단 밴드를 돌파했지만 현재 종가는 다시 상단 밴드 아래로 내려왔습니다.', '돌파를 따라온 매수세가 부족했거나 차익실현 압력이 커졌을 가능성이 있어 상승 지속성에 의문을 주는 조건입니다.', '중심선 위에서 안정되는 정상 조정일 수도 있으므로 중심선 이탈과 거래량, 이전 고점 회복 여부를 확인하세요.'),
  back_inside_band: reasonLesson('밴드 안쪽으로 복귀', '상단 돌파 뒤 가격의 밴드 내 상대 위치가 낮아져 다시 일반 변동 범위 안으로 들어왔습니다.', '돌파 직후의 강한 모멘텀이 약해졌다는 보조 증거로 사용하며, 실패 돌파 조건과 함께 나타날 때 주의도를 높입니다.', '밴드 안 복귀만으로 추세 종료를 단정하지 말고 중심선 지지와 이후 재돌파를 확인하세요.'),
  expanded_band_curling: reasonLesson('넓어진 밴드의 기울기 둔화', '밴드폭은 높은 수준이지만 확장 지속, 상단 밴드 기울기 또는 가격의 상단 위치가 약해졌습니다.', '강한 변동성 국면의 속도가 둔해지고 있다는 뜻이어서 추세 추격보다 힘의 유지 여부를 점검하는 구간으로 봅니다.', '속도 둔화는 횡보 후 재상승으로 이어질 수도 있습니다. 중심선과 거래량이 무너지기 전에는 반전으로 단정하지 마세요.'),
  no_bollinger_signal: reasonLesson('뚜렷한 볼린저 방향 없음', '수축 돌파, 하방 확장, 실패 돌파 중 어느 조건도 충분히 충족하지 않았습니다.', '볼린저 밴드만으로는 현재 방향을 설명하기 어려워 이 지표를 중립으로 둡니다.', '일목균형표·RSI·거래량이 더 명확한 근거를 제공하는지 보고 다음 밴드 변화까지 기다리세요.'),

  lower_band_cross_above_ma60: reasonLesson('하단 밴드가 60일선 상향 통과', '볼린저 하단 밴드가 전일에는 60일 이동평균 이하였지만 현재는 위로 올라왔습니다.', '가격 변동 범위의 낮은 경계까지 장기 평균 위로 이동했다는 뜻이어서 중기 추세 환경이 개선되는 후보로 해석합니다.', '이동평균은 후행하며 한 번의 교차는 흔들릴 수 있습니다. 60일선 기울기와 가격의 지속 위치를 확인하세요.'),
  lower_band_above_ma60: reasonLesson('하단 밴드가 60일선 위에 위치', '현재 볼린저 하단 밴드 전체가 60일 이동평균보다 위에 있습니다.', '통상적인 하락 변동 범위의 아래쪽조차 장기 평균 위에 있다는 점에서 중기 상승 추세의 완충 구간이 유지된다고 해석할 수 있습니다.', '실제 지지를 보장하지 않으며 밴드와 60일선 모두 후행합니다. 두 선의 기울기와 가격 이탈 여부를 함께 보세요.'),
  lower_band_cross_below_ma60: reasonLesson('하단 밴드가 60일선 하향 통과', '볼린저 하단 밴드가 전일에는 60일 이동평균 이상이었지만 현재는 아래로 내려왔습니다.', '가격의 통상 변동 범위가 장기 평균 아래로 넓어지기 시작했다는 뜻일 수 있어 중기 지지 약화를 경계합니다.', '일시적인 변동성 확대일 수도 있으므로 60일선 기울기, 종가 위치, 밴드 안 복귀 여부를 확인하세요.'),
  bollinger_lower_crossed_above_ma60: reasonLesson('하단 밴드가 장기 이평선 상향 돌파', '볼린저 하단 밴드가 60일 이동평균 아래에서 위로 교차했습니다.', '변동 범위의 하단이 장기 평균 위로 회복됐다는 점에서 추세의 바닥이 높아지는 초기 신호로 사용할 수 있습니다.', '교차 직후 재이탈 가능성이 있으므로 며칠간 유지되는지와 장기 이동평균 자체가 상승하는지 확인하세요.'),
  bollinger_lower_above_ma60: reasonLesson('하단 밴드가 장기 이평선 위', '볼린저 하단 밴드가 현재 60일 이동평균보다 높은 위치를 유지합니다.', '가격이 흔들려도 장기 평균 위 범위에서 움직일 가능성이 상대적으로 높다는 점에서 지지 환경의 보조 근거가 됩니다.', '지지는 확정 가격선이 아닙니다. 종가와 60일선의 관계, 거래량을 동반한 하향 이탈 여부를 같이 보세요.'),
  bollinger_lower_crossed_below_ma60: reasonLesson('하단 밴드가 장기 이평선 하향 이탈', '볼린저 하단 밴드가 60일 이동평균 위에서 아래로 교차했습니다.', '변동 범위가 장기 추세선 아래까지 열리기 시작했다는 의미라 중기 위험이 커질 수 있는 조건으로 봅니다.', '변동성 급증으로 잠깐 발생할 수 있으므로 종가도 60일선 아래인지와 다음 일봉의 복귀 여부를 확인하세요.'),

  price_above_cloud: reasonLesson('주가가 일목 구름대 위에 위치', '종가가 선행스팬 A와 B 중 더 높은 경계보다 위에 있습니다.', '일목 구름대는 최근 여러 기간의 균형 가격을 묶어 추세와 지지·저항 영역으로 해석합니다. 가격이 그 영역을 위로 벗어났다면 매수세가 균형 구간과 잠재 저항을 넘어선 것으로 볼 수 있어 긍정적인 추세 환경의 근거가 됩니다.', '구름대 위라는 사실만으로 상승이 계속되지는 않습니다. 전환선·기준선 관계, 선행 구름 방향, 구름 두께, 거래량과 재진입 여부를 함께 보세요.'),
  price_below_cloud: reasonLesson('주가가 일목 구름대 아래에 위치', '종가가 선행스팬 A와 B 중 더 낮은 경계보다 아래에 있습니다.', '가격이 균형 영역과 잠재 지지대를 아래로 벗어난 상태라 매도 압력이 우세하거나 구름대가 위쪽 저항으로 작용할 가능성을 경고합니다.', '이미 하락이 진행된 뒤 나타날 수 있습니다. 구름 안 복귀, 기준선 회복, 거래량 감소와 반전 패턴을 함께 확인하세요.'),
  tenkan_above_kijun: reasonLesson('전환선이 기준선 위에 위치', '단기 균형을 나타내는 전환선이 더 긴 기간의 균형을 나타내는 기준선보다 높습니다.', '단기 가격 중심이 중기 가격 중심보다 위라는 뜻이어서 최근 모멘텀이 중기 흐름보다 강한 긍정 조건으로 해석할 수 있습니다.', '단순 위치이며 오늘 막 교차했다는 뜻은 아닙니다. 두 선의 기울기와 가격·교차가 구름대 어느 위치에서 발생했는지 확인하세요.'),
  tenkan_below_kijun: reasonLesson('전환선이 기준선 아래에 위치', '단기 균형선인 전환선이 중기 기준선보다 낮습니다.', '최근 가격 중심이 중기 중심보다 약하다는 뜻이어서 단기 모멘텀 약화 또는 하락 추세의 보조 근거로 사용합니다.', '횡보장에서는 교차가 자주 뒤집힐 수 있습니다. 구름대 위치와 기준선 방향, 거래량을 함께 확인하세요.'),
  bullish_forward_cloud: reasonLesson('선행 구름이 상승 방향', '앞으로 이동해 표시되는 선행스팬 A가 선행스팬 B보다 높습니다.', '단기·중기 균형을 더 많이 반영하는 A가 장기 범위 중심인 B보다 높아 향후 표시 구간의 지지 구조가 상대적으로 긍정적으로 배열됐다고 해석합니다.', '미래 가격을 예언하는 선이 아니라 과거 계산값을 앞으로 옮겨 표시한 것입니다. 현재 가격 위치와 구름 두께를 함께 보세요.'),
  bearish_forward_cloud: reasonLesson('선행 구름이 약세 방향', '앞으로 이동해 표시되는 선행스팬 A가 선행스팬 B보다 낮습니다.', '향후 표시 구간의 균형 구조가 약세 방향으로 배열돼 구름대가 저항으로 작용할 가능성을 경계합니다.', '현재 가격이 이미 구름 위에 있으면 신호가 엇갈릴 수 있습니다. 구름 전환 시점과 두께, 가격 위치를 함께 확인하세요.'),
  chikou_confirmed: reasonLesson('후행 비교가 현재 추세를 확인', '이 분석에서는 현재 종가가 26개 일봉 전 종가보다 높은지를 비교합니다.', '현재 가격이 과거 동일 비교점보다 높으면 중기적으로 가격 수준이 상승했다는 단순 확인이 되어 긍정 추세의 보조 근거가 됩니다.', '전통적인 후행스팬 해석 전체를 대신하지 않습니다. 당시 가격대의 저항과 현재 구름대·기준선 관계를 함께 보세요.'),
  chikou_below_past_price: reasonLesson('후행 비교가 과거 가격보다 낮음', '현재 종가가 26개 일봉 전 종가보다 낮은 상태입니다.', '중기 비교에서 가격 수준이 낮아졌다는 뜻이므로 현재 추세의 힘이 약하거나 하락 방향일 가능성을 경고합니다.', '비교 기준일의 일시적 고점·저점에 영향을 받을 수 있으므로 다른 추세 조건과 함께 판단하세요.'),

  rsi_crossed_above_50_with_signal: reasonLesson('RSI가 기준선 위로 회복', 'RSI가 전일에는 50 아래였지만 현재 50 이상으로 올라왔고 자체 시그널선보다도 높습니다.', '상승폭과 하락폭의 상대적 힘이 중립선 위로 회복되고 단기 RSI 흐름도 개선됐다는 뜻이어서 모멘텀 전환의 긍정 근거로 해석합니다.', '50 부근에서는 왕복 신호가 잦습니다. 가격 추세와 거래량, 며칠간 기준선 위를 유지하는지 확인하세요.'),
  rsi_oversold_recovery: reasonLesson('RSI 과매도 구간 회복', 'RSI가 30 이하의 침체 구간에서 다시 30 위로 올라오고 시그널선도 웃돌았습니다.', '강한 매도 압력이 완화되고 단기 반등 모멘텀이 생겼을 가능성을 보여주므로 회복 후보로 해석합니다.', '하락 추세에서는 일시적 기술적 반등에 그칠 수 있습니다. 가격 지지와 거래량, 중립선까지 회복하는지 확인하세요.'),
  rsi_breakdown: reasonLesson('RSI 모멘텀 약화', 'RSI가 45 아래에 있고 시그널선보다 낮으며 전일보다도 하락했습니다.', '최근 상승폭보다 하락폭의 힘이 커지고 약화가 이어지는 조건이 겹쳐 단기 모멘텀 악화를 경고합니다.', '낮은 RSI가 곧 추가 하락을 뜻하지는 않습니다. 과매도 구간과 가격 지지, 상승 다이버전스 출현 여부를 함께 보세요.'),
  bearish_rsi_divergence: reasonLesson('RSI 약세 다이버전스', '가격은 최근 고점 부근을 유지하지만 RSI의 고점은 이전보다 뚜렷하게 낮아진 상태입니다.', '가격이 높아지는 동안 상승 속도와 힘이 따라오지 못한다는 뜻이어서 상승 추세가 지치거나 반전할 수 있다는 선행 경고로 해석합니다.', '다이버전스는 오래 지속될 수 있고 정확한 반전 시점을 주지 않습니다. 가격 지지 이탈이나 거래량 변화로 확인해야 합니다.'),

  breakout_confirmed: reasonLesson('가격 돌파와 거래량 확인', '가격이 최근 고점을 넘었고 거래량도 최근 평균보다 충분히 증가한 상태입니다.', '저항 돌파에 더 많은 시장 참여가 동반됐다는 뜻이어서 소수 거래로 생긴 일시적 움직임보다 지속 가능성이 높다는 보조 근거가 됩니다.', '뉴스성 일회 거래량이나 장중 돌파 후 밀림일 수 있습니다. 종가 유지와 다음 일봉의 후속 거래량을 확인하세요.'),
  price_breakout_with_relative_volume: reasonLesson('고점 돌파에 거래량 동반', '종가가 직전 20개 일봉의 고점을 넘고 거래량이 20일 평균의 1.5배 이상입니다.', '기존 저항을 넘는 가격 변화에 평소보다 많은 참여가 붙었다는 점에서 돌파의 신뢰도를 높이는 긍정 조건으로 해석합니다.', '거래량 기준은 유동성이 낮은 종목에서 왜곡될 수 있습니다. 돌파 가격을 유지하는지와 후속 거래량을 확인하세요.'),
  squeeze_release_weak_volume: reasonLesson('상방 확장 대비 거래량 부족', '볼린저 상방 확장 조건은 나타났지만 거래량이 최근 평균에 미치지 못한 상태입니다.', '가격은 움직였지만 참여 강도가 약해 돌파가 널리 확인되지 않았을 가능성이 있으므로 신뢰도를 낮춰 해석합니다.', '저유동성 종목이나 거래량이 원래 적은 시기일 수 있습니다. 다음 일봉의 거래량 증가와 상단 밴드 유지 여부를 보세요.'),
  squeeze_release_lacks_volume: reasonLesson('상방 확장 대비 거래량 확인 부족', '수축 뒤 상단 밴드 확장이 나타났지만 현재 거래량이 20일 평균보다 적습니다.', '추세 시작 후보를 뒷받침할 시장 참여가 부족하다는 뜻이어서 거짓 돌파 또는 짧은 반등 가능성을 함께 경계합니다.', '후속 거래량이 붙으면 해석이 달라질 수 있습니다. 가격 유지와 상대 거래량 변화를 다음 분석에서 확인하세요.'),
  no_volume_setup: reasonLesson('뚜렷한 거래량 확인 없음', '고점 돌파와 거래량 급증도, 상방 확장 중 거래량 부족 경고도 해당하지 않았습니다.', '거래량이 현재 해석을 강하게 지지하거나 반박하지 않아 중립으로 둔 상태입니다.', '가격 방향이 바뀔 때 거래량이 함께 증가하는지 다음 분석에서 확인하세요.'),

  valued: reasonLesson('가치 참고 조건 반영', '사용 가능한 PER·PBR·ROE·부채·이익 성장 자료를 내부 참고 구간에 따라 보조 점수로 반영했습니다. 이 교실에서는 PER 0 초과~10 이하, PBR 0 초과~1.5 이하를 낮은 참고 구간으로, PER 10 초과~20 이하와 PBR 1.5 초과~3 이하를 중간 참고 구간으로 봅니다. PBR 3 초과~5 이하는 별도 PBR 가감이 없는 구간이고, PBR 5 초과는 높은 참고 구간으로 분류합니다.', '가격 흐름만 보는 기술지표의 한계를 보완하기 위해 기업의 수익성과 재무 부담을 참고한 상태입니다. 여기서 낮고 높다는 표현은 시장 전체의 절대 기준이 아니라 이 분석에서 정한 교육용 구간이라고 이해할 수 있어요.', 'PER·PBR은 업종과 성장률에 따라 정상 범위가 크게 달라집니다. PBR이 0 이하이거나 값이 없으면 낮은 PBR로 보지 않고 해당 근거를 제외하며, 동일 업종 비교와 최신 공시를 반드시 함께 보세요.'),
  negative_or_zero_earnings: reasonLesson('이익이 없거나 PER 해석 곤란', '현재 PER 값이 0 이하로 계산돼 순이익이 없거나 일반적인 PER 비교가 어려운 상태입니다.', '지속적인 적자는 가치 평가와 재무 안정성에 부담이 될 수 있어 주의 조건으로 반영합니다.', '일회성 손실, 경기순환, 회계 요인일 수 있으므로 실제 손익계산서와 현금흐름을 확인하세요.'),
  low_per: reasonLesson('낮은 PER 참고 조건', 'PER가 0 초과~10 이하인 내부 낮은 참고 구간입니다. PER은 주가가 1년 이익의 몇 배인지 보는 값이라, 숫자가 10이면 이익의 10배 수준으로 가격이 매겨졌다고 읽습니다.', '같은 이익이 유지된다고 가정하면 투자자가 이익 1원에 지불하는 가격이 상대적으로 낮아 가치 여지가 있다는 보조 근거로 해석할 수도 있어요.', '낮은 PER은 성장 둔화나 이익 감소 위험을 반영한 가치 함정일 수 있습니다. 동일 업종과 미래 이익을 비교하세요.'),
  reasonable_per: reasonLesson('중간 PER 참고 조건', 'PER가 10 초과~20 이하인 내부 중간 참고 구간입니다.', '현재 이익 대비 가격 부담이 극단적이지 않다는 의미로 기술적 조건을 약하게 보조한다고 볼 수도 있어요.', '업종과 성장률에 따라 적정 배수는 크게 다릅니다. 이 구간만으로 저평가라고 판단하지 마세요.'),
  elevated_but_positive_per: reasonLesson('다소 높은 PER 참고 조건', 'PER가 20 초과~35 이하인 내부 다소 높은 참고 구간입니다.', '시장 기대가 가격에 어느 정도 반영됐을 수 있어 성장성이 실제로 뒷받침되는지 확인할 필요가 있다고 볼 수도 있어요.', '고성장 기업에는 자연스러울 수 있고 경기 고점의 일시적 이익 감소로 높아질 수도 있습니다. 업종과 성장률을 비교하세요.'),
  high_per: reasonLesson('높은 PER 주의 조건', 'PER가 50을 초과하는 내부 높은 참고 구간입니다. 35 초과~50 이하 구간은 별도 PER 가감 없이 중간 관찰 구간으로 둡니다.', '높은 성장 기대가 이미 가격에 반영돼 실적이 기대에 못 미칠 때 변동성이 커질 수 있어 주의 조건으로 해석할 수도 있어요.', 'PER 하나로 고평가를 확정할 수 없습니다. 성장률, 이익의 질, 업종 평균과 일회성 손익을 확인하세요.'),
  low_pbr: reasonLesson('낮은 PBR 참고 조건', 'PBR이 0 초과~1.5 이하인 내부 낮은 참고 구간입니다. PBR은 시장이 평가한 기업가치를 장부상 순자산으로 나눈 값이라, 1.0이면 장부가와 비슷하고 1.5면 장부가의 1.5배 수준으로 읽습니다.', '자산가치 대비 가격 부담이 낮을 가능성이 있어 자산 중심 업종에서는 가치 참고 근거로 해석할 수도 있어요.', '부실 자산이나 낮은 수익성을 반영한 것일 수 있고 무형자산 기업에는 의미가 약합니다. 자산의 질과 ROE를 함께 보세요.'),
  reasonable_pbr: reasonLesson('중간 PBR 참고 조건', 'PBR이 1.5 초과~3 이하인 내부 중간 참고 구간입니다. 3 초과~5 이하는 PBR만으로 별도 가감하지 않는 관찰 구간으로 둡니다.', '장부가치 대비 가격 부담이 지나치게 낮거나 높지 않은 구간이라, 다른 재무·기술 조건을 보조하는 중립적인 근거로 해석할 수도 있어요.', '업종별 자산 구조가 다르므로 동일 업종 비교와 ROE, 부채 수준을 함께 확인하세요.'),
  high_pbr: reasonLesson('높은 PBR 주의 조건', 'PBR이 5를 초과하는 내부 높은 참고 구간입니다.', '주가가 장부상 순자산의 5배를 넘어 높은 수익성과 성장 기대가 이미 반영됐을 수 있어 가격 부담이 커질 가능성을 경고한다고 볼 수도 있어요.', '브랜드·기술 같은 무형자산이 큰 기업에는 PBR이 높아도 자연스러울 수 있습니다. ROE와 업종 특성을 함께 보세요.'),
  high_roe: reasonLesson('높은 ROE 참고 조건', 'ROE가 15% 이상인 내부 높은 참고 구간입니다. ROE는 자기자본으로 얼마의 순이익을 냈는지 보는 비율입니다.', '주주가 투입한 자본을 효율적으로 이익으로 전환하고 있다는 의미라 수익성의 긍정적 보조 근거로 해석할 수도 있어요.', '과도한 부채나 일회성 이익도 ROE를 높일 수 있습니다. 부채비율과 이익의 지속성을 함께 확인하세요.'),
  positive_roe: reasonLesson('양호한 ROE 참고 조건', 'ROE가 8% 이상~15% 미만인 내부 양호 구간입니다.', '자기자본으로 일정 수준의 이익을 내고 있다는 점에서 재무 보조 근거로 이해할 수도 있어요.', '업종 평균과 자본 구조에 따라 의미가 다릅니다. 여러 해의 추세와 부채를 함께 보세요.'),
  negative_roe: reasonLesson('음의 ROE 주의 조건', '자기자본 대비 순이익이 음수인 상태입니다.', '주주자본이 이익을 만들지 못하고 손실이 발생했다는 뜻일 수 있어 재무 위험을 경고합니다.', '일회성 손실이나 구조조정 영향일 수 있으므로 최근 여러 기간의 순이익과 현금흐름을 확인하세요.'),
  manageable_debt: reasonLesson('부채 부담이 내부 기준 이하', '부채비율이 100% 이하인 내부 관리 가능한 참고 구간입니다.', '재무 레버리지 부담이 상대적으로 낮아 경기 악화나 금리 상승에 대응할 여지가 있다는 보조 근거로 해석할 수도 있어요.', '금융업처럼 업종 구조상 부채가 큰 산업에는 같은 기준을 적용하기 어렵습니다. 업종 평균과 이자 부담을 보세요.'),
  high_debt: reasonLesson('높은 부채비율 주의', '부채비율이 200%를 초과하는 내부 높은 참고 구간입니다. 100% 초과~200% 이하는 부채만으로 별도 가감하지 않는 관찰 구간입니다.', '이자와 상환 부담이 커져 실적 악화 시 재무 위험이 확대될 수 있으므로 주의 조건으로 해석할 수도 있어요.', '안정적인 현금흐름이 있거나 업종 특성상 높은 부채가 일반적일 수 있습니다. 이자보상 능력과 만기 구조를 확인하세요.'),
  operating_profit_growing: reasonLesson('영업이익 성장 참고 조건', '영업이익 증가율이 10% 이상인 내부 긍정 참고 구간입니다.', '본업에서 벌어들이는 이익이 늘었다는 뜻이어서 기술적 상승 조건을 뒷받침할 수 있는 기초 체력의 보조 근거로 해석할 수도 있어요.', '낮은 전년 기저나 일회성 비용 감소 효과일 수 있습니다. 매출 성장과 영업이익률의 지속성을 함께 보세요.'),
  operating_profit_shrinking: reasonLesson('영업이익 감소 주의', '영업이익 증가율이 -10% 이하인 내부 주의 참고 구간입니다.', '본업의 수익 창출력이 약해졌을 수 있어 가격의 긍정 신호가 실적으로 뒷받침되는지 재확인이 필요하다고 볼 수도 있어요.', '일시적 투자비용이나 계절성 때문일 수 있습니다. 원인과 향후 가이던스, 현금흐름을 확인하세요.'),

  penalty_below_lower_band: reasonLesson('하단 밴드 이탈 감점', '종가가 볼린저 하단 밴드 아래에 있어 종합점수에서 별도 위험 감점을 적용했습니다.', '최근 변동 범위를 벗어난 하락을 다른 긍정 조건보다 우선 경계하기 위한 안전장치입니다.', '과매도 반등 가능성도 있으므로 밴드 안 복귀 전까지는 긍정 점수만 보고 판단하지 마세요.'),
  below_ichimoku_cloud: reasonLesson('일목 구름대 하단 이탈 위험', '종가가 일목 구름대의 낮은 경계보다 아래에 있어 위험 플래그가 추가됐습니다.', '균형 가격대와 잠재 지지 영역을 모두 밑돈 상태라 추세 약화가 깊어졌을 가능성을 경고합니다.', '구름 안 복귀와 기준선 회복, 거래량 변화가 나타나는지 확인하세요.'),
  failed_box_breakout: reasonLesson('최근 고점 돌파 유지 실패', '전일에는 최근 고점 부근의 돌파 기준을 지켰지만 현재 종가는 그 아래로 내려왔습니다.', '저항을 넘으려던 시도가 이어지지 못했다는 뜻이어서 매수세 약화나 가짜 돌파 가능성을 경고합니다.', '작은 되돌림일 수도 있으므로 이전 고점 재돌파, 지지선과 거래량을 다음 일봉에서 확인하세요.'),
};

export function getReasonLesson(value) {
  for (const candidate of reasonKeyCandidates(value)) {
    if (reasonExplanations[candidate]) return reasonExplanations[candidate];
  }
  return reasonLesson(
    '추가 해설을 준비 중인 조건',
    '분석 코드가 조건을 기록했지만 아직 교실용 설명표에 연결되지 않았습니다.',
    '미번역 내부 코드를 그대로 보여주지 않고 중립 조건으로 표시했습니다.',
    '이 항목만으로 방향을 판단하지 말고 다른 지표와 다음 분석 갱신을 함께 확인하세요.',
  );
}


export function publicStateLabel(state) {
  const normalized = String(state || 'NEUTRAL').toUpperCase();
  const labels = {
    BULLISH: '상승 조건 우세',
    BEARISH: '약세 조건 주의',
    NEUTRAL: '중립 · 추적',
    NO_DATA: '계산 데이터 부족',
    SQUEEZE_RELEASE_UP: '수축 후 상방 확장',
    SQUEEZE: '변동성 수축',
    DOWNSIDE_EXPANSION: '하방 변동성 확장',
    FAILED_RELEASE: '상단 돌파 유지 실패',
    EXPANSION_CURL_NEUTRAL: '확장 흐름 둔화',
    LOWER_BAND_CROSS_ABOVE_MA60: '하단 밴드가 60일선 상향 통과',
    LOWER_BAND_ABOVE_MA60: '하단 밴드가 60일선 위',
    LOWER_BAND_CROSS_BELOW_MA60: '하단 밴드가 60일선 하향 통과',
    BREAKOUT_CONFIRMED: '돌파 · 거래량 확인',
    SQUEEZE_RELEASE_WEAK_VOLUME: '상방 확장 대비 거래량 부족',
    VALUED: '가치 참고 조건 충족',
    NORMAL: '특별한 위험 신호 없음',
    CAUTION: '주의 조건 확인',
    DEFENSIVE: '방어 조건 우세',
  };
  return labels[normalized] || '세부 분석 상태';
}

export function publicStateExplanation(key, state) {
  const normalized = String(state || '').toUpperCase();
  if (normalized === 'NO_DATA') return '계산에 필요한 일봉이나 유효값이 아직 충분하지 않아요. 약한 신호가 아니라 이번에는 판단을 보류한 상태라고 읽으면 돼요.';
  if (key === 'ichimoku' && normalized === 'BULLISH') return '구름대 위 위치와 전환선·기준선의 배열이 현재 추세 환경을 긍정적으로 뒷받침한다고 해석할 수도 있어요.';
  if (key === 'ichimoku' && normalized === 'BEARISH') return '가격과 균형선의 배열이 약한 쪽에 더 가까워, 구름대가 지지보다 저항으로 작용할 가능성을 살펴볼 수 있어요.';
  if (key === 'bollinger' && normalized === 'SQUEEZE_RELEASE_UP') return '변동성이 줄었던 구간 뒤에 밴드가 위쪽으로 넓어져, 새로운 상승 흐름이 시작되는 후보라고 해석할 수도 있어요.';
  if (key === 'bollinger' && normalized === 'DOWNSIDE_EXPANSION') return '가격이 하단 밴드 밖으로 밀리는 동안 변동성도 커져, 매도 압력이 강해지는 흐름이라고 해석할 수도 있어요.';
  if (key === 'bollinger' && normalized === 'FAILED_RELEASE') return '상단 밴드를 넘었던 힘이 이어지지 못해, 돌파의 지속성이 약해졌다고 해석할 수도 있어요.';
  if (key === 'bollinger' && normalized === 'EXPANSION_CURL_NEUTRAL') return '넓어지던 밴드의 힘이 둔해져, 강한 움직임이 잠시 쉬어 가는 구간이라고 볼 수도 있어요.';
  if (key === 'maSupport' && normalized === 'LOWER_BAND_CROSS_ABOVE_MA60') return '가격 변동 범위의 낮은 경계까지 60일선 위로 올라와, 중기 지지 환경이 개선되는 초기 모습이라고 볼 수도 있어요.';
  if (key === 'maSupport' && normalized === 'LOWER_BAND_ABOVE_MA60') return '가격이 흔들릴 수 있는 범위의 아래쪽도 60일선 위에 있어, 중기 지지 환경이 이어진다고 해석할 수도 있어요.';
  if (key === 'maSupport' && normalized === 'LOWER_BAND_CROSS_BELOW_MA60') return '가격 변동 범위가 60일선 아래까지 열리기 시작해, 중기 지지가 약해지는 모습이라고 볼 수도 있어요.';
  if (key === 'rsi' && normalized === 'BULLISH') return '최근 상승폭의 힘이 하락폭보다 상대적으로 커져, 가격 모멘텀이 회복되는 과정이라고 해석할 수도 있어요.';
  if (key === 'rsi' && normalized === 'BEARISH') return '가격을 밀어 올리는 힘이 이전보다 약해져, 단기 모멘텀이 식는 과정이라고 해석할 수도 있어요.';
  if (key === 'volume' && normalized === 'BREAKOUT_CONFIRMED') return '가격이 최근 고점을 넘을 때 평소보다 많은 거래가 함께 들어와, 돌파에 참여가 실렸다고 해석할 수도 있어요.';
  if (key === 'volume' && normalized === 'SQUEEZE_RELEASE_WEAK_VOLUME') return '가격은 위쪽으로 움직였지만 거래 참여가 충분히 늘지 않아, 돌파의 힘을 조금 더 확인해야 하는 상태라고 볼 수도 있어요.';
  if (key === 'volume' && normalized === 'NEUTRAL') return '거래량이 현재 가격 움직임을 강하게 뒷받침하거나 약화시키지 않아, 참여 강도는 중립이라고 볼 수도 있어요.';
  if (key === 'valuation' && normalized === 'VALUED') return '이 교실은 PBR 0 초과~1.5 이하를 낮은 참고 구간, 1.5 초과~3 이하를 중간 참고 구간, 5 초과를 높은 참고 구간으로 두고 PER·ROE·부채·영업이익 성장과 함께 기술적 흐름을 보충한다고 해석할 수도 있어요.';
  if ((key === 'maSupport' || key === 'rsi') && normalized === 'NEUTRAL') return '현재는 한 방향의 힘이 뚜렷하지 않아, 다음 분석에서 회복과 약화 중 어느 쪽이 먼저 강해지는지 지켜볼 수 있어요.';
  return publicStateNarrative(key, state);
}

export function isCautionReason(value) {
  const key = normalizedReasonKey(value);
  const cautionTokens = [
    'no_data', 'below_lower_band', 'downside_band_expansion', 'failed_upper_band_release',
    'back_inside_band', 'expanded_band_curling', 'no_bollinger_signal',
    'bollinger_lower_crossed_below_ma60', 'valuation_data_missing',
    'negative_or_zero_earnings', 'high_per', 'high_pbr', 'negative_roe', 'high_debt',
    'operating_profit_shrinking', 'price_below_cloud', 'tenkan_below_kijun',
    'bearish_forward_cloud', 'chikou_below_past_price', 'rsi_breakdown',
    'bearish_rsi_divergence', 'squeeze_release_lacks_volume', 'no_volume_setup',
    'below_bollinger_lower', 'below_ichimoku_cloud', 'failed_box_breakout',
  ];
  return cautionTokens.some((token) => key === token || key.endsWith('_' + token));
}

export function AnalysisContentsRail({ sections }) {
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
export const publicIndicatorGuides = {
  bollinger: { label: '볼린저밴드', focus: '최근 변동성이 줄어드는지 커지는지, 가격이 밴드의 어느 쪽에 있는지 함께 읽어 볼 수 있어요.' },
  maSupport: { label: '이동평균선', focus: '중장기 추세선 위에서 지지가 이어지는지, 흐름이 바뀌는지 살펴볼 수 있어요.' },
  ichimoku: { label: '일목균형표', focus: '구름대와 전환선·기준선의 위치를 비교해 현재 추세 환경을 읽어 볼 수 있어요.' },
  rsi: { label: 'RSI', focus: '가격 움직임의 힘이 회복되는지 약해지는지, 과열·침체 구간에 가까운지 살펴볼 수 있어요.' },
  volume: { label: '거래량 확인', focus: '가격 움직임에 얼마나 많은 시장 참여가 함께했는지 확인해 볼 수 있어요.' },
  valuation: { label: '가치 참고값', focus: '재무 참고값이 현재 기술적 흐름을 어느 정도 보완하는지 살펴볼 수 있어요.' },
};

function publicStateNarrative(key, state) {
  const normalized = String(state || '').toUpperCase();
  if (key === 'bollinger' && normalized.includes('SQUEEZE_RELEASE_UP')) return '변동성이 좁아진 뒤 위쪽으로 확장되는 모습이라, 상승 흐름이 시작되는 후보라고 해석할 수도 있어요.';
  if (key === 'bollinger' && normalized.includes('SQUEEZE')) return '변동성은 줄었지만 방향은 아직 드러나지 않아, 다음 확장을 기다리는 구간이라고 볼 수도 있어요.';
  if (key === 'bollinger' && normalized.includes('LOWER')) return '하단 밴드 쪽 압력이 커져, 가격의 힘이 약해진 상태라고 해석할 수도 있어요.';
  if (key === 'maSupport' && normalized.includes('ABOVE')) return '가격 변동 범위가 중장기 이동평균선 위에 있어, 지지 환경이 이어진다고 볼 수도 있어요.';
  if (key === 'maSupport' && normalized.includes('BELOW')) return '가격 변동 범위가 중장기 이동평균선 아래로 약해져, 추세 지지가 흔들리는 모습이라고 볼 수도 있어요.';
  if (key === 'ichimoku' && normalized.includes('ABOVE')) return '가격이 구름대 위 환경에 있어, 현재 추세 조건이 상대적으로 우호적이라고 해석할 수도 있어요.';
  if (key === 'ichimoku' && normalized.includes('BELOW')) return '가격이 구름대 아래 환경에 있어, 균형 구간이 지지보다 저항에 가까워졌다고 볼 수도 있어요.';
  if (key === 'rsi' && (normalized.includes('RECOVERY') || normalized.includes('ABOVE'))) return '상승폭의 힘이 다시 살아나는 과정이라고 해석할 수도 있어요.';
  if (key === 'rsi' && (normalized.includes('BREAK') || normalized.includes('WEAK'))) return '최근 상승 힘이 줄고 하락 힘이 커지는 과정이라고 해석할 수도 있어요.';
  return publicIndicatorGuides[key]?.focus || '이 지표와 다른 기술 조건이 같은 방향을 가리키는지 함께 읽어 볼 수 있어요.';
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

export const educationalGuides = {
  bollinger: {
    title: '볼린저 밴드',
    points: [
      { 
        label: '수축 뒤 상단 확장 조건',
        desc: '최근 15개 일봉 안에 밴드 수축이 있었고, 밴드폭이 3일 연속 넓어지면서 종가가 상단 밴드와 중심선 위에 있는지 함께 봐요. 변동성이 위쪽으로 풀리며 새 흐름이 시작되는 후보라고 해석할 수도 있어요.',
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
        label: '밴드폭 수축 조건',
        desc: '현재 밴드폭이 최근 25개 일봉의 최소 밴드폭에서 105% 이내인지 확인해요. 가격 움직임이 잠잠해져 에너지가 모이는 구간이며, 이후 어느 방향으로 균형이 깨지는지 기다리는 상태라고 볼 수도 있어요.',
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
        label: '하단 이탈·밴드 확장 조건',
        desc: '종가가 하단 밴드 아래에 있고 밴드폭도 전일보다 넓어진 경우예요. 가격 하락과 변동성 확대가 겹쳐 매도 압력이 커지는 과정이라고 해석할 수도 있어요.',
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
            <text x="160" y="112" fontSize="12" fill="#3b82f6" fontWeight="bold">하단 이탈 · 밴드폭 확대</text>
          </svg>
        )
      },
      { 
        label: '최근 상단 돌파 되돌림 조건',
        desc: '직전 5개 일봉 안에는 상단 돌파가 있었지만, 현재 종가는 다시 상단 아래에 있고 %B도 0.75 미만인지 확인해요. 돌파를 이어 갈 힘이 약해진 모습이라고 해석할 수도 있어요.',
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
        label: '하단 밴드의 60일선 상향 교차',
        desc: '주가나 단기 이동평균이 아니라, 볼린저 하단 밴드가 전일 60일선 아래에서 현재 위로 이동했는지 확인해요. 변동 범위의 바닥이 장기 평균 위로 높아지는 초기 모습이라고 해석할 수도 있어요.',
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
            <text x="180" y="80" fontSize="12" fill="#ef4444" fontWeight="bold">하단 밴드가 60일선 위</text>
            <text x="10" y="80" fontSize="11" fill="var(--accent-purple, #8b5cf6)">60일선(장기)</text>
            <text x="10" y="105" fontSize="11" fill="var(--text-soft)">볼린저 하단 밴드</text>
          </svg>
        )
      },
      { 
        label: '하단 밴드가 60일선 위',
        desc: '현재 볼린저 하단 밴드가 60일 이동평균 위에 있는 위치 조건이에요. 가격이 흔들리는 범위의 아래쪽도 장기 평균보다 높아 중기 지지 환경이 이어진다고 해석할 수도 있어요.',
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
            <text x="100" y="110" fontSize="12" fill="#ef4444" fontWeight="bold">하단 밴드가 60일선 위</text>
          </svg>
        )
      },
      { 
        label: '하단 밴드의 60일선 하향 교차',
        desc: '볼린저 하단 밴드가 전일 60일선 위에서 현재 아래로 이동했는지 확인해요. 가격 변동 범위가 장기 평균 아래까지 열리기 시작해 중기 지지가 약해지는 모습이라고 볼 수도 있어요.',
        graphic: (
          <svg viewBox="0 0 300 120" width="100%" height="100%" preserveAspectRatio="xMidYMid meet">
            <path d="M 10,70 L 280,60" fill="none" stroke="var(--accent-purple, #8b5cf6)" strokeWidth="2.5" />
            <Candle x={40} h={30} l={65} o={50} c={40} />
            <Candle x={80} h={35} l={70} o={40} c={55} />
            <Candle x={120} h={50} l={85} o={55} c={75} />
            <Candle x={160} h={70} l={100} o={75} c={90} />
            <Candle x={200} h={85} l={110} o={90} c={105} />
            <text x="10" y="60" fontSize="11" fill="var(--accent-purple, #8b5cf6)">60일선(장기)</text>
            <text x="140" y="45" fontSize="12" fill="#3b82f6" fontWeight="bold">하단 밴드 하향 교차</text>
          </svg>
        )
      }
    ]
  },
  ichimoku: {
    title: '일목균형표',
    points: [
      { 
        label: '종가가 현재 구름대 위',
        desc: '종가가 선행스팬 A와 B 중 더 높은 경계보다 위에 있는지 확인해요. 가격이 여러 기간의 균형 영역과 잠재 저항을 넘어, 추세 환경이 긍정적으로 바뀐 모습이라고 해석할 수도 있어요.',
        graphic: (
          <svg viewBox="0 0 300 120" width="100%" height="100%" preserveAspectRatio="xMidYMid meet">
            <path d="M 10,80 Q 150,70 280,60 L 280,110 Q 150,100 10,120 Z" fill="rgba(16,185,129,0.15)" stroke="rgba(16,185,129,0.5)" strokeWidth="1" />
            <Candle x={40} h={40} l={70} o={60} c={45} />
            <Candle x={90} h={45} l={65} o={45} c={55} />
            <Candle x={140} h={30} l={60} o={55} c={35} />
            <Candle x={190} h={20} l={50} o={35} c={25} />
            <Candle x={240} h={15} l={40} o={25} c={30} />
            <text x="110" y="30" fontSize="12" fill="#ef4444" fontWeight="bold">종가가 구름의 높은 경계 위</text>
            <text x="10" y="100" fontSize="11" fill="#10b981">양운(지지구름)</text>
          </svg>
        )
      },
      { 
        label: '종가가 현재 구름대 아래',
        desc: '종가가 선행스팬 A와 B 중 더 낮은 경계보다 아래에 있는지 확인해요. 가격이 균형 영역과 잠재 지지 아래로 밀려, 구름대가 위쪽 저항으로 작용하는 모습이라고 해석할 수도 있어요.',
        graphic: (
          <svg viewBox="0 0 300 120" width="100%" height="100%" preserveAspectRatio="xMidYMid meet">
            <path d="M 10,20 Q 150,40 280,30 L 280,70 Q 150,80 10,60 Z" fill="rgba(239,68,68,0.15)" stroke="rgba(239,68,68,0.5)" strokeWidth="1" />
            <Candle x={40} h={70} l={90} o={75} c={85} />
            <Candle x={90} h={65} l={100} o={85} c={70} />
            <Candle x={140} h={70} l={95} o={70} c={85} />
            <Candle x={190} h={80} l={110} o={85} c={100} />
            <Candle x={240} h={95} l={120} o={100} c={110} />
            <text x="120" y="100" fontSize="12" fill="#3b82f6" fontWeight="bold">종가가 구름의 낮은 경계 아래</text>
            <text x="10" y="45" fontSize="11" fill="#ef4444">음운(저항구름)</text>
          </svg>
        )
      },
      { 
        label: '전환선이 기준선 위',
        desc: '현재 전환선이 기준선보다 높은지 비교해요. 단기 가격 중심이 중기 가격 중심보다 위에 있어, 최근 모멘텀이 상대적으로 강한 상태라고 해석할 수도 있어요.',
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
        label: 'RSI 50 상향 통과·시그널 확인',
        desc: '전일 RSI는 50 아래였지만 현재는 50 이상이고, RSI가 시그널선보다도 높은지 함께 확인해요. 매수와 매도의 힘이 중립선 위에서 회복되는 과정이라고 해석할 수도 있어요.',
        graphic: (
          <svg viewBox="0 0 300 120" width="100%" height="100%" preserveAspectRatio="xMidYMid meet">
            <line x1="0" y1="20" x2="300" y2="20" stroke="var(--negative-muted)" strokeWidth="1" strokeDasharray="3,3" />
            <line x1="0" y1="60" x2="300" y2="60" stroke="var(--text-soft)" strokeWidth="1.5" strokeDasharray="4,4" />
            <line x1="0" y1="100" x2="300" y2="100" stroke="var(--positive-muted)" strokeWidth="1" strokeDasharray="3,3" />
            <path d="M 10,90 Q 70,80 120,60 Q 180,30 280,40" fill="none" stroke="#ef4444" strokeWidth="2.5" />
            <circle cx="120" cy="60" r="5" fill="#ef4444" />
            <text x="10" y="55" fontSize="11" fill="var(--text-soft)">50 (기준선)</text>
            <text x="130" y="80" fontSize="12" fill="#ef4444" fontWeight="bold">50 상향 통과 · 시그널 위</text>
          </svg>
        )
      },
      { 
        label: 'RSI 30 회복·시그널 확인',
        desc: '전일 RSI는 30 이하였지만 현재는 30을 넘었고, RSI가 시그널선보다도 높은지 함께 확인해요. 강했던 매도 압력이 누그러지고 단기 회복 힘이 생기는 과정이라고 해석할 수도 있어요.',
        graphic: (
          <svg viewBox="0 0 300 120" width="100%" height="100%" preserveAspectRatio="xMidYMid meet">
            <line x1="0" y1="20" x2="300" y2="20" stroke="var(--negative-muted)" strokeWidth="1" strokeDasharray="3,3" />
            <line x1="0" y1="60" x2="300" y2="60" stroke="var(--text-soft)" strokeWidth="1" strokeDasharray="4,4" />
            <line x1="0" y1="100" x2="300" y2="100" stroke="var(--positive-muted)" strokeWidth="2" strokeDasharray="3,3" />
            <path d="M 10,80 L 80,115 L 140,95 L 200,80 L 280,65" fill="none" stroke="#ef4444" strokeWidth="2.5" />
            <circle cx="140" cy="95" r="5" fill="#ef4444" />
            <text x="10" y="95" fontSize="11" fill="var(--text-soft)">30 (침체)</text>
            <text x="150" y="110" fontSize="12" fill="#ef4444" fontWeight="bold">30선 회복 · 시그널 위</text>
          </svg>
        )
      },
      { 
        label: 'RSI 약화 조건',
        desc: '현재 RSI가 45 미만이고 시그널선과 전일 RSI보다도 낮은지 확인해요. 최근 하락폭의 힘이 상승폭보다 커지며 모멘텀이 약해지는 과정이라고 해석할 수도 있어요.',
        graphic: (
          <svg viewBox="0 0 300 120" width="100%" height="100%" preserveAspectRatio="xMidYMid meet">
            <line x1="0" y1="20" x2="300" y2="20" stroke="var(--negative-muted)" strokeWidth="1" strokeDasharray="3,3" />
            <line x1="0" y1="60" x2="300" y2="60" stroke="var(--text-soft)" strokeWidth="2" strokeDasharray="4,4" />
            <line x1="0" y1="100" x2="300" y2="100" stroke="var(--positive-muted)" strokeWidth="1" strokeDasharray="3,3" />
            <path d="M 10,40 Q 80,45 130,60 Q 200,80 280,105" fill="none" stroke="#3b82f6" strokeWidth="2.5" />
            <circle cx="130" cy="60" r="5" fill="#3b82f6" />
            <text x="140" y="55" fontSize="12" fill="#3b82f6" fontWeight="bold">45 미만 · 시그널/전일 하회</text>
          </svg>
        )
      }
    ]
  },
  valuation: {
    title: '가치 참고값 읽는 법',
    points: [
      {
        label: 'PBR은 무엇을 비교하나요?',
        desc: 'PBR은 시장이 평가한 기업가치를 장부상 순자산으로 나눈 값이에요. 1.0이면 시장가치와 장부가치가 비슷하고, 2.0이면 장부가치의 두 배 수준으로 평가된다고 읽을 수 있어요.'
      },
      {
        label: '이 교실의 PBR 참고 구간',
        desc: 'PBR 0 초과~1.5 이하는 낮은 참고 구간, 1.5 초과~3 이하는 중간 참고 구간, 3 초과~5 이하는 PBR만으로 별도 가감하지 않는 관찰 구간, 5 초과는 높은 참고 구간으로 보고 있어요. 이 숫자는 업종을 초월한 절대 기준이 아니라 이 분석에서 정한 교육용 구간이에요.'
      },
      {
        label: 'PBR만으로 결론 내리지 않기',
        desc: 'PBR이 낮아도 부실 자산이나 낮은 수익성이 반영된 가치 함정일 수 있고, PBR이 높아도 무형자산·성장성이 큰 기업에서는 자연스러울 수 있어요. PER·ROE·부채비율과 동일 업종 비교를 함께 확인해 보세요.'
      }
    ]
  }
};

const reasonGraphicMap = {
  price_above_cloud: ['ichimoku', 0],
  price_below_cloud: ['ichimoku', 1],
  below_ichimoku_cloud: ['ichimoku', 1],
  tenkan_above_kijun: ['ichimoku', 2],
  tenkan_below_kijun: ['ichimoku', 2],
  bullish_forward_cloud: ['ichimoku', 0],
  bearish_forward_cloud: ['ichimoku', 1],
  squeeze_release_up: ['bollinger', 0],
  upper_band_release: ['bollinger', 0],
  recent_squeeze: ['bollinger', 1],
  squeeze: ['bollinger', 1],
  bandwidth_low_percentile: ['bollinger', 1],
  volatility_compression: ['bollinger', 1],
  bandwidth_expanding: ['bollinger', 0],
  downside_expansion: ['bollinger', 2],
  below_lower_band: ['bollinger', 2],
  below_bollinger_lower: ['bollinger', 2],
  failed_release: ['bollinger', 3],
  lower_band_cross_above_ma60: ['maSupport', 0],
  bollinger_lower_crossed_above_ma60: ['maSupport', 0],
  lower_band_above_ma60: ['maSupport', 1],
  bollinger_lower_above_ma60: ['maSupport', 1],
  lower_band_cross_below_ma60: ['maSupport', 2],
  bollinger_lower_crossed_below_ma60: ['maSupport', 2],
  rsi_crossed_above_50_with_signal: ['rsi', 0],
  rsi_oversold_recovery: ['rsi', 1],
  rsi_breakdown: ['rsi', 2],
};

export function getReasonGraphic(value) {
  const match = reasonKeyCandidates(value).map((key) => reasonGraphicMap[key]).find(Boolean);
  if (!match) return null;
  const [guideKey, pointIndex] = match;
  const point = educationalGuides[guideKey]?.points?.[pointIndex];
  return point?.graphic ? { graphic: point.graphic, label: point.label } : null;
}
