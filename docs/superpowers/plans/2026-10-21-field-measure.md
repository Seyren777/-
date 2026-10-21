# Field Measurement PWA (วัดหน้างาน → DXF) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** An offline-capable iPhone web app where a municipal engineer records road stations (widths, cross-section staff readings, features) or toilet rooms (walls, openings, fixtures) and exports a DXF R2000 that opens in AutoCAD 2027 as a plan + cross-sections (road) or a dimensioned plan (toilet).

**Architecture:** Pure-logic ES modules (`level`, `road`, `toilet`, `dxf`, `export`, `store`) with no DOM, unit-tested under Node's built-in test runner; one `index.html` shell with small view modules renders forms and calls the logic; a service worker caches everything for offline use. DXF output is validated in tests by reading it back with `ezdxf` (Python).

**Tech Stack:** Vanilla JavaScript (ES2020 modules), HTML/CSS, `node:test` (Node 22), Python `ezdxf` for DXF validation, GitHub Pages for hosting.

**Spec:** `docs/superpowers/specs/2026-10-21-field-measure-design.md`

## Global Constraints

- No external libraries or CDN at runtime; everything served from `apps/field-measure/`.
- Target browser: Safari on iPhone; installable via "Add to Home Screen"; works offline after first load.
- Units: horizontal distances in metres (2 decimals), staff readings and RL in metres (3 decimals); DXF model units = metres.
- DXF version R2000 (`$ACADVER = AC1015`); Thai text encoded as `\U+XXXX`; layers exactly: `CL, EDGE-EXIST, SHOULDER, ROW, STA-TEXT, XS-GROUND, XS-GRID, XS-TEXT, FEATURE, WALL, OPENING, FIXTURE, DIM, TEXT, NOTE`.
- Plot-scale defaults: road plan 1:100, cross-section 1:25 (vertical exaggeration default 1:1, options 1,2,5,10), toilet plan 1:50; plotted text height 2.5 mm → model text height = 0.0025 × scale denominator.
- Station format `k+mmm` with up to one decimal when needed (`0+025`, `1+237.5`); default interval 25 m, user-adjustable; extra (odd) stations allowed.
- All station distances are measured from the centerline; left = negative offset, right = positive.
- UI text in Thai; code identifiers, layer names and units in English.
- Data persists in `localStorage` under one key; project JSON has `"version": 1`.

## Review Focus

1. A cross-section whose point list is unsorted or has duplicate offsets must still draw a left-to-right ground line and label every point once (tested in Task 4).
2. A level book that never closes back to a BM (open run) must still compute RL for every row and show "ไม่มีการปิดวงรอบ" rather than a false misclosure (tested in Task 2).
3. A toilet polygon that does not close must be exported anyway (open polyline) with the gap reported in the UI, never silently closed (tested in Task 5).
4. Thai text in project names, notes and labels must survive the DXF round trip exactly, including combining vowels/tone marks (tested in Task 6).
5. Importing a JSON file with a higher `version` or missing fields must refuse with a message rather than overwrite the current store (tested in Task 1).

---

## File Structure

```
apps/field-measure/
  index.html            # shell: nav, view container, loads src/app.js as module
  manifest.json         # PWA manifest (name, icons, display: standalone)
  sw.js                 # cache-first service worker, versioned cache name
  icon.svg              # app icon (inline SVG, also used for apple-touch-icon via PNG data URL in index.html)
  style.css             # mobile-first styles, large touch targets
  src/store.js          # project list CRUD, localStorage persistence, JSON import/export, schema v1 + defaults
  src/level.js          # level-book maths: HI/RL per row, sums, closure
  src/road.js           # station naming/parsing, station generation, cross-section ordering, plan geometry
  src/toilet.js         # wall polygon from turtle-style walls, closure gap, opening/fixture placement
  src/dxf.js            # DXF R2000 writer: header, tables (layers/styles), entities (LINE, LWPOLYLINE, TEXT, CIRCLE, DIMENSION as exploded lines+text)
  src/export.js         # project → list of DXF entities (road plan, sections, toilet plan)
  src/app.js            # router + views: home, road settings, station page, level book, toilet room, export panel
  src/views/*.js        # one file per view (home, roadSettings, station, levelBook, toilet, exportPanel)
tests/field-measure/
  level.test.mjs, road.test.mjs, toilet.test.mjs, dxf.test.mjs, export.test.mjs, store.test.mjs
  check_dxf.py          # ezdxf reader used by dxf/export tests via child_process
```

---

