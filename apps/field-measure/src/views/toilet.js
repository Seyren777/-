// Toilet project: rooms; per room walls (length + direction) with live closure check,
// openings, fixtures and finishes.

import { wallPolygon } from '../toilet.js';
import { h, field, numInput, select, textInput, save, render, fmt } from '../app.js';

export const DIR_LABEL = { U: 'ขึ้น', D: 'ลง', L: 'ซ้าย', R: 'ขวา' };
const NEXT_CW = { U: 'R', R: 'D', D: 'L', L: 'U' }; // walking clockwise
export const OPENING_KINDS = [['door', 'ประตู'], ['window', 'หน้าต่าง'], ['vent', 'ช่องระบายอากาศ']];
export const SWINGS = [['L', 'บานพับซ้าย เปิดเข้า'], ['R', 'บานพับขวา เปิดเข้า'], ['LO', 'บานพับซ้าย เปิดออก'], ['RO', 'บานพับขวา เปิดออก']];
export const FIXTURE_KINDS = [
  ['toilet', 'โถส้วมนั่งราบ'], ['squat', 'โถส้วมนั่งยอง'], ['basin', 'อ่างล้างหน้า'], ['urinal', 'โถปัสสาวะ'],
  ['shower', 'ฝักบัว'], ['drain', 'ท่อน้ำทิ้ง/floor drain'], ['tap', 'ก๊อกน้ำ'],
];
const CONDS = ['ใช้ได้', 'เปลี่ยน'];

/** Closure status text for a wall list. */
export function closureText(walls) {
  const wp = wallPolygon(walls);
  if (wp.pts.length < 3) return { ok: false, text: 'ใส่ผนังอย่างน้อย 3 ด้าน' };
  if (wp.closed) return { ok: true, text: 'ปิดรูปสนิท' };
  return { ok: false, text: `ไม่ปิด ขาด ${fmt(wp.gap.dist, 2)} m (dx ${fmt(wp.gap.dx, 2)}, dy ${fmt(wp.gap.dy, 2)})` };
}

/** Delete wall i and keep openings pointing at the same physical walls. */
export function deleteWall(room, i) {
  room.walls.splice(i, 1);
  room.openings = (room.openings || [])
    .filter((o) => Number(o.wallIdx) !== i)
    .map((o) => (Number(o.wallIdx) > i ? { ...o, wallIdx: Number(o.wallIdx) - 1 } : o));
}

function newRoom(n) {
  return { name: `ห้อง ${n}`, wallThk: 0.1, walls: [], openings: [], fixtures: [], ceiling: null, floorLevel: null, floorMat: '', wallMat: '' };
}

const roomIdx = new Map(); // project id -> selected room

function sketch(walls) {
  const NS = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(NS, 'svg');
  svg.setAttribute('class', 'sketch');
  svg.setAttribute('role', 'img');
  svg.setAttribute('aria-label', 'ภาพร่างผังห้อง');
  const wp = wallPolygon(walls);
  if (!wp.pts.length) return svg;
  const end = [-wp.gap.dx, -wp.gap.dy];
  const all = [...wp.pts, end];
  const xs = all.map((q) => q[0]);
  const ys = all.map((q) => q[1]);
  const minX = Math.min(...xs);
  const maxY = Math.max(...ys);
  const span = Math.max(Math.max(...xs) - minX, maxY - Math.min(...ys), 0.5);
  const k = 160 / span;
  const X = (x) => (10 + (x - minX) * k).toFixed(1);
  const Y = (y) => (10 + (maxY - y) * k).toFixed(1);
  svg.setAttribute('viewBox', '0 0 180 180');
  const el = (tag, attrs) => {
    const e = document.createElementNS(NS, tag);
    for (const [a, v] of Object.entries(attrs)) e.setAttribute(a, v);
    svg.append(e);
  };
  const line = [...wp.pts, wp.closed ? wp.pts[0] : end];
  el('polyline', { points: line.map(([x, y]) => `${X(x)},${Y(y)}`).join(' '), class: 'sk-wall' });
  if (!wp.closed) el('line', { x1: X(end[0]), y1: Y(end[1]), x2: X(0), y2: Y(0), class: 'sk-gap' });
  el('circle', { cx: X(0), cy: Y(0), r: 4, class: 'sk-start' });
  return svg;
}

