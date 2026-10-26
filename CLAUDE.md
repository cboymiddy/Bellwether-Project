# Bellwether Project: Spec & Working Agreement

> Place in the repo root as `CLAUDE.md` (Claude Code loads it every session, so it is kept compact).
> Start the first session in **Plan Mode**. Carson Middleton is the **creative director**; you are the **engine**.
> Never cross a **GATE** without Carson's explicit approval.

## 1. Goal

Find one or more **bellwethers** that "correctly predict" the winner of every US presidential election from **1900 to 2024 (32 elections)**, built only from evergreen, non-political, objectively checkable conditions. Target shape:

> "If X, Y, and Z, then the incumbent president's party will win."

**The deeper purpose is satire-as-methodology:** show how easy it is to find a perfect-fit rule by chance. A perfect fit is *expected*. The real contribution is (a) the **search size** and (b) a **null distribution** showing the identical search finds perfect rules for *fake* election histories. The final site must disclose both. Never present any rule as genuinely predictive.

## 2. Hard criteria (operationalized)

**C1. Pre-election resolution.** Every condition must resolve strictly before Election Day.
- Each literal carries `resolves_by` (date). Automated test: `resolves_by < election_day` for all 32 years.
- Banned: anything observed on/after Election Day (Election-Day weather, results, exit polls, county bellwethers).
- Allowed: deterministic calendar/astronomy facts about Election Day itself (knowable years ahead).

**C2. Evergreen and non-political.** A literal passes only if all hold:
1. The underlying event/series still exists in 2024 and is expected to continue; it can be evaluated for 2028 *before* the 2028 election.
2. It never references candidates, parties, incumbency, polls, approval, the economy-as-politics, or campaign events.
3. It does not depend on a defunct entity or name (e.g. anything like the "Redskins Rule" fails).
4. The rule's conclusion must be apparent from the conditions alone, regardless of that year's political circumstances.

**C3. Rule form.**
- **Primary: conjunction.** `predict WIN iff ALL conditions true; otherwise predict NOT-WIN`. This biconditional reading is mandatory: the rule must emit a binary prediction for *every* election, not only years when the conjunction holds.
- **Tier-2 fallback: Lichtman-style keys.** `predict WIN iff at least t of N statements are true`, used only if no conjunction tier fires, with the frozen caps N* and m* (Section 5).
- **Allowed targets:** T1 incumbent party wins; T2 Democratic Party wins; T3 Republican Party wins. T4 "incumbent party loses" is allowed only if Carson approves.

**C4. Absence logic.** Literals are Boolean predicates defined for **every** year. If the underlying event did not occur, the positive predicate is **False** and its negation **True** (e.g. "the Phillies won the World Series this year" is False in 1904 because no Series was played).
- **Incomplete events are False.** An event not *completed* before Election Day is False, uniformly across all years, and each literal's definition text must say so. Set `resolves_by` per event to its actual completion date (e.g. the 2020 Masters was held in November; some Olympics ran past Election Day or were held outside their nominal year; verify each against a source).
- **Era indicators.** Literals constant across a block of years (e.g. "a Super Bowl was held this year") are tagged `era_indicator`, excluded from the main pool, and reported separately. Frozen before any searching.
- This applies to *events*. It does **not** license missing *measurements*: weather or other measured series with a gap in any election year are ineligible unless the literal is defined so the gap cannot silently flip its value.
- Every literal's negation is automatically in the pool.

**C5. Selection and objectivity.** Correctness (32/32) is the gate; the rest only rank perfect rules.
- **Familiarity F:** 3 = a casual American would recognize it without lookup (World Series, Super Bowl, Olympics, solstice, Election Day date, first snow in a major city); 2 = enthusiast knowledge; 1 = niche/technical.
- **Objectivity O:** **A** = one authoritative source, no judgment, no boundary sensitivity; **B** = depends on a named dataset, station, definition, or timezone, so the dataset **must be cited** in the literal's metadata; **C** = requires judgment, so **forbidden** unless Carson approves that literal.
- **Ranking (lexicographic):** (1) all literals O in {A, B}; (2) higher minimum F; (3) higher mean F; (4) fewer conditions; (5) fewer `tz_sensitive` literals. Also output the Pareto frontier so Carson can override. Timezone-sensitive literals are admitted (graded O = B) and must be flagged on rule cards.

