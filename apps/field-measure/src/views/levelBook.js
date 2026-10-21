// Level book: editable BS/IS/FS rows with live HI/RL, sums, arithmetic check and closure banner.

import { computeLevelBook } from '../level.js';
import { formatSta } from '../road.js';
import { h, numInput, textInput, save, render, fmt, uid } from '../app.js';

export const CLOSURE_TOL = 0.010; // m

/** {cls, text} for the closure banner. */
export function closureBanner(closure) {
  if (!closure) return { cls: 'grey', text: 'ไม่มีการปิดวงรอบ' };
  const e = Math.abs(closure.error);
  const ok = e <= CLOSURE_TOL + 1e-9;
  return {
    cls: ok ? 'green' : 'red',
    text: `ปิดวงรอบ คลาดเคลื่อน ±${fmt(e, 3)} m${ok ? '' : ` (เกินเกณฑ์ ±${fmt(CLOSURE_TOL, 3)} m)`}`,
  };
}

/** Remove row i; section points that read from it lose their link (their RL becomes blank). */
function deleteRow(p, i) {
  const row = p.levelBook[i];
  for (const st of p.stations) {
    for (const pt of st.section || []) if (pt.readingId === row.id) delete pt.readingId;
  }
  p.levelBook.splice(i, 1);
}

export function levelBook(p) {
  const cells = []; // per row: {hi, rl} spans
  const sums = h('div', { class: 'sums' });
  const banner = h('div', { class: 'banner' });

  const refresh = () => {
    const book = computeLevelBook(p.levelBook, p.bms);
    book.rows.forEach((r, i) => {
      if (!cells[i]) return;
      cells[i].hi.textContent = Number.isFinite(r.hi) ? fmt(r.hi, 3) : '';
      cells[i].rl.textContent = Number.isFinite(r.rl) ? fmt(r.rl, 3) : '';
    });
    const diff = book.sumBS - book.sumFS;
    const check = Math.abs(diff - book.deltaRL) < 0.0005;
    sums.replaceChildren(...[
      h('span', null, `ΣBS ${fmt(book.sumBS, 3)}`),
      h('span', null, `ΣFS ${fmt(book.sumFS, 3)}`),
      h('span', null, `ΣBS−ΣFS ${fmt(diff, 3)}`),
      h('span', null, `ΔRL ${fmt(book.deltaRL, 3)}`),
      check ? null : h('b', { class: 'warn' }, 'ΣBS−ΣFS ไม่เท่ากับ RL สุดท้าย − RL แรก — ตรวจแถวที่ขาดค่า'),
    ].filter(Boolean));
    const b = closureBanner(book.closure);
    banner.className = `banner ${b.cls}`;
    banner.textContent = b.text;
  };

  const rows = p.levelBook.map((r, i) => {
    const hi = h('td', { class: 'calc' });
    const rl = h('td', { class: 'calc rl' });
    cells[i] = { hi, rl };
    const n = (key) => h('td', null, numInput(r[key], (v) => { r[key] = v; save(p); refresh(); }, { digits: 3 }));
    const linked = p.stations.some((st) => (st.section || []).some((pt) => pt.readingId === r.id));
    return h('tr', null,
      h('td', null, textInput(r.point, (v) => { r.point = v; save(p); refresh(); }, { 'aria-label': 'จุด' }),
        r.staRef !== undefined && r.staRef !== null && Number.isFinite(Number(r.staRef))
          ? h('small', { class: 'staref' }, `STA ${formatSta(Number(r.staRef))}`) : null),
      n('bs'), n('is'), n('fs'), hi, rl,
      h('td', null, textInput(r.note, (v) => { r.note = v; save(p); }, { 'aria-label': 'หมายเหตุ' })),
      h('td', null, h('button', {
        type: 'button', class: 'btn danger small', 'aria-label': 'ลบแถว',
        onClick: () => {
          const msg = linked ? 'แถวนี้เป็นค่าอ่านของจุดรูปตัด ลบแล้ว RL ของจุดนั้นจะว่าง ลบหรือไม่?' : 'ลบแถวนี้?';
          if (!confirm(msg)) return;
          deleteRow(p, i);
          save(p);
          render();
        },
      }, '×')));
  });

  const add = () => {
    const first = p.levelBook.length === 0 && p.bms[0];
    p.levelBook.push({ id: uid(), point: first ? p.bms[0].name : '', bs: null, is: null, fs: null, note: '' });
    save(p);
    render();
  };

  const view = [
    h('section', { class: 'card' },
      h('h2', null, 'สมุดระดับ'),
      p.bms.length
        ? h('p', { class: 'hint' }, `BM: ${p.bms.map((b) => `${b.name} = ${fmt(b.rl, 3)}`).join(' · ')} — แถวแรกตั้งชื่อจุดเป็นชื่อ BM`)
        : h('p', { class: 'warn' }, h('a', { href: `#/road/${p.id}/settings` }, 'ยังไม่มี BM — ไปเพิ่มในหน้าตั้งค่า')),
      banner,
      h('div', { class: 'scroll-x' },
        h('table', { class: 'lb' },
          h('thead', null, h('tr', null, ['จุด', 'BS', 'IS', 'FS', 'HI', 'RL', 'หมายเหตุ', ''].map((t) => h('th', null, t)))),
          h('tbody', null, rows))),
      h('button', { type: 'button', class: 'btn', onClick: add }, '+ เพิ่มแถว'),
      sums),
  ];
  refresh();
  return view;
}
