import { test, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import {
  setStorage, newProject, listProjects, saveProject, loadProject,
  deleteProject, exportJSON, importJSON,
} from '../../apps/field-measure/src/store.js';

function fakeStorage() {
  const m = new Map();
  return {
    getItem: (k) => (m.has(k) ? m.get(k) : null),
    setItem: (k, v) => { m.set(k, String(v)); },
    removeItem: (k) => { m.delete(k); },
  };
}

beforeEach(() => setStorage(fakeStorage()));

test('newProject builds a v1 project with default settings', () => {
  const p = newProject('road-new', 'ถนนสาย 1');
  assert.equal(p.version, 1);
  assert.equal(p.type, 'road-new');
  assert.equal(p.name, 'ถนนสาย 1');
  assert.ok(typeof p.id === 'string' && p.id.length > 0);
  assert.ok(!Number.isNaN(Date.parse(p.createdAt)));
  assert.deepEqual(p.settings, {
    stationStart: 0, interval: 25, length: 0,
    scales: { plan: 100, section: 25, toilet: 50 }, vExag: 1, font: 'Tahoma',
  });
  assert.deepEqual([p.bms, p.stations, p.levelBook, p.rooms], [[], [], [], []]);
});

test('newProject rejects unknown type', () => {
  assert.throws(() => newProject('bogus', 'x'));
});

test('newProject instances do not share state', () => {
  const a = newProject('toilet', 'a');
  const b = newProject('toilet', 'b');
  a.settings.scales.plan = 1;
  a.rooms.push({});
  assert.equal(b.settings.scales.plan, 100);
  assert.equal(b.rooms.length, 0);
  assert.notEqual(a.id, b.id);
});

test('saveProject then listProjects returns one summary', () => {
  const p = newProject('road-improve', 'งานปรับปรุง');
  saveProject(p);
  const list = listProjects();
  assert.equal(list.length, 1);
  assert.deepEqual(list[0], { id: p.id, name: p.name, type: p.type, createdAt: p.createdAt });
});

test('saveProject overwrites same id; loadProject round-trips', () => {
  const p = newProject('toilet', 'ห้องน้ำ');
  saveProject(p);
  p.name = 'ห้องน้ำ 2';
  saveProject(p);
  assert.equal(listProjects().length, 1);
  assert.deepEqual(loadProject(p.id), p);
});

test('loadProject returns null for unknown id', () => {
  assert.equal(loadProject('nope'), null);
});

test('listProjects sorted newest first', () => {
  const a = newProject('toilet', 'a'); a.createdAt = '2026-01-01T00:00:00.000Z';
  const b = newProject('toilet', 'b'); b.createdAt = '2026-03-01T00:00:00.000Z';
  const c = newProject('toilet', 'c'); c.createdAt = '2026-02-01T00:00:00.000Z';
  [a, b, c].forEach(saveProject);
  assert.deepEqual(listProjects().map((s) => s.name), ['b', 'c', 'a']);
});

test('deleteProject removes it', () => {
  const p = newProject('toilet', 'x');
  const q = newProject('toilet', 'y');
  saveProject(p); saveProject(q);
  deleteProject(p.id);
  assert.equal(loadProject(p.id), null);
  assert.deepEqual(listProjects().map((s) => s.id), [q.id]);
});

test('persists in storage under key fieldmeasure.v1', () => {
  const s = fakeStorage();
  setStorage(s);
  saveProject(newProject('toilet', 'x'));
  assert.ok(s.getItem('fieldmeasure.v1'));
});

test('exportJSON / importJSON round-trip', () => {
  const p = newProject('road-new', 'rt');
  p.bms.push({ name: 'BM1', rl: 100.5 });
  const r = importJSON(exportJSON(p));
  assert.equal(r.ok, true);
  assert.deepEqual(r.project, p);
  assert.equal(listProjects().length, 1);
  assert.deepEqual(loadProject(p.id), p);
});

test('importJSON rejects wrong version and leaves list unchanged', () => {
  saveProject(newProject('toilet', 'keep'));
  const r = importJSON('{"version":2}');
  assert.equal(r.ok, false);
  assert.ok(r.reason);
  assert.equal(listProjects().length, 1);
});

test('importJSON rejects invalid JSON, non-objects, unknown type', () => {
  for (const t of ['{not json', 'null', '[]', '"x"', '{"version":1,"type":"bogus","id":"a"}']) {
    const r = importJSON(t);
    assert.equal(r.ok, false, t);
    assert.ok(r.reason);
  }
  assert.equal(listProjects().length, 0);
});

test('importJSON fills missing arrays (rooms) and settings defaults', () => {
  const r = importJSON(JSON.stringify({
    version: 1, id: 'abc', type: 'road-new', name: 'n', createdAt: '2026-01-01T00:00:00.000Z',
    settings: { interval: 10, scales: { plan: 200 } },
    stations: [{ sta: 0 }],
  }));
  assert.equal(r.ok, true);
  const p = r.project;
  assert.deepEqual(p.rooms, []);
  assert.deepEqual(p.bms, []);
  assert.deepEqual(p.levelBook, []);
  assert.equal(p.stations.length, 1);
  assert.deepEqual(p.settings, {
    stationStart: 0, interval: 10, length: 0,
    scales: { plan: 200, section: 25, toilet: 50 }, vExag: 1, font: 'Tahoma',
  });
  assert.deepEqual(loadProject('abc'), p);
  assert.equal(listProjects().length, 1);
});

test('importJSON fills missing settings entirely', () => {
  const r = importJSON('{"version":1,"type":"toilet","id":"z","name":"n"}');
  assert.equal(r.ok, true);
  assert.equal(r.project.settings.interval, 25);
  assert.ok(r.project.createdAt);
});

test('falls back to in-memory storage when setStorage(null)', () => {
  setStorage(null);
  const p = newProject('toilet', 'mem');
  saveProject(p);
  assert.equal(listProjects().length, 1);
  assert.equal(loadProject(p.id).name, 'mem');
});
