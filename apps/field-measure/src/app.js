// App shell: hash router + shared DOM helpers. Views live in ./views/*.js.
// Nothing touches the DOM at import time, so the pure helpers can be imported in Node tests.

import { loadProject, saveProject } from './store.js';
import { home } from './views/home.js';
import { roadSettings } from './views/roadSettings.js';
import { station } from './views/station.js';
import { levelBook } from './views/levelBook.js';
import { toilet } from './views/toilet.js';
import { exportPanel } from './views/exportPanel.js';

// crypto.randomUUID only exists in secure contexts (https/localhost); opening the app over plain
// http on a LAN would otherwise break newProject(). getRandomValues works everywhere.
if (globalThis.crypto && typeof globalThis.crypto.randomUUID !== 'function' && globalThis.crypto.getRandomValues) {
  globalThis.crypto.randomUUID = () => {
    const b = globalThis.crypto.getRandomValues(new Uint8Array(16));
    b[6] = (b[6] & 0x0f) | 0x40;
    b[8] = (b[8] & 0x3f) | 0x80;
    const x = [...b].map((v) => v.toString(16).padStart(2, '0')).join('');
    return `${x.slice(0, 8)}-${x.slice(8, 12)}-${x.slice(12, 16)}-${x.slice(16, 20)}-${x.slice(20)}`;
  };
}

// ---------- pure helpers ----------

export const TYPE_LABEL = { 'road-new': 'สร้างถนนใหม่', 'road-improve': 'ปรับปรุงถนน', toilet: 'ปรับปรุงห้องน้ำ' };
export const CL_LABEL = 'กึ่งกลาง';

export function uid() {
  return globalThis.crypto.randomUUID();
}

/** '1,25' | '1.25' | 1.25 -> 1.25; blank -> null; garbage -> NaN */
export function parseNum(v) {
  if (v === null || v === undefined) return null;
  const s = String(v).trim().replace(',', '.');
  if (s === '') return null;
  const n = Number(s);
  return Number.isFinite(n) ? n : NaN;
}

/** Number -> fixed decimals for display ('' when not a number). */
export function fmt(v, d) {
  if (v === null || v === undefined || v === '' || !Number.isFinite(Number(v))) return '';
  const s = Number(v).toFixed(d);
  return /^-0\.?0*$/.test(s) ? s.slice(1) : s;
}

export function newStation(sta) {
  return {
    sta,
    widths: { pavL: null, pavR: null, shL: null, shR: null, rowL: null, rowR: null },
    surface: '',
    condition: '',
    section: [{ offset: 0, label: CL_LABEL }],
    features: [],
    note: '',
  };
}

// ---------- DOM helpers ----------

/** h('div', {class:'x', onClick: fn}, child, 'text', [more]) */
export function h(tag, props, ...kids) {
  const el = document.createElement(tag);
  const late = {};
  for (const [k, v] of Object.entries(props || {})) {
    if (v === undefined || v === null || v === false) continue;
    if (k === 'value' || k === 'checked') late[k] = v;
    else if (k.startsWith('on') && typeof v === 'function') el.addEventListener(k.slice(2).toLowerCase(), v);
    else if (k === 'class') el.className = v;
    else el.setAttribute(k, v === true ? '' : String(v));
  }
  const add = (c) => {
    if (c === null || c === undefined || c === false) return;
    if (Array.isArray(c)) c.forEach(add);
    else el.append(c instanceof Node ? c : document.createTextNode(String(c)));
  };
  kids.forEach(add);
  for (const [k, v] of Object.entries(late)) el[k] = v; // after <option>s exist
  return el;
}

/**
 * Numeric text field with the decimal keypad. onValue(number|null) fires on every valid edit;
 * invalid text is flagged red and not stored. signed: adds a ± button (iOS decimal pad has no minus).
 */
export function numInput(value, onValue, { digits, signed = false, placeholder, cls, readonly } = {}) {
  const input = h('input', {
    type: 'text', inputmode: 'decimal', autocomplete: 'off', class: `num ${cls || ''}`,
    placeholder, readonly,
    value: value === null || value === undefined ? '' : digits !== undefined ? fmt(value, digits) : String(value),
  });
  const emit = () => {
    const n = parseNum(input.value);
    const bad = Number.isNaN(n);
    input.classList.toggle('bad', bad);
    if (!bad) onValue(n);
  };
  input.addEventListener('input', emit);
  if (!signed || readonly) return input;
  const flip = h('button', {
    type: 'button', class: 'sign', 'aria-label': 'สลับเครื่องหมาย +/−',
    onClick: () => {
      const s = input.value.trim();
      if (!s) input.value = '-';
      else input.value = s.startsWith('-') ? s.slice(1) : `-${s}`;
      emit();
      input.focus();
    },
  }, '±');
  return h('span', { class: 'signed' }, input, flip);
}

