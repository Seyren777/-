// Station page: widths, surface, cross-section points (staff reading -> level book IS row, or RL),
// features, notes; prev/next, copy from previous, insert station.

import { formatSta, parseSta, insertStation } from '../road.js';
import { computeLevelBook, rlOf } from '../level.js';
import {
  h, field, numInput, select, textInput, save, toast, render, navigate, newStation, parseNum, fmt, uid,
  lastStation, CL_LABEL,
} from '../app.js';

const EPS = 1e-6;
export const SURFACES = ['ลูกรัง', 'คสล.', 'แอสฟัลต์', 'หินคลุก', 'ดิน'];
export const CONDITIONS = ['ดี', 'ชำรุด', 'เป็นหลุม'];
export const FEATURE_KINDS = ['เสาไฟ', 'ท่อลอด/ท่อระบายน้ำ', 'บ่อพัก', 'รั้ว/บ้าน', 'ต้นไม้', 'ทางแยก', 'อื่นๆ'];
// quick label -> [width key used to prefill the offset, side sign]
const CHIPS = [
  ['กึ่งกลาง', null, 0],
  ['ขอบผิวทาง ซ.', 'pavL', -1], ['ขอบผิวทาง ข.', 'pavR', 1],
  ['ไหล่ ซ.', 'shL', -1], ['ไหล่ ข.', 'shR', 1],
  ['ร่องน้ำ ซ.', null, -1], ['ร่องน้ำ ข.', null, 1],
  ['เขตทาง ซ.', 'rowL', -1], ['เขตทาง ข.', 'rowR', 1],
];
const WIDTHS = [['ผิวทาง', 'pavL', 'pavR'], ['ไหล่ทาง', 'shL', 'shR'], ['เขตทาง', 'rowL', 'rowR']];

const isCL = (pt) => pt && pt.offset === 0 && pt.label === CL_LABEL;
const blank = (v) => v === null || v === undefined || v === '';

// ---------- pure helpers (tested) ----------

/** Make sure a station has every container and its centreline point. Returns true when it changed. */
export function ensureStation(st) {
  let changed = false;
  const fresh = newStation(st.sta);
  for (const k of ['widths', 'section', 'features']) {
    if (!st[k] || typeof st[k] !== 'object') { st[k] = fresh[k]; changed = true; }
  }
  if (!st.section.some((pt) => pt && pt.offset === 0)) {
    st.section.unshift({ offset: 0, label: CL_LABEL });
    changed = true;
  }
  return changed;
}

/** Drop the level-book link of a point: remove its IS row, or only clear IS when the row is also a BS/FS. */
function unlink(project, point) {
  const i = point.readingId ? project.levelBook.findIndex((r) => r.id === point.readingId) : -1;
  if (i >= 0) {
    const row = project.levelBook[i];
    if (blank(row.bs) && blank(row.fs)) project.levelBook.splice(i, 1);
    else row.is = null;
  }
  delete point.readingId;
}

/** Staff reading for a section point: appends/updates an IS row in the level book; blank empties it in place. */
export function setPointReading(project, station, point, value) {
  const v = typeof value === 'number' ? value : parseNum(value);
  if (Number.isNaN(v)) return;
  delete point.rl;
  const row = point.readingId ? project.levelBook.find((r) => r.id === point.readingId) : undefined;
  if (v === null) {
    // Keep the row (and its place in the reading order) so retyping restores the same RL;
    // computeLevelBook skips a row with no readings. Only deletePoint / RL entry unlink.
    if (row) row.is = null;
    else delete point.readingId;
    return;
  }
  if (row) {
    row.is = v;
    row.point = point.label || '';
    row.staRef = station.sta;
  } else {
    const r = { id: uid(), point: point.label || '', is: v, staRef: station.sta };
    project.levelBook.push(r);
    point.readingId = r.id;
  }
}

/** RL typed directly: sets rl and drops any reading link. */
export function setPointRL(project, point, value) {
  const v = typeof value === 'number' ? value : parseNum(value);
  if (Number.isNaN(v)) return;
  unlink(project, point);
  if (v === null) delete point.rl;
  else point.rl = v;
}

export function setPointLabel(project, point, label) {
  point.label = label;
  const row = point.readingId ? project.levelBook.find((r) => r.id === point.readingId) : undefined;
  if (row) row.point = label;
}

