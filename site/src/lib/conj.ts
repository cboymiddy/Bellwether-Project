// TypeScript port of the frozen conjunction search (src/nulls/search_core.py::conj_exists), plus a cover finder.
// A perfect conjunction: facts that are true in every year the target is true, whose "false" masks over the other
// years together cover all of them. Only maximal masks matter for existence, so dominated masks are dropped.
export interface Pool { n: number; vecs: Uint32Array; isA: Uint8Array }
export type Tier = 'conjA' | 'conjB' | 'none';
export interface Analysis { tier: Tier; minK: number; candidatesA: number; candidatesB: number; nFalse: number; cover: number[] | null }
const KMAX = 4;

export function parsePool(buf: ArrayBuffer): Pool {
  const dv = new DataView(buf);
  const n = dv.getUint32(0, true);
  const vecs = new Uint32Array(n);
  for (let i = 0; i < n; i++) vecs[i] = dv.getUint32(4 + 4 * i, true);
  return { n, vecs, isA: new Uint8Array(buf.slice(4 + 4 * n, 4 + 5 * n)) };
}

function supersetSum(a: Int32Array, n: number): void {
  const size = 1 << n;
  for (let b = 0; b < n; b++) { const bit = 1 << b; for (let s = 0; s < size; s++) if ((s & bit) === 0) a[s] += a[s | bit]; }
}
function supersetOr(a: Uint8Array, n: number): void {
  const size = 1 << n;
  for (let b = 0; b < n; b++) { const bit = 1 << b; for (let s = 0; s < size; s++) if ((s & bit) === 0 && a[s | bit]) a[s] = 1; }
}

interface Maximal { mask: number; idx: number }
function maximalMasks(masks: number[], n: number): Maximal[] {
  const size = 1 << n;
  const t = new Int32Array(size), first = new Int32Array(size).fill(-1);
  for (let i = 0; i < masks.length; i++) if (!t[masks[i]]) { t[masks[i]] = 1; first[masks[i]] = i; }
  const cnt = t.slice();
  supersetSum(cnt, n);
  const out: Maximal[] = [];
  for (let m = 0; m < size; m++) if (t[m] && cnt[m] === 1) out.push({ mask: m, idx: first[m] });
  return out;
}

/** Smallest k <= 4 for which some k masks cover all n bits, or 0 if none (matches conj_exists). */
export function minK(masks: number[], n: number): number {
  if (masks.length === 0) return 0;
  const size = 1 << n, full = size - 1;
  const mx = maximalMasks(masks, n);
  const present = new Uint8Array(size);
  for (const m of masks) present[m] = 1;
  if (present[full]) return 1;
  const g1 = present.slice();
  supersetOr(g1, n);
  for (const { mask } of mx) if (g1[full ^ mask]) return 2;
  const t2 = new Uint8Array(size);
  for (let i = 0; i < mx.length; i++) for (let j = i; j < mx.length; j++) t2[mx[i].mask | mx[j].mask] = 1;
  const g2 = t2.slice();
  supersetOr(g2, n);
  for (const { mask } of mx) if (g2[full ^ mask]) return 3;
  for (let p = 0; p < size; p++) if (t2[p] && g2[full ^ p]) return KMAX;
  return 0;
}

/** One cover of size <= k (indices into `masks`), branching on the least-covered bit; null if none. */
export function findCover(masks: number[], n: number, k: number): number[] | null {
  const full = (1 << n) - 1;
  const mx = maximalMasks(masks, n);
  const byBit: number[][] = Array.from({ length: n }, () => []);
  mx.forEach((m, i) => { for (let b = 0; b < n; b++) if ((m.mask >> b) & 1) byBit[b].push(i); });
  const rec = (covered: number, chosen: number[]): number[] | null => {
    if (covered === full) return chosen;
    if (chosen.length === k) return null;
    let bit = -1;
    for (let b = 0; b < n; b++) if (!((covered >> b) & 1) && (bit < 0 || byBit[b].length < byBit[bit].length)) bit = b;
    for (const i of byBit[bit]) {
      if (chosen.includes(i)) continue;
      const r = rec(covered | mx[i].mask, [...chosen, i]);
      if (r) return r;
    }
    return null;
  };
  const found = rec(0, []);
  return found ? found.map((i) => mx[i].idx) : null;
}

export function analyze(pool: Pool, target: number, wantCover = false): Analysis {
  const t = target >>> 0;
  const P: number[] = [], N: number[] = [];
  for (let i = 0; i < 32; i++) (((t >>> i) & 1) ? P : N).push(i);
  const n = N.length;
  if (n === 0 || n > 20) throw new Error(`unsupported number of false years: ${n}`);
  let pmask = 0;
  for (const i of P) pmask = (pmask | (1 << i)) >>> 0;
  const idxA: number[] = [], maskA: number[] = [], idxB: number[] = [], maskB: number[] = [];
  for (let k = 0; k < pool.n; k++) {
    const v = pool.vecs[k];
    if (((v & pmask) >>> 0) !== pmask) continue;
    let m = 0;
    for (let j = 0; j < n; j++) if (((v >>> N[j]) & 1) === 0) m |= 1 << j;
    idxB.push(k); maskB.push(m);
    if (pool.isA[k]) { idxA.push(k); maskA.push(m); }
  }
  const kA = minK(maskA, n);
  const base = { candidatesA: idxA.length, candidatesB: idxB.length, nFalse: n };
  if (kA > 0) {
    const c = wantCover ? findCover(maskA, n, kA) : null;
    return { tier: 'conjA', minK: kA, ...base, cover: c ? c.map((i) => idxA[i]) : null };
  }
  const kB = minK(maskB, n);
  if (kB > 0) {
    const c = wantCover ? findCover(maskB, n, kB) : null;
    return { tier: 'conjB', minK: kB, ...base, cover: c ? c.map((i) => idxB[i]) : null };
  }
  return { tier: 'none', minK: 0, ...base, cover: null };
}

/** Bits of "all of these facts hold" per year; a perfect cover reproduces the target exactly. */
export function ruleBits(pool: Pool, cover: number[]): number {
  let r = 0xffffffff;
  for (const k of cover) r &= pool.vecs[k];
  return r >>> 0;
}