### Task 1: Store (schema, persistence, import/export)

**Files:**
- Create: `apps/field-measure/src/store.js`
- Test: `tests/field-measure/store.test.mjs`

**Interfaces:**
- Produces: `newProject(type: 'road-new'|'road-improve'|'toilet', name: string): Project`; `listProjects(): ProjectSummary[]`; `saveProject(p: Project): void`; `loadProject(id: string): Project|null`; `deleteProject(id)`; `exportJSON(p): string`; `importJSON(text: string): {ok: true, project} | {ok: false, reason: string}`; `storage` injectable via `setStorage(obj)` for tests.
- `Project` shape (v1): `{version:1, id, type, name, createdAt, settings:{stationStart:0, interval:25, length, scales:{plan:100, section:25, toilet:50}, vExag:1, font:'Tahoma'}, bms:[{name, rl}], stations:[{sta:number, widths:{pavL,pavR,shL,shR,rowL,rowR}, surface, condition, section:[{offset, readingId|rl, label}], features:[{kind, offset, note}], note}], levelBook:[{id, point, bs, is, fs, note, staRef}], rooms:[{name, wallThk:0.10, walls:[{len, dir:'U'|'D'|'L'|'R'}], openings:[{wallIdx, from, width, height, sill, kind, swing}], fixtures:[{kind, x, y, cond}], ceiling, floorLevel, floorMat, wallMat}]}`

- [ ] **Step 1: Write failing tests** `store.test.mjs`: `newProject('road-new','ถนนสาย 1')` has `version 1`, `settings.interval 25`, `scales {plan:100, section:25, toilet:50}`; `saveProject` then `listProjects()` returns one summary with same name; `importJSON('{"version":2}')` returns `{ok:false}` and leaves list unchanged; `importJSON` of a v1 project missing `rooms` fills `rooms: []`.
- [ ] **Step 2: Run** `node --test tests/field-measure/store.test.mjs` → FAIL (module not found).
- [ ] **Step 3: Implement `store.js`** with an in-memory fallback when `localStorage` is undefined; key `fieldmeasure.v1`.
- [ ] **Step 4: Run tests** → PASS.
- [ ] **Step 5: Commit** `feat(field-measure): project store with JSON import/export`.

### Task 2: Level book

**Files:**
- Create: `apps/field-measure/src/level.js`
- Test: `tests/field-measure/level.test.mjs`

**Interfaces:**
- Produces: `computeLevelBook(rows: LevelRow[], bms: {name, rl}[]): {rows: (LevelRow & {hi, rl})[], sumBS, sumFS, deltaRL, closure: null | {expected, got, error}}`; `rlOf(book, readingId): number|undefined`.
- Rules: first row must reference a BM by `point` name (RL taken from `bms`); row with `bs` and `fs` is a change point; HI = RL + BS; RL = HI − IS or HI − FS; a row whose `point` matches a BM name and has `fs` triggers closure (`error = got − expected`); if no such row, `closure = null`.

- [ ] **Step 1: Write failing tests**: 3-row run BM 100.000, BS 1.500, IS 1.200 → RL 100.300, FS 2.000 → 99.500, `sumBS−sumFS = −0.500 = deltaRL`; open run → `closure === null`; closed run returning to BM with 0.004 error → `closure.error ≈ 0.004`; `rlOf` returns RL for an IS row id.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement `level.js`** (pure, no rounding until display; round to 3 dp in a helper `r3`).
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat(field-measure): level book computation`.

### Task 3: Road station maths and plan geometry

**Files:**
- Create: `apps/field-measure/src/road.js`
- Test: `tests/field-measure/road.test.mjs`

**Interfaces:**
- Produces: `formatSta(m: number): string` (`25 → '0+025'`, `1237.5 → '1+237.5'`); `parseSta(s: string): number`; `generateStations(start, length, interval): number[]` (includes end station); `insertStation(stations, sta)` (sorted, unique); `planLines(project): {cl:[[x,y]], edgeL, edgeR, shL, shR, rowL, rowR: [[x,y]][]}` where x = station metres, y = +offset right? **No:** y = −offset for left (left is +y in plan when travelling +x? Decide: plan drawn with chainage along +X and **left side at +Y**, so `y = −offset`), skipping stations with missing widths; `orderSection(points): points sorted by offset, duplicates by offset keep last`.

- [ ] **Step 1: Write failing tests** with the values above; `generateStations(0, 110, 25)` → `[0,25,50,75,100,110]`; `planLines` with two stations `pavL 3, pavR 3.5` yields `edgeL = [[0,3],[25,3]]`, `edgeR = [[0,-3.5],[25,-3.5]]`; `orderSection([{offset:2},{offset:-2},{offset:2,rl:5}])` → offsets `[-2,2]` with second entry rl 5.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement `road.js`**.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat(field-measure): station and plan geometry`.