/** Delete section point idx (never the centreline point) and its level-book row. */
export function deletePoint(project, station, idx) {
  const pt = station.section[idx];
  if (!pt || isCL(pt)) return false;
  unlink(project, pt);
  station.section.splice(idx, 1);
  return true;
}

/** Fill blanks of station i from station i-1 (widths, surface, condition, section offsets/labels). */
export function copyFromPrevious(project, i) {
  const cur = project.stations[i];
  const prev = project.stations[i - 1];
  if (!cur || !prev || i < 1) return false;
  ensureStation(cur);
  for (const [k, v] of Object.entries(prev.widths || {})) if (blank(cur.widths[k]) && !blank(v)) cur.widths[k] = v;
  if (!cur.surface && prev.surface) cur.surface = prev.surface;
  if (!cur.condition && prev.condition) cur.condition = prev.condition;
  for (const pt of prev.section || []) {
    if (!pt || isCL(pt) || typeof pt.offset !== 'number') continue;
    if (!cur.section.some((q) => typeof q.offset === 'number' && Math.abs(q.offset - pt.offset) < EPS)) {
      cur.section.push({ offset: pt.offset, label: pt.label });
    }
  }
  return true;
}

// ---------- view ----------

const pointMode = new WeakMap(); // point -> 'reading' | 'rl' (UI only)
let selected = null; // section point the label chips apply to

function staHref(p, i) {
  return `#/road/${p.id}/sta/${i}`;
}

function insertPrompt(p, current) {
  const raw = prompt('แทรกสถานี (เช่น 0+037.5 หรือ 37.5)', current !== undefined ? formatSta(current) : '');
  if (raw === null) return;
  const sta = parseSta(raw);
  if (!Number.isFinite(sta)) { toast('รูปแบบสถานีไม่ถูกต้อง', true); return; }
  const list = insertStation(p.stations.map((s) => s.sta), sta);
  let i = p.stations.findIndex((s) => Math.abs(s.sta - sta) < EPS);
  if (i < 0) {
    i = list.findIndex((s) => Math.abs(s - sta) < EPS);
    p.stations.splice(i, 0, newStation(sta)); // stations are kept sorted by chainage
    save(p);
    toast(`แทรกสถานี ${formatSta(sta)} แล้ว`);
  }
  navigate(staHref(p, i));
}

function widthsCard(p, st) {
  return h('section', { class: 'card' },
    h('h2', null, 'ความกว้างจากกึ่งกลาง (m)'),
    h('div', { class: 'wgrid' },
      h('span'), h('b', null, 'ซ้าย'), h('b', null, 'ขวา'),
      WIDTHS.map(([label, l, r]) => [
        h('span', null, label),
        numInput(st.widths[l], (v) => { st.widths[l] = v; save(p); }),
        numInput(st.widths[r], (v) => { st.widths[r] = v; save(p); }),
      ])),
    h('div', { class: 'two' },
      field('ชนิดผิวเดิม', select([['', '—'], ...SURFACES], st.surface, (v) => { st.surface = v; save(p); })),
      field('สภาพ', select([['', '—'], ...CONDITIONS], st.condition, (v) => { st.condition = v; save(p); }))),
    p.type === 'road-improve' ? h('div', { class: 'two' },
      field('ความหนาผิวเดิม (cm)', numInput(st.oldThk, (v) => { st.oldThk = v; save(p); })),
      field('ช่วงที่ต้องรื้อ', textInput(st.demolish, (v) => { st.demolish = v; save(p); }, { placeholder: 'เช่น ซ.0–3 m' })))
      : null);
}

