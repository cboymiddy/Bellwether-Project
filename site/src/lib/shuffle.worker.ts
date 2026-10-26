// Runs the search off the main thread. Every shuffle is analysed exactly once: a shuffle that finds nothing is
// reported as "none"; nothing is redrawn, retried, or skipped. Errors are counted and shown, never swallowed.
import { analyze, parsePool, ruleBits, type Pool } from './conj';
import { hashSeed, mulberry32, randomTarget } from './shuffle';

let pool: Pool | null = null;
let cancelled = false;
const tick = () => new Promise<void>((r) => setTimeout(r, 0));

self.onmessage = async (ev: MessageEvent) => {
  const m = ev.data;
  try {
    if (m.type === 'init') {
      pool = parsePool(await (await fetch(m.url)).arrayBuffer());
      postMessage({ type: 'ready', n: pool.n });
    } else if (m.type === 'cancel') {
      cancelled = true;
    } else if (m.type === 'one') {
      const t0 = performance.now();
      const a = analyze(pool!, m.target, true);
      const verified = a.cover ? ruleBits(pool!, a.cover) === (m.target >>> 0) : null;
      postMessage({ type: 'one', analysis: a, coverVecs: a.cover ? a.cover.map((k) => pool!.vecs[k]) : null, verified, ms: performance.now() - t0, target: m.target });
    } else if (m.type === 'batch') {
      cancelled = false;
      const rng = mulberry32(hashSeed(m.seed));
      const tally = { conjA: 0, conjB: 0, none: 0, error: 0, done: 0 };
      const t0 = performance.now();
      for (let i = 0; i < m.count && !cancelled; i++) {
        try { tally[analyze(pool!, randomTarget(rng, m.nTrue), false).tier]++; } catch { tally.error++; }
        tally.done++;
        if (tally.done % 25 === 0) { postMessage({ type: 'progress', tally: { ...tally } }); await tick(); }
      }
      postMessage({ type: 'batch', tally, cancelled, ms: performance.now() - t0, requested: m.count });
    }
  } catch (err) {
    postMessage({ type: 'error', message: String(err) });
  }
};