### Task 4: DXF writer

**Files:**
- Create: `apps/field-measure/src/dxf.js`, `tests/field-measure/check_dxf.py`
- Test: `tests/field-measure/dxf.test.mjs`

**Interfaces:**
- Produces: `class Dxf { constructor(opts:{font:'Tahoma'}); line(layer,x1,y1,x2,y2); polyline(layer, pts:[[x,y]], closed=false); circle(layer,x,y,r); text(layer,x,y,h,str,{align:'left'|'center'|'right', rot:0}); dim(layer,x1,y1,x2,y2,offset,h) /* exploded: ext lines, dim line, ticks, centred text of distance 2 dp */; toString(): string }`; `LAYERS` constant array of `[name, colorIndex]` for the 15 layers; `encodeThai(str)` → `\U+XXXX` for non-ASCII.
- `check_dxf.py <file>` prints JSON `{version, layers:[...], counts:{LINE:n, LWPOLYLINE:n, TEXT:n, CIRCLE:n}, texts:[decoded strings]}` using `ezdxf.readfile` + `ezdxf.audit`; exits 1 on audit errors.

- [ ] **Step 1: Write failing tests**: build a Dxf with one line, one closed polyline of 4 pts, one text `'ถนนสาย 1'`; write to temp file; run `python3 tests/field-measure/check_dxf.py tmp.dxf` via `child_process.execFileSync`; assert `version === 'AC1015'`, all 15 layers present, counts `{LINE:1, LWPOLYLINE:1, TEXT:1}`, decoded text equals `'ถนนสาย 1'`; `encodeThai('ก1')` → `'\\U+0E01' + '1'`.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement `dxf.js`** (HEADER with `$ACADVER`, `$INSUNITS 6`; TABLES: LTYPE Continuous, LAYER ×15, STYLE `STD` with font file name from opts; ENTITIES; `0\nEOF`); **and `check_dxf.py`**.
- [ ] **Step 4: Run** → PASS (ezdxf audit clean).
- [ ] **Step 5: Commit** `feat(field-measure): DXF R2000 writer with ezdxf check`.

### Task 5: Toilet geometry

**Files:**
- Create: `apps/field-measure/src/toilet.js`
- Test: `tests/field-measure/toilet.test.mjs`

**Interfaces:**
- Produces: `wallPolygon(walls: {len, dir}[]): {pts:[[x,y]], closed: boolean, gap:{dx,dy,dist}}` starting at `(0,0)`, `R:+x, L:−x, U:+y, D:−y`; `outerPolygon(pts, thk)` (offset outward for a clockwise or counter-clockwise rectilinear polygon; implement by offsetting each edge away from polygon centroid); `openingSegment(pts, wallIdx, from, width): {a:[x,y], b:[x,y]}`; `fixtureShape(kind, x, y): {kind:'rect'|'circle', ...}` with sizes: toilet 0.40×0.70, squat 0.50×0.60, basin 0.45×0.35 (circle r 0.20 for drain), urinal 0.35×0.30, shower circle r 0.10.

- [ ] **Step 1: Write failing tests**: walls `R2, U1.5, L2, D1.5` → closed, 4 pts; `R2, U1.5, L2, D1.4` → `closed false`, `gap.dist 0.1`; `openingSegment` on wall 0 from 0.3 width 0.8 → `a [0.3,0], b [1.1,0]`; `outerPolygon` of the 2×1.5 room with thk 0.1 → bounding box `−0.1..2.1 × −0.1..1.6`.
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement.** **Step 4: Run** → PASS. **Step 5: Commit** `feat(field-measure): toilet room geometry`.

### Task 6: Export (project → DXF)

**Files:**
- Create: `apps/field-measure/src/export.js`
- Test: `tests/field-measure/export.test.mjs`

