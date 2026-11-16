import test from 'node:test';
import assert from 'node:assert/strict';
import { calculateBandWindow } from '../src/bandLab.js';

const near = (actual, expected) => assert.ok(Math.abs(actual - expected) < 1e-10, `${actual} != ${expected}`);
test('five-value hand calculation matches the displayed worked example', () => {
  const result = calculateBandWindow('96, 98, 100, 102, 104');
  near(result.mean, 100);
  near(result.squaredSum, 40);
  near(result.deviation, Math.sqrt(10));
  near(result.upper, 106.32455532033676);
  near(result.lower, 93.67544467966324);
  near(result.bandwidth, 0.12649110640673517);
  near(result.percentB, 0.8162277660168379);
});
test('reversing the sequence changes position but preserves width', () => {
  const rise = calculateBandWindow('96 98 100 102 104');
  const fall = calculateBandWindow('104 102 100 98 96');
  near(rise.mean, fall.mean);
  near(rise.bandwidth, fall.bandwidth);
  near(fall.percentB, 0.18377223398316206);
});
test('population and sample conventions differ by the expected factor', () => {
  const input = Array.from({ length: 20 }, (_, i) => 90 + i).join(',');
  const sample = calculateBandWindow(input, 1);
  const population = calculateBandWindow(input, 0);
  near(sample.mean, 99.5);
  near(sample.deviation, Math.sqrt(35));
  near(sample.deviation / population.deviation, Math.sqrt(20 / 19));
});
test('flat prices have no defined percent B', () => {
  for (const ddof of [0, 1]) {
    const result = calculateBandWindow('100 100 100 100 100', ddof);
    assert.equal(result.bandwidth, 0);
    assert.equal(result.percentB, null);
    assert.equal(calculateBandWindow(Array(120).fill(0.1).join(','), ddof).percentB, null);
  }
});
test('invalid and oversized input never yields misleading numeric output', () => {
  for (const input of ['', '100', '100 -2', '100 0', '100 NaN', '100 Infinity', '100 0x10', '100 1e9', '100 1000000001', '100 <script>', Array(121).fill(100).join(' ')]) {
    const result = calculateBandWindow(input);
    assert.ok(result.error, input);
    assert.equal(result.mean, undefined);
  }
  assert.ok(calculateBandWindow('100 101', 2).error);
});
test('decimal, newline and maximum length inputs are accepted', () => {
  near(calculateBandWindow('1.5\n2.5').mean, 2);
  assert.equal(calculateBandWindow(Array(120).fill(100).join(',')).values.length, 120);
});
