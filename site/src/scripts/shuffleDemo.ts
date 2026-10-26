import { hashSeed, mulberry32, popcount, randomTarget, wilson } from '../lib/shuffle';

const data = JSON.parse(document.getElementById('demo-data')!.textContent!);
const $ = (id: string) => document.getElementById(id)!;
const MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);
const SUBJECT: Record<string, string> = { T1: 'The party holding the White House on Election Day', T2: 'The Democratic Party', T3: 'The Republican Party' };
const TARGET_PHRASE: Record<string, string> = { T1: 'incumbent party won', T2: 'Democratic Party won', T3: 'Republican Party won' };
const pct = (x: number, d = 1) => `${(x * 100).toFixed(d)}%`;
const fmt = (n: number) => n.toLocaleString('en-US');
const text = (el: Element, s: string) => { el.textContent = s; };
function node<K extends keyof HTMLElementTagNameMap>(tag: K, cls?: string, s?: string): HTMLElementTagNameMap[K] {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (s !== undefined) e.textContent = s;
  return e;
}

interface Meta { n: number; ids: string[]; gloss: Record<string, string>; years: number[] }
let meta: Meta;
let ready = false;
let targetKey = 'T1';
let current: number = data.real.T1.target;
let isReal = true;
let lastSeed = '';

const worker = new Worker(new URL('../lib/shuffle.worker.ts', import.meta.url), { type: 'module' });

function gloss(id: string): string {
  const neg = id.startsWith('NOT_');
  const base = neg ? id.slice(4) : id;
  let m = base.match(/^astro_geo_(\d{2})(\d{2})_sep_([a-z]+)_([a-z]+)_ge(\d{3})$/);
  let t: string | null = null;
  if (m) t = `${cap(m[3])} and ${cap(m[4])} are at least ${Number(m[5])}° apart in ecliptic longitude on ${MON[Number(m[1]) - 1]} ${Number(m[2])} (00:00 UTC)`;
  else if ((m = base.match(/^astro_geo_(\d{2})(\d{2})_([a-z]+)_lon(\d{3})$/)))
    t = `${cap(m[3])}'s ecliptic longitude is in [${Number(m[4])}°, ${Number(m[4]) + 30}°) on ${MON[Number(m[1]) - 1]} ${Number(m[2])}`;
  if (t !== null) return neg ? `NOT: ${t}` : t;
  return meta.gloss[id] ?? id;
}
function sentence(ids: string[]): string {
  const g = ids.map(gloss);
  const pos = g.filter((x) => !x.startsWith('NOT: '));
  const neg = g.filter((x) => x.startsWith('NOT: ')).map((x) => x.slice(5));
  let s = `${SUBJECT[targetKey]} wins`;
  if (pos.length) s += ` if ${pos.join(' and ')}`;
  if (neg.length) s += `, unless ${neg.length > 1 ? `${neg.slice(0, -1).join(', ')}, or ${neg[neg.length - 1]}` : neg[0]}`;
  return `${s}.`;
}

function strip(bitsReal: number, bitsNow: number): SVGSVGElement {
  const CELL = 20, GAP = 5, LEFT = 150, W = LEFT + 32 * (CELL + GAP), H = 78;
  const ns = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(ns, 'svg');
  svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
  svg.setAttribute('role', 'img');
  svg.setAttribute('aria-label', 'Real history and the history shown, one square per election; filled means the target was true');
  const add = (tag: string, attrs: Record<string, string | number>, txt?: string) => {
    const e = document.createElementNS(ns, tag);
    for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, String(v));
    if (txt) e.textContent = txt;
    svg.appendChild(e);
  };
  add('text', { x: 0, y: 38, class: 'rowlabel' }, 'Real history');
  add('text', { x: 0, y: 66, class: 'rowlabel' }, isReal ? 'History shown (real)' : 'History shown (shuffled)');
  for (let i = 0; i < 32; i++) {
    const x = LEFT + i * (CELL + GAP);
    if (i % 4 === 0) add('text', { x: x + CELL / 2, y: 13, 'text-anchor': 'middle', class: 'yr' }, String(data.years[i]));
    add('rect', { x, y: 22, width: CELL, height: CELL, rx: 3, class: (bitsReal >>> i) & 1 ? 'on' : 'off' });
    add('rect', { x, y: 50, width: CELL, height: CELL, rx: 3, class: (bitsNow >>> i) & 1 ? 'on' : 'off' });
  }
  return svg;
}

