import { test } from 'node:test';
import assert from 'node:assert/strict';
import { computeLevelBook, rlOf, r3 } from '../../apps/field-measure/src/level.js';

const near = (a, b, eps = 1e-9) => assert.ok(Math.abs(a - b) < eps, `${a} !~ ${b}`);
const BMS = [{ name: 'BM1', rl: 100 }];

test('r3 rounds to 3 decimals', () => {
  assert.equal(r3(1.23456), 1.235);
  assert.equal(r3(-0.5), -0.5);
  assert.equal(r3(100.0004), 100);
});

test('3-row open run: BS, IS, FS', () => {
  const rows = [
    { id: 'a', point: 'BM1', bs: 1.5, is: null, fs: null },
    { id: 'b', point: 'P1', bs: null, is: 1.2, fs: null },
    { id: 'c', point: 'P2', bs: null, is: null, fs: 2.0 },
  ];
  const book = computeLevelBook(rows, BMS);
  near(book.rows[0].rl, 100);
  near(book.rows[0].hi, 101.5);
  near(book.rows[1].rl, 100.3);
  near(book.rows[2].rl, 99.5);
  near(book.sumBS, 1.5);
  near(book.sumFS, 2.0);
  near(book.sumBS - book.sumFS, -0.5);
  near(book.deltaRL, -0.5);
  assert.equal(book.closure, null);
});

test('closed run returning to BM reports closure error', () => {
  const rows = [
    { id: 'a', point: 'BM1', bs: 1.5 },
    { id: 'b', point: 'TP1', bs: 1.2, fs: 1.0 }, // change point
    { id: 'c', point: 'BM1', fs: 1.696 },
  ];
  const book = computeLevelBook(rows, BMS);
  near(book.rows[1].rl, 100.5);
  near(book.rows[1].hi, 101.7);
  assert.equal(book.closure.expected, 100);
  near(book.closure.got, 100.004);
  near(book.closure.error, 0.004);
  near(book.deltaRL, 0.004);
});

test('rlOf returns RL by row id, undefined if unknown', () => {
  const rows = [
    { id: 'a', point: 'BM1', bs: 1.5 },
    { id: 'b', point: 'P1', is: 1.2 },
  ];
  const book = computeLevelBook(rows, BMS);
  near(rlOf(book, 'b'), 100.3);
  assert.equal(rlOf(book, 'zzz'), undefined);
});

test('empty rows are skipped; blank strings and null treated as unread', () => {
  const rows = [
    { id: 'a', point: 'BM1', bs: '1.500', is: '', fs: '' },
    { id: 'x', point: '', bs: null, is: null, fs: null },
    { id: 'b', point: 'P1', is: 1.0 },
    { id: 'c', point: 'P2', fs: 1.0 },
  ];
  const book = computeLevelBook(rows, BMS);
  assert.equal(book.rows[1].hi, undefined);
  assert.equal(book.rows[1].rl, undefined);
  near(book.sumBS, 1.5);
  near(book.sumFS, 1.0);
  near(book.deltaRL, 0.5); // 100.5 (FS row) - 100 (BM)
});

test('first row not a known BM: RL starts at 0, closure null, no throw', () => {
  const rows = [
    { id: 'a', point: 'XX', bs: 1.0 },
    { id: 'b', point: 'BM1', fs: 0.5 },
  ];
  const book = computeLevelBook(rows, BMS);
  near(book.rows[0].rl, 0);
  near(book.rows[1].rl, 0.5);
  assert.equal(book.closure, null);
});

test('empty input', () => {
  const book = computeLevelBook([], BMS);
  assert.deepEqual(book.rows, []);
  assert.equal(book.sumBS, 0);
  assert.equal(book.sumFS, 0);
  assert.equal(book.deltaRL, 0);
  assert.equal(book.closure, null);
});

test('input rows are not mutated', () => {
  const rows = [{ id: 'a', point: 'BM1', bs: 1.5 }];
  computeLevelBook(rows, BMS);
  assert.equal('rl' in rows[0], false);
});

test('IS/FS before the first BS has no RL or HI; a later BS row starts the run', () => {
  const onBM = computeLevelBook([
    { id: 'a', point: 'กึ่งกลาง', is: 1.2 },
    { id: 'b', point: 'BM1', bs: 1.5 },
  ], BMS);
  assert.equal(onBM.rows[0].rl, undefined);
  assert.equal(onBM.rows[0].hi, undefined);
  near(onBM.rows[1].rl, 100);
  near(onBM.rows[1].hi, 101.5);

  const unknown = computeLevelBook([
    { id: 'a', point: 'กึ่งกลาง', is: 1.2 },
    { id: 'b', point: 'XX', bs: 1.5 },
  ], BMS);
  assert.equal(unknown.rows[0].rl, undefined);
  near(unknown.rows[1].rl, 0);
});

test('sum check: book without FS is not checkable and reports no sums', () => {
  const book = computeLevelBook([
    { id: 'a', point: 'BM1', bs: 1.5 },
    { id: 'b', point: 'P1', is: 1.2 },
    { id: 'c', point: 'P2', is: 1.8 },
  ], BMS);
  assert.equal(book.checkable, false);
  assert.equal(book.sumBS, 0);
  assert.equal(book.sumFS, 0);
  assert.equal(book.deltaRL, 0);
  assert.equal(computeLevelBook([], BMS).checkable, false);
});

test('sum check covers rows only up to the last FS; a trailing IS is ignored', () => {
  const book = computeLevelBook([
    { id: 'a', point: 'BM1', bs: 1.5 },
    { id: 'b', point: 'BM1', fs: 1.3 },
    { id: 'c', point: 'P1', is: 0.9 },
  ], BMS);
  assert.equal(book.checkable, true);
  near(book.sumBS, 1.5);
  near(book.sumFS, 1.3);
  near(book.deltaRL, 0.2);
  near(book.sumBS - book.sumFS, book.deltaRL);
});

test('sum check: BS on the last FS row (change point) belongs to the next leg', () => {
  const book = computeLevelBook([
    { id: 'a', point: 'BM1', bs: 1.5 },
    { id: 'b', point: 'TP1', bs: 1.2, fs: 1.0 },
    { id: 'c', point: 'P1', is: 0.9 },
  ], BMS);
  near(book.sumBS, 1.5);
  near(book.sumFS, 1.0);
  near(book.deltaRL, 0.5);
});