## 3. Locked configuration (`config.yaml`; changes require a Gate)

| Parameter | Value |
|---|---|
| Elections | 1900, 1904, ..., 2024 (32) |
| Election Day | First Tuesday after the first Monday in November (computed, never scraped) |
| Incumbent party | Party of the sitting president on Election Day, whether or not he runs |
| "Win" | Wins the **Electoral College** (**confirmed by Carson, Phase 0**). 2000 coded as incumbent-party **loss**. Run a sensitivity pass with popular-vote coding. |
| "Perfect" | 32/32 correct on the locked outcome vector. No exceptions, no "close enough". |
| Event dating | By **actual event date**, not "season". Event counts only if it occurs in the election year and before Election Day. |
| Timezone for calendar/astronomy | **UTC canonical.** Flag any literal whose truth value changes under US/Eastern or US/Pacific, and grade it O = B. |
| Max conditions | Prefer <= 3; accept 4; flag 5+. Keys: N <= 13. |
| Franchise lineage | Use the league's official lineage (relocations/renames = same franchise). Document each mapping. |
| Seeds | All randomness seeded and logged. |

**Seed outcome table.** Written from memory, so verify every row against a primary source (e.g. National Archives Electoral College records), then commit the verified file as `data/processed/outcomes.csv` with source and retrieval date. Expect 18 wins / 14 losses.

```csv
year,incumbent_party,incumbent_party_won
1900,R,1
1904,R,1
1908,R,1
1912,R,0
1916,D,1
1920,D,0
1924,R,1
1928,R,1
1932,R,0
1936,D,1
1940,D,1
1944,D,1
1948,D,1
1952,D,0
1956,R,1
1960,R,0
1964,D,1
1968,D,0
1972,R,1
1976,R,0
1980,D,0
1984,R,1
1988,R,1
1992,R,0
1996,D,1
2000,D,0
2004,R,1
2008,R,0
2012,D,1
2016,D,0
2020,R,0
2024,D,0
```

## 4. Literal library

Every literal is one YAML record plus one row in a 32-column Boolean matrix:
`id, statement, category, polarity, definition, source_url, dataset_citation, retrieval_date, resolves_by, F, O, status (auto | human_verified | quarantined)`

**Generate by template x entity** (e.g. "Franchise F won the MLB World Series this year" for every franchise; plus event-feature literals like "AL team won", "Series went 7 games", "sweep"). Cheapest and most familiar first:

1. **Calendar/astronomy (computed, no scraping):** Election Day date (Nov 2-8); solstice/equinox dates; eclipses before Election Day; moon phase on Election Day; Easter date. Use Skyfield with JPL DE421 (covers roughly 1899-2053). Planetary geometry is objective but F = 1. The frozen **astronomy geometry family** (tier-1b expansion, `src/literals/astro_family.py`) uses 10 bodies (Sun, Moon, Mercury-Pluto), 60 fixed 00:00-UTC instants (days 1, 6, 11, 16, 21, 26 of Jan-Oct), 12 thirty-degree longitude sectors, and pairwise separation >= c for c = 20, 40, ..., 160 degrees; grid chosen from the noise-power table, never from real outcomes. Literals that change value at US Eastern/Pacific local midnight are `tz_sensitive` (O = B).
2. **Sports (event-date keyed):** MLB World Series (franchise, league, length); Super Bowl (since 1967); NBA Finals; Stanley Cup; Summer Olympics (host, held or not); FIFA men's World Cup (since 1930); Kentucky Derby / Triple Crown; Indy 500; Masters; Wimbledon; Heisman. Pre-1936 college-football champions are disputed, so exclude unless an official dataset is cited.
3. **Weather (NOAA GHCN-D / NWS climate records):** first measurable snowfall by Election Day in Chicago / NYC / DC; warm or cold summers. Station moves and instrument changes make these O = B with the station and dataset cited. Require complete data for all 32 years.
4. **Other continuous series (optional):** Academy Awards (since 1929; absence logic applies), Nobel categories, etc.
5. **Markets/macro: OFF by default.** Plausible mechanisms weaken the absurdity and drift toward political circumstances. Carson may enable.

