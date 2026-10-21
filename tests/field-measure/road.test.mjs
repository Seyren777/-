import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  formatSta, parseSta, generateStations, insertStation, planLines, orderSection,
} from '../../apps/field-measure/src/road.js';

test('formatSta', () => {
  assert.equal(formatSta(0), '0+000');
  assert.equal(formatSta(25), '0+025');
  assert.equal(formatSta(1237.5), '1+237.5');
  assert.equal(formatSta(1000), '1+000');
  assert.equal(formatSta(999.999), '0+999.999');
  assert.equal(formatSta(12345), '12+345');
});

test('parseSta', () => {
  assert.equal(parseSta('0+025'), 25);
  assert.equal(parseSta('1+237.5'), 1237.5);
  assert.equal(parseSta('25'), 25);
  assert.equal(parseSta(' 2+000 '), 2000);
  assert.equal(parseSta(formatSta(1237.5)), 1237.5);
  assert.ok(Number.isNaN(parseSta('abc')));
});

test('generateStations includes end and is float safe', () => {
  assert.deepEqual(generateStations(0, 110, 25), [0, 25, 50, 75, 100, 110]);
  assert.deepEqual(generateStations(0, 100, 25), [0, 25, 50, 75, 100]);
  assert.deepEqual(generateStations(0, 1, 0.1), [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1]);
  assert.deepEqual(generateStations(1000, 50, 20), [1000, 1020, 1040, 1050]);
});

test('insertStation sorted unique, no mutation', () => {
  const a = [0, 25, 50];
  assert.deepEqual(insertStation(a, 30), [0, 25, 30, 50]);
  assert.deepEqual(a, [0, 25, 50]);
  assert.deepEqual(insertStation(a, 25), [0, 25, 50]);
  assert.deepEqual(insertStation(a, 25 + 1e-8), [0, 25, 50]);
  assert.deepEqual(insertStation(a, -5), [-5, 0, 25, 50]);
});

const st = (sta, widths) => ({ sta, widths });

test('planLines basic', () => {
  const p = { stations: [st(0, { pavL: 3, pavR: 3.5 }), st(25, { pavL: 3, pavR: 3.5 })] };
  const r = planLines(p);
  assert.deepEqual(r.cl, [[0, 0], [25, 0]]);
  assert.deepEqual(r.edgeL, [[0, 3], [25, 3]]);
  assert.deepEqual(r.edgeR, [[0, -3.5], [25, -3.5]]);
  assert.deepEqual(r.shL, []);
  assert.deepEqual(r.rowR, []);
});

test('planLines skips missing widths per line, all keys present', () => {
  const p = { stations: [
    st(0, { pavL: 3, shL: 1, rowL: 10, rowR: 10 }),
    st(25, { pavL: 3, shL: '', rowL: 10, rowR: null }),
    st(50, { pavL: 3, shL: 1.5, rowL: 10, rowR: 9 }),
    st(75, {}),
  ] };
  const r = planLines(p);
  assert.deepEqual(Object.keys(r).sort(), ['cl', 'edgeL', 'edgeR', 'rowL', 'rowR', 'shL', 'shR']);
  assert.deepEqual(r.cl, [[0, 0], [75, 0]]);
  assert.deepEqual(r.edgeL, [[0, 3], [25, 3], [50, 3]]);
  assert.deepEqual(r.shL, [[0, 1], [50, 1.5]]);
  assert.deepEqual(r.rowR, [[0, -10], [50, -9]]);
  assert.deepEqual(r.shR, []);
});

test('planLines handles empty / unsorted stations', () => {
  assert.deepEqual(planLines({ stations: [] }).cl, []);
  const r = planLines({ stations: [st(50, { pavR: 2 }), st(0, { pavR: 2 })] });
  assert.deepEqual(r.cl, [[0, 0], [50, 0]]);
  assert.deepEqual(r.edgeR, [[0, -2], [50, -2]]);
});

test('orderSection', () => {
  const input = [{ offset: 2 }, { offset: -2 }, { offset: 2, rl: 5 }];
  const snap = JSON.stringify(input);
  const out = orderSection(input);
  assert.deepEqual(out.map((p) => p.offset), [-2, 2]);
  assert.equal(out[1].rl, 5);
  assert.equal(JSON.stringify(input), snap);
  assert.deepEqual(orderSection([{ offset: 'x' }, { offset: 1 }, { offset: null }, {}]).map((p) => p.offset), [1]);
});
