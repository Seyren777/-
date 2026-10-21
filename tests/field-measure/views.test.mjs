// Pure helpers exported by the view modules (no DOM needed to import them).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { newStation } from '../../apps/field-measure/src/app.js';
import { validateRoadSettings, mergeStations } from '../../apps/field-measure/src/views/roadSettings.js';
import {
  setPointReading, setPointRL, deletePoint, copyFromPrevious,
} from '../../apps/field-measure/src/views/station.js';
import { computeLevelBook, rlOf } from '../../apps/field-measure/src/level.js';

test('newStation has the centreline point', () => {
  const s = newStation(25);
  assert.equal(s.sta, 25);
  assert.deepEqual(s.section.map((p) => [p.offset, p.label]), [[0, 'กึ่งกลาง']]);
  assert.deepEqual(s.features, []);
});

test('validateRoadSettings rejects values that would hang generateStations', () => {
  assert.equal(validateRoadSettings({ stationStart: 0, length: 100, interval: 25 }), null);
  assert.ok(validateRoadSettings({ stationStart: 0, length: 100, interval: 0.5 }));
  assert.ok(validateRoadSettings({ stationStart: 0, length: 0, interval: 25 }));
  assert.ok(validateRoadSettings({ stationStart: 0, length: Infinity, interval: 25 }));
  assert.ok(validateRoadSettings({ stationStart: NaN, length: 100, interval: 25 }));
  assert.ok(validateRoadSettings({ stationStart: 0, length: '', interval: 25 }));
});

test('mergeStations keeps existing data by chainage and drops only empty stations', () => {
  const a = newStation(0); a.widths.pavL = 3;
  const odd = newStation(37.5); odd.note = 'ท่อลอด';
  const emptyOld = newStation(25);
  const out = mergeStations([a, emptyOld, odd], [0, 20, 40]);
  assert.deepEqual(out.map((s) => s.sta), [0, 20, 37.5, 40]);
  assert.equal(out[0], a);
  assert.equal(out[2], odd);
});

function roadProject() {
  return {
    bms: [{ name: 'BM1', rl: 100 }],
    levelBook: [{ id: 'bm', point: 'BM1', bs: 1.5 }],
    stations: [newStation(0), newStation(25)],
  };
}

test('entering a reading appends an IS row and links it; editing updates it', () => {
  const p = roadProject();
  const st = p.stations[1];
  const cl = st.section[0];
  setPointReading(p, st, cl, '1.300');
  assert.equal(p.levelBook.length, 2);
  const row = p.levelBook[1];
  assert.deepEqual({ point: row.point, is: row.is, staRef: row.staRef }, { point: 'กึ่งกลาง', is: 1.3, staRef: 25 });
  assert.equal(cl.readingId, row.id);
  assert.equal(cl.rl, undefined);
  assert.ok(Math.abs(rlOf(computeLevelBook(p.levelBook, p.bms), cl.readingId) - 100.2) < 1e-9);

  setPointReading(p, st, cl, '1.250');
  assert.equal(p.levelBook.length, 2);
  assert.equal(p.levelBook[1].is, 1.25);

  setPointReading(p, st, cl, '');
  assert.equal(p.levelBook.length, 2, 'clearing keeps the row in place');
  assert.equal(p.levelBook[1].is, null);
  assert.equal(cl.readingId, row.id);
});

test('clearing then retyping a reading keeps the IS row position and its RL', () => {
  const p = roadProject();
  const cl0 = p.stations[0].section[0];
  setPointReading(p, p.stations[0], cl0, 1.3); // HI 101.5 -> RL 100.200
  p.levelBook.push({ id: 'cp', point: 'TP1', fs: 1.0, bs: 2.0 }); // change point
  setPointReading(p, p.stations[1], p.stations[1].section[0], 1.4);
  const rl = () => rlOf(computeLevelBook(p.levelBook, p.bms), cl0.readingId);
  assert.ok(Math.abs(rl() - 100.2) < 1e-9);
  setPointReading(p, p.stations[0], cl0, null); // backspaced to empty
  assert.equal(rl(), undefined);
  setPointReading(p, p.stations[0], cl0, 1.3);
  assert.ok(Math.abs(rl() - 100.2) < 1e-9);
  assert.deepEqual(p.levelBook.map((r) => r.point), ['BM1', 'กึ่งกลาง', 'TP1', 'กึ่งกลาง']);
});

test('entering RL directly sets rl and removes the reading link', () => {
  const p = roadProject();
  const st = p.stations[0];
  const cl = st.section[0];
  setPointReading(p, st, cl, '1.2');
  setPointRL(p, cl, '99.876');
  assert.equal(cl.rl, 99.876);
  assert.equal(cl.readingId, undefined);
  assert.equal(p.levelBook.length, 1);
});

test('deletePoint removes its level-book row; the centreline point cannot be deleted', () => {
  const p = roadProject();
  const st = p.stations[0];
  st.section.push({ offset: -3, label: 'ขอบผิวทาง ซ.' });
  setPointReading(p, st, st.section[1], '1.4');
  assert.equal(p.levelBook.length, 2);
  deletePoint(p, st, 1);
  assert.equal(st.section.length, 1);
  assert.equal(p.levelBook.length, 1);
  deletePoint(p, st, 0);
  assert.equal(st.section.length, 1);
});

test('copyFromPrevious fills blanks and adds missing section offsets without readings', () => {
  const p = roadProject();
  const [a, b] = p.stations;
  Object.assign(a.widths, { pavL: 3, pavR: 3 });
  a.surface = 'คสล.';
  a.section.push({ offset: -3, label: 'ขอบผิวทาง ซ.', rl: 100.1 });
  b.widths.pavL = 2.5;
  copyFromPrevious(p, 1);
  assert.equal(b.widths.pavL, 2.5);
  assert.equal(b.widths.pavR, 3);
  assert.equal(b.surface, 'คสล.');
  assert.deepEqual(b.section.map((q) => [q.offset, q.label, q.rl]), [[0, 'กึ่งกลาง', undefined], [-3, 'ขอบผิวทาง ซ.', undefined]]);
  assert.equal(copyFromPrevious(p, 0), false);
});
