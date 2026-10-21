import { test } from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { mkdtempSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  exportRoad, exportToilet, exportCSV, fileName,
} from '../../apps/field-measure/src/export.js';

const here = dirname(fileURLToPath(import.meta.url));
const CHECK = join(here, 'check_dxf.py');

function check(dxfText) {
  const dir = mkdtempSync(join(tmpdir(), 'fm-export-'));
  const file = join(dir, 'tmp.dxf');
  try {
    writeFileSync(file, dxfText);
    const out = execFileSync('python3', [CHECK, file], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });
    return JSON.parse(out);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
}

/** Minimal DXF entity reader: [{type, layer, closed, pts:[[x,y]], x, y, text, rot}] */
function entities(dxf) {
  const lines = dxf.split(/\r?\n/);
  const pairs = [];
  for (let i = 0; i + 1 < lines.length; i += 2) pairs.push([Number(lines[i].trim()), lines[i + 1]]);
  const start = pairs.findIndex(([c, v], i) => c === 2 && v === 'ENTITIES' && pairs[i - 1][1] === 'SECTION');
  const out = [];
  let e = null;
  for (let i = start + 1; i < pairs.length; i++) {
    const [c, v] = pairs[i];
    if (c === 0) {
      if (e) out.push(e);
      if (v === 'ENDSEC') break;
      e = { type: v, pts: [], closed: false };
    } else if (c === 8) e.layer = v;
    else if (c === 70) e.closed = v.trim() === '1';
    else if (c === 10) e.pts.push([Number(v), NaN]);
    else if (c === 20) e.pts[e.pts.length - 1][1] = Number(v);
    else if (c === 1) e.text = v;
    else if (c === 50) e.rot = Number(v);
    else if (c === 40) e.h = Number(v);
  }
  for (const x of out) if (x.pts.length) [x.x, x.y] = x.pts[0];
  return out;
}
const of = (ents, type, layer) => ents.filter((e) => e.type === type && e.layer === layer);

const THAI_NAME = 'ปรับปรุงถนนซอยเทศบาล 5';

function roadProject() {
  return {
    version: 1, id: 'r', type: 'road-improve', name: THAI_NAME, createdAt: '2026-10-21T00:00:00Z',
    settings: { stationStart: 0, interval: 25, length: 50, scales: { plan: 100, section: 25, toilet: 50 }, vExag: 1, font: 'Tahoma' },
    bms: [{ name: 'BM1', rl: 100 }],
    levelBook: [
      { id: 'a', point: 'BM1', bs: 1.5 }, // HI 101.5
      { id: 'b', point: 'CL', is: 1.3 }, // 100.200
      { id: 'c', point: 'L', is: 1.4 }, // 100.100
      { id: 'd', point: 'R', is: 1.45 }, // 100.050
      { id: 'e', point: 'CL', is: 1.2 }, // 100.300
      { id: 'f', point: 'L', is: 1.35 }, // 100.150
      { id: 'g', point: 'R', is: 1.38 }, // 100.120
    ],
    stations: [
      {
        sta: 0, widths: { pavL: 3, pavR: 3, shL: 3.5, shR: 3.5, rowL: 5, rowR: 5 },
        section: [
          { offset: 0, readingId: 'b', label: 'กึ่งกลาง' },
          { offset: -3, readingId: 'c', label: 'ขอบผิวทาง ซ.' },
          { offset: 3, readingId: 'd', label: 'ขอบผิวทาง ข.' },
        ],
        features: [{ kind: 'เสาไฟ', offset: -4, note: 'คอนกรีต' }],
      },
      {
        sta: 25, widths: { pavL: 3, pavR: 3, shL: 3.5, shR: 3.5, rowL: 5, rowR: 5 },
        // deliberately unsorted
        section: [
          { offset: 3, readingId: 'g', label: 'R' },
          { offset: -3, readingId: 'f', label: 'L' },
          { offset: 0, readingId: 'e', label: 'CL' },
        ],
        features: [],
      },
      {
        sta: 50, widths: { pavL: 3, pavR: 3, shL: 3.5, shR: 3.5, rowL: 5, rowR: 5 },
        section: [
          { offset: -3, rl: 99.9, label: 'L' },
          { offset: 0, rl: 100.0, label: 'CL' },
          { offset: 3, rl: 99.95, label: 'R' },
          { offset: 4, readingId: 'missing', label: 'skip me' },
        ],
        features: [],
      },
    ],
    rooms: [],
  };
}

const ROOM = [{ len: 2, dir: 'R' }, { len: 1.5, dir: 'U' }, { len: 2, dir: 'L' }, { len: 1.5, dir: 'D' }];

