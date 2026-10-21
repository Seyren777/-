// Export panel: DXF / CSV / JSON backup downloads.

import { exportRoad, exportToilet, exportCSV, fileName } from '../export.js';
import { exportJSON } from '../store.js';
import { computeLevelBook } from '../level.js';
import { h, toast, fmt } from '../app.js';
import { closureBanner } from './levelBook.js';
import { closureText } from './toilet.js';

export const BACKUP_NOTE = 'สำรอง JSON ทุกครั้งก่อนปิดงาน — iPhone อาจล้างข้อมูลเว็บที่ไม่ได้เปิดเกิน 7 วัน';

/** Blob + <a download>: works in iOS Safari 13+ (saves to Files / Downloads). */
export function download(text, name, type) {
  const blob = new Blob([text], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = name;
  a.rel = 'noopener';
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 30000); // iOS reads the blob after click() returns
}

function run(make, ext, type) {
  return (p) => {
    try {
      download(make(p), fileName(p, ext), type);
      toast(`ดาวน์โหลด ${fileName(p, ext)}`);
    } catch (err) {
      toast(`ส่งออกไม่สำเร็จ: ${err && err.message ? err.message : err}`, true);
    }
  };
}

const dxf = run((p) => (p.type === 'toilet' ? exportToilet(p) : exportRoad(p)), 'dxf', 'application/octet-stream');
const csv = run(exportCSV, 'csv', 'text/csv;charset=utf-8');
const json = run(exportJSON, 'json', 'application/json');

function summary(p) {
  if (p.type === 'toilet') {
    return h('ul', { class: 'summary' }, p.rooms.map((r, i) => {
      const c = closureText(r.walls || []);
      return h('li', { class: c.ok ? '' : 'warn' }, `${r.name || `ห้อง ${i + 1}`}: ผนัง ${(r.walls || []).length} ด้าน · ${c.text}`);
    }));
  }
  const book = computeLevelBook(p.levelBook, p.bms);
  const b = closureBanner(book.closure);
  const pts = p.stations.reduce((n, s) => n + (s.section || []).length, 0);
  return h('ul', { class: 'summary' },
    h('li', null, `${p.stations.length} สถานี · ${pts} จุดรูปตัด`),
    h('li', null, `สมุดระดับ ${p.levelBook.length} แถว · ΣBS−ΣFS ${fmt(book.sumBS - book.sumFS, 3)}`),
    h('li', { class: b.cls === 'red' ? 'warn' : '' }, b.text));
}

export function exportPanel(p) {
  return h('section', { class: 'card' },
    h('h2', null, 'ส่งออก'),
    summary(p),
    h('button', { type: 'button', class: 'btn primary big', onClick: () => dxf(p) }, 'ดาวน์โหลด DXF'),
    h('button', { type: 'button', class: 'btn big', onClick: () => csv(p) }, 'ดาวน์โหลด CSV'),
    h('button', { type: 'button', class: 'btn big', onClick: () => json(p) }, 'สำรอง JSON'),
    h('p', { class: 'warn backup' }, BACKUP_NOTE),
    h('p', { class: 'hint' }, 'DXF เป็น R2000 หน่วยเมตร เปิดใน AutoCAD ได้โดยตรง · ไฟล์ JSON ใช้ "นำเข้า" ที่หน้าแรกเพื่อย้ายเครื่อง'));
}
