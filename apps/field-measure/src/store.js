// Project store: schema, persistence (localStorage with in-memory fallback), JSON import/export.
// Units: metres. No external dependencies.

export const STORAGE_KEY = 'fieldmeasure.v1';
export const PROJECT_TYPES = ['road-new', 'road-improve', 'toilet'];

const memory = new Map();
const memoryStorage = {
  getItem: (k) => (memory.has(k) ? memory.get(k) : null),
  setItem: (k, v) => { memory.set(k, String(v)); },
  removeItem: (k) => { memory.delete(k); },
};

let storage = null; // null => resolve lazily

/** Inject a storage object (getItem/setItem/removeItem). Pass null to reset to default. */
export function setStorage(obj) {
  storage = obj || null;
}

function getStorage() {
  if (storage) return storage;
  try {
    if (typeof localStorage !== 'undefined' && localStorage) return localStorage;
  } catch { /* access denied (private mode etc.) */ }
  return memoryStorage;
}

function defaultSettings() {
  return {
    stationStart: 0,
    interval: 25,
    length: 0,
    scales: { plan: 100, section: 25, toilet: 50 },
    vExag: 1,
    font: 'Tahoma',
  };
}

const isObj = (v) => v !== null && typeof v === 'object' && !Array.isArray(v);

function readAll() {
  try {
    const raw = getStorage().getItem(STORAGE_KEY);
    if (!raw) return {};
    const data = JSON.parse(raw);
    return isObj(data) && isObj(data.projects) ? data.projects : {};
  } catch {
    return {};
  }
}

function writeAll(projects) {
  getStorage().setItem(STORAGE_KEY, JSON.stringify({ version: 1, projects }));
}

export function newProject(type, name) {
  if (!PROJECT_TYPES.includes(type)) throw new Error(`unknown project type: ${type}`);
  return {
    version: 1,
    id: crypto.randomUUID(),
    type,
    name,
    createdAt: new Date().toISOString(),
    settings: defaultSettings(),
    bms: [],
    stations: [],
    levelBook: [],
    rooms: [],
  };
}

export function listProjects() {
  return Object.values(readAll())
    .map((p) => ({ id: p.id, name: p.name, type: p.type, createdAt: p.createdAt }))
    .sort((a, b) => (a.createdAt < b.createdAt ? 1 : a.createdAt > b.createdAt ? -1 : 0));
}

export function saveProject(p) {
  const all = readAll();
  all[p.id] = p;
  writeAll(all);
}

export function loadProject(id) {
  const p = readAll()[id];
  return p ? p : null;
}

export function deleteProject(id) {
  const all = readAll();
  if (!(id in all)) return;
  delete all[id];
  writeAll(all);
}

export function exportJSON(p) {
  return JSON.stringify(p, null, 2);
}

export function importJSON(text) {
  let data;
  try {
    data = JSON.parse(text);
  } catch {
    return { ok: false, reason: 'ไฟล์ JSON ไม่ถูกต้อง' };
  }
  if (!isObj(data)) return { ok: false, reason: 'โครงสร้างไฟล์ไม่ถูกต้อง' };
  if (data.version !== 1) return { ok: false, reason: 'เวอร์ชันไฟล์ไม่รองรับ (ต้องเป็น version 1)' };
  if (!PROJECT_TYPES.includes(data.type)) return { ok: false, reason: 'ชนิดโครงการไม่รู้จัก' };

  const defs = defaultSettings();
  const s = isObj(data.settings) ? data.settings : {};
  const settings = {
    ...defs,
    ...s,
    scales: { ...defs.scales, ...(isObj(s.scales) ? s.scales : {}) },
  };
  const arr = (v) => (Array.isArray(v) ? v : []);
  const project = {
    ...data,
    version: 1,
    id: typeof data.id === 'string' && data.id ? data.id : crypto.randomUUID(),
    name: typeof data.name === 'string' ? data.name : '',
    createdAt: typeof data.createdAt === 'string' && data.createdAt ? data.createdAt : new Date().toISOString(),
    settings,
    bms: arr(data.bms),
    stations: arr(data.stations),
    levelBook: arr(data.levelBook),
    rooms: arr(data.rooms),
  };
  saveProject(project);
  return { ok: true, project };
}
