// Project -> DXF / CSV export. Units: metres. No dependencies.
// Road: plan at origin (chainage +X, left at +Y), cross-sections tiled below.
// Toilet: each room's inner/outer walls, openings, fixtures and dimensions, rooms tiled left to right.

import { Dxf } from './dxf.js';
import { computeLevelBook, rlOf } from './level.js';
import { formatSta, planLines, orderSection } from './road.js';
import { wallPolygon, outerPolygon, openingSegment, fixtureShape } from './toilet.js';

const EPS = 1e-6;
const DEFAULT_SCALES = { plan: 100, section: 25, toilet: 50 };

// ---------- helpers ----------

function num(v) {
  if (v === null || v === undefined) return null;
  if (typeof v === 'string' && v.trim() === '') return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

/** Fixed decimals without "-0.00". */
function fmt(n, d) {
  const s = Number(n).toFixed(d);
  return /^-0\.?0*$/.test(s) ? s.slice(1) : s;
}

function scaleOf(project, key) {
  const v = num(project?.settings?.scales?.[key]);
  return v !== null && v > 0 ? v : DEFAULT_SCALES[key];
}

function newDxf(project) {
  try {
    return new Dxf({ font: project?.settings?.font ?? 'Tahoma' });
  } catch {
    return new Dxf({ font: 'Tahoma' });
  }
}

const textH = (project, key) => 0.0025 * scaleOf(project, key);

// ---------- road ----------

/** Resolved, ordered section points [{offset, rl}] (readingId -> level book, else numeric rl). */
function sectionPoints(station, book) {
  const out = [];
  for (const p of orderSection(station.section)) {
    const hasReading = p.readingId !== undefined && p.readingId !== null && p.readingId !== '';
    const rl = hasReading ? num(rlOf(book, p.readingId)) : num(p.rl);
    if (rl !== null) out.push({ offset: p.offset, rl, label: p.label });
  }
  return out;
}

export function exportRoad(project) {
  const d = newDxf(project);
  const hp = textH(project, 'plan');
  const hs = textH(project, 'section');
  const vx = num(project?.settings?.vExag);
  const vExag = vx !== null && vx > 0 ? vx : 1;
  const book = computeLevelBook(project?.levelBook, project?.bms);
  const stations = (project?.stations ?? [])
    .filter((s) => s && num(s.sta) !== null)
    .map((s) => ({ ...s, sta: num(s.sta) }))
    .sort((a, b) => a.sta - b.sta);

  // --- plan ---
  const pl = planLines({ stations });
  const layerOf = { cl: 'CL', edgeL: 'EDGE-EXIST', edgeR: 'EDGE-EXIST', shL: 'SHOULDER', shR: 'SHOULDER', rowL: 'ROW', rowR: 'ROW' };
  for (const [key, layer] of Object.entries(layerOf)) {
    if (pl[key] && pl[key].length >= 2) d.polyline(layer, pl[key]);
  }

  // Plan extent each side of CL (left = +Y, right = -Y); ticks reach +-1, feature circles r 0.3.
  let maxLeft = 0;
  let maxRight = stations.length ? 1 : 0;
  for (const st of stations) {
    for (const k of ['pavL', 'shL', 'rowL']) {
      const w = num(st.widths?.[k]);
      if (w !== null) maxLeft = Math.max(maxLeft, w);
    }
    for (const k of ['pavR', 'shR', 'rowR']) {
      const w = num(st.widths?.[k]);
      if (w !== null) maxRight = Math.max(maxRight, w);
    }
    for (const f of st.features ?? []) {
      const o = num(f?.offset);
      if (o === null) continue;
      maxLeft = Math.max(maxLeft, -o + 0.3);
      maxRight = Math.max(maxRight, o + 0.3);
    }
  }
  const x0 = stations.length ? stations[0].sta : 0;

  for (const st of stations) {
    d.line('STA-TEXT', st.sta, -1, st.sta, 1);
    d.text('STA-TEXT', st.sta, 1 + hp * 0.5, hp, formatSta(st.sta), { align: 'center' });
    for (const f of st.features ?? []) {
      const o = num(f?.offset);
      if (o === null) continue;
      d.circle('FEATURE', st.sta, -o, 0.3);
      const label = [f.kind, f.note].filter((t) => t !== undefined && t !== null && String(t).trim() !== '').join(' ');
      if (label) d.text('FEATURE', st.sta + 0.4, -o - hp / 2, hp, label);
    }
  }
  d.text('TEXT', x0, maxLeft + 2, hp, project?.name || '');

  // --- cross-sections ---
  const secs = [];
  for (const st of stations) {
    const pts = sectionPoints(st, book);
    if (pts.length < 2) continue;
    const rls = pts.map((p) => p.rl);
    const minRL = Math.min(...rls);
    const maxRL = Math.max(...rls);
    const datum = Math.floor(minRL) - 1;
    const top = Math.ceil(maxRL) + 1;
    let cl = pts[0];
    for (const p of pts) if (Math.abs(p.offset) < Math.abs(cl.offset)) cl = p;
    secs.push({ sta: st.sta, pts, minRL, maxRL, datum, top, cl });
  }
  if (!secs.length) return d.toString();

  const maxLOff = Math.max(0, ...secs.map((s) => -s.pts[0].offset));
  const maxROff = Math.max(0, ...secs.map((s) => s.pts[s.pts.length - 1].offset));
  const cellW = maxLOff + maxROff + 4;
  const titleBand = 3 * hs;
  const labelBand = 9 * hs + 0.2;
  const maxRange = Math.max(...secs.map((s) => s.maxRL - s.minRL));
  const maxGrid = Math.max(...secs.map((s) => (s.top - s.datum) * vExag));
  // Brief: range*vExag + 3; enlarged when the grid, title and labels need more room.
  const cellH = Math.max(maxRange * vExag + 3, titleBand + maxGrid + labelBand + 2);
  const yStart = -(Math.max(maxLeft, maxRight) + 10); // below the full plan extent

  secs.forEach((s, i) => {
    const col = i % 3;
    const row = Math.floor(i / 3);
    const yTop = yStart - row * cellH;
    const cx = x0 + col * cellW + 2 + maxLOff;
    const topY = yTop - titleBand;
    const datumY = topY - (s.top - s.datum) * vExag;
    const Y = (rl) => datumY + (rl - s.datum) * vExag;
    const minOff = s.pts[0].offset;
    const maxOff = s.pts[s.pts.length - 1].offset;
    const xa = cx + Math.min(minOff, 0) - 1;
    const xb = cx + Math.max(maxOff, 0) + 1;

    for (let rl = s.datum; rl <= s.top; rl++) {
      d.line('XS-GRID', xa, Y(rl), xb, Y(rl));
      d.text('XS-TEXT', xa - 0.1, Y(rl) - hs / 2, hs, fmt(rl, 3), { align: 'right' });
    }
    d.line('XS-GRID', cx, datumY, cx, topY);
    d.polyline('XS-GROUND', s.pts.map((p) => [cx + p.offset, Y(p.rl)]));
    for (const p of s.pts) {
      const gx = cx + p.offset;
      d.text('XS-TEXT', gx + hs / 2, datumY - 0.1, hs, fmt(p.offset, 2), { align: 'right', rot: 90 });
      d.text('XS-TEXT', gx + hs / 2, Y(p.rl) + 0.1, hs, fmt(p.rl, 3), { rot: 90 });
    }
    d.text('XS-TEXT', cx, topY + hs, hs, `STA ${formatSta(s.sta)}  CL RL ${fmt(s.cl.rl, 3)}`, { align: 'center' });
  });

  return d.toString();
}

// ---------- toilet ----------

const DIRS = { R: 1, L: 1, U: 1, D: 1 };
const isWall = (w) => !!w && Object.hasOwn(DIRS, w.dir) && Number.isFinite(Number(w.len)) && Number(w.len) > 0;

function area2(pts) {
  let a = 0;
  for (let i = 0; i < pts.length; i++) {
    const [x1, y1] = pts[i];
    const [x2, y2] = pts[(i + 1) % pts.length];
    a += x1 * y2 - x2 * y1;
  }
  return a;
}

function centroid(pts) {
  const a = area2(pts);
  if (Math.abs(a) < EPS) {
    const n = pts.length || 1;
    return [pts.reduce((s, p) => s + p[0], 0) / n, pts.reduce((s, p) => s + p[1], 0) / n];
  }
  let cx = 0;
  let cy = 0;
  for (let i = 0; i < pts.length; i++) {
    const [x1, y1] = pts[i];
    const [x2, y2] = pts[(i + 1) % pts.length];
    const c = x1 * y2 - x2 * y1;
    cx += (x1 + x2) * c;
    cy += (y1 + y2) * c;
  }
  return [cx / (3 * a), cy / (3 * a)];
}

/**
 * Split a ring into solid runs. cuts: Map edgeIdx -> [[t0,t1]] (distances along the edge).
 * Returns {closedRing: true} when nothing is cut on a closed ring, else {runs:[[pts]]}.
 */
function solidRuns(ring, closed, cuts) {
  const n = ring.length;
  const nEdges = closed ? n : n - 1;
  let anyCut = false;
  const runs = [];
  let cur = null;
  const extend = (p, q) => {
    if (!cur) cur = [p];
    cur.push(q);
  };
  const flush = () => {
    if (cur && cur.length >= 2) runs.push(cur);
    cur = null;
  };
  for (let i = 0; i < nEdges; i++) {
    const P = ring[i];
    const Q = ring[(i + 1) % n];
    const len = Math.hypot(Q[0] - P[0], Q[1] - P[1]);
    if (len < EPS) continue;
    const ux = (Q[0] - P[0]) / len;
    const uy = (Q[1] - P[1]) / len;
    const at = (t) => [P[0] + ux * t, P[1] + uy * t];
    const iv = (cuts.get(i) ?? [])
      .map(([a, b]) => [Math.max(0, Math.min(a, b)), Math.min(len, Math.max(a, b))])
      .filter(([a, b]) => b - a > EPS)
      .sort((p, q) => p[0] - q[0]);
    let t = 0;
    for (const [a, b] of iv) {
      anyCut = true;
      if (a > t + EPS) extend(at(t), at(a));
      flush();
      t = Math.max(t, b);
    }
    if (len > t + EPS) extend(t > 0 ? at(t) : P, Q);
  }
  flush();
  if (closed && !anyCut) return { closedRing: true, runs: [] };
  const same = (p, q) => Math.hypot(p[0] - q[0], p[1] - q[1]) < EPS;
  if (closed && runs.length >= 2 && same(runs[0][0], ring[0]) && same(runs[runs.length - 1].at(-1), ring[0])) {
    const last = runs.pop();
    runs[0] = [...last, ...runs[0].slice(1)];
  }
  return { closedRing: false, runs };
}

function drawRing(d, ring, closed, cuts) {
  const { closedRing, runs } = solidRuns(ring, closed, cuts);
  if (closedRing) d.polyline('WALL', ring, true);
  else for (const r of runs) d.polyline('WALL', r);
}

const translate = (pts, dx) => pts.map(([x, y]) => [x + dx, y]);

/** Geometry of one room in local coordinates, or null when it has no walls. */
function roomGeometry(room) {
  const walls = Array.isArray(room?.walls) ? room.walls : [];
  const wp = wallPolygon(walls);
  if (wp.pts.length < 1) return null;
  const closed = wp.closed && wp.pts.length >= 3;
  const ring = closed ? wp.pts : [...wp.pts, [-wp.gap.dx, -wp.gap.dy]];
  if (ring.length < 2) return null;
  const tk = num(room.wallThk);
  const thk = tk !== null && tk > 0 ? tk : 0.1;
  const outer = closed ? outerPolygon(ring, thk) : null;
  // raw wall index -> polygon edge index (wallPolygon skips invalid walls)
  const edgeOf = new Map();
  let k = 0;
  walls.forEach((w, i) => { if (isWall(w)) edgeOf.set(i, k++); });
  return { wp, closed, ring, outer, thk, edgeOf };
}

function drawRoom(d, room, g, dx, ht, idx) {
  const { wp, closed, thk, edgeOf } = g;
  const ring = translate(g.ring, dx);
  const outer = g.outer ? translate(g.outer, dx) : null;
  const n = ring.length;
  const nEdges = closed ? n : n - 1;
  const s = area2(ring) >= 0 ? 1 : -1; // +1 CCW
  const unit = (i) => {
    const P = ring[i];
    const Q = ring[(i + 1) % n];
    const len = Math.hypot(Q[0] - P[0], Q[1] - P[1]);
    return len > 0 ? [(Q[0] - P[0]) / len, (Q[1] - P[1]) / len, len] : [0, 0, 0];
  };
  const outward = (i) => {
    const [ux, uy] = unit(i);
    return [s * uy, -s * ux];
  };

  const innerCuts = new Map();
  const outerCuts = new Map();
  const ops = [];
  for (const op of Array.isArray(room.openings) ? room.openings : []) {
    const e = edgeOf.get(Number(op?.wallIdx));
    if (e === undefined || e >= nEdges) continue;
    const { a, b } = openingSegment(ring, e, op.from, op.width);
    const P = ring[e];
    const t0 = Math.hypot(a[0] - P[0], a[1] - P[1]);
    const t1 = Math.hypot(b[0] - P[0], b[1] - P[1]);
    if (t1 - t0 < EPS) continue;
    if (!innerCuts.has(e)) innerCuts.set(e, []);
    innerCuts.get(e).push([t0, t1]);
    const [nx, ny] = outward(e);
    const a2 = [a[0] + nx * thk, a[1] + ny * thk];
    const b2 = [b[0] + nx * thk, b[1] + ny * thk];
    if (outer) {
      const O = outer[e];
      const [ux, uy] = unit(e);
      const p = (q) => (q[0] - O[0]) * ux + (q[1] - O[1]) * uy;
      if (!outerCuts.has(e)) outerCuts.set(e, []);
      outerCuts.get(e).push([p(a2), p(b2)]);
    }
    ops.push({ op, e, a, b, a2, b2, nx, ny });
  }

  // walls
  drawRing(d, ring, closed, innerCuts);
  if (outer) drawRing(d, outer, true, outerCuts);

  // openings
  for (const { op, a, b, a2, b2, nx, ny } of ops) {
    if (outer) {
      d.line('WALL', a[0], a[1], a2[0], a2[1]);
      d.line('WALL', b[0], b[1], b2[0], b2[1]);
    }
    const kind = String(op.kind ?? '').toLowerCase();
    if (kind === 'door' || kind === 'ประตู') {
      const sw = String(op.swing ?? 'L').toUpperCase();
      const right = sw.startsWith('R');
      const out = sw.includes('O');
      const hinge = right ? b : a;
      const free = right ? a : b;
      const r = Math.hypot(free[0] - hinge[0], free[1] - hinge[1]);
      const a0 = Math.atan2(free[1] - hinge[1], free[0] - hinge[0]);
      const sgn = out ? 1 : -1; // inward = -outward normal
      const a1 = Math.atan2(sgn * ny, sgn * nx);
      let da = a1 - a0;
      while (da > Math.PI) da -= 2 * Math.PI;
      while (da < -Math.PI) da += 2 * Math.PI;
      const arc = [];
      for (let j = 0; j <= 8; j++) {
        const t = a0 + (da * j) / 8;
        arc.push([hinge[0] + r * Math.cos(t), hinge[1] + r * Math.sin(t)]);
      }
      d.line('OPENING', hinge[0], hinge[1], arc[8][0], arc[8][1]);
      d.polyline('OPENING', arc);
    } else {
      const h = outer ? thk / 2 : 0;
      d.line('OPENING', a[0] + nx * h, a[1] + ny * h, b[0] + nx * h, b[1] + ny * h);
    }
  }

  // dimensions: walls at thk + 0.5 outside, openings one step further out
  const outSign = -s; // dim() offset > 0 is left of the direction; outside is right for CCW
  for (let i = 0; i < nEdges; i++) {
    const P = ring[i];
    const Q = ring[(i + 1) % n];
    if (Math.hypot(Q[0] - P[0], Q[1] - P[1]) < EPS) continue;
    d.dim('DIM', P[0], P[1], Q[0], Q[1], outSign * (thk + 0.5), ht);
  }
  for (const { a, b } of ops) d.dim('DIM', a[0], a[1], b[0], b[1], outSign * (thk + 1.0), ht);

  // fixtures
  for (const f of Array.isArray(room.fixtures) ? room.fixtures : []) {
    const x = num(f?.x);
    const y = num(f?.y);
    if (x === null || y === null) continue;
    const sh = fixtureShape(f.kind, x + dx, y);
    let lx;
    if (sh.kind === 'circle') {
      d.circle('FIXTURE', sh.x, sh.y, sh.r);
      lx = sh.x + sh.r + 0.05;
    } else {
      const hw = sh.w / 2;
      const hh = sh.h / 2;
      d.polyline('FIXTURE', [[sh.x - hw, sh.y - hh], [sh.x + hw, sh.y - hh], [sh.x + hw, sh.y + hh], [sh.x - hw, sh.y + hh]], true);
      lx = sh.x + hw + 0.05;
    }
    const cond = f.cond !== undefined && f.cond !== null && String(f.cond).trim() !== '' ? ` (${f.cond})` : '';
    d.text('FIXTURE', lx, sh.y - ht / 2, ht, `${f.kind ?? ''}${cond}`);
  }

  // name and closure note
  const [cx, cy] = centroid(ring);
  const name = room.name !== undefined && room.name !== null && String(room.name).trim() !== '' ? String(room.name) : `ห้อง ${idx + 1}`;
  d.text('TEXT', cx, cy, ht, name, { align: 'center' });
  if (!wp.closed) d.text('NOTE', cx, cy - 2 * ht, ht, `ไม่ปิดรูป ขาด ${fmt(wp.gap.dist, 2)} m`, { align: 'center' });
}

export function exportToilet(project) {
  const d = newDxf(project);
  const ht = textH(project, 'toilet');
  const margin = 1.0 + 3 * ht; // room outline -> outermost dimension text
  let cursor = null; // first room keeps its reference corner at (0,0)
  let maxY = 0;
  (Array.isArray(project?.rooms) ? project.rooms : []).forEach((room, i) => {
    const g = roomGeometry(room);
    if (!g) return;
    const shape = g.outer ?? g.ring;
    const xs = shape.map((p) => p[0]);
    const ys = shape.map((p) => p[1]);
    const minX = Math.min(...xs) - margin;
    const maxX = Math.max(...xs) + margin;
    const dx = cursor === null ? 0 : cursor - minX;
    drawRoom(d, room, g, dx, ht, i);
    cursor = maxX + dx + 2;
    maxY = Math.max(maxY, Math.max(...ys) + margin);
  });
  d.text('TEXT', 0, maxY + 1, ht, project?.name || '');
  return d.toString();
}

// ---------- CSV / file name ----------

function csvCell(v) {
  const s = v === undefined || v === null ? '' : String(v);
  return /[",\r\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

export function exportCSV(project) {
  const rows = [];
  if (project?.type === 'toilet') {
    rows.push(['room', 'wallIdx', 'dir', 'len']);
    for (const room of project.rooms ?? []) {
      (room?.walls ?? []).forEach((w, i) => {
        const len = num(w?.len);
        rows.push([room.name, i, w?.dir, len === null ? '' : fmt(len, 2)]);
      });
    }
  } else {
    rows.push(['sta', 'offset', 'label', 'rl']);
    const book = computeLevelBook(project?.levelBook, project?.bms);
    const stations = (project?.stations ?? []).filter((s) => s && num(s.sta) !== null)
      .sort((a, b) => num(a.sta) - num(b.sta));
    for (const st of stations) {
      const pts = [...(st.section ?? [])].filter(Boolean).sort((a, b) => {
        const x = num(a.offset);
        const y = num(b.offset);
        if (x === null || y === null) return (x === null) - (y === null);
        return x - y;
      });
      for (const p of pts) {
        const hasReading = p.readingId !== undefined && p.readingId !== null && p.readingId !== '';
        const rl = hasReading ? num(rlOf(book, p.readingId)) : num(p.rl);
        const off = num(p.offset);
        rows.push([formatSta(num(st.sta)), off === null ? '' : fmt(off, 2), p.label, rl === null ? '' : fmt(rl, 3)]);
      }
    }
  }
  return '﻿' + rows.map((r) => r.map(csvCell).join(',')).join('\r\n') + '\r\n';
}

export function fileName(project, ext, date = new Date()) {
  const base = String(project?.name ?? '').replace(/[/\\:*?"<>|\u0000-\u001f]/g, '').trim() || 'project';
  const ymd = `${date.getFullYear()}${String(date.getMonth() + 1).padStart(2, '0')}${String(date.getDate()).padStart(2, '0')}`;
  return `${base}_${ymd}.${ext}`;
}
