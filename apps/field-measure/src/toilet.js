// Toilet room geometry. Units: metres. Axes: R:+x, L:-x, U:+y, D:-y.

const r9 = (n) => Math.round(n * 1e9) / 1e9;
const EPS = 1e-6;
const DIRS = { R: [1, 0], L: [-1, 0], U: [0, 1], D: [0, -1] };

/**
 * Walk the walls from (0,0). pts holds the start corner of every wall.
 * gap is the vector from the end point back to (0,0); never throws.
 */
export function wallPolygon(walls) {
  const pts = [];
  let x = 0;
  let y = 0;
  for (const w of Array.isArray(walls) ? walls : []) {
    const len = Number(w && w.len);
    const d = w && DIRS[w.dir];
    if (!d || !Number.isFinite(len) || len <= 0) continue;
    pts.push([r9(x), r9(y)]);
    x += d[0] * len;
    y += d[1] * len;
  }
  const dx = r9(-x);
  const dy = r9(-y);
  const dist = r9(Math.hypot(dx, dy));
  const closed = dist < EPS;
  return { pts, closed, gap: { dx: closed ? 0 : dx, dy: closed ? 0 : dy, dist: closed ? 0 : dist } };
}

/** Offset every edge of a rectilinear polygon outward by thk and intersect neighbours. */
export function outerPolygon(pts, thk) {
  const n = pts.length;
  if (n < 3) return pts.map((p) => [p[0], p[1]]);
  let area2 = 0;
  for (let i = 0; i < n; i++) {
    const [x1, y1] = pts[i];
    const [x2, y2] = pts[(i + 1) % n];
    area2 += x1 * y2 - x2 * y1;
  }
  const s = area2 >= 0 ? 1 : -1; // CCW: outward normal is right of direction
  // Offset line for edge i: point + unit direction.
  const lines = pts.map((p, i) => {
    const q = pts[(i + 1) % n];
    const len = Math.hypot(q[0] - p[0], q[1] - p[1]);
    if (len < EPS) return null;
    const ux = (q[0] - p[0]) / len;
    const uy = (q[1] - p[1]) / len;
    const nx = s * uy;
    const ny = -s * ux;
    return { px: p[0] + nx * thk, py: p[1] + ny * thk, ux, uy, nx, ny };
  });
  return pts.map((p, i) => {
    let a = lines[(i - 1 + n) % n];
    let b = lines[i];
    if (!a && !b) return [p[0], p[1]];
    if (!a) a = b;
    if (!b) b = a;
    const cross = a.ux * b.uy - a.uy * b.ux;
    if (Math.abs(cross) < 1e-9) { // collinear: just push the vertex out
      return [r9(p[0] + a.nx * thk), r9(p[1] + a.ny * thk)];
    }
    const t = ((b.px - a.px) * b.uy - (b.py - a.py) * b.ux) / cross;
    return [r9(a.px + a.ux * t), r9(a.py + a.uy * t)];
  });
}

/** Segment of wall wallIdx from `from` to `from+width` (clamped to wall end). */
export function openingSegment(pts, wallIdx, from, width) {
  const n = pts.length;
  const p = pts[wallIdx];
  const q = pts[(wallIdx + 1) % n];
  const len = Math.hypot(q[0] - p[0], q[1] - p[1]);
  const ux = len > 0 ? (q[0] - p[0]) / len : 0;
  const uy = len > 0 ? (q[1] - p[1]) / len : 0;
  const t0 = Math.min(Math.max(Number(from) || 0, 0), len);
  const t1 = Math.min(t0 + Math.max(Number(width) || 0, 0), len);
  return {
    a: [r9(p[0] + ux * t0), r9(p[1] + uy * t0)],
    b: [r9(p[0] + ux * t1), r9(p[1] + uy * t1)],
  };
}

const RECTS = {
  toilet: [0.4, 0.7],
  squat: [0.5, 0.6],
  basin: [0.45, 0.35],
  urinal: [0.35, 0.3],
};
const CIRCLES = { shower: 0.1, drain: 0.05, tap: 0.05 };

/** Fixture footprint centred on (x, y). */
export function fixtureShape(kind, x, y) {
  if (Object.hasOwn(RECTS, kind)) {
    const [w, h] = RECTS[kind];
    return { kind: 'rect', x, y, w, h };
  }
  if (Object.hasOwn(CIRCLES, kind)) return { kind: 'circle', x, y, r: CIRCLES[kind] };
  return { kind: 'rect', x, y, w: 0.3, h: 0.3 };
}
