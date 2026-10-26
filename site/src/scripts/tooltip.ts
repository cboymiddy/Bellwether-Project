// One shared tooltip for every chart. Tooltips enhance; every value is also in the data table below each chart.
// Strings come from data attributes and are inserted with textContent only.
interface TipRow { series: number; value: string; label: string }
interface TipData { title: string; rows: TipRow[] }

const tip = document.createElement('div');
tip.className = 'viz-tip';
tip.setAttribute('role', 'tooltip');
tip.hidden = true;
document.body.appendChild(tip);

function show(el: Element, x: number, y: number): void {
  let data: TipData | null = null;
  try { data = JSON.parse(el.getAttribute('data-tip') ?? 'null'); } catch { data = null; }
  if (!data) { tip.hidden = true; return; }
  tip.replaceChildren();
  const title = document.createElement('div');
  title.className = 'tt-title';
  title.textContent = data.title;
  tip.appendChild(title);
  for (const r of data.rows) {
    const row = document.createElement('div');
    row.className = 'tt-row';
    const key = document.createElement('span');
    key.className = `tt-key s${r.series}`;
    const val = document.createElement('strong');
    val.textContent = r.value;
    const lab = document.createElement('span');
    lab.className = 'tt-label';
    lab.textContent = r.label;
    row.append(key, val, lab);
    tip.appendChild(row);
  }
  tip.hidden = false;
  const pad = 12;
  const w = tip.offsetWidth, h = tip.offsetHeight;
  const left = Math.min(Math.max(8, x + pad), window.innerWidth - w - 8);
  const top = y + pad + h > window.innerHeight ? Math.max(8, y - h - pad) : y + pad;
  tip.style.left = `${left}px`;
  tip.style.top = `${top}px`;
}

document.addEventListener('pointermove', (e) => {
  const el = (e.target as Element | null)?.closest?.('[data-tip]');
  if (el) show(el, e.clientX, e.clientY); else tip.hidden = true;
});
document.addEventListener('focusin', (e) => {
  const el = (e.target as Element | null)?.closest?.('[data-tip]');
  if (!el) return;
  const r = el.getBoundingClientRect();
  show(el, r.left + r.width / 2, r.top);
});
document.addEventListener('focusout', () => { tip.hidden = true; });
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') tip.hidden = true; });