export function field(label, control, hint) {
  return h('label', { class: 'field' }, h('span', { class: 'lbl' }, label), control, hint ? h('small', { class: 'hint' }, hint) : null);
}

export function select(options, value, onChange, attrs = {}) {
  // options: [[value, label]] or [value]
  return h('select', { ...attrs, value: value ?? '', onChange: (e) => onChange(e.target.value) },
    options.map((o) => (Array.isArray(o) ? h('option', { value: o[0] }, o[1]) : h('option', { value: o }, o))));
}

export function textInput(value, onValue, attrs = {}) {
  return h('input', { type: 'text', ...attrs, value: value ?? '', onInput: (e) => onValue(e.target.value) });
}

let toastTimer = null;
export function toast(msg, bad = false) {
  const el = document.getElementById('toast');
  if (!el) return;
  el.textContent = msg;
  el.className = bad ? 'show bad' : 'show';
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { el.className = ''; }, bad ? 6000 : 2500);
}

// ---------- state & persistence ----------

const state = { id: null, project: null };

export function currentProject() {
  return state.project;
}

/** Autosave. Storage can throw (quota, private mode) — tell the user to back up instead of failing silently. */
export function save(p = state.project) {
  if (!p) return false;
  try {
    saveProject(p);
    return true;
  } catch {
    toast('บันทึกลงเครื่องไม่สำเร็จ — กด "สำรอง JSON" ทันที', true);
    return false;
  }
}

export function navigate(hash) {
  if (location.hash === hash) render();
  else location.hash = hash;
}

// ---------- router ----------

const ROUTES = [
  [/^#\/road\/([^/]+)\/settings$/, roadSettings, 'settings'],
  [/^#\/road\/([^/]+)\/sta\/(\d+)$/, station, 'sta'],
  [/^#\/road\/([^/]+)\/level$/, levelBook, 'level'],
  [/^#\/road\/([^/]+)\/export$/, exportPanel, 'export'],
  [/^#\/toilet\/([^/]+)\/export$/, exportPanel, 'export'],
  [/^#\/toilet\/([^/]+)$/, toilet, 'rooms'],
];

export const lastStation = new Map(); // project id -> station index last viewed

function tabs(p, active) {
  const base = p.type === 'toilet' ? `#/toilet/${p.id}` : `#/road/${p.id}`;
  const list = p.type === 'toilet'
    ? [['rooms', base, 'ห้อง'], ['export', `${base}/export`, 'ส่งออก']]
    : [
      ['settings', `${base}/settings`, 'ตั้งค่า'],
      ['sta', `${base}/sta/${lastStation.get(p.id) ?? 0}`, 'สถานี'],
      ['level', `${base}/level`, 'สมุดระดับ'],
      ['export', `${base}/export`, 'ส่งออก'],
    ];
  return h('nav', { class: 'tabs' }, list.map(([key, href, label]) => h('a', { href, class: key === active ? 'on' : '' }, label)));
}

export function render() {
  const root = document.getElementById('app');
  if (!root) return;
  const hash = location.hash || '#/';
  const scrollY = window.scrollY;
  const sameView = root.dataset.hash === hash;
  root.dataset.hash = hash;
  root.replaceChildren();

  for (const [re, view, key] of ROUTES) {
    const m = re.exec(hash);
    if (!m) continue;
    const id = decodeURIComponent(m[1]);
    if (state.id !== id || !state.project) {
      state.id = id;
      state.project = loadProject(id);
    }
    const p = state.project;
    if (!p) {
      root.append(h('main', null, h('p', null, 'ไม่พบโครงการนี้ในเครื่อง'), h('a', { href: '#/', class: 'btn' }, 'กลับหน้าแรก')));
      return;
    }
    root.append(
      h('header', { class: 'top' },
        h('a', { href: '#/', class: 'back', 'aria-label': 'กลับรายการโครงการ' }, '‹ โครงการ'),
        h('div', { class: 'title' }, h('b', null, p.name || '(ไม่มีชื่อ)'), h('small', null, TYPE_LABEL[p.type] || ''))),
      h('main', null, view(p, m.slice(2), key)),
      tabs(p, key),
    );
    window.scrollTo(0, sameView ? scrollY : 0);
    return;
  }
  state.id = null;
  state.project = null;
  root.append(h('main', { class: 'home' }, home()));
  window.scrollTo(0, sameView ? scrollY : 0);
}

if (typeof window !== 'undefined' && typeof document !== 'undefined') {
  window.addEventListener('hashchange', render);
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', render);
  else render();
}