function toiletProject(rooms) {
  return {
    version: 1, id: 't', type: 'toilet', name: 'ห้องน้ำ ตลาดสด', createdAt: '2026-10-21T00:00:00Z',
    settings: { scales: { plan: 100, section: 25, toilet: 50 }, vExag: 1, font: 'Tahoma' },
    bms: [], stations: [], levelBook: [], rooms,
  };
}

test('road: ezdxf reads it, polylines for plan lines and sections, station and RL texts', () => {
  const dxf = exportRoad(roadProject());
  const r = check(dxf);
  assert.equal(r.version, 'AC1015');
  assert.ok(r.counts.LWPOLYLINE >= 6, `LWPOLYLINE ${r.counts.LWPOLYLINE}`);
  for (const t of ['0+000', '0+025', '0+050', '100.300', 'STA 0+025  CL RL 100.300', THAI_NAME]) {
    assert.ok(r.texts.includes(t), `missing text ${t}`);
  }
  const ents = entities(dxf);
  assert.equal(of(ents, 'LWPOLYLINE', 'CL').length, 1);
  assert.equal(of(ents, 'LWPOLYLINE', 'EDGE-EXIST').length, 2);
  assert.equal(of(ents, 'LWPOLYLINE', 'SHOULDER').length, 2);
  assert.equal(of(ents, 'LWPOLYLINE', 'ROW').length, 2);
  assert.equal(of(ents, 'LWPOLYLINE', 'XS-GROUND').length, 3);
  // left edge drawn at +Y
  const edges = of(ents, 'LWPOLYLINE', 'EDGE-EXIST').map((e) => e.pts[0][1]).sort((a, b) => a - b);
  assert.deepEqual(edges, [-3, 3]);
  // feature at (sta, -offset) on FEATURE
  const circ = of(ents, 'CIRCLE', 'FEATURE');
  assert.equal(circ.length, 1);
  assert.deepEqual([circ[0].x, circ[0].y], [0, 4]);
  assert.ok(r.texts.some((t) => t.includes('เสาไฟ')));
});

test('road: unsorted section gives ground polyline with increasing x; unresolved points skipped', () => {
  const ents = entities(exportRoad(roadProject()));
  const grounds = of(ents, 'LWPOLYLINE', 'XS-GROUND');
  for (const g of grounds) {
    assert.equal(g.pts.length, 3);
    for (let i = 1; i < g.pts.length; i++) assert.ok(g.pts[i][0] > g.pts[i - 1][0], 'x not increasing');
  }
  // the 0+025 section: -3 -> 100.150, 0 -> 100.300, +3 -> 100.120 (vExag 1)
  const g25 = grounds[1];
  assert.ok(Math.abs((g25.pts[1][1] - g25.pts[0][1]) - 0.15) < 1e-6);
  assert.ok(Math.abs((g25.pts[1][0] - g25.pts[0][0]) - 3) < 1e-6);
});

test('road: sections are tiled below the plan, start y = -(maxLeft + 10)', () => {
  const ents = entities(exportRoad(roadProject()));
  const xsY = ents.filter((e) => e.layer && e.layer.startsWith('XS-')).flatMap((e) => e.pts.map((p) => p[1]));
  assert.ok(Math.max(...xsY) <= -(5 + 10) + 1e-9, `section above start line: ${Math.max(...xsY)}`);
  // 3 per row: three sections share one row -> their grounds sit in distinct columns
  const xs = of(ents, 'LWPOLYLINE', 'XS-GROUND').map((g) => g.pts[0][0]);
  assert.ok(xs[0] < xs[1] && xs[1] < xs[2]);
});

test('road: asymmetric road (wide right side) keeps sections below the whole plan', () => {
  const p = roadProject();
  for (const st of p.stations) st.widths = { ...st.widths, rowL: 3, rowR: 20 };
  p.stations[1].features = [{ kind: 'บ่อพัก', offset: 18, note: '' }];
  const ents = entities(exportRoad(p));
  const isSection = (e) => e.layer && e.layer.startsWith('XS-');
  const planYs = ents.filter((e) => !isSection(e)).flatMap((e) => {
    const ys = e.pts.map((q) => q[1]);
    return e.type === 'CIRCLE' ? ys.map((y) => y - 0.3) : ys;
  });
  const planMin = Math.min(...planYs);
  assert.ok(planMin <= -20 + 1e-9, `plan should reach the right ROW: ${planMin}`);
  const secMax = Math.max(...ents.filter(isSection).flatMap((e) => e.pts.map((q) => q[1])));
  assert.ok(secMax < planMin, `section entity at y ${secMax} is not below plan bottom ${planMin}`);
});

