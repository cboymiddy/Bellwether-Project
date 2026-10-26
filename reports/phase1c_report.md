# Phase 1c report (noise only; no real outcome was scored; the real search has NOT been run)

- **freeze sha256: `475aba0811048404051d238c3ccdcb368f9e8e075b992e50738b604363965c1a`**  (config `17350119fff5ee54...`, astro grid `5399209bd46f9491...`)
- pool A: 266 distinct vectors (`a4fc1686c2e65a48...`); pool B: 15010 distinct vectors (`9d8bb6b37c151bc0...`)
- cutoffs: k<=4; tier 2 N*=4, m*=2; null plan {'N1_per_target': 100000, 'N1_party': 100000, 'N2_block': 100000, 'N2_exact': 63}

## 1. Astronomy family (built)

| quantity | value |
|---|---|
| positives_built | 28800 |
| constant | 4510 |
| era_indicator | 2814 |
| included_positives | 21476 |
| tz_sensitive among included positives | 3355 |
| distinct vectors among included positives (matrix.csv) | 8372 |
| DE421 sha256 | a20a7139da04cbc4... |

Tests (all pass): date grid frozen; every instant's date precedes Election Day in all 32 years; DE421 evaluates all instants including US Eastern/Pacific local midnights and 2028-10-26 and rejects 2060; Sun's longitude is 0 within 0.01 degrees at the March equinox (1900, 1960, 2024), confirming the of-date convention; built files match the index.

## 2. Number of perfect conjunctions per noise permutation (pool B, 20,000 perms/target)

| target | P(>=1) | mean (all) | mean | >=1 | median | >=1 | p90 | >=1 | max | median count at min k | >=1 | min-k histogram |
|---|---|---|---|---|---|---|---|---|
| T1 | 0.9816 | 1882 | 1918 | 245 | 3170 | 2056751 | 85 | {2: 33, 3: 3980, 4: 15618} |
| T2 | 0.9769 | 5152 | 5273 | 441 | 7676 | 3773386 | 156 | {2: 26, 3: 3500, 4: 16013} |
| T3 | 0.9765 | 2322 | 2378 | 278 | 3985 | 1047037 | 99 | {2: 26, 3: 3651, 4: 15852} |

Counts are exact numbers of perfect k-subsets (k<=4) of distinct vectors. Typical noise permutation yields hundreds of perfect conjunctions, so a real hit will not be a unique rule: the output must be ranked and shown as a frontier.

## 3. Keys null on pool B (1,500 perms/target, exact)

**T1** minimal N by required margin m:
| margin | distribution of minimal N |
|---|---|
| m>=1 | {2: 6, 3: 863, 4: 631} |
| m>=2 | {4: 1, 5: 267, 6: 1201, 7: 31} |
| m>=3 | {6: 2, 7: 110, 8: 1056, 9: 332} |
| m>=4 | {8: 1, 9: 52, 10: 682, 11: 690, 12: 75} |

| N cap | P(m>=1) | P(m>=2) | P(m>=3) | P(m>=4) |
|---|---|---|---|---|
| 2 | 0.0040 | 0.0000 | 0.0000 | 0.0000 |
| 3 | 0.5793 | 0.0000 | 0.0000 | 0.0000 |
| 4 | 1.0000 | 0.0007 | 0.0000 | 0.0000 |
| 5 | 1.0000 | 0.1787 | 0.0000 | 0.0000 |
| 6 | 1.0000 | 0.9793 | 0.0013 | 0.0000 |
| 7 | 1.0000 | 1.0000 | 0.0747 | 0.0000 |
| 8 | 1.0000 | 1.0000 | 0.7787 | 0.0007 |
| 9 | 1.0000 | 1.0000 | 1.0000 | 0.0353 |
| 10 | 1.0000 | 1.0000 | 1.0000 | 0.4900 |
| 11 | 1.0000 | 1.0000 | 1.0000 | 0.9500 |
| 12 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |

**T2** minimal N by required margin m:
| margin | distribution of minimal N |
|---|---|
| m>=1 | {2: 3, 3: 834, 4: 663} |
| m>=2 | {5: 242, 6: 1207, 7: 51} |
| m>=3 | {7: 86, 8: 990, 9: 422, 10: 2} |
| m>=4 | {9: 46, 10: 588, 11: 787, 12: 79} |

| N cap | P(m>=1) | P(m>=2) | P(m>=3) | P(m>=4) |
|---|---|---|---|---|
| 2 | 0.0020 | 0.0000 | 0.0000 | 0.0000 |
| 3 | 0.5580 | 0.0000 | 0.0000 | 0.0000 |
| 4 | 1.0000 | 0.0000 | 0.0000 | 0.0000 |
| 5 | 1.0000 | 0.1613 | 0.0000 | 0.0000 |
| 6 | 1.0000 | 0.9660 | 0.0000 | 0.0000 |
| 7 | 1.0000 | 1.0000 | 0.0573 | 0.0000 |
| 8 | 1.0000 | 1.0000 | 0.7173 | 0.0000 |
| 9 | 1.0000 | 1.0000 | 0.9987 | 0.0307 |
| 10 | 1.0000 | 1.0000 | 1.0000 | 0.4227 |
| 11 | 1.0000 | 1.0000 | 1.0000 | 0.9473 |
| 12 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |

**T3** minimal N by required margin m:
| margin | distribution of minimal N |
|---|---|
| m>=1 | {2: 1, 3: 786, 4: 713} |
| m>=2 | {5: 218, 6: 1231, 7: 51} |
| m>=3 | {7: 83, 8: 980, 9: 434, 10: 3} |
| m>=4 | {9: 39, 10: 577, 11: 787, 12: 97} |

| N cap | P(m>=1) | P(m>=2) | P(m>=3) | P(m>=4) |
|---|---|---|---|---|
| 2 | 0.0007 | 0.0000 | 0.0000 | 0.0000 |
| 3 | 0.5247 | 0.0000 | 0.0000 | 0.0000 |
| 4 | 1.0000 | 0.0000 | 0.0000 | 0.0000 |
| 5 | 1.0000 | 0.1453 | 0.0000 | 0.0000 |
| 6 | 1.0000 | 0.9660 | 0.0000 | 0.0000 |
| 7 | 1.0000 | 1.0000 | 0.0553 | 0.0000 |
| 8 | 1.0000 | 1.0000 | 0.7087 | 0.0000 |
| 9 | 1.0000 | 1.0000 | 0.9980 | 0.0260 |
| 10 | 1.0000 | 1.0000 | 1.0000 | 0.4107 |
| 11 | 1.0000 | 1.0000 | 1.0000 | 0.9353 |
| 12 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |

**Proposed and frozen caps: N* = 4, m* = 2.** Noise rate P(keys rule with N<=4, margin>=2): T1 0.0007 (1/1500), T2 0/1500, T3 0/1500 (rule-of-three upper bound about 0.002). Alternatives with a similar noise rate are N<=6/m>=3 (T1 0.0013) and N<=8/m>=4 (T1 0.0007); the 288-vector-pool figure of ~3% (N<=5, m=1) no longer applies because the expanded pool makes N<=5, m=1 certain.

## 4. Whole-procedure nulls (frozen; labels: conjA, conjB, keys, none)

| null | perms | conjA | conjB | keys | none | unknown |
|---|---|---|---|---|---|---|
| N1 T1 | 100000 | 40 (0.0004) [0.0003, 0.0005] | 98079 (0.9808) [0.9799, 0.9816] | 0 (0.0000) [0.0000, 0.0000] | 1881 (0.0188) [0.0180, 0.0197] | 0 (0.0000) [0.0000, 0.0000] |
| N1 T2 | 100000 | 14 (0.0001) [0.0001, 0.0002] | 97663 (0.9766) [0.9757, 0.9775] | 0 (0.0000) [0.0000, 0.0000] | 2323 (0.0232) [0.0223, 0.0242] | 0 (0.0000) [0.0000, 0.0000] |
| N1 T3 | 100000 | 21 (0.0002) [0.0001, 0.0003] | 97545 (0.9755) [0.9745, 0.9764] | 0 (0.0000) [0.0000, 0.0000] | 2434 (0.0243) [0.0234, 0.0253] | 0 (0.0000) [0.0000, 0.0000] |
| N1-party, best of T1-T3 | 100000 | 84 (0.0008) [0.0007, 0.0010] | 99914 (0.9991) [0.9989, 0.9993] | 0 (0.0000) [0.0000, 0.0000] | 2 (0.0000) [0.0000, 0.0001] | 0 (0.0000) [0.0000, 0.0000] |
| N1-party, T1 | 100000 | 51 (0.0005) [0.0004, 0.0007] | 98142 (0.9814) [0.9806, 0.9822] | 0 (0.0000) [0.0000, 0.0000] | 1807 (0.0181) [0.0173, 0.0189] | 0 (0.0000) [0.0000, 0.0000] |
| N1-party, T2 | 100000 | 16 (0.0002) [0.0001, 0.0003] | 97566 (0.9757) [0.9747, 0.9766] | 0 (0.0000) [0.0000, 0.0000] | 2418 (0.0242) [0.0232, 0.0252] | 0 (0.0000) [0.0000, 0.0000] |
| N1-party, T3 | 100000 | 17 (0.0002) [0.0001, 0.0003] | 97583 (0.9758) [0.9749, 0.9768] | 0 (0.0000) [0.0000, 0.0000] | 2400 (0.0240) [0.0231, 0.0250] | 0 (0.0000) [0.0000, 0.0000] |
| N2 exact (63 shifts/reversals), best | 63 | 0 (0.0000) [0.0000, 0.0575] | 63 (1.0000) [0.9425, 1.0000] | 0 (0.0000) [0.0000, 0.0575] | 0 (0.0000) [0.0000, 0.0575] | 0 (0.0000) [0.0000, 0.0575] |
| N2 block perms, best | 100000 | 48 (0.0005) [0.0004, 0.0006] | 99952 (0.9995) [0.9994, 0.9996] | 0 (0.0000) [0.0000, 0.0000] | 0 (0.0000) [0.0000, 0.0000] | 0 (0.0000) [0.0000, 0.0000] |

N1-party rejected 7655 winner sequences (T1 with fewer than 12 true years; fraction 0.071) to stay within exact-counting limits; the real T1 has 18 true years.

k of the conjunction tiers (N1, per target):
- T1: conjA k=3: 1, conjA k=4: 39, conjB k=2: 153, conjB k=3: 19869, conjB k=4: 78057
- T2: conjA k=3: 1, conjA k=4: 13, conjB k=2: 131, conjB k=3: 17773, conjB k=4: 79759
- T3: conjA k=4: 21, conjB k=2: 114, conjB k=3: 18052, conjB k=4: 79379
