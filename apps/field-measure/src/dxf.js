// Minimal DXF R2000 (AC1015) writer. Model units: metres. No dependencies.
// Non-ASCII text is written as \U+XXXX so AutoCAD and ezdxf decode it
// regardless of the file code page.

export const LAYERS = [
  ['CL', 1],
  ['EDGE-EXIST', 8],
  ['SHOULDER', 3],
  ['ROW', 6],
  ['STA-TEXT', 2],
  ['XS-GROUND', 30],
  ['XS-GRID', 9],
  ['XS-TEXT', 4],
  ['FEATURE', 5],
  ['WALL', 7],
  ['OPENING', 140],
  ['FIXTURE', 200],
  ['DIM', 11],
  ['TEXT', 50],
  ['NOTE', 40],
];

const LAYER_NAMES = new Set(LAYERS.map(([n]) => n));

const FONTS = { Tahoma: 'tahoma.ttf', Angsana: 'angsa.ttf' };

function fontFile(font) {
  if (FONTS[font]) return FONTS[font];
  if (typeof font === 'string' && /\.(ttf|ttc|otf|shx)$/i.test(font)) return font;
  throw new Error(`Unknown font: ${font}`);
}

/** Escape every non-ASCII UTF-16 code unit as \U+XXXX; control chars become spaces. */
export function encodeThai(str) {
  let out = '';
  const s = String(str);
  for (let i = 0; i < s.length; i++) {
    const c = s.charCodeAt(i);
    if (c > 0x7e) out += '\\U+' + c.toString(16).toUpperCase().padStart(4, '0');
    else if (c < 0x20) out += ' ';
    else out += s[i];
  }
  return out;
}

/** Up to 6 decimals, trailing zeros stripped, never exponent notation. */
function num(n) {
  const v = Number(n);
  if (!Number.isFinite(v)) throw new Error(`Non-finite number in DXF: ${n}`);
  let s = v.toFixed(6);
  if (s.includes('.')) s = s.replace(/0+$/, '').replace(/\.$/, '');
  return s === '-0' ? '0' : s;
}

const hex = (h) => h.toString(16).toUpperCase();

function checkLayer(layer) {
  if (!LAYER_NAMES.has(layer)) throw new Error(`Unknown layer: ${layer}`);
}

const ALIGN = { left: 0, center: 1, right: 2 };

export class Dxf {
  constructor(opts = { font: 'Tahoma' }) {
    this.fontFile = fontFile(opts.font ?? 'Tahoma');
    this.entities = []; // { type, layer, tags: [[code, value], ...] }
  }

  _add(type, layer, tags) {
    checkLayer(layer);
    this.entities.push({ type, layer, tags });
    return this;
  }

  line(layer, x1, y1, x2, y2) {
    return this._add('LINE', layer, [
      [100, 'AcDbLine'],
      [10, num(x1)], [20, num(y1)], [30, '0'],
      [11, num(x2)], [21, num(y2)], [31, '0'],
    ]);
  }

  polyline(layer, pts, closed = false) {
    checkLayer(layer);
    if (!Array.isArray(pts) || pts.length < 2) throw new Error('polyline needs at least 2 points');
    const tags = [[100, 'AcDbPolyline'], [90, String(pts.length)], [70, closed ? '1' : '0']];
    for (const [x, y] of pts) tags.push([10, num(x)], [20, num(y)]);
    return this._add('LWPOLYLINE', layer, tags);
  }

  circle(layer, x, y, r) {
    return this._add('CIRCLE', layer, [
      [100, 'AcDbCircle'],
      [10, num(x)], [20, num(y)], [30, '0'],
      [40, num(r)],
    ]);
  }

  text(layer, x, y, h, str, { align = 'left', rot = 0 } = {}) {
    checkLayer(layer);
    if (!(align in ALIGN)) throw new Error(`Unknown text align: ${align}`);
    const a = ALIGN[align];
    const tags = [
      [100, 'AcDbText'],
      [10, num(x)], [20, num(y)], [30, '0'],
      [40, num(h)],
      [1, encodeThai(str)],
      [50, num(rot)],
      [7, 'STD'],
    ];
    if (a !== 0) tags.push([72, String(a)], [11, num(x)], [21, num(y)], [31, '0']);
    tags.push([100, 'AcDbText']);
    return this._add('TEXT', layer, tags);
  }

