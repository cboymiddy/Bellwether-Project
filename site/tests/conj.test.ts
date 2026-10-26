// Parity tests: the TypeScript search must reproduce the Python (frozen) results on 303 goldens:
// the three real histories plus null shuffles regenerated from the published seeds (none, tier 1a, tier 1b).
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { analyze, parsePool, ruleBits } from '../src/lib/conj';
import { hashSeed, mulberry32, popcount, randomTarget } from '../src/lib/shuffle';

const pool = parsePool(readFileSync('public/data/pool.bin').buffer.slice(0) as ArrayBuffer);
const goldens: any[] = JSON.parse(readFileSync('tests/fixtures/goldens.json', 'utf8'));
const shuffleData = JSON.parse(readFileSync('src/data/shuffle.json', 'utf8'));

describe('pool', () => {
  it('has 15,010 vectors of which 266 are in pool A', () => {
    expect(pool.n).toBe(15010);
    expect(pool.isA.reduce((a, b) => a + b, 0)).toBe(266);
  });
});

describe('goldens cover every case type', () => {
  it('has none, tier 1a and tier 1b for every target plus the three real histories', () => {
    for (const t of ['T1', 'T2', 'T3']) {
      const labs = goldens.filter((g) => g.source === `null_${t}`).map((g) => g.python_label);
      expect(labs.filter((l) => l === 'none').length).toBe(12);
      expect(labs.filter((l) => l === 'conjA').length).toBe(12);
      expect(labs.filter((l) => l === 'conjB').length).toBe(76);
    }
    expect(goldens.filter((g) => g.source === 'real').map((g) => g.python_label)).toEqual(['conjB', 'none', 'conjB']);
  });
});

describe('parity with Python', () => {
  it('matches tier, minimal k and both candidate counts on all goldens', () => {
    const bad: string[] = [];
    for (const g of goldens) {
      const a = analyze(pool, g.target, false);
      if (a.tier !== g.python_label || a.minK !== g.min_k || a.candidatesA !== g.candidates_A || a.candidatesB !== g.candidates_B) {
        bad.push(`${g.id}: ts ${a.tier}/${a.minK}/${a.candidatesB} vs py ${g.python_label}/${g.min_k}/${g.candidates_B}`);
      }
    }
    expect(bad).toEqual([]);
  });

  it('returns real perfect covers of the minimal size for every found case', () => {
    let checked = 0;
    for (const g of goldens.filter((x) => x.python_label !== 'none')) {
      const a = analyze(pool, g.target, true);
      expect(a.cover, g.id).not.toBeNull();
      expect(a.cover!.length, g.id).toBe(g.min_k);
      expect(ruleBits(pool, a.cover!), g.id).toBe(g.target >>> 0); // fits every year exactly
      if (a.tier === 'conjA') for (const k of a.cover!) expect(pool.isA[k], g.id).toBe(1);
      checked++;
    }
    expect(checked).toBe(goldens.filter((x) => x.python_label !== 'none').length);
  });

  it('reproduces the real labels from the published results', () => {
    for (const t of ['T1', 'T2', 'T3']) {
      const a = analyze(pool, shuffleData.real[t].target, false);
      expect(a.tier).toBe(shuffleData.real_labels[t]);
    }
  });

  it('reports none (no cover, no retry) when nothing is found', () => {
    for (const g of goldens.filter((x) => x.python_label === 'none').slice(0, 10)) {
      const a = analyze(pool, g.target, true);
      expect(a.tier).toBe('none');
      expect(a.cover).toBeNull();
    }
  });
});

describe('seeded shuffle', () => {
  it('is deterministic and keeps the number of true years', () => {
    const a = randomTarget(mulberry32(hashSeed('abc')), 18), b = randomTarget(mulberry32(hashSeed('abc')), 18);
    const c = randomTarget(mulberry32(hashSeed('abd')), 18);
    expect(a).toBe(b);
    expect(popcount(a)).toBe(18);
    expect(popcount(c)).toBe(18);
    expect(c).not.toBe(a);
  });
});
