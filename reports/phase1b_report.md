# Phase 1b report (noise only; no real outcomes were scored)

- config.yaml sha256: `17350119fff5ee544f343d12b5b9dff20573f6f9ea0a111527c6c32e0b8e0ceb`
- pool files sha256 (frozen main pool, unchanged since the Phase 1 N1 run): `659669db4430315ff375b4035eb6984553fc177dfec2f93d829ba174da8a021a`
- Item 5 (Chicago threaded-record check; NHL 1900-1912 dependence check) was already delivered:
  see the Phase 1 pool report, sections "NHL 1900-1912 judgment check" and "Chicago threaded record check".

## 1. Power curve: P(perfect conjunction, k<=4 | noise) vs synthetic pool size M

20,000 permutations per target; same permutations at every M (common random numbers); synthetic series iid Uniform(0,1), grid c = 0.1..0.9, literals `>= c` and `<= c` (18 literals, 9 distinct vectors up to complement, per series); pools nested.

| M series | added literals | added classes | P(T1) | P(T2) | P(T3) |
|---|---|---|---|---|---|
| 0 | 0 | 0 | 0.000 | 0.000 | 0.000 |
| 50 | 900 | 450 | 0.022 | 0.024 | 0.021 |
| 100 | 1800 | 900 | 0.099 | 0.120 | 0.097 |
| 150 | 2700 | 1350 | 0.230 | 0.279 | 0.225 |
| 200 | 3600 | 1800 | 0.401 | 0.473 | 0.397 |
| 250 | 4500 | 2250 | 0.557 | 0.644 | 0.555 |
| 300 | 5400 | 2700 | 0.684 | 0.775 | 0.687 |
| 400 | 7200 | 3600 | 0.871 | 0.926 | 0.875 |
| 500 | 9000 | 4500 | 0.955 | 0.983 | 0.959 |
| 700 | 12600 | 6300 | 0.997 | 0.999 | 0.997 |
| 1000 | 18000 | 9000 | 1.000 | 1.000 | 1.000 |
| 3000 | 54000 | 27000 | 1.000 | 1.000 | 1.000 |

Linear interpolation between grid points (M where P reaches the level):

| target | M for ~50% | M for ~90% |
|---|---|---|
| T1 | 232 | 434 |
| T2 | 208 | 383 |
| T3 | 233 | 429 |

95% Wilson half-width at P=0.5 with 20,000 perms is about 0.007, so the interpolated M values are good to a few series.

Reading: the current pool alone (M=0) gives about 0.0002; the curve is steep and S-shaped, passing
50% near M of about 210-235 and 90% near M of about 385-435. T2 (15 true years) is somewhat easier
than T1 (18) and T3 (17); I did not investigate why.

## 2. Keys null (current frozen pool, no cap)

Pool: frozen main pool (288 distinct vectors). Minimal N of a perfect unit-weight keys rule (CP-SAT, N uncapped up to 40), per noise permutation:

| target | perms | N=4 | N=5 | N=6 | N=7 | N=8 | N=9 |
|---|---|---|---|---|---|---|---|
| T1 | 2000 | 0.2% | 3.1% | 22.1% | 47.1% | 24.8% | 2.7% |
| T2 | 2000 | 0.2% | 2.8% | 21.0% | 47.7% | 25.2% | 3.1% |
| T3 | 2000 | 0.2% | 3.4% | 20.1% | 49.7% | 23.8% | 2.8% |

(No permutation needed N<4 or N>9.)