  /** Exploded linear dimension; offset > 0 places it left of x1->x2. */
  dim(layer, x1, y1, x2, y2, offset, h) {
    checkLayer(layer);
    const dx = x2 - x1;
    const dy = y2 - y1;
    const len = Math.hypot(dx, dy);
    if (!(len > 0)) throw new Error('dim needs two distinct points');
    const ux = dx / len, uy = dy / len; // along
    const nx = -uy, ny = ux;            // left normal
    const s = offset < 0 ? -1 : 1;
    const over = h * 0.5;               // extension-line overshoot / tick half-length
    const a1 = [x1 + nx * offset, y1 + ny * offset];
    const a2 = [x2 + nx * offset, y2 + ny * offset];
    // extension lines
    this.line(layer, x1, y1, a1[0] + nx * s * over, a1[1] + ny * s * over);
    this.line(layer, x2, y2, a2[0] + nx * s * over, a2[1] + ny * s * over);
    // dimension line
    this.line(layer, a1[0], a1[1], a2[0], a2[1]);
    // 45 degree ticks
    const tx = (ux + nx) * Math.SQRT1_2 * over, ty = (uy + ny) * Math.SQRT1_2 * over;
    for (const [px, py] of [a1, a2]) this.line(layer, px - tx, py - ty, px + tx, py + ty);
    // text: readable rotation, baseline just above the dimension line
    let ang = (Math.atan2(dy, dx) * 180) / Math.PI;
    if (ang < 0) ang += 360;
    if (ang > 90 && ang <= 270) ang -= 180;
    const r = (ang * Math.PI) / 180;
    const upx = -Math.sin(r), upy = Math.cos(r);
    const gap = h * 0.3;
    const mx = (a1[0] + a2[0]) / 2 + upx * gap;
    const my = (a1[1] + a2[1]) / 2 + upy * gap;
    return this.text(layer, mx, my, h, len.toFixed(2), { align: 'center', rot: ang });
  }