function renderHistory(): void {
  const host = $('history');
  host.replaceChildren(strip(data.real[targetKey].target, current));
  text($('hist-caption'), `Filled: ${TARGET_PHRASE[targetKey]} that year. ${popcount(current)} filled of 32.`);
}

function status(msg: string): void { text($('status'), msg); }

function renderResult(m: any): void {
  const out = $('result');
  out.replaceChildren();
  const a = m.analysis;
  const head = node('p', a.tier === 'none' ? 'nothing' : 'found');
  if (a.tier === 'none') {
    head.textContent = 'Nothing found at tier 1a or tier 1b for this history.';
    out.append(head, node('p', 'sub',
      'No shuffle is redrawn, retried or skipped: this is the search’s answer for this history. Tier 2 (the fallback) is not run in your browser; ' +
      `in the ${fmt(data.published.totalShuffles)} published shuffles it fired ${fmt(data.published.keysFired)} times.`));
  } else {
    head.textContent = a.tier === 'conjA'
      ? `Tier 1a: a perfect rule of ${a.minK} facts was found using only the original pool.`
      : `Tier 1b: a perfect rule of ${a.minK} facts was found once the sky facts were allowed.`;
    out.append(head);
    const ids = a.cover.map((k: number) => meta.ids[k]);
    const bq = node('blockquote', 'rule', sentence(ids));
    out.append(bq);
    out.append(node('p', 'sub', m.verified ? 'Checked: the rule gets all 32 years of this history right.' : 'WARNING: the returned rule does not fit every year (this is a bug; please report it).'));
    out.append(ruleTable(m.coverVecs, ids));
  }
  const base = node('p', 'sub');
  base.textContent = `${isReal ? 'Real history' : 'Shuffled history'}, target ${targetKey}. Searched ${fmt(meta.n)} facts; ${fmt(a.candidatesB)} were true in every year the target is true (${fmt(a.candidatesA)} from the original pool). ${m.ms.toFixed(0)} ms.`;
  out.append(base);
  if (isReal) {
    const pub = data.realLabels[targetKey];
    const same = pub === a.tier;
    out.append(node('p', 'sub', same ? `This matches the published result for the real history (${pub === 'none' ? 'none' : pub}).` : `MISMATCH with the published real-history result (${pub}).`));
  }
}

function ruleTable(vecs: number[], ids: string[]): HTMLElement {
  const wrap = node('div', 'table-wrap');
  const t = node('table', 'plain');
  const head = node('tr');
  const cols = ['Year', 'History', ...ids.map((id) => gloss(id).replace(/^NOT: /, 'not: ').slice(0, 60)), 'Rule says', 'Match'];
  cols.forEach((c) => head.append(node('th', undefined, c)));
  const thead = node('thead');
  thead.append(head);
  t.append(thead);
  const body = node('tbody');
  for (let i = 0; i < 32; i++) {
    const tr = node('tr');
    const hist = ((current >>> i) & 1) === 1;
    const vals = vecs.map((v) => ((v >>> i) & 1) === 1);
    const says = vals.every(Boolean);
    tr.append(node('th', undefined, String(data.years[i])), node('td', hist ? 'yes' : 'no', hist ? '✓' : '✗'));
    vals.forEach((v) => tr.append(node('td', v ? 'yes' : 'no', v ? '✓' : '✗')));
    tr.append(node('td', says ? 'yes' : 'no', says ? '✓' : '✗'), node('td', says === hist ? 'yes' : 'no', says === hist ? '✓' : '✗'));
    body.append(tr);
  }
  t.append(body);
  wrap.append(t);
  return wrap;
}

function currentSeed(): string { return (($('seed') as HTMLInputElement).value || '').trim() || 'seed'; }
function setBusy(b: boolean): void {
  ['btn-shuffle', 'btn-random', 'btn-reset', 'btn-batch'].forEach((id) => (($(id) as HTMLButtonElement).disabled = b || !ready));
  ($('btn-cancel') as HTMLButtonElement).hidden = !b;
}
function analyzeCurrent(): void { status('Searching…'); worker.postMessage({ type: 'one', target: current }); }

function shuffleOnce(seed: string): void {
  lastSeed = seed;
  const nTrue = data.real[targetKey].n_true;
  current = randomTarget(mulberry32(hashSeed(seed)), nTrue);
  isReal = false;
  history.replaceState(null, '', `?t=${targetKey}&seed=${encodeURIComponent(seed)}`);
  renderHistory();
  analyzeCurrent();
}
function reset(): void {
  current = data.real[targetKey].target;
  isReal = true;
  history.replaceState(null, '', `?t=${targetKey}`);
  renderHistory();
  analyzeCurrent();
}