function sectionCard(p, st) {
  const hasBS = p.levelBook.some((r) => !blank(r.bs));
  const rlSpans = new Map();
  const refreshRL = () => {
    const book = computeLevelBook(p.levelBook, p.bms);
    for (const [pt, span] of rlSpans) {
      const rl = pt.readingId ? rlOf(book, pt.readingId) : pt.rl;
      span.textContent = Number.isFinite(rl) ? `RL ${fmt(rl, 3)}` : 'RL —';
    }
  };

  const rowOf = (pt, idx) => {
    const mode = pointMode.get(pt) || (blank(pt.rl) || pt.readingId ? 'reading' : 'rl');
    const cl = isCL(pt);
    const rlSpan = h('span', { class: 'rl' });
    rlSpans.set(pt, rlSpan);
    const value = mode === 'reading'
      ? numInput(pt.readingId ? p.levelBook.find((r) => r.id === pt.readingId)?.is : null,
        (v) => { setPointReading(p, st, pt, v); save(p); refreshRL(); }, { placeholder: 'ค่าอ่านไม้', digits: 3 })
      : numInput(pt.rl, (v) => { setPointRL(p, pt, v); save(p); refreshRL(); }, { placeholder: 'RL (m)', digits: 3 });
    const modeBtn = h('button', {
      type: 'button', class: 'chip mode',
      onClick: () => { pointMode.set(pt, mode === 'reading' ? 'rl' : 'reading'); selected = pt; render(); },
    }, mode === 'reading' ? 'ค่าอ่าน ⇄' : 'RL ⇄');
    const label = cl
      ? h('b', { class: 'cl' }, CL_LABEL)
      : textInput(pt.label, (v) => { setPointLabel(p, pt, v); save(p); }, { placeholder: 'ชื่อจุด', list: 'fm-labels', 'aria-label': 'ชื่อจุด' });
    const row = h('div', {
      class: `pt${pt === selected ? ' sel' : ''}`,
      onFocusin: () => {
        selected = pt;
        row.parentNode?.querySelectorAll('.pt.sel').forEach((n) => n.classList.remove('sel'));
        row.classList.add('sel');
      },
    },
    h('div', { class: 'pt-head' }, label,
      cl ? null : h('button', {
        type: 'button', class: 'btn danger small',
        onClick: () => {
          if ((pt.readingId || !blank(pt.rl)) && !confirm('ลบจุดนี้ (และค่าอ่านในสมุดระดับ)?')) return;
          if (deletePoint(p, st, idx)) { save(p); render(); }
        },
      }, 'ลบ')),
    h('div', { class: 'pt-body' },
      field('ระยะ (m)', cl ? h('input', { class: 'num', value: '0.00', readonly: true })
        : numInput(pt.offset, (v) => { pt.offset = v; save(p); }, { signed: true, placeholder: '−ซ / +ข', digits: 2 })),
      h('div', { class: 'field' }, modeBtn, value), // not a <label>: a tap would hit the toggle
      rlSpan));
    return row;
  };

  const chips = CHIPS.map(([label, key, sign]) => h('button', {
    type: 'button', class: 'chip',
    onClick: () => {
      if (sign === 0) { selected = st.section.find(isCL) || null; render(); return; }
      const w = key ? parseNum(st.widths[key]) : null;
      const off = Number.isFinite(w) ? sign * w : null;
      // A chip names the selected point only while it has no name yet; otherwise it adds a new point.
      if (selected && !isCL(selected) && st.section.includes(selected) && !(selected.label || '').trim()) {
        setPointLabel(p, selected, label);
        if (blank(selected.offset) && off !== null) selected.offset = off;
      } else {
        selected = { offset: off, label };
        st.section.push(selected);
      }
      save(p);
      render();
    },
  }, label));

  const add = () => {
    selected = { offset: null, label: '' };
    st.section.push(selected);
    save(p);
    render();
  };

  const card = h('section', { class: 'card' },
    h('h2', null, 'รูปตัดตามขวาง'),
    h('p', { class: 'hint' }, 'ระยะ: ลบ = ซ้าย, บวก = ขวา · ค่าอ่านไม้จะลงสมุดระดับเป็น IS อัตโนมัติ'),
    hasBS ? null : h('p', { class: 'warn' }, 'ยังไม่มี BS ในสมุดระดับ — ตั้งกล้องอ่าน BS บน BM ก่อน RL จึงจะคำนวณได้'),
    h('div', { class: 'chips' }, chips),
    h('datalist', { id: 'fm-labels' }, CHIPS.map(([l]) => h('option', { value: l }))),
    st.section.map((pt, i) => rowOf(pt, i)),
    h('button', { type: 'button', class: 'btn', onClick: add }, '+ เพิ่มจุด'));
  refreshRL();
  return card;
}