function wallsCard(p, room) {
  const status = h('p', { class: 'status' });
  const pic = h('div', { class: 'sketch-box' });
  const refresh = () => {
    const c = closureText(room.walls);
    status.className = `status ${c.ok ? 'green' : 'red'}`;
    status.textContent = c.text;
    pic.replaceChildren(sketch(room.walls));
  };
  const rows = room.walls.map((w, i) => h('div', { class: 'wall' },
    h('b', null, `${i + 1}`),
    numInput(w.len, (v) => { w.len = v; save(p); refresh(); }, { placeholder: 'ยาว (m)', digits: 2 }),
    h('div', { class: 'dirs' }, Object.entries(DIR_LABEL).map(([d, label]) => h('button', {
      type: 'button', class: `chip${w.dir === d ? ' on' : ''}`,
      onClick: (e) => {
        w.dir = d;
        save(p);
        e.currentTarget.parentNode.querySelectorAll('.chip').forEach((b) => b.classList.remove('on'));
        e.currentTarget.classList.add('on');
        refresh();
      },
    }, label))),
    h('button', {
      type: 'button', class: 'btn danger small', 'aria-label': `ลบผนัง ${i + 1}`,
      onClick: () => {
        const hasOps = (room.openings || []).some((o) => Number(o.wallIdx) === i);
        if (hasOps && !confirm('ผนังนี้มีช่องเปิด ลบผนังและช่องเปิดนั้นหรือไม่?')) return;
        deleteWall(room, i);
        save(p);
        render();
      },
    }, '×')));
  const add = () => {
    const last = room.walls[room.walls.length - 1];
    room.walls.push({ len: null, dir: last ? NEXT_CW[last.dir] || 'R' : 'U' });
    save(p);
    render();
    const inputs = document.querySelectorAll('.wall input');
    inputs[inputs.length - 1]?.focus();
  };
  const card = h('section', { class: 'card' },
    h('h2', null, 'ผนัง (ผิวด้านใน)'),
    h('p', { class: 'hint' }, 'เริ่มที่มุมอ้างอิง (0,0) แล้ววัดวนตามเข็มนาฬิกา ทีละด้าน'),
    rows,
    h('button', { type: 'button', class: 'btn', onClick: add }, '+ เพิ่มผนัง'),
    status, pic);
  refresh();
  return card;
}

function openingsCard(p, room) {
  const wallOpts = room.walls.map((w, i) => [String(i), `ผนัง ${i + 1} (${DIR_LABEL[w.dir] || '?'} ${fmt(w.len, 2)})`]);
  const rows = room.openings.map((o, i) => h('div', { class: 'item' },
    h('div', { class: 'two' },
      field('ชนิด', select(OPENING_KINDS, o.kind, (v) => { o.kind = v; save(p); render(); })),
      field('อยู่บน', select(wallOpts, String(o.wallIdx ?? ''), (v) => { o.wallIdx = Number(v); save(p); }))),
    h('div', { class: 'four' },
      field('ห่างจากมุมเริ่มผนัง', numInput(o.from, (v) => { o.from = v; save(p); }, { digits: 2 })),
      field('กว้าง', numInput(o.width, (v) => { o.width = v; save(p); }, { digits: 2 })),
      field('สูง', numInput(o.height, (v) => { o.height = v; save(p); }, { digits: 2 })),
      field('ธรณี', numInput(o.sill, (v) => { o.sill = v; save(p); }, { digits: 2 }))),
    o.kind === 'door' ? field('บานเปิด', select(SWINGS, o.swing || 'L', (v) => { o.swing = v; save(p); })) : null,
    h('button', {
      type: 'button', class: 'btn danger small',
      onClick: () => { room.openings.splice(i, 1); save(p); render(); },
    }, 'ลบช่องเปิด')));
  return h('section', { class: 'card' },
    h('h2', null, 'ช่องเปิด (m)'),
    room.walls.length ? null : h('p', { class: 'hint' }, 'ใส่ผนังก่อน'),
    rows,
    room.walls.length ? h('button', {
      type: 'button', class: 'btn',
      onClick: () => {
        room.openings.push({ wallIdx: 0, from: null, width: null, height: null, sill: null, kind: 'door', swing: 'L' });
        save(p);
        render();
      },
    }, '+ เพิ่มช่องเปิด') : null);
}