function renderTally(t: any, final: boolean, cancelled = false, ms = 0, requested = 1000): void {
  const out = $('tally');
  out.replaceChildren();
  const found = t.conjA + t.conjB;
  const n = t.done;
  const pub = data.published[targetKey];
  const [lo, hi] = wilson(found, n);
  const inside = pub.foundRate >= lo && pub.foundRate <= hi;
  const tb = node('table', 'plain');
  const thr = node('tr');
  ['Result', 'Your shuffles', 'Share'].forEach((c) => thr.append(node('th', undefined, c)));
  const tbh = node('thead');
  tbh.append(thr);
  tb.append(tbh);
  const body = node('tbody');
  ([['Tier 1a: perfect rule from the original pool', t.conjA], ['Tier 1b: perfect rule with the sky facts', t.conjB], ['Nothing found', t.none], ['Errors', t.error]] as [string, number][]).forEach(([label, c]) => {
    const r = node('tr');
    r.append(node('td', undefined, label), node('td', 'num', fmt(c)), node('td', 'num', n ? pct(c / n, 1) : '-'));
    body.append(r);
  });
  tb.append(body);
  out.append(tb);
  const p = node('p');
  p.textContent = `${fmt(n)} of ${fmt(requested)} shuffles${final ? ' done' : ' so far'}${cancelled ? ' (cancelled)' : ''}. A perfect rule was found in ${pct(n ? found / n : 0, 1)} of them (95% interval ${pct(lo, 1)} to ${pct(hi, 1)}).`;
  out.append(p);
  const c = node('p', inside || !final ? '' : 'nothing');
  c.textContent = `Published (${fmt(pub.B)} shuffles of target ${targetKey}): ${pct(pub.foundRate, 1)} found a perfect rule. ` +
    (final ? (inside ? 'Your result is consistent with that.' : 'Your result is outside this batch’s own 95% interval for the published rate; about one batch in twenty does that by chance.') : '');
  out.append(c);
  if (final) out.append(node('p', 'sub', `Every shuffle was counted once. Nothing was redrawn or skipped. ${(ms / 1000).toFixed(1)} s.`));
}

worker.onmessage = (ev: MessageEvent) => {
  const m = ev.data;
  if (m.type === 'ready') { ready = true; setBusy(false); status('Ready.'); reset(); }
  else if (m.type === 'one') { setBusy(false); status('Done.'); renderResult(m); }
  else if (m.type === 'progress') { renderTally(m.tally, false, false, 0, 1000); ($('progress') as HTMLProgressElement).value = m.tally.done; }
  else if (m.type === 'batch') { setBusy(false); ($('progress') as HTMLProgressElement).value = m.tally.done; renderTally(m.tally, true, m.cancelled, m.ms, m.requested); status(m.cancelled ? 'Cancelled.' : 'Done.'); }
  else if (m.type === 'error') { setBusy(false); status(`Error: ${m.message}`); }
};

async function start(): Promise<void> {
  setBusy(true);
  status('Loading the pool of facts…');
  meta = await (await fetch(`${data.base}data/pool_meta.json`)).json();
  const q = new URLSearchParams(location.search);
  if (q.get('t') && data.real[q.get('t')!]) { targetKey = q.get('t')!; ($('target') as HTMLSelectElement).value = targetKey; }
  if (q.get('seed')) ($('seed') as HTMLInputElement).value = q.get('seed')!;
  worker.postMessage({ type: 'init', url: `${data.base}data/pool.bin` });
}

$('target').addEventListener('change', (e) => { targetKey = (e.target as HTMLSelectElement).value; $('tally').replaceChildren(); reset(); });
$('btn-shuffle').addEventListener('click', () => { setBusy(true); shuffleOnce(currentSeed()); });
$('btn-random').addEventListener('click', () => { const s = Math.random().toString(36).slice(2, 8); ($('seed') as HTMLInputElement).value = s; setBusy(true); shuffleOnce(s); });
$('btn-reset').addEventListener('click', () => { setBusy(true); reset(); });
$('btn-batch').addEventListener('click', () => {
  setBusy(true);
  const seed = `${currentSeed()}:batch`;
  ($('progress') as HTMLProgressElement).value = 0;
  ($('progress') as HTMLProgressElement).max = 1000;
  status('Running 1,000 shuffles…');
  worker.postMessage({ type: 'batch', seed, count: 1000, nTrue: data.real[targetKey].n_true });
});
$('btn-cancel').addEventListener('click', () => worker.postMessage({ type: 'cancel' }));
void start();
void lastSeed;