test('road: text heights follow the scales', () => {
  const ents = entities(exportRoad(roadProject()));
  const heights = (layer) => [...new Set(of(ents, 'TEXT', layer).map((t) => t.h))];
  assert.deepEqual(heights('STA-TEXT'), [0.25]);
  assert.deepEqual(heights('XS-TEXT'), [0.0625]);
});

test('road: empty project still exports a valid DXF', () => {
  const p = roadProject();
  p.stations = [];
  const r = check(exportRoad(p));
  assert.ok(r.texts.includes(THAI_NAME));
});

test('toilet: unclosed walls export without throwing, wall polyline open, gap note', () => {
  const p = toiletProject([{ name: 'ห้องชาย', wallThk: 0.1, walls: [...ROOM.slice(0, 3), { len: 1.4, dir: 'D' }], openings: [], fixtures: [] }]);
  const dxf = exportToilet(p);
  const r = check(dxf);
  const walls = of(entities(dxf), 'LWPOLYLINE', 'WALL');
  assert.ok(walls.length >= 1);
  assert.ok(walls.every((w) => !w.closed), 'wall polyline should be open');
  const pts = walls[0].pts;
  assert.equal(pts.length, 5);
  assert.ok(Math.abs(pts[4][1] - (pts[0][1] + 0.1)) < 1e-6, 'last point is the real end point');
  assert.ok(r.texts.includes('ไม่ปิดรูป ขาด 0.10 m'), r.texts.join('|'));
  assert.ok(r.texts.includes('ห้องชาย'));
});

test('toilet: closed room has inner + outer closed polylines, wall dims outside', () => {
  for (const walls of [ROOM, [{ len: 1.5, dir: 'U' }, { len: 2, dir: 'R' }, { len: 1.5, dir: 'D' }, { len: 2, dir: 'L' }]]) {
    const p = toiletProject([{ name: 'A', wallThk: 0.1, walls, openings: [], fixtures: [] }]);
    const dxf = exportToilet(p);
    const r = check(dxf);
    const ents = entities(dxf);
    const w = of(ents, 'LWPOLYLINE', 'WALL');
    assert.equal(w.length, 2);
    assert.ok(w.every((e) => e.closed));
    const dimTexts = of(ents, 'TEXT', 'DIM');
    assert.deepEqual(dimTexts.map((t) => t.text).sort(), ['1.50', '1.50', '2.00', '2.00']);
    // inner bbox from the inner polyline (the smaller one)
    const inner = w.map((e) => e.pts).sort((a, b) => Math.max(...a.map((q) => q[0])) - Math.max(...b.map((q) => q[0])))[0];
    const xs = inner.map((q) => q[0]); const ys = inner.map((q) => q[1]);
    const [x0, x1, y0, y1] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)];
    for (const t of dimTexts) {
      const outside = t.x < x0 - 0.1 || t.x > x1 + 0.1 || t.y < y0 - 0.1 || t.y > y1 + 0.1;
      assert.ok(outside, `dim text ${t.text} at ${t.x},${t.y} is inside the room`);
    }
    assert.ok(r.texts.includes('A'));
  }
});

test('toilet: door makes a gap, 8-segment swing arc, opening dim; window line; fixtures', () => {
  const p = toiletProject([{
    name: 'ห้องหญิง', wallThk: 0.1, walls: ROOM,
    openings: [
      { wallIdx: 0, from: 0.5, width: 0.8, height: 2, sill: 0, kind: 'door', swing: 'L' },
      { wallIdx: 1, from: 0.4, width: 0.6, height: 0.6, sill: 1.5, kind: 'window' },
    ],
    fixtures: [{ kind: 'toilet', x: 1.6, y: 1.0, cond: 'ใช้ได้' }, { kind: 'drain', x: 1, y: 0.7 }],
  }]);
  const dxf = exportToilet(p);
  const r = check(dxf);
  const ents = entities(dxf);
  const walls = of(ents, 'LWPOLYLINE', 'WALL');
  assert.ok(walls.every((w) => !w.closed), 'walls must be split at openings');
  // no wall run passes through the door gap on the inner face (y = 0, 0.5 < x < 1.3)
  for (const w of walls) {
    for (let i = 1; i < w.pts.length; i++) {
      const [a, b] = [w.pts[i - 1], w.pts[i]];
      if (Math.abs(a[1]) < 1e-9 && Math.abs(b[1]) < 1e-9) {
        const lo = Math.min(a[0], b[0]); const hi = Math.max(a[0], b[0]);
        assert.ok(hi <= 0.5 + 1e-9 || lo >= 1.3 - 1e-9, `wall crosses door gap: ${lo}..${hi}`);
      }
    }
  }
  const arcs = of(ents, 'LWPOLYLINE', 'OPENING').filter((e) => e.pts.length === 9);
  assert.equal(arcs.length, 1);
  for (const [x, y] of arcs[0].pts) {
    assert.ok(Math.abs(Math.hypot(x - 0.5, y) - 0.8) < 1e-6, 'arc radius = width about hinge');
    assert.ok(y >= -1e-9, 'door swings into the room');
  }
  const dims = of(ents, 'TEXT', 'DIM').map((t) => t.text);
  for (const t of ['2.00', '1.50', '0.80', '0.60']) assert.ok(dims.includes(t), `dim ${t} missing`);
  assert.ok(of(ents, 'LINE', 'OPENING').length >= 1, 'window line');
  assert.equal(of(ents, 'CIRCLE', 'FIXTURE').length, 1);
  assert.ok(of(ents, 'LWPOLYLINE', 'FIXTURE').some((e) => e.closed && e.pts.length === 4));
  assert.ok(r.texts.some((t) => t.startsWith('toilet')));
  assert.ok(r.texts.includes('ห้องหญิง'));
  assert.ok(r.texts.includes('ห้องน้ำ ตลาดสด'));
});

