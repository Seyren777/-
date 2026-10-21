// Road station maths and plan geometry.
// Plan axes: chainage along +X, left side at +Y (right at -Y).

const r3 = (n) => Math.round(n * 1000) / 1000;
const EPS = 1e-6;

/** 25 -> '0+025', 1237.5 -> '1+237.5', 1000 -> '1+000' */
export function formatSta(m) {
  const v = r3(Number(m));
  const sign = v < 0 ? '-' : '';
  const a = Math.abs(v);
  const km1000 = Math.floor(a / 1000);
  const rest = r3(a - km1000 * 1000);
  const whole = Math.floor(rest);
  const frac = rest - whole;
  let s = String(whole).padStart(3, '0');
  if (frac > 1e-9) s += String(r3(frac)).slice(1); // '.5'
  return `${sign}${km1000}+${s}`;
}

/** '0+025' | '1+237.5' | '25' -> metres (NaN when invalid) */
export function parseSta(s) {
  const t = String(s ?? '').trim();
  const m = /^(-)?(\d+)\+(\d+(?:\.\d+)?)$/.exec(t);
  if (m) {
    const v = Number(m[2]) * 1000 + Number(m[3]);
    return m[1] ? -v : v;
  }
  if (/^-?\d+(?:\.\d+)?$/.test(t)) return Number(t);
  return NaN;
}

/** Stations from start every interval to start+length, always including the end. */
export function generateStations(start, length, interval) {
  const out = [];
  const end = r3(start + length);
  if (!(interval > 0) || !(length >= 0)) return [r3(start)];
  for (let i = 0; ; i++) {
    const v = r3(start + i * interval);
    if (v >= end - EPS) break;
    out.push(v);
  }
  out.push(end);
  return out;
}

/** New sorted array with sta added unless already present (within 1e-6). */
export function insertStation(stations, sta) {
  const out = [...stations];
  if (!out.some((s) => Math.abs(s - sta) < EPS)) out.push(sta);
  return out.sort((a, b) => a - b);
}

function width(w) {
  if (w === null || w === undefined || w === '') return null;
  const n = typeof w === 'number' ? w : Number(w);
  return Number.isFinite(n) ? n : null;
}

const LINES = [
  ['edgeL', 'pavL', 1], ['edgeR', 'pavR', -1],
  ['shL', 'shL', 1], ['shR', 'shR', -1],
  ['rowL', 'rowL', 1], ['rowR', 'rowR', -1],
];

/** Plan polylines [[x,y]] per line; missing widths skipped; <2 points -> []. */
export function planLines(project) {
  const stations = [...(project?.stations ?? [])].sort((a, b) => a.sta - b.sta);
  const res = { cl: [] };
  for (const [name] of LINES) res[name] = [];
  if (stations.length >= 2) {
    res.cl = [[stations[0].sta, 0], [stations[stations.length - 1].sta, 0]];
  }
  for (const [name, key, sign] of LINES) {
    const pts = [];
    for (const st of stations) {
      const w = width(st.widths?.[key]);
      if (w !== null) pts.push([st.sta, sign * w]);
    }
    res[name] = pts.length >= 2 ? pts : [];
  }
  return res;
}

/** Sort by numeric offset; duplicate offsets keep last; non-numeric ignored; no mutation. */
export function orderSection(points) {
  const byOffset = new Map();
  for (const p of points ?? []) {
    const o = p?.offset;
    if (typeof o === 'number' && Number.isFinite(o)) byOffset.set(o, p);
  }
  return [...byOffset.entries()].sort((a, b) => a[0] - b[0]).map(([, p]) => p);
}
