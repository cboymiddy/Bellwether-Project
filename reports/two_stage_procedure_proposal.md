# Proposed frozen two-stage procedure (proposal only; nothing here is implemented as the real search)

Goal: the null must measure the *whole* procedure the real data go through, not just stage 1.

## Frozen inputs (hashed together before Gate 2)
- `config.yaml` sha256, pool files sha256 (`literals_main.yaml`, `matrix_main.csv`, `resolves_by_main.csv`), and the sha256 of `src/nulls/search_core.py` and the driver.
- Pool = main pool only (era indicators and quarantined literals excluded), deduplicated to distinct 32-bit vectors with recorded aliases. Search size is reported as raw literals, distinct vectors, and distinct-up-to-complement.
- Seeds, solver parameters (CP-SAT `num_workers=1`, time limit, tie-break order), and the ranking function (CLAUDE.md C5) are fixed in config.

## Procedure, per target T in {T1, T2, T3}
1. **Stage 1, conjunctions k <= 4.** Exhaustive over distinct vectors (true in all target years; OR of false-masks covers the rest). Output the exact count of perfect k-subsets for k = 1..4 and the minimal covers.
2. **Stage 2, keys, only if stage 1 finds nothing for that target.** Unit-weight "at least t of N statements", N <= 13, perfect separation (`min over wins > max over losses`), CP-SAT objective: smallest N, then largest margin.
3. **Outcome label:** `conj(k)`, `keys(N, margin)`, or `none`. Conjunction beats keys; smaller k or N beats larger.

## Null for the whole procedure
- **N1 per target** (what was run): permute that target's own vector, holding its true count fixed; run stages 1 and 2 exactly as above; record the outcome label distribution. Report P(conj), P(keys | no conj), P(none), and the null distribution of k and N.
- **N1-party (recommended addition):** T1-T3 are not independent (T2 and T3 are complements; T1 is derived from the winner sequence: incumbent party in year y is the winner of year y-4). To calibrate "some target gives some rule", permute the D/R winner sequence (counts fixed, 1896 held fixed), derive T1, T2, T3 jointly, and run the procedure on all three. The family-wise statistic is P(any target yields a rule).
- **N2** (circular shifts and reversal of the winner sequence, then block permutations) and **N3** (fit 1900-1980, score 1984-2024) use the same procedure and the same frozen pool.
- **Comparison statistic for the real result:** place the real outcome label in the null label distribution. For `conj(k)` the p-value is P(null label is `conj(k')` with k' <= k); for `keys(N, margin)` it is P(keys with N' <= N), conditional on no conjunction.

## Problem exposed by the N1 run (needs your decision)
Stage 2 as specified is essentially vacuous on this pool: a perfect unit-weight keys rule with N <= 13 exists for random targets in (almost) every permutation (see the N1 table). If stage 2 always succeeds, the procedure's outcome is never `none`, and a keys result carries no evidential weight. Options for you to choose between:
1. Drop the keys fallback entirely.
2. Keep it but tighten it so it is informative: for example N <= 5 and a required margin of at least 2, with the cutoffs frozen before anything else is looked at and justified from the null (not from the real result).
3. Keep it as specified but present it only as a demonstration that a keys rule is always findable.

## Other items to freeze or decide
- The multiplicity across three targets (above) and across stages.
- Real-result tie-breaks: ranking by C5 (all O in {A, B}, higher minimum F, higher mean F, fewer conditions) is applied only after correctness.
- Whether N1 uses 10,000 permutations (spec) or more; the conjunction stage is cheap enough for 100,000+, which matters because P(conj | noise) is small and its confidence interval is wide at 10,000.
