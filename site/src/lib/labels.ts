const MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);
const title = (slug: string) => slug.split('_').map(cap).join(' ');

/** Short column/row label for a literal id (display only; the pool is untouched). */
export function shortLabel(id: string, gloss: string): string {
  const neg = id.startsWith('NOT_');
  const base = neg ? id.slice(4) : id;
  let m = base.match(/^astro_geo_(\d{2})(\d{2})_sep_([a-z]+)_([a-z]+)_ge(\d{3})$/);
  if (m) {
    const t = `${cap(m[3])}–${cap(m[4])} ≥${Number(m[5])}° (${MON[Number(m[1]) - 1]} ${Number(m[2])})`;
    return neg ? `not ${t}` : t;
  }
  m = base.match(/^sports_nfl_sb_winner_franchise_(.+)$/);
  if (m) return `${neg ? 'not: ' : ''}${title(m[1])} won the Super Bowl`;
  return gloss;
}

export const fmtPct = (x: number, digits = 1) => `${(x * 100).toFixed(digits)}%`;
export const fmtDeg = (x: number, digits = 2) => `${x.toFixed(digits)}°`;
export const fmtHours = (h: number) => (h >= 100 ? `${Math.round(h)} h` : `${h.toFixed(1)} h`);