function fixturesCard(p, room) {
  const rows = room.fixtures.map((f, i) => h('div', { class: 'item' },
    h('div', { class: 'two' },
      field('ชนิด', select(FIXTURE_KINDS, f.kind, (v) => { f.kind = v; save(p); })),
      field('สภาพ', select(CONDS, f.cond || CONDS[0], (v) => { f.cond = v; save(p); }))),
    h('div', { class: 'two' },
      field('x (m)', numInput(f.x, (v) => { f.x = v; save(p); }, { signed: true, digits: 2 })),
      field('y (m)', numInput(f.y, (v) => { f.y = v; save(p); }, { signed: true, digits: 2 }))),
    h('button', {
      type: 'button', class: 'btn danger small',
      onClick: () => { room.fixtures.splice(i, 1); save(p); render(); },
    }, 'ลบสุขภัณฑ์')));
  return h('section', { class: 'card' },
    h('h2', null, 'สุขภัณฑ์เดิม'),
    h('p', { class: 'hint' }, 'x, y = ระยะจากมุมอ้างอิง (0,0) ไปกึ่งกลางสุขภัณฑ์ · x ไปทางขวา, y ขึ้น'),
    rows,
    h('button', {
      type: 'button', class: 'btn',
      onClick: () => { room.fixtures.push({ kind: 'toilet', x: null, y: null, cond: CONDS[0] }); save(p); render(); },
    }, '+ เพิ่มสุขภัณฑ์'));
}

function settingsCard(p) {
  const s = p.settings;
  return h('details', { class: 'card' },
    h('summary', null, 'ตั้งค่าโครงการ'),
    field('ชื่อโครงการ', textInput(p.name, (v) => { p.name = v; save(p); document.querySelector('.top .title b').textContent = v; })),
    field('สเกลแปลนห้องน้ำ 1 :', numInput(s.scales.toilet, (v) => { if (v > 0) { s.scales.toilet = v; save(p); } })),
    field('ฟอนต์ใน DXF', select([['Tahoma', 'Tahoma'], ['Angsana', 'Angsana New']], s.font || 'Tahoma', (v) => { s.font = v; save(p); })));
}

export function toilet(p) {
  let changed = false;
  if (!p.rooms.length) { p.rooms.push(newRoom(1)); changed = true; }
  for (const r of p.rooms) {
    for (const k of ['walls', 'openings', 'fixtures']) if (!Array.isArray(r[k])) { r[k] = []; changed = true; }
  }
  if (changed) save(p);
  const ri = Math.min(roomIdx.get(p.id) ?? 0, p.rooms.length - 1);
  const room = p.rooms[ri];

  const roomTabs = h('div', { class: 'chips rooms' },
    p.rooms.map((r, i) => h('button', {
      type: 'button', class: `chip${i === ri ? ' on' : ''}`, onClick: () => { roomIdx.set(p.id, i); render(); },
    }, r.name || `ห้อง ${i + 1}`)),
    h('button', {
      type: 'button', class: 'chip add',
      onClick: () => { p.rooms.push(newRoom(p.rooms.length + 1)); roomIdx.set(p.id, p.rooms.length - 1); save(p); render(); },
    }, '+ เพิ่มห้อง'));

  return [
    settingsCard(p),
    roomTabs,
    h('section', { class: 'card' },
      h('div', { class: 'two' },
        field('ชื่อห้อง', textInput(room.name, (v) => { room.name = v; save(p); }, { placeholder: 'ชาย / หญิง / ผู้พิการ' })),
        field('ผนังหนา (m)', numInput(room.wallThk ?? 0.1, (v) => { room.wallThk = v; save(p); }, { digits: 2 }))),
      p.rooms.length > 1 ? h('button', {
        type: 'button', class: 'btn danger small',
        onClick: () => {
          if (!confirm(`ลบ "${room.name}"?`)) return;
          p.rooms.splice(ri, 1);
          roomIdx.set(p.id, 0);
          save(p);
          render();
        },
      }, 'ลบห้องนี้') : null),
    wallsCard(p, room),
    openingsCard(p, room),
    fixturesCard(p, room),
    h('section', { class: 'card' },
      h('h2', null, 'อื่นๆ'),
      h('div', { class: 'two' },
        field('ความสูงฝ้า (m)', numInput(room.ceiling, (v) => { room.ceiling = v; save(p); }, { digits: 2 })),
        field('ระดับพื้นเทียบทางเดิน (m)', numInput(room.floorLevel, (v) => { room.floorLevel = v; save(p); }, { signed: true, digits: 2 }))),
      field('ชนิดพื้นเดิม', textInput(room.floorMat, (v) => { room.floorMat = v; save(p); }, { placeholder: 'เช่น กระเบื้องเซรามิก' })),
      field('ชนิดผนังเดิม', textInput(room.wallMat, (v) => { room.wallMat = v; save(p); }, { placeholder: 'เช่น ก่ออิฐฉาบปูน บุกระเบื้อง' }))),
  ];
}
