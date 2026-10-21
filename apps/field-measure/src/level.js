// Level-book (dumpy level) computation. Pure functions, no rounding except r3 (display).

/** Round to 3 decimal places (mm). Display only; computations stay unrounded. */
export function r3(x) {
  return Math.round(x * 1000) / 1000 + 0; // + 0 turns -0 into 0
}

// Reading value -> finite number, or null when not read (null/undefined/''/non-numeric).
function num(v) {
  if (v === null || v === undefined) return null;
  if (typeof v === 'string' && v.trim() === '') return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

/**
 * rows: [{id, point, bs, is, fs, ...}], bms: [{name, rl}]
 * Returns {rows (with hi, rl), sumBS, sumFS, deltaRL, checkable, closure}.
 *  - The first row WITH a BS starts the run: RL = BM rl if `point` names a BM, else 0 (closure then null).
 *    Reading rows before it (IS/FS only) have no HI and no RL and are left out of the sums.
 *  - HI = RL + BS; RL = HI - IS or HI - FS. A row with FS and BS is a change point
 *    (RL from FS, then HI recomputed from its BS).
 *  - A later row naming a BM and having FS closes the run: closure = {expected, got, error}.
 *  - Rows with no bs/is/fs get hi/rl undefined and are left out of the sums.
 *  - sumBS, sumFS and deltaRL cover only the rows up to and including the LAST row with an FS (the BS on that
 *    row starts the next leg, so it is excluded); the identity sumBS - sumFS = deltaRL holds there.
 *    checkable is false when no such FS row exists (the sums are then 0).
 */
export function computeLevelBook(rows, bms) {
  const bmByName = new Map((bms || []).map((b) => [b.name, b.rl]));
  const out = [];
  let started = false;
  let startedAtBM = false;
  let hi = null;
  let sumBS = 0;
  let sumFS = 0;
  let firstRL = null;
  let closure = null;
  let checked = null; // {sumBS, sumFS, rl} snapshot at the last FS row after the run started

  for (const row of rows || []) {
    const bs = num(row.bs);
    const is = num(row.is);
    const fs = num(row.fs);
    const copy = { ...row, hi: undefined, rl: undefined };
    out.push(copy);
    if (bs === null && is === null && fs === null) continue;

    let rl;
    let isStart = false;
    if (!started) {
      if (bs === null) continue; // no HI yet: IS/FS before the first BS has no RL
      started = true;
      isStart = true;
      startedAtBM = bmByName.has(row.point);
      rl = startedAtBM ? bmByName.get(row.point) : 0;
      hi = rl + bs;
    } else {
      const drop = fs !== null ? fs : is;
      if (drop !== null) {
        rl = hi !== null ? hi - drop : undefined;
        if (fs !== null && startedAtBM && rl !== undefined && bmByName.has(row.point)) {
          const expected = bmByName.get(row.point);
          closure = { expected, got: rl, error: rl - expected };
        }
        if (bs !== null && rl !== undefined) hi = rl + bs; // change point
      } else if (bmByName.has(row.point)) {
        // BS-only on a known BM mid-run: re-base on that BM.
        rl = bmByName.get(row.point);
        hi = rl + bs;
      }
      // else: BS-only on an unknown point has no defined RL; HI is left unchanged.
    }

    if (hi !== null) copy.hi = hi;
    if (rl !== undefined) {
      copy.rl = rl;
      if (firstRL === null) firstRL = rl;
    }
    const sumBSBefore = sumBS;
    if (bs !== null) sumBS += bs;
    if (fs !== null) sumFS += fs;
    if (fs !== null && rl !== undefined && !isStart) checked = { sumBS: sumBSBefore, sumFS, rl };
  }

  if (!checked) return { rows: out, sumBS: 0, sumFS: 0, deltaRL: 0, checkable: false, closure };
  return {
    rows: out, sumBS: checked.sumBS, sumFS: checked.sumFS, deltaRL: checked.rl - firstRL, checkable: true, closure,
  };
}

/** RL of the row whose id is readingId, or undefined. */
export function rlOf(book, readingId) {
  const row = book && book.rows ? book.rows.find((r) => r.id === readingId) : undefined;
  return row ? row.rl : undefined;
}
