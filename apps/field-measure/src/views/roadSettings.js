// Road project settings: name, chainage range, BMs, drawing scales, font; generate stations.

import { formatSta, parseSta, generateStations } from '../road.js';
import {
  h, field, numInput, select, textInput, save, toast, render, newStation, parseNum, CL_LABEL,
} from '../app.js';

const EPS = 1e-6;

/** null when OK, else a Thai error message. Guards generateStations against non-finite / tiny input. */
export function validateRoadSettings({ stationStart, length, interval }) {
  const n = (v) => (typeof v === 'number' ? v : parseNum(v));
  const s = n(stationStart);
  const l = n(length);
  const i = n(interval);
  if (!Number.isFinite(s)) return 'สถานีเริ่มไม่ถูกต้อง';
  if (!Number.isFinite(l) || l <= 0) return 'ความยาวต้องเป็นตัวเลขมากกว่า 0';
  if (!Number.isFinite(i) || i < 1) return 'ระยะสถานีต้องไม่น้อยกว่า 1 m';
  if (l / i > 5000) return 'จำนวนสถานีมากเกินไป (เกิน 5000)';
  return null;
}

/** True when a station holds anything the user typed. */
export function stationHasData(st) {
  if (!st) return false;
  if (Object.values(st.widths || {}).some((v) => v !== null && v !== undefined && v !== '')) return true;
  if (st.surface || st.condition || (st.note && st.note.trim()) || st.oldThk != null || st.demolish) return true;
  if ((st.features || []).length) return true;
  return (st.section || []).some((p) => p.readingId || (p.rl !== undefined && p.rl !== null) || p.label !== CL_LABEL || p.offset !== 0);
}

/**
 * Stations for the generated chainages, reusing existing station objects at the same chainage.
 * Existing stations off the new grid are kept when they hold data (e.g. inserted odd stations).
 */
export function mergeStations(existing, staList) {
  const out = [];
  const used = new Set();
  for (const sta of staList) {
    const old = existing.find((s) => Math.abs(s.sta - sta) < EPS);
    if (old) used.add(old);
    out.push(old || newStation(sta));
  }
  for (const s of existing) if (!used.has(s) && stationHasData(s)) out.push(s);
  return out.sort((a, b) => a.sta - b.sta);
}

function bmTable(p) {
  const rows = p.bms.map((bm, i) => h('div', { class: 'row' },
    textInput(bm.name, (v) => { bm.name = v.trim(); save(p); }, { placeholder: 'ชื่อ BM', 'aria-label': 'ชื่อ BM' }),
    numInput(bm.rl, (v) => { bm.rl = v; save(p); }, { placeholder: 'RL (m)', digits: 3 }),
    h('button', {
      type: 'button', class: 'btn danger small',
      onClick: () => { if (confirm(`ลบ ${bm.name || 'BM'}?`)) { p.bms.splice(i, 1); save(p); render(); } },
    }, 'ลบ')));
  return h('section', { class: 'card' },
    h('h2', null, 'หมุดหลักฐาน (BM)'),
    h('p', { class: 'hint' }, 'ชื่อ BM ต้องตรงกับชื่อจุดในสมุดระดับ เพื่อเริ่มและปิดวงรอบ'),
    rows,
    h('button', { type: 'button', class: 'btn', onClick: () => { p.bms.push({ name: `BM${p.bms.length + 1}`, rl: null }); save(p); render(); } }, '+ เพิ่ม BM'));
}

export function roadSettings(p) {
  const s = p.settings;
  const err = h('p', { class: 'error', role: 'alert' });

  const startInput = textInput(formatSta(s.stationStart ?? 0), (v) => {
    const n = parseSta(v);
    startInput.classList.toggle('bad', !Number.isFinite(n));
    if (Number.isFinite(n)) { s.stationStart = n; save(p); }
  }, { inputmode: 'decimal', placeholder: '0+000', class: 'num' });
  startInput.addEventListener('blur', () => { if (Number.isFinite(parseSta(startInput.value))) startInput.value = formatSta(s.stationStart); });

  const interval = h('input', {
    type: 'number', inputmode: 'decimal', step: 5, min: 1, class: 'num', value: s.interval ?? 25,
    onInput: (e) => {
      const n = parseNum(e.target.value);
      if (Number.isFinite(n)) { s.interval = n; save(p); }
    },
  });
  const quick = [10, 20, 25, 50].map((v) => h('button', {
    type: 'button', class: 'chip', onClick: () => { s.interval = v; interval.value = v; save(p); },
  }, `${v} m`));

  const generate = () => {
    const msg = validateRoadSettings(s);
    err.textContent = msg || '';
    if (msg) return;
    const kept = p.stations.filter(stationHasData).length;
    p.stations = mergeStations(p.stations, generateStations(s.stationStart, s.length, s.interval));
    if (!save(p)) return;
    toast(`สร้างแล้ว ${p.stations.length} สถานี${kept ? ` · ข้อมูลที่จดไว้ ${kept} สถานียังอยู่ครบ` : ''}`);
    render();
  };

  const scale = (key, label) => field(label, h('span', { class: 'ratio' }, '1 : ',
    numInput(s.scales[key], (v) => { if (v > 0) { s.scales[key] = v; save(p); } }, { placeholder: '100' })));

  return [
    h('section', { class: 'card' },
      h('h2', null, 'ข้อมูลโครงการ'),
      field('ชื่อสาย / ชื่อโครงการ', textInput(p.name, (v) => { p.name = v; save(p); document.querySelector('.top .title b').textContent = v; })),
      field('สถานีเริ่ม', startInput, 'พิมพ์ 0+000 หรือเป็นเมตร'),
      field('ความยาว (m)', numInput(s.length, (v) => { s.length = v; save(p); }, { placeholder: 'เช่น 250' })),
      field('ระยะสถานี (m)', interval),
      h('div', { class: 'chips' }, quick),
      err,
      h('button', { type: 'button', class: 'btn primary', onClick: generate }, 'สร้างสถานี'),
      h('p', { class: 'hint' }, `ตอนนี้มี ${p.stations.length} สถานี · กดซ้ำได้ ข้อมูลที่จดแล้วไม่หาย`)),
    bmTable(p),
    h('section', { class: 'card' },
      h('h2', null, 'สเกลแบบ (ใช้ตั้งขนาดตัวอักษร)'),
      scale('plan', 'แปลนถนน'),
      scale('section', 'รูปตัดตามขวาง'),
      scale('toilet', 'แปลนห้องน้ำ'),
      field('ขยายสเกลดิ่งรูปตัด', select([['1', '×1 (ไม่ขยาย)'], ['2', '×2'], ['5', '×5'], ['10', '×10']], String(s.vExag ?? 1),
        (v) => { s.vExag = Number(v); save(p); })),
      field('ฟอนต์ใน DXF', select([['Tahoma', 'Tahoma'], ['Angsana', 'Angsana New']], s.font || 'Tahoma',
        (v) => { s.font = v; save(p); }))),
  ];
}
