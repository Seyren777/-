// Home: project list, new project, import JSON, delete.

import { listProjects, newProject, deleteProject, importJSON, loadProject } from '../store.js';
import { h, navigate, render, toast, save, TYPE_LABEL } from '../app.js';

export function projectHref(p) {
  return p.type === 'toilet' ? `#/toilet/${p.id}` : `#/road/${p.id}/settings`;
}

function dateTH(iso) {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? '' : d.toLocaleDateString('th-TH', { day: 'numeric', month: 'short', year: '2-digit' });
}

function newForm() {
  let type = 'road-new';
  const name = h('input', { type: 'text', placeholder: 'เช่น ถนนซอยเทศบาล 5', 'aria-label': 'ชื่อโครงการ' });
  const typeBtns = Object.entries(TYPE_LABEL).map(([t, label]) => h('button', {
    type: 'button', class: t === type ? 'choice on' : 'choice',
    onClick: (e) => {
      type = t;
      typeBtns.forEach((b) => b.classList.remove('on'));
      e.currentTarget.classList.add('on');
    },
  }, label));
  const create = () => {
    const p = newProject(type, name.value.trim() || `${TYPE_LABEL[type]} ${new Date().toLocaleDateString('th-TH')}`);
    if (type === 'toilet') p.rooms.push({ name: 'ห้อง 1', wallThk: 0.1, walls: [], openings: [], fixtures: [] });
    if (!save(p)) return;
    navigate(projectHref(p));
  };
  return h('section', { class: 'card' },
    h('h2', null, 'สร้างโครงการใหม่'),
    h('div', { class: 'choices' }, typeBtns),
    h('label', { class: 'field' }, h('span', { class: 'lbl' }, 'ชื่อโครงการ / ชื่อสาย'), name),
    h('button', { type: 'button', class: 'btn primary', onClick: create }, 'สร้าง'));
}

function importBox() {
  const file = h('input', {
    type: 'file', accept: '.json,application/json', class: 'hidden-file',
    onChange: async (e) => {
      const f = e.target.files && e.target.files[0];
      e.target.value = '';
      if (!f) return;
      const text = await f.text();
      let id = null;
      try { id = JSON.parse(text)?.id; } catch { /* importJSON reports it */ }
      if (typeof id === 'string' && loadProject(id)
        && !confirm('มีโครงการนี้ในเครื่องแล้ว ต้องการเขียนทับด้วยไฟล์ที่นำเข้าหรือไม่?')) return;
      let res;
      try {
        res = importJSON(text);
      } catch {
        res = { ok: false, reason: 'บันทึกลงเครื่องไม่สำเร็จ' };
      }
      if (!res.ok) {
        toast(`นำเข้าไม่ได้: ${res.reason}`, true);
        return;
      }
      toast('นำเข้าแล้ว');
      navigate(projectHref(res.project));
    },
  });
  return h('label', { class: 'btn' }, 'นำเข้าไฟล์ JSON', file);
}

export function home() {
  const projects = listProjects();
  const list = projects.length
    ? h('ul', { class: 'plist' }, projects.map((p) => h('li', null,
      h('a', { href: projectHref(p), class: 'pitem' },
        h('b', null, p.name || '(ไม่มีชื่อ)'),
        h('small', null, `${TYPE_LABEL[p.type] || p.type} · ${dateTH(p.createdAt)}`)),
      h('button', {
        type: 'button', class: 'btn danger small', 'aria-label': `ลบ ${p.name}`,
        onClick: () => {
          if (!confirm(`ลบโครงการ "${p.name}"? ข้อมูลในเครื่องจะหายถาวร (ควรสำรอง JSON ก่อน)`)) return;
          try { deleteProject(p.id); } catch { toast('ลบไม่สำเร็จ', true); }
          render();
        },
      }, 'ลบ'))))
    : h('p', { class: 'muted' }, 'ยังไม่มีโครงการ');

  return [
    h('header', { class: 'hero' }, h('h1', null, 'วัดหน้างาน'), h('p', null, 'จดหน้างานถนน / ห้องน้ำ แล้วส่งออก DXF เข้า AutoCAD')),
    h('section', { class: 'card' }, h('h2', null, 'โครงการในเครื่อง'), list, importBox()),
    newForm(),
  ];
}