Per cap N (statements allowed): P(perfect rule exists), the maximum margin achieved across permutations, and P(a rule with margin >= 2 exists). Margin = min(#true on wins) - max(#true on losses); a perfect rule has margin >= 1.

| N cap | T1 P | T1 max margin | T1 P(m>=2) | T2 P | T2 max margin | T2 P(m>=2) | T3 P | T3 max margin | T3 P(m>=2) |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.000 | - | 0.0000 | 0.000 | - | 0.0000 | 0.000 | - | 0.0000 |
| 2 | 0.000 | - | 0.0000 | 0.000 | - | 0.0000 | 0.000 | - | 0.0000 |
| 3 | 0.000 | - | 0.0000 | 0.000 | - | 0.0000 | 0.000 | - | 0.0000 |
| 4 | 0.002 | 1 | 0.0000 | 0.003 | 1 | 0.0000 | 0.003 | 1 | 0.0000 |
| 5 | 0.033 | 1 | 0.0000 | 0.030 | 1 | 0.0000 | 0.036 | 1 | 0.0000 |
| 6 | 0.254 | 1 | 0.0000 | 0.240 | 1 | 0.0000 | 0.237 | 1 | 0.0000 |
| 7 | 0.725 | 2 | 0.0005 | 0.717 | 1 | 0.0000 | 0.734 | 1 | 0.0000 |
| 8 | 0.973 | 2 | 0.0005 | 0.969 | 2 | 0.0005 | 0.972 | 2 | 0.0010 |
| 9 | 1.000 | 2 | 0.0055 | 1.000 | 2 | 0.0040 | 1.000 | 2 | 0.0060 |
| 10 | 1.000 | 2 | 0.0280 | 1.000 | 2 | 0.0235 | 1.000 | 2 | 0.0300 |
| 11 | 1.000 | 2 | 0.1145 | 1.000 | 2 | 0.1015 | 1.000 | 2 | 0.1005 |
| 12 | 1.000 | 3 | 0.3205 | 1.000 | 3 | 0.2985 | 1.000 | 3 | 0.3060 |
| 13 | 1.000 | 3 | 0.5880 | 1.000 | 3 | 0.5780 | 1.000 | 3 | 0.5950 |
| free(40) | 1.000 | 7 | 1.0000 | 1.000 | 7 | 1.0000 | 1.000 | 7 | 1.0000 |

Reading: with no tight cap the keys fallback always succeeds: median minimal N is 7, the maximum over
permutations is 9, and P(feasible) is 0.2% at N<=4, 3% at N<=5, 24% at N<=6, 72% at N<=7, 97% at N<=8.
Margins above 1 are rare below N=10: the best noise margin at N<=9 is 2, and 3 first appears at N=12.
A cap that keeps the null probability near 5% is N<=5 (margin 1); N<=4 gives about 0.2%.
`P(m>=2)` is the fraction of permutations in which a margin-2 rule fits within the cap.

## 3. Proposed astronomy family (NOT built; scratch feasibility run in src/verify/astro_proposal.py)

**Construction (all Skyfield + JPL DE421, apparent geocentric ecliptic coordinates of date):**
- Bodies: Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn, Uranus, Neptune, Pluto (barycenters for planets).
- Fixed pre-election instants: 00:00 UTC on a frozen date grid inside Jan 1 - Oct 31 of each election year.
- Series per date: ecliptic longitude of each body (10) and pairwise angular separation (45).
- Literals: longitude in each of 12 thirty-degree sectors (`lon in [30k, 30k+30)`); separation `>= c` on a frozen grid.
- Both polarities are in the pool as usual. Distinct-vector counts below include negations.

**Size options (counts are measured; N1 power is noise-only, B=2,000-3,000 perms on the main pool plus the family):**

| variant | positives | distinct vectors (with negations) | N1 power T1 / T2 / T3 |
|---|---|---|---|
| 7 bodies, 60 dates (every 5 days), sep step 30 deg | 11,340 | 6,232 | 0.54 / 0.56 / 0.54 |
| 7 bodies, 100 dates, sep step 30 | 18,900 | 7,742 | 0.67 / - / - |
| 10 bodies, 60 dates, sep step 30 | 20,700 | 10,938 | 0.84 / - / - |
| **10 bodies, 80 dates (1,4,8,12,16,20,24,28 of Jan-Oct), sep step 30 (30..150)** | **27,600** | **12,196** | **0.89 / 0.94 / 0.91** |
| 10 bodies, 60 dates, sep step 20 | 28,800 | 15,308 | 0.99 / 0.97 / 0.98 |
| 10 bodies, 40 dates, sep step 15 | 24,600 | 15,776 | 0.986 / 0.976 / 0.985 |

Recommended size for ~90%: the bold row (about 12,000 distinct vectors from 27,600 positives). The power of the
astronomy family is far above a naive synthetic-M equivalent only because it is a pool of many vectors;
the distinct-vector count is what counts, and adjacent dates for slow planets give many duplicates
(27,600 positives collapse to about 6,100 complement classes).

- **Grades:** F=1 for planetary geometry (CLAUDE.md Section 4); Sun-Moon separation could be F=2 (phase). O=A for planet-only
  literals; O=B and `tz_sensitive` for any literal whose value flips if the instant is shifted by -5 h or +8 h
  (US Eastern / Pacific midnight). In the 7-body runs about 20% of positives were flagged; I did not check how many involve the Moon.
- **resolves_by:** the fixed instant itself (a deterministic astronomy fact; all dates are on or before Oct 31, which precedes Election Day in all 32 years: checked).
- **Range check (DE421):** probes succeed at 1899-08-02 and 2053-10-07 and fail at 1899-07-27 and 2053-10-14, so coverage is about 1899-07-29 to 2053-10-09 as documented. All needed instants (1900-01-01 through 2028-10-31, covering the 2028 evaluation) are inside it.
- **Open points:** it is a deliberate search-size expansion (the astronomy pool adds about 12,000 distinct vectors, roughly 40 times the current main pool's 288); the site must disclose that. The date/grid choices must be frozen before any real outcome is scored.

## 4. Draft tiered frozen procedure (proposal)

Targets T1-T3 are handled per target; the same procedure runs on real and null data.

| tier | stage | pool | label if it fires |
|---|---|---|---|
| 1a | conjunction, k<=4 | current main pool restricted to F>=2 (638 literals, 266 distinct, 319 positives) | `conjA(k)` |
| 1b | conjunction, k<=4 (only if 1a found nothing for the target) | F>=2 pool plus the astronomy family (~12k distinct vectors) | `conjB(k)` |
| 2 | unit-weight keys with a tightened cap, N <= N*, margin >= m* (only if neither conjunction tier fired) | tier-1b pool | `keys(N, m)` |
| - | nothing fired | - | `none` |

**Frozen before Gate 2:** hashes of config, the F>=2 pool, the astronomy grid and its vectors, the solver and search code; seeds; the N* and m* cutoffs, which are chosen from the keys null above and not from real data (candidate: N*=5, m*=1, null P about 3%; or N*=10, m*=2, null P about 2-3%).

**Nulls on the whole procedure:** N1 per target and N1-party (permute the D/R winner sequence, hold counts, derive T1-T3 jointly, take the best label across targets) and N2 (circular shifts, reversal, block permutations of the winner sequence) all run all tiers, in order, exactly as above. Each reports the label distribution.

What each distribution would show (using the numbers above):
- **`conjA` (F>=2 pool, M=0):** F>=2 pool noise rate is 4/3/4 hits in 20,000 (about 0.0002 per target). A real tier-1a hit would have p of about 2e-4 against N1. It is the only tier whose firing is evidence of anything, and it is expected to fail on noise.
- **`conjB` (expanded pool):** noise rate about 0.9 per target. A real tier-1b hit is expected under pure noise (p about 0.9); it demonstrates search size, not signal. The N1 label distribution is the headline figure for the site: P(find a perfect rule | no signal) is about 0.9 once the pool reaches this size.
- **`keys(N, m)`:** noise rate is about 3% at N*=5, m*=1. With a margin-2 requirement (section 2): about 0.05-0.1% at N<=8, 0.4-0.6% at N<=9, 2.4-3.0% at N<=10, 10-11% at N<=11. A tier-2 hit is only informative if the cap is that tight.
- **`none`:** roughly 10% under N1 (about 0.1 that no conjunction tier fires, times about 0.97 that keys also misses at N*=5, m*=1; treating the tiers as independent, which they are not exactly). That is the chance the whole procedure fails on noise.
- **N1-party vs N1 per target:** if the party-level family-wise rate exceeds the per-target rate, the three targets give extra shots at a rule (T1 differs from T2/T3; T2 and T3 are complements); if it matches, they are effectively one shot. I have not run N1-party yet.
- **N2 vs N1-party:** a lower N2 rate would mean autocorrelation in the real winner sequence hurts the search; a similar rate means exchangeability is adequate for the headline figure. With at most 63 distinct shifts and reversals, N2 has coarse resolution; block permutations give volume.

## Caveats
- All figures use true counts only (18/14, 15/17, 17/15); no outcome vector was scored against any pool.
- Synthetic noise series are iid uniform; real astronomical series are smooth in time, so the astronomy power was measured directly with the actual vectors (table in section 3) rather than inferred from M.
- The 10,000-permutation conjunction estimate at M=0 has a wide interval (about 0.00008-0.0005); 20,000 permutations tighten only slightly.