**Traps to handle explicitly:** 1900 was *not* a leap year; no World Series in 1904; Olympics cancelled in 1916/1940/1944; franchise relocations/renames; Wikipedia is fine for a first pass but needs a second independent source for anything in a final rule; polarity is free, so expect surviving literals to be mostly negations of rare events or positives of common ones (see Open Decisions #3).

## 5. Search: frozen tiered procedure

Per target T1-T3 (never both polarities of a target at once). Pools: **A** = main pool restricted to F >= 2; **B** = A plus the astronomy geometry family. Era indicators, constants, and quarantined (O = C) literals are excluded everywhere.

- **Tier 1a:** perfect conjunction, k <= 4, on pool A. Label `conjA(k)`.
- **Tier 1b** (only if 1a finds nothing for that target): same search on pool B. Label `conjB(k)`.
- **Tier 2** (only if neither fires): perfect unit-weight keys rule on pool B with N <= N\* and margin >= m\*. Label `keys(N, m)`. **N\* = 4, m\* = 2** (frozen from the keys null on pool B, where the noise rate is about 0.1%; never from real data). Otherwise `none`.

**Conjunction search details.** P = years where the target is true, N = years where it is false.
1. Keep only literals (and negations) true in **all** of P.
2. For each, compute a 32-bit mask over N of the years where it is **false**.
3. A conjunction S is **perfect** iff the OR of its masks covers all of N.
4. **Enumerate all** minimal perfect covers up to k = 4, not just the first (exact counts via zeta/Moebius transform; enumeration by branching on the least-covered unexplained year).
5. **Dedupe literals with identical 32-bit vectors** into equivalence classes; keep the most familiar representative and record the aliases. Report **both** raw-literal and distinct-vector counts, since honest search size depends on it.

**Keys search details.** Subset S and threshold t with `min_over_wins(count) > max_over_losses(count)`; margin = min over wins minus max over losses. CP-SAT; objective: smallest N, then largest margin. Candidates are first reduced by exact Pareto dominance (u dominates v when u is true wherever v is true on wins and false wherever v is false on losses).

**Freeze and one-shot rule.** `freeze.yaml` hashes config, pools, the astronomy date grid and vectors, search/solver code, cutoffs, and seeds. The real search (`src/search/real.py`) runs exactly once, after Carson's Gate 2 approval, with no pool or procedure change afterward; it refuses to run if the hashes differ or if a lock file exists.

## 6. Statistical honesty layer (a deliverable, not an extra)

Run **after the pipeline config is frozen and hashed**, using the *identical* pool, gates, and k-limit:
- **N1, exchangeable null:** >= 10,000 random permutations of each target's own outcome vector, holding its true count fixed, run through the **whole tiered procedure**. Record the label distribution (`conjA`, `conjB`, `keys`, `none`), the number of perfect conjunctions per permutation, and minimum k.
- **N1-party:** permute the D/R winner sequence (counts fixed, 1896 winner fixed), derive T1-T3 jointly, run the whole procedure on all three, and record the best label across targets (family-wise rate). Draws whose derived T1 has fewer than 12 true years are rejected and counted (exact conjunction counting needs <= 20 non-target years).
- **N2, structured null:** circular shifts / block permutations that preserve the real outcome sequence's autocorrelation (incumbent losses are anti-clustered), run through the whole procedure. A 32-element circular shift gives at most 31 distinct non-identity shifts: report that exact count, add reversal, and use block permutations for volume. In N1 and N2, permute each target's own vector (T1, T2, T3 separately).
- **N3, pseudo-out-of-sample:** fit on 1900-1980 only, score on 1984-2024; also show a rule found on 1900-1990 being "confirmed" on 1992-2024.
- **Always report:** pool size, distinct vectors, number of conjunctions examined, and P(perfect rule exists | no signal).

## 7. Data integrity (non-negotiable)

- **Never enter a historical fact from model memory into a data file.** Values come from a fetched source or from computation, with the URL, retrieval date, and sha256 of raw files stored in `data/raw/`.
- If a domain is blocked or a source is unavailable, **say so and stop**; do not substitute recollection.
- Search runs on `auto` literals. Any literal in a candidate final rule must reach `human_verified` (Phase 4).
- If verification corrects any value, **rerun the whole pipeline and nulls**, since the pool changed.

## 8. Repo layout and tooling

```
bellwether/
  CLAUDE.md  config.yaml
  data/raw/  data/processed/
  src/{acquire,literals,search,nulls,verify}/
  tests/  reports/  site/
```
Python >= 3.11; pandas, numpy, skyfield, requests, bs4/lxml, ortools, pytest, ruff. Site: static (Astro or Vite+TS), GitHub Pages.

**Required tests:** outcomes are 18/14 (and 20/12 under popular-vote sensitivity, flips: 2000 and 2016); Election Day dates correct (1900-11-06, 2020-11-03, 2024-11-05); every literal has a value for all 32 years; `resolves_by < election_day` everywhere; 1904 World Series absence logic; **planted-rule recovery** (inject a known rule into synthetic data and confirm the engine finds it); null harness reproducible from seed.

## 9. Phases and gates

| Phase | Work | Output |
|---|---|---|
| 0 | Scaffold, `config.yaml`, verify `outcomes.csv`, test stubs (Plan Mode) | Repo + verified outcomes. **GATE 0:** Carson confirms config and Open Decisions |
| 1 | Build literal library: computed -> sports -> weather. **No searching yet.** | Pool report: counts by category, exclusions, coverage failures. **GATE 1** |
| 2 | The frozen tiered procedure for T1-T3, run once: ranked output + search-size report | **GATE 2:** Carson picks candidates |
| 3 | Nulls N1-N3 on the frozen pipeline | Null report with histograms |
| 4 | Hand-verification of chosen rule(s): `verification_sheet.csv` (literal, year, value, primary source URL, second source, checked) | Verified rule; rerun if anything changed |
| 5 | Site: rule card with year-by-year table and source links; "How we found it" (search size + null histogram); shuffle-the-history demo (client-side rerun of the cover search on the precomputed matrix); what the rule says for 2028 (with disclaimer); limitations page | **GATE 5** before publishing |

**Freeze rule:** hash the literal pool and `config.yaml` before Phase 2 starts. Any later change to either restarts the pipeline and nulls.

**Compute/token discipline:** scripts do the heavy lifting; print summaries, not raw tables. Use one session per phase. Sonnet is the default; escalate to Opus only for a single adversarial methodology review before Phase 3 or for a stubborn debugging loop.

## 10. Open decisions for Carson (defaults apply until overridden)

1. **2000 coding:** Electoral College (default, confirmed) vs popular vote. Popular-vote coding flips both 2000 and 2016 (the incumbent party won the popular vote but lost the Electoral College in each), changing the split from 18/14 to 20/12 (derived from fetched data in Phase 0).
2. **T4 "incumbent loses":** off by default.
3. **Polarity:** both polarities allowed. Note: under win-targeted conjunctions every literal must hold in *all* win years, so positive rare events ("Team X won the Series") can't appear and rules will read as "...did not win..." T4 does not help: it requires every literal to hold in all 14 loss years, which excludes rare positive events just as T1 excludes them across the 18 win years. For positive phrasing, render a negation-conjunction as "the incumbent party wins unless A, B, or C" (not-A and not-B and not-C is equivalent to not-(A or B or C)). T4 stays OFF.
4. **Markets/macro series:** off.
5. **Timezone convention:** UTC canonical with boundary flags. Timezone-sensitive literals are admitted (O = B), flagged on rule cards, and ranked below equivalent rules with fewer of them.
6. **Site name, tone, and visual identity:** open (Carson decides).
7. **2028 forecast display:** on, with a prominent "this is spurious" disclaimer.
8. **Search-size expansion (Gate 1, decided):** the pool is deliberately expanded with a frozen astronomy geometry family so that a perfect conjunction is likely under noise. The site must disclose the pool sizes, the tier structure, and the null label distribution (P(perfect rule | no signal) per tier), and must never present any rule as predictive.

## 11. Collaboration rules

- Be candid. Flag hidden assumptions, confounders, and the strongest counterargument to any result. No reassurance padding.
- Explain *why* behind conventions and design choices (mechanism, incentives, causal pathway), briefly.
- Express uncertainty with calibrated language ("probably ~X because...").
- Before writing any large block of code (>~100 lines), confirm the spec is "ready to ship"; handle edge cases, validation, and fallbacks.
- Distinguish what a source *says* from what you *verified*.