**Interfaces:**
- Consumes: Tasks 2–5.
- Produces: `exportRoad(project): string` (DXF text), `exportToilet(project): string`, `exportCSV(project): string`, `fileName(project, ext): string` → `<name>_<YYYYMMDD>.<ext>`.
- Layout: plan at origin, chainage along +X; cross-sections start at `y = −(maxLeftWidth + 10)` and tile 3 per row, cell width = (max section width + 4 m), cell height = (max RL range × vExag + 3 m); each section: ground polyline on `XS-GROUND`, vertical CL line, horizontal grid every 1 m RL on `XS-GRID` with RL labels, point labels `offset / RL` on `XS-TEXT`, title `STA 0+025  CL RL 100.300`; text height = `0.0025 × scales.section`; plan text height = `0.0025 × scales.plan`; features drawn as circle r 0.3 + label on `FEATURE`; toilet: inner polyline + outer polyline on `WALL`, openings as gaps (polyline split) + swing arc approximated by 8-segment polyline on `OPENING`, fixtures on `FIXTURE`, `dim()` along every wall and every opening on `DIM`, room name on `TEXT`.

- [ ] **Step 1: Write failing tests**: a 3-station road project with sections (CL + 2 points each, RL from level book) exported, checked with `check_dxf.py`: `LWPOLYLINE ≥ 3 (CL+edges) + 3 (sections)`, texts include `'0+025'` and `'100.300'`; unsorted section still produces polyline with increasing x; project name with Thai `'ปรับปรุงถนนซอยเทศบาล 5'` found in decoded texts; toilet project with unclosed walls exports (no throw) and polyline is open; `fileName` matches `/_\d{8}\.dxf$/`.
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement `export.js`.** **Step 4: Run** → PASS. **Step 5: Commit** `feat(field-measure): DXF export for road and toilet`.

### Task 7: App shell, PWA and views

**Files:**
- Create: `apps/field-measure/index.html`, `style.css`, `manifest.json`, `sw.js`, `icon.svg`, `src/app.js`, `src/views/{home,roadSettings,station,levelBook,toilet,exportPanel}.js`
- Test: manual on iPhone Safari + Node smoke test `tests/field-measure/smoke.test.mjs` that imports every `src/*.js` logic module (no DOM) and asserts exports exist; `sw.js` cache list matches files on disk (test reads `sw.js` and checks each path exists).

**Interfaces:**
- Consumes: all previous modules.
- Views (hash router `#/`, `#/road/:id/settings`, `#/road/:id/sta/:i`, `#/road/:id/level`, `#/road/:id/export`, `#/toilet/:id`): 
  - home: project list, new project (type + name), import JSON (file input), delete with confirm.
  - roadSettings: name, start, length, interval (number input, step 5), BM list, scales, vExag, font; "สร้างสถานี" regenerates stations keeping existing data.
  - station: prev/next buttons (large), fields per spec §4.2, section table with quick-label chips, "เพิ่มจุด", reading entry adds IS row to level book (`staRef`), features checklist, "คัดลอกจากสถานีก่อนหน้า", "แทรกสถานี".
  - levelBook: editable table, computed HI/RL, sums, closure banner (green/red/grey).
  - toilet: rooms list; per room walls (len + dir buttons), live closure status with gap, openings, fixtures (x,y), misc fields.
  - exportPanel: buttons DXF / CSV / JSON backup via Blob download (`a[download]`), reminder text to back up.
- `sw.js`: cache name `fm-v1`, precache all app files, cache-first fetch; `index.html` registers it and shows "พร้อมใช้ออฟไลน์" once installed.

- [ ] **Step 1: Write failing smoke test** (module exports + sw cache list).
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement shell, views, PWA files.** **Step 4: Run** → PASS; open `index.html` via `python3 -m http.server` and drive a 3-station road + 1 toilet room, export DXF, run `check_dxf.py` on it → audit clean.
- [ ] **Step 5: Commit** `feat(field-measure): PWA shell and views`.

### Task 8: Hosting and handover

**Files:**
- Create: `apps/field-measure/README.md` (Thai: how to enable GitHub Pages on repo `Seyren777/-` → Settings → Pages → Deploy from branch → branch + `/` root, then open `https://seyren777.github.io/-/apps/field-measure/`, Add to Home Screen; backup/restore JSON; AutoCAD import notes: `DXFIN`, layers, scales)
- Modify: `sw.js` cache paths to be relative so the Pages sub-path works.

- [ ] **Step 1: Verify** relative paths by serving from a sub-path locally (`python3 -m http.server` at repo root, open `/apps/field-measure/`) → app loads, sw registers.
- [ ] **Step 2: Publish a preview Artifact** of `index.html` (inline modules) for immediate trial on the phone while Pages is being enabled.
- [ ] **Step 3: Commit + push** `docs(field-measure): hosting and usage guide`.
