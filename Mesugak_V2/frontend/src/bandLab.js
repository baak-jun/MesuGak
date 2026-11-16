// One educational window, not a trading signal or a rolling chart.
export function calculateBandWindow(input, ddof = 1) {
  if (![0, 1].includes(ddof)) return { error: '표준편차 방식을 선택해 주세요.' };
  const tokens = String(input).trim().split(/[\s,·]+/).filter(Boolean);
  if (tokens.length < 2 || tokens.length > 120) return { error: '가상 종가를 2개 이상 120개 이하로 입력해 주세요.' };
  if (tokens.some((token) => !/^\d+(?:\.\d+)?$/.test(token))) return { error: '양수와 소수점만 사용하고, 값 사이는 쉼표나 공백으로 구분해 주세요.' };
  const values = tokens.map(Number);
  if (values.some((value) => !Number.isFinite(value) || value <= 0 || value > 1e9)) return { error: '각 가상 종가는 0보다 크고 10억 이하여야 합니다.' };
  const origin = values[0];
  const mean = origin + values.reduce((sum, value) => sum + (value - origin), 0) / values.length;
  const squaredSum = values.reduce((sum, value) => sum + (value - mean) ** 2, 0);
  const divisor = values.length - ddof;
  const deviation = Math.sqrt(squaredSum / divisor);
  const upper = mean + 2 * deviation;
  const lower = mean - 2 * deviation;
  const last = values.at(-1);
  return { values, mean, squaredSum, divisor, deviation, upper, lower, last,
    bandwidth: 4 * deviation / mean,
    percentB: deviation === 0 ? null : (last - lower) / (4 * deviation) };
}
