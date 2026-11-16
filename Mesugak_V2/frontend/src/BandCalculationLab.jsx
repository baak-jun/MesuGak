import { useState } from 'react';
import { calculateBandWindow } from './bandLab.js';

const examples = [
  { label: '상승 순서', values: '96, 98, 100, 102, 104' },
  { label: '하락 순서', values: '104, 102, 100, 98, 96' },
  { label: '가격이 같을 때', values: '100, 100, 100, 100, 100' },
];
const format = (number) => number.toLocaleString('ko-KR', { maximumFractionDigits: 4 });

export default function BandCalculationLab() {
  const [input, setInput] = useState(examples[0].values);
  const [ddof, setDdof] = useState(1);
  const result = calculateBandWindow(input, ddof);
  return (
    <section className="band-lab learning-section" id="band-calculator" aria-labelledby="band-lab-title">
      <div className="section-heading"><span>숫자를 바꾸는 계산 실습</span><h2 id="band-lab-title">같은 밴드 폭인데 방향이 다를 수 있을까요?</h2>
        <p>종가 5개를 직접 바꾸며 평균·표준편차·밴드 폭·%b가 어떻게 달라지는지 바로 계산해 보세요.</p></div>
      <p>손으로 검산하기 쉽도록 기본 예시는 5개 종가를 하나의 창으로 묶어 계산하며, 마지막 숫자를 오늘 종가로 봅니다(실제 MesuGak 종목 분석은 오늘을 포함한 20봉·표본 표준편차·2배 경계 기준).</p>
      <div className="band-presets" role="group" aria-label="가상 종가 예시">
        {examples.map((example) => <button type="button" key={example.label} onClick={() => setInput(example.values)}>{example.label}</button>)}
      </div>
      <div className="band-inputs">
        <label htmlFor="band-prices">가상 종가 · 오래된 값부터<textarea id="band-prices" value={input} maxLength={1800} onChange={(event) => setInput(event.target.value)} aria-describedby="band-input-help" aria-invalid={Boolean(result.error)} rows={3} /></label>
        <label htmlFor="band-deviation">표준편차 방식<select id="band-deviation" value={ddof} onChange={(event) => setDdof(Number(event.target.value))}><option value={1}>표본 · N−1로 나누기 (MesuGak)</option><option value={0}>모집단 · N으로 나누기</option></select></label>
      </div>
      <p id="band-input-help">2~120개의 양수를 쉼표 또는 공백으로 구분하세요. 천 단위 구분 쉼표는 쓰지 않습니다. 예: 1000, 1020, 980</p>
      <div className="band-result" aria-live="polite" aria-atomic="true">
        {result.error ? <p className="band-error">{result.error}</p> : <>
          <h3>입력한 {result.values.length}개 값의 계산 결과</h3>
          <dl className="band-metrics">
            <div><dt>평균</dt><dd>{format(result.mean)}</dd></div><div><dt>표준편차</dt><dd>{format(result.deviation)}</dd></div>
            <div><dt>하단 / 상단</dt><dd>{format(result.lower)} / {format(result.upper)}</dd></div>
            <div><dt>밴드 폭 / 평균</dt><dd>{format(result.bandwidth * 100)}%</dd></div>
            <div><dt>마지막 종가의 %b</dt><dd>{result.percentB === null ? '계산 불가 · 폭이 0' : format(result.percentB)}</dd></div>
          </dl>
          <BandDiagram result={result} />
          <details className="band-working"><summary>계산 과정 펼치기</summary>
            <p>평균 = 합계 {format(result.values.reduce((sum, value) => sum + value, 0))} ÷ {result.values.length} = {format(result.mean)}</p>
            <p>평균과의 차이를 제곱한 합 = {format(result.squaredSum)}. 표준편차 = √({format(result.squaredSum)} ÷ {result.divisor}) = {format(result.deviation)}</p>
            <p>하단·상단 = {format(result.mean)} ± 2 × {format(result.deviation)}. 밴드 폭 = (상단−하단) ÷ 평균.</p>
            <p>{result.percentB === null ? '모든 값이 같아 상단과 하단이 겹칩니다. 0으로 나눌 수 없어 %b를 계산하지 않습니다.' : `%b = (${format(result.last)} − ${format(result.lower)}) ÷ ${format(4 * result.deviation)} = ${format(result.percentB)}`}</p>
            <p>표시는 소수 넷째 자리까지 반올림하며, 계산에는 반올림 전 값을 사용합니다.</p>
          </details>
        </>}
      </div>
      <div className="band-lesson">
        <h3>비교하고 설명해 보기</h3>
        <ol><li>표본 방식을 선택하고 ‘상승 순서’와 ‘하락 순서’를 번갈아 눌러 보세요. 평균과 폭이 바뀌나요?</li><li>같은 값을 모집단 방식으로 바꾸면 왜 경계가 좁아질까요?</li><li>‘가격이 같을 때’를 선택하면 %b를 0.5라고 할 수 있을까요?</li></ol>
        <details><summary>비교 해설 읽기</summary><p>96·98·100·102·104와 그 역순은 평균 100, 제곱 차이의 합 40으로 같습니다. 표본 표준편차는 √10 ≈ 3.1623, 경계는 93.6754와 106.3246, 폭은 약 12.6491%입니다. 마지막 종가가 달라 %b는 약 0.8162와 0.1838로 달라집니다. 폭만으로 가격 방향을 정할 수 없는 이유입니다.</p><p>모집단 방식은 40을 5로 나누어 표준편차가 √8 ≈ 2.8284가 됩니다. 같은 입력이라도 분모가 달라 경계가 좁아집니다. 모든 값이 100이면 표준편차와 폭이 0이므로 %b는 0÷0입니다. 중앙이라는 이유로 0.5를 부여하지 않습니다.</p></details>
        <p>핵심 정리: 밴드 폭(Bandwidth)은 가격이 흩어진 정도만 보여주고, 현재 종가가 밴드 안에서 어느 쪽에 놓여 있는지는 %b가 보여줍니다. 따라서 밴드 폭과 %b를 함께 읽어야 변동성의 크기와 방향을 동시에 파악할 수 있습니다.</p>
        <p><a href="/learn/articles/bollinger">볼린저 밴드 계산 원리 읽기</a> · <a href="https://www.bollingerbands.com/bollinger-band-rules" target="_blank" rel="noopener noreferrer">John Bollinger의 해석 규칙</a> · <a href="/methodology">MesuGak 계산 기준</a></p>
      </div>
    </section>
  );
}

