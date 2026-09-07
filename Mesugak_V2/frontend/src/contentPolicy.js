/* Pure content checks shared by the public analysis UI and policy tests. */

const invalidDates = new Set(['', '-', 'unknown', '미상']);

export function hasSubstantialAnalysisContent(stock) {
  if (!stock || typeof stock !== 'object') return false;
  const name = String(stock.name || '').trim();
  const code = String(stock.code || '').trim();
  const updatedAt = String(stock.updatedAt || '').trim().toLowerCase();
  const confidence = Number(stock.confidence);
  const states = Object.values(stock.indicatorStates || {}).filter((state) => state && typeof state === 'object');
  const meaningfulStates = states.filter((state) => String(state.state || '').toUpperCase() !== 'NO_DATA');
  const reasons = [
    ...(stock.raw?.confidenceReasons || []),
    ...(stock.raw?.signal?.reasons || []),
    ...states.flatMap((state) => state.reasons || []),
  ].filter(Boolean);

  return Boolean(
    name
    && code
    && Number.isFinite(confidence)
    && !invalidDates.has(updatedAt)
    && meaningfulStates.length >= 1
    && states.length >= 3
    && reasons.length >= 2,
  );
}