function featuresCard(p, st) {
  const kindRows = FEATURE_KINDS.map((kind) => {
    const items = st.features.filter((f) => f.kind === kind);
    const on = items.length > 0;
    const toggle = h('button', {
      type: 'button', class: `check${on ? ' on' : ''}`, 'aria-pressed': on ? 'true' : 'false',
      onClick: () => {
        if (on) {
          const typed = items.some((f) => !blank(f.offset) || (f.note && f.note.trim()));
          if (typed && !confirm(`เอา "${kind}" ออก?`)) return;
          st.features = st.features.filter((f) => f.kind !== kind);
        } else st.features.push({ kind, offset: null, note: '' });
        save(p);
        render();
      },
    }, `${on ? '☑' : '☐'} ${kind}`);
    const notePh = kind.startsWith('ท่อ') ? 'ขนาด เช่น Ø0.60' : kind === 'อื่นๆ' ? 'ระบุ' : 'หมายเหตุ';
    return h('div', { class: 'feat' }, toggle,
      items.map((f) => h('div', { class: 'feat-item' },
        numInput(f.offset, (v) => { f.offset = v; save(p); }, { signed: true, placeholder: 'ระยะ −ซ/+ข', digits: 2 }),
        textInput(f.note, (v) => { f.note = v; save(p); }, { placeholder: notePh }),
        items.length > 1 ? h('button', {
          type: 'button', class: 'btn danger small',
          onClick: () => { st.features.splice(st.features.indexOf(f), 1); save(p); render(); },
        }, 'ลบ') : null)),
      on ? h('button', {
        type: 'button', class: 'chip', onClick: () => { st.features.push({ kind, offset: null, note: '' }); save(p); render(); },
      }, `+ ${kind} อีก`) : null);
  });
  return h('section', { class: 'card' }, h('h2', null, 'สิ่งที่พบ'), kindRows,
    field('หมายเหตุ', h('textarea', { rows: 3, value: st.note || '', onInput: (e) => { st.note = e.target.value; save(p); } })));
}

export function station(p, [iStr]) {
  if (!p.stations.length) {
    return h('section', { class: 'card' },
      h('p', null, 'ยังไม่มีสถานี — ไปที่ "ตั้งค่า" ใส่ความยาวและระยะสถานีแล้วกด "สร้างสถานี"'),
      h('a', { class: 'btn primary', href: `#/road/${p.id}/settings` }, 'ไปตั้งค่า'),
      h('button', { type: 'button', class: 'btn', onClick: () => insertPrompt(p) }, 'แทรกสถานี'));
  }
  if (p.stations.some((s, j) => j > 0 && s.sta < p.stations[j - 1].sta)) { // imported out of order
    p.stations.sort((a, b) => a.sta - b.sta);
    save(p);
  }
  const i = Math.min(Math.max(Number(iStr) || 0, 0), p.stations.length - 1);
  lastStation.set(p.id, i);
  const st = p.stations[i];
  if (ensureStation(st)) save(p);
  if (selected && !st.section.includes(selected)) selected = null;

  const go = (j) => navigate(staHref(p, j));
  const jump = select(p.stations.map((s, j) => [String(j), `STA ${formatSta(s.sta)}`]), String(i), (v) => go(Number(v)),
    { class: 'sta-pick', 'aria-label': 'เลือกสถานี' });

  return [
    h('div', { class: 'sta-head' }, jump, h('small', null, `${i + 1} / ${p.stations.length}`)),
    h('div', { class: 'actions' },
      h('button', {
        type: 'button', class: 'btn', disabled: i === 0,
        onClick: () => { if (copyFromPrevious(p, i)) { save(p); toast('คัดลอกช่องที่ว่างจากสถานีก่อนหน้าแล้ว'); render(); } },
      }, 'คัดลอกจากสถานีก่อนหน้า'),
      h('button', { type: 'button', class: 'btn', onClick: () => insertPrompt(p, st.sta) }, 'แทรกสถานี')),
    widthsCard(p, st),
    sectionCard(p, st),
    featuresCard(p, st),
    h('div', { class: 'sta-nav' },
      h('button', { type: 'button', class: 'btn big', disabled: i === 0, onClick: () => go(i - 1) }, '‹ ก่อนหน้า'),
      h('button', { type: 'button', class: 'btn big primary', disabled: i === p.stations.length - 1, onClick: () => go(i + 1) }, 'ถัดไป ›')),
  ];
}
