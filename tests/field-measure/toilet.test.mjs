import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  wallPolygon, outerPolygon, openingSegment, fixtureShape,
} from '../../apps/field-measure/src/toilet.js';

const room = [
  { len: 2, dir: 'R' }, { len: 1.5, dir: 'U' }, { len: 2, dir: 'L' }, { len: 1.5, dir: 'D' },
];
const bbox = (p) => {
  const xs = p.map((q) => q[0]); const ys = p.map((q) => q[1]);
  return [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)];
};
const near = (a, b) => assert.ok(Math.abs(a - b) < 1e-9, `${a} != ${b}`);

test('wallPolygon closed room', () => {
  const r = wallPolygon(room);
  assert.equal(r.closed, true);
  assert.deepEqual(r.pts, [[0, 0], [2, 0], [2, 1.5], [0, 1.5]]);
  assert.equal(r.gap.dist, 0);
});

test('wallPolygon unclosed gives gap', () => {
  const r = wallPolygon([...room.slice(0, 3), { len: 1.4, dir: 'D' }]);
  assert.equal(r.closed, false);
  assert.equal(r.pts.length, 4);
  near(r.gap.dist, 0.1);
  near(r.gap.dx, 0);
  near(r.gap.dy, -0.1);
});

test('wallPolygon ignores bad lengths, no float dust, never throws', () => {
  const r = wallPolygon([{ len: 0.1, dir: 'R' }, { len: 0.2, dir: 'R' }, { len: 0, dir: 'U' },
    { len: 'x', dir: 'U' }, { len: -1, dir: 'U' }]);
  assert.equal(r.pts.length, 2);
  assert.equal(r.closed, false);
  assert.equal(wallPolygon([]).pts.length, 0);
  const d = wallPolygon([{ len: 0.1, dir: 'R' }, { len: 0.2, dir: 'R' }, { len: 0.3, dir: 'U' }]);
  assert.equal(d.pts[2][0], 0.3);
});

test('wallPolygon directions', () => {
  const r = wallPolygon([{ len: 1, dir: 'U' }, { len: 1, dir: 'L' }, { len: 1, dir: 'D' }, { len: 1, dir: 'R' }]);
  assert.deepEqual(r.pts, [[0, 0], [0, 1], [-1, 1], [-1, 0]]);
  assert.equal(r.closed, true);
});

test('outerPolygon CCW', () => {
  const o = outerPolygon(wallPolygon(room).pts, 0.1);
  assert.equal(o.length, 4);
  const [x0, x1, y0, y1] = bbox(o);
  near(x0, -0.1); near(x1, 2.1); near(y0, -0.1); near(y1, 1.6);
});

test('outerPolygon CW', () => {
  const cw = [[0, 0], [0, 1.5], [2, 1.5], [2, 0]];
  const o = outerPolygon(cw, 0.1);
  assert.equal(o.length, 4);
  const [x0, x1, y0, y1] = bbox(o);
  near(x0, -0.1); near(x1, 2.1); near(y0, -0.1); near(y1, 1.6);
});

test('outerPolygon L-shape stays outward at reflex corner', () => {
  const L = [[0, 0], [2, 0], [2, 1], [1, 1], [1, 2], [0, 2]];
  const o = outerPolygon(L, 0.1);
  assert.equal(o.length, 6);
  near(o[3][0], 1.1); near(o[3][1], 1.1);
  near(o[0][0], -0.1); near(o[0][1], -0.1);
});

test('openingSegment', () => {
  const pts = wallPolygon(room).pts;
  const s = openingSegment(pts, 0, 0.3, 0.8);
  near(s.a[0], 0.3); near(s.a[1], 0); near(s.b[0], 1.1); near(s.b[1], 0);
  const v = openingSegment(pts, 1, 0.5, 0.5);
  near(v.a[0], 2); near(v.a[1], 0.5); near(v.b[1], 1);
  const c = openingSegment(pts, 0, 1.8, 0.8);
  near(c.b[0], 2);
  const w = openingSegment(pts, 3, 0.5, 0.5); // wraps to pts[0]
  near(w.a[0], 0); near(w.a[1], 1); near(w.b[1], 0.5);
});

test('fixtureShape', () => {
  assert.deepEqual(fixtureShape('toilet', 1, 2), { kind: 'rect', x: 1, y: 2, w: 0.4, h: 0.7 });
  assert.deepEqual(fixtureShape('squat', 1, 2), { kind: 'rect', x: 1, y: 2, w: 0.5, h: 0.6 });
  assert.deepEqual(fixtureShape('basin', 1, 2), { kind: 'rect', x: 1, y: 2, w: 0.45, h: 0.35 });
  assert.deepEqual(fixtureShape('urinal', 1, 2), { kind: 'rect', x: 1, y: 2, w: 0.35, h: 0.3 });
  assert.deepEqual(fixtureShape('shower', 1, 2), { kind: 'circle', x: 1, y: 2, r: 0.1 });
  assert.deepEqual(fixtureShape('drain', 1, 2), { kind: 'circle', x: 1, y: 2, r: 0.05 });
  assert.deepEqual(fixtureShape('tap', 1, 2), { kind: 'circle', x: 1, y: 2, r: 0.05 });
  assert.deepEqual(fixtureShape('???', 1, 2), { kind: 'rect', x: 1, y: 2, w: 0.3, h: 0.3 });
});