test('toilet: swing R hinges at the far end', () => {
  const p = toiletProject([{
    name: 'B', wallThk: 0.1, walls: ROOM,
    openings: [{ wallIdx: 0, from: 0.5, width: 0.8, kind: 'door', swing: 'R' }], fixtures: [],
  }]);
  const arc = of(entities(exportToilet(p)), 'LWPOLYLINE', 'OPENING').find((e) => e.pts.length === 9);
  for (const [x, y] of arc.pts) assert.ok(Math.abs(Math.hypot(x - 1.3, y) - 0.8) < 1e-6);
});

test('toilet: rooms tile left to right with at least a 2 m gap', () => {
  const p = toiletProject([
    { name: 'A', wallThk: 0.1, walls: ROOM, openings: [], fixtures: [] },
    { name: 'B', wallThk: 0.1, walls: [{ len: 1, dir: 'R' }, { len: 1, dir: 'U' }, { len: 1, dir: 'L' }, { len: 1, dir: 'D' }], openings: [], fixtures: [] },
  ]);
  const walls = of(entities(exportToilet(p)), 'LWPOLYLINE', 'WALL');
  assert.equal(walls.length, 4);
  const boxes = walls.map((w) => [Math.min(...w.pts.map((q) => q[0])), Math.max(...w.pts.map((q) => q[0]))]);
  const a = boxes.filter((b) => b[1] - b[0] > 1.5); // room A inner + outer
  const b = boxes.filter((bx) => bx[1] - bx[0] < 1.5);
  assert.equal(a.length, 2);
  assert.equal(b.length, 2);
  assert.ok(Math.min(...b.map((x) => x[0])) - Math.max(...a.map((x) => x[1])) >= 2 - 1e-9);
});

test('exportCSV road: BOM, header, one row per point with resolved RL', () => {
  const csv = exportCSV(roadProject());
  assert.ok(csv.startsWith('﻿'));
  const rows = csv.slice(1).trim().split(/\r?\n/);
  assert.equal(rows[0], 'sta,offset,label,rl');
  assert.equal(rows.length, 1 + 10);
  assert.ok(rows.includes('0+025,0.00,CL,100.300'));
  assert.ok(rows.includes('0+000,-3.00,ขอบผิวทาง ซ.,100.100'));
  assert.ok(rows.includes('0+050,4.00,skip me,'));
});

test('exportCSV toilet: one row per wall', () => {
  const csv = exportCSV(toiletProject([{ name: 'ห้อง, 1', walls: ROOM }]));
  assert.ok(csv.startsWith('﻿'));
  const rows = csv.slice(1).trim().split(/\r?\n/);
  assert.deepEqual(rows, [
    'room,wallIdx,dir,len',
    '"ห้อง, 1",0,R,2.00', '"ห้อง, 1",1,U,1.50', '"ห้อง, 1",2,L,2.00', '"ห้อง, 1",3,D,1.50',
  ]);
});

test('fileName: sanitized name + local date', () => {
  assert.match(fileName(roadProject(), 'dxf'), /_\d{8}\.dxf$/);
  assert.equal(fileName({ name: 'ถนน/ซอย:5*?' }, 'csv', new Date(2026, 9, 21, 23, 30)), 'ถนนซอย5_20261021.csv');
  assert.equal(fileName({ name: '  ' }, 'dxf', new Date(2026, 0, 2)), 'project_20260102.dxf');
});
