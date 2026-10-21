import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const APP = join(here, '../../apps/field-measure');

const MODULES = {
  'store.js': ['STORAGE_KEY', 'PROJECT_TYPES', 'setStorage', 'newProject', 'listProjects', 'saveProject',
    'loadProject', 'deleteProject', 'exportJSON', 'importJSON'],
  'level.js': ['r3', 'computeLevelBook', 'rlOf'],
  'road.js': ['formatSta', 'parseSta', 'generateStations', 'insertStation', 'planLines', 'orderSection'],
  'toilet.js': ['wallPolygon', 'outerPolygon', 'openingSegment', 'fixtureShape'],
  'dxf.js': ['LAYERS', 'encodeThai', 'Dxf'],
  'export.js': ['exportRoad', 'exportToilet', 'exportCSV', 'fileName'],
};

for (const [file, names] of Object.entries(MODULES)) {
  test(`logic module ${file} exposes its named exports`, async () => {
    const mod = await import(join(APP, 'src', file));
    for (const n of names) assert.ok(mod[n] !== undefined, `${file} is missing export ${n}`);
  });
}

function precacheList() {
  const sw = readFileSync(join(APP, 'sw.js'), 'utf8');
  const m = /const\s+PRECACHE\s*=\s*\[([\s\S]*?)\]/.exec(sw);
  assert.ok(m, 'sw.js must declare const PRECACHE = [...]');
  return [...m[1].matchAll(/['"]([^'"]+)['"]/g)].map((x) => x[1]);
}

test('sw.js uses cache name fm-v1', () => {
  const sw = readFileSync(join(APP, 'sw.js'), 'utf8');
  assert.match(sw, /['"]fm-v1['"]/);
});

test('every precached path is relative and exists on disk', () => {
  const list = precacheList();
  assert.ok(list.length > 0);
  for (const p of list) {
    assert.ok(!p.startsWith('/') && !/^[a-z]+:/i.test(p), `precache path must be relative: ${p}`);
    if (p === './') continue; // the directory itself (served as index.html)
    assert.ok(existsSync(join(APP, p)), `precached file missing on disk: ${p}`);
  }
});

test('precache covers index.html, the logic modules and every view', () => {
  const list = precacheList().map((p) => p.replace(/^\.\//, ''));
  const must = ['index.html', 'style.css', 'manifest.json', 'icon.svg', 'src/app.js',
    ...Object.keys(MODULES).map((f) => `src/${f}`),
    ...['home', 'roadSettings', 'station', 'levelBook', 'toilet', 'exportPanel'].map((v) => `src/views/${v}.js`)];
  for (const f of must) assert.ok(list.includes(f), `precache is missing ${f}`);
});

test('index.html references only relative URLs for script/link/manifest', () => {
  const html = readFileSync(join(APP, 'index.html'), 'utf8');
  const refs = [...html.matchAll(/<(?:script|link)\b[^>]*\b(?:src|href)\s*=\s*["']([^"']+)["']/gi)].map((m) => m[1]);
  assert.ok(refs.some((r) => /app\.js$/.test(r)), 'index.html must load src/app.js');
  assert.ok(refs.some((r) => /manifest\.json$/.test(r)), 'index.html must link manifest.json');
  for (const r of refs) {
    if (r.startsWith('data:')) continue;
    assert.ok(!r.startsWith('/') && !/^[a-z]+:\/\//i.test(r), `non-relative URL in index.html: ${r}`);
  }
  assert.match(html, /<html[^>]*\blang="th"/);
  assert.match(html, /viewport-fit=cover/);
  assert.match(html, /sw\.js/);
});

test('manifest.json is valid with relative start_url', () => {
  const m = JSON.parse(readFileSync(join(APP, 'manifest.json'), 'utf8'));
  assert.equal(m.name, 'วัดหน้างาน');
  assert.equal(m.display, 'standalone');
  assert.equal(m.start_url, './');
  for (const icon of m.icons) {
    assert.ok(!icon.src.startsWith('/'));
    assert.ok(existsSync(join(APP, icon.src)), `icon missing: ${icon.src}`);
  }
});
