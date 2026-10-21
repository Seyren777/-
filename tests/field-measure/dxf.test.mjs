import { test } from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { mkdtempSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { Dxf, LAYERS, encodeThai } from '../../apps/field-measure/src/dxf.js';

const here = dirname(fileURLToPath(import.meta.url));
const CHECK = join(here, 'check_dxf.py');

function check(dxfText) {
  const dir = mkdtempSync(join(tmpdir(), 'fm-dxf-'));
  const file = join(dir, 'tmp.dxf');
  try {
    writeFileSync(file, dxfText);
    const out = execFileSync('python3', [CHECK, file], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });
    return JSON.parse(out);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
}

const NAMES = ['CL', 'EDGE-EXIST', 'SHOULDER', 'ROW', 'STA-TEXT', 'XS-GROUND', 'XS-GRID', 'XS-TEXT',
  'FEATURE', 'WALL', 'OPENING', 'FIXTURE', 'DIM', 'TEXT', 'NOTE'];

test('LAYERS: the 15 layers with distinct colours', () => {
  assert.deepEqual(LAYERS.map(([n]) => n), NAMES);
  const colours = LAYERS.map(([, c]) => c);
  assert.equal(new Set(colours).size, 15);
  for (const c of colours) assert.ok(Number.isInteger(c) && c >= 1 && c <= 255);
});

test('encodeThai escapes non-ASCII as \\U+XXXX', () => {
  assert.equal(encodeThai('ก1'), '\\U+0E01' + '1');
  assert.equal(encodeThai('abc 1.5'), 'abc 1.5');
  assert.equal(encodeThai('°'), '\\U+00B0');
});

test('line, closed polyline, Thai text: ezdxf reads it and audit is clean', () => {
  const d = new Dxf();
  d.line('CL', 0, 0, 100, 0)
    .polyline('WALL', [[0, 0], [4, 0], [4, 3], [0, 3]], true)
    .text('TEXT', 1, 1, 0.25, 'ถนนสาย 1');
  const r = check(d.toString());
  assert.equal(r.version, 'AC1015');
  for (const n of NAMES) assert.ok(r.layers.includes(n), `layer ${n} missing`);
  assert.deepEqual(r.counts, { LINE: 1, LWPOLYLINE: 1, TEXT: 1, CIRCLE: 0 });
  assert.deepEqual(r.texts, ['ถนนสาย 1']);
});

test('header, style font, polyline flag, alignment groups', () => {
  const s = new Dxf().polyline('WALL', [[0, 0], [1, 0], [1, 1]], true)
    .text('TEXT', 5, 6, 0.2, 'X', { align: 'center' }).toString();
  assert.match(s, /\$ACADVER\r?\n\s*1\r?\nAC1015\r?\n/);
  assert.match(s, /\$INSUNITS\r?\n\s*70\r?\n\s*6\r?\n/);
  assert.match(s, /\$HANDSEED\r?\n\s*5\r?\n[0-9A-F]+\r?\n/);
  assert.match(s, /STYLE\r?\n[\s\S]*?\n\s*2\r?\nSTD\r?\n[\s\S]*?\n\s*3\r?\ntahoma\.ttf\r?\n/);
  assert.match(s, /AcDbPolyline\r?\n\s*90\r?\n\s*3\r?\n\s*70\r?\n\s*1\r?\n/);
  assert.match(s, /\n\s*72\r?\n\s*1\r?\n/);
  assert.match(s, /\n\s*11\r?\n5\r?\n\s*21\r?\n6\r?\n/);
  assert.ok(s.trimEnd().endsWith('EOF'));
  assert.match(new Dxf({ font: 'Angsana' }).toString(), /\n\s*3\r?\nangsa\.ttf\r?\n/);
});

test('numbers have at most 6 decimals and no exponent', () => {
  const s = new Dxf().line('CL', 1e-9, 1 / 3, 1e21 / 1e15, -2.5e-7).toString();
  assert.ok(!/\d[eE][+-]?\d/.test(s), 'exponent notation found');
  assert.match(s, /\n0\.333333\r?\n/);
  assert.match(s, /\n1000000\r?\n/);
});

test('unknown layer throws', () => {
  const d = new Dxf();
  assert.throws(() => d.line('NOPE', 0, 0, 1, 1), /layer/i);
  assert.throws(() => d.text('0', 0, 0, 1, 'x'), /layer/i);
  assert.throws(() => d.circle('cl', 0, 0, 1), /layer/i);
});

test('dim draws exploded linear dimension with readable 2 dp text', () => {
  const d = new Dxf().dim('DIM', 0, 0, 3, 4, 1, 0.2).circle('FIXTURE', 2, 2, 0.3);
  const r = check(d.toString());
  // 2 extension lines + dimension line + 2 ticks
  assert.deepEqual(r.counts, { LINE: 5, LWPOLYLINE: 0, TEXT: 1, CIRCLE: 1 });
  assert.deepEqual(r.texts, ['5.00']);

  // right-to-left segment: angle 180 -> text rotation 0
  const s = new Dxf().dim('DIM', 10, 0, 0, 0, 1, 0.2).toString();
  const txt = s.slice(s.search(/\n\s*0\r?\nTEXT\r?\n/));
  assert.match(txt, /\n\s*1\r?\n10\.00\r?\n/);
  assert.match(txt, /\n\s*50\r?\n0\r?\n/);
});