  toString() {
    let next = 1;
    const H = () => hex(next++);
    const out = [];
    const tag = (code, value) => out.push(String(code).padStart(3, ' '), String(value));

    // Pre-assign handles that are referenced across sections.
    const h = {
      vportT: H(), ltypeT: H(), layerT: H(), styleT: H(), viewT: H(), ucsT: H(),
      appidT: H(), dimT: H(), brT: H(),
      msBR: H(), psBR: H(), standardStyle: H(), stdStyle: H(),
      rootDict: H(), groupDict: H(),
    };

    const body = [];
    const emitBody = (fn) => {
      const saved = out.length;
      fn();
      body.push(...out.splice(saved));
    };

    emitBody(() => {
      // CLASSES (empty)
      tag(0, 'SECTION'); tag(2, 'CLASSES'); tag(0, 'ENDSEC');

      // TABLES
      tag(0, 'SECTION'); tag(2, 'TABLES');
      const table = (name, handle, count, sub) => {
        tag(0, 'TABLE'); tag(2, name); tag(5, handle); tag(330, '0');
        tag(100, 'AcDbSymbolTable'); tag(70, count);
        if (sub) tag(100, sub);
      };
      const record = (type, owner, sub, handle = H(), handleCode = 5) => {
        tag(0, type); tag(handleCode, handle); tag(330, owner);
        tag(100, 'AcDbSymbolTableRecord'); tag(100, sub);
      };

      table('VPORT', h.vportT, 1);
      record('VPORT', h.vportT, 'AcDbViewportTableRecord');
      tag(2, '*Active'); tag(70, 0);
      tag(10, 0); tag(20, 0); tag(11, 1); tag(21, 1);
      tag(12, 0); tag(22, 0); tag(13, 0); tag(23, 0);
      tag(14, 1); tag(24, 1); tag(15, 1); tag(25, 1);
      tag(16, 0); tag(26, 0); tag(36, 1); tag(17, 0); tag(27, 0); tag(37, 0);
      tag(40, 100); tag(41, 1.5); tag(42, 50); tag(43, 0); tag(44, 0);
      tag(50, 0); tag(51, 0);
      tag(71, 0); tag(72, 100); tag(73, 1); tag(74, 3); tag(75, 0); tag(76, 0);
      tag(77, 0); tag(78, 0);
      tag(0, 'ENDTAB');

      table('LTYPE', h.ltypeT, 3);
      for (const [name, desc] of [['ByBlock', ''], ['ByLayer', ''], ['Continuous', 'Solid line']]) {
        record('LTYPE', h.ltypeT, 'AcDbLinetypeTableRecord');
        tag(2, name); tag(70, 0); tag(3, desc); tag(72, 65); tag(73, 0); tag(40, 0);
      }
      tag(0, 'ENDTAB');

      table('LAYER', h.layerT, LAYERS.length + 1);
      for (const [name, color] of [['0', 7], ...LAYERS]) {
        record('LAYER', h.layerT, 'AcDbLayerTableRecord');
        tag(2, name); tag(70, 0); tag(62, color); tag(6, 'Continuous'); tag(370, -3);
      }
      tag(0, 'ENDTAB');

      table('STYLE', h.styleT, 2);
      for (const [name, handle, font] of [
        ['Standard', h.standardStyle, 'txt'],
        ['STD', h.stdStyle, this.fontFile],
      ]) {
        record('STYLE', h.styleT, 'AcDbTextStyleTableRecord', handle);
        tag(2, name); tag(70, 0); tag(40, 0); tag(41, 1); tag(50, 0); tag(71, 0);
        tag(42, 0.2); tag(3, font); tag(4, '');
      }
      tag(0, 'ENDTAB');

      table('VIEW', h.viewT, 0); tag(0, 'ENDTAB');
      table('UCS', h.ucsT, 0); tag(0, 'ENDTAB');

      table('APPID', h.appidT, 1);
      record('APPID', h.appidT, 'AcDbRegAppTableRecord');
      tag(2, 'ACAD'); tag(70, 0);
      tag(0, 'ENDTAB');

      table('DIMSTYLE', h.dimT, 1, 'AcDbDimStyleTable');
      record('DIMSTYLE', h.dimT, 'AcDbDimStyleTableRecord', H(), 105);
      tag(2, 'Standard'); tag(70, 0); tag(340, h.standardStyle);
      tag(0, 'ENDTAB');

      table('BLOCK_RECORD', h.brT, 2);
      record('BLOCK_RECORD', h.brT, 'AcDbBlockTableRecord', h.msBR);
      tag(2, '*Model_Space');
      record('BLOCK_RECORD', h.brT, 'AcDbBlockTableRecord', h.psBR);
      tag(2, '*Paper_Space');
      tag(0, 'ENDTAB');

      tag(0, 'ENDSEC');

      // BLOCKS
      tag(0, 'SECTION'); tag(2, 'BLOCKS');
      for (const [name, br, paper] of [['*Model_Space', h.msBR, false], ['*Paper_Space', h.psBR, true]]) {
        tag(0, 'BLOCK'); tag(5, H()); tag(330, br); tag(100, 'AcDbEntity');
        if (paper) tag(67, 1);
        tag(8, '0'); tag(100, 'AcDbBlockBegin'); tag(2, name); tag(70, 0);
        tag(10, 0); tag(20, 0); tag(30, 0); tag(3, name); tag(1, '');
        tag(0, 'ENDBLK'); tag(5, H()); tag(330, br); tag(100, 'AcDbEntity');
        if (paper) tag(67, 1);
        tag(8, '0'); tag(100, 'AcDbBlockEnd');
      }
      tag(0, 'ENDSEC');

      // ENTITIES
      tag(0, 'SECTION'); tag(2, 'ENTITIES');
      for (const e of this.entities) {
        tag(0, e.type); tag(5, H()); tag(330, h.msBR);
        tag(100, 'AcDbEntity'); tag(8, e.layer);
        for (const [c, v] of e.tags) tag(c, v);
      }
      tag(0, 'ENDSEC');

      // OBJECTS
      tag(0, 'SECTION'); tag(2, 'OBJECTS');
      tag(0, 'DICTIONARY'); tag(5, h.rootDict); tag(330, '0'); tag(100, 'AcDbDictionary');
      tag(281, 1); tag(3, 'ACAD_GROUP'); tag(350, h.groupDict);
      tag(0, 'DICTIONARY'); tag(5, h.groupDict); tag(330, h.rootDict); tag(100, 'AcDbDictionary');
      tag(281, 1);
      tag(0, 'ENDSEC');
      tag(0, 'EOF');
    });

    // HEADER last so $HANDSEED is the next free handle.
    tag(0, 'SECTION'); tag(2, 'HEADER');
    tag(9, '$ACADVER'); tag(1, 'AC1015');
    tag(9, '$DWGCODEPAGE'); tag(3, 'ANSI_1252');
    tag(9, '$HANDSEED'); tag(5, H());
    tag(9, '$INSUNITS'); tag(70, 6);
    tag(9, '$MEASUREMENT'); tag(70, 1);
    tag(9, '$CLAYER'); tag(8, '0');
    tag(9, '$TEXTSTYLE'); tag(7, 'STD');
    tag(0, 'ENDSEC');

    return [...out, ...body].join('\n') + '\n';
  }
}