function BandDiagram({ result }) {
  const min = Math.min(result.lower, ...result.values);
  const max = Math.max(result.upper, ...result.values);
  const padding = (max - min) * 0.15 || 1;
  const y = (value) => 170 - (value - min + padding) / (max - min + 2 * padding) * 140;
  const points = result.values.map((value, index) => `${30 + index / (result.values.length - 1) * 480},${y(value)}`).join(' ');
  return <figure className="band-diagram"><svg viewBox="0 0 640 210" role="img" aria-label="가상 종가 흐름과 마지막 창의 상단·평균·하단 비교">
    {[['상단', result.upper], ['평균', result.mean], ['하단', result.lower]].map(([label, value]) => <g key={label}><line x1="30" x2="510" y1={y(value)} y2={y(value)} stroke="#8190a5" strokeDasharray="5 4" /><text x="525" y={y(value) + (result.deviation === 0 ? { 상단: -20, 평균: 0, 하단: 20 }[label] : 0)} fill="#334155" fontSize="13">{label}</text></g>)}
    <polyline points={points} fill="none" stroke="#2563eb" strokeWidth="3" /><text x="30" y="200" fill="#334155" fontSize="13">오래된 종가 → 마지막 종가</text>
  </svg><figcaption>파란 선: 입력한 가상 종가 · 점선: 마지막 창의 경계와 평균. 값과 계산식은 위 결과와 아래 계산 과정에서도 읽을 수 있습니다.</figcaption></figure>;
}
