# Gate-2 real-search report (pre-declared runs; no interpretation)

- freeze sha256 `475aba0811048404051d238c3ccdcb368f9e8e075b992e50738b604363965c1a`; frozen real-search driver `351ddbf8315e33d4...` (unchanged); caps N*=4, m*=2
- outcomes.csv sha256 `788dac38a7e61bbfbbd581f6ba0210ff5a1d96d6d49322bd8a4bf22ddb197868` (identical to Phase 0 commit d73cdb2)
- runner `src/search/gate2.py` sha256 `85ba976bd0a2e665...` (committed before the run, commit 2f3166e; it is an unfrozen orchestrator over the frozen functions)
- run order: PRIMARY (Electoral College, T1-T3), SENSITIVITY (popular vote), N3; each exactly once; lock file present; no reruns, no pool/code/cutoff/ranking changes
- progress log: `reports/real_search/progress.log`

## Deviations and notes the pre-declaration did not anticipate

1. The frozen driver `run_real` writes only to `reports/real_search_results.json`, logs nothing, and keeps only the top 40 rules, so it could not meet the pre-declared outputs. I ran the same frozen functions (`evaluate`, `conjunction_report`, `keys_solution`, `literal_table`) from a new runner, passing an unbounded `top`, and wrote to `reports/real_search/`. The frozen driver was not run.
2. N3 null: 2,000 permutations per target (not 20,000). Finding the top-ranked rule exactly is expensive on the 21-year training data when tier 1b fires (up to about 1e6 covers per permutation); the run took about 3 h 20 min. N3 permutes each target's own full 32-year vector (counts fixed), fits on 1900-1980, scores 1984-2024.
3. N3 merges literals that are identical on the 21 training years; the representative literal is chosen by the frozen alias order (highest F, then O, then not tz_sensitive, then id), never by test performance, and its own 1984-2024 values are scored.
4. Ranking dependence of the nulls: the earlier N1, N1-party and N2 label distributions use only existence and minimal k (not the ranking function). The N3 null uses the frozen ranking to pick the top rule.
5. The popular-vote sensitivity has no null (the frozen nulls used the Electoral College counts 18/15/17; popular-vote counts are 20/17/15). The CLAUDE.md second N3 split (1900-1990 / 1992-2024) was not pre-declared and was not run.

## 1. PRIMARY: Electoral College coding

### Labels and frontier summary

| target | true yrs | false yrs | label | min k | candidate vectors | minimal perfect rules | pareto rules | rules by k | perfect k-subsets (incl. non-minimal) |
|---|---|---|---|---|---|---|---|---|---|
| T1 | 18 | 14 | conjB | 4 | 110 | 446 | 22 | {'4': 446} | {'1': 0, '2': 0, '3': 0, '4': 446} |
| T2 | 15 | 17 | none | - | - | - | - | - | - |
| T3 | 17 | 15 | conjB | 4 | 142 | 126 | 2 | {'4': 126} | {'1': 0, '2': 0, '3': 0, '4': 126} |

**T1: top 10 of 50 by the frozen ranking** (full frontier: `frontier_primary_ec_T1.csv`, 446 rules)

| rank | k | literals | F | O | min F | mean F | tz flags | # tz |
|---|---|---|---|---|---|---|---|---|
| 1 | 4 | NOT_sports_nhl_winner_franchise_quebec_bulldogs & NOT_astro_geo_0206_sep_mercury_jupiter_ge160 & NOT_astro_geo_0906_sep_sun_moon_ge140 & astro_geo_0201_sep_venus_pluto_ge060 | 3,1,1,1 | B,A,A,A | 1 | 1.5 | 0,0,0,0 | 0 |
| 2 | 4 | astro_geo_0306_sep_venus_uranus_ge020 & NOT_astro_geo_0906_sep_sun_moon_ge140 & NOT_sports_mlb_ws_loser_franchise_kansas_city_royals & astro_geo_0121_sep_venus_pluto_ge040 | 1,1,3,1 | A,A,B,A | 1 | 1.5 | 0,0,0,0 | 0 |
| 3 | 4 | astro_geo_0306_sep_venus_uranus_ge020 & NOT_astro_geo_0906_sep_sun_moon_ge140 & NOT_sports_mlb_ws_loser_franchise_kansas_city_royals & astro_geo_0201_sep_venus_pluto_ge060 | 1,1,3,1 | A,A,B,A | 1 | 1.5 | 0,0,0,0 | 0 |
| 4 | 4 | astro_geo_0306_sep_venus_uranus_ge020 & NOT_astro_geo_0906_sep_sun_moon_ge140 & NOT_sports_mlb_ws_winner_franchise_philadelphia_phillies & astro_geo_0121_sep_venus_pluto_ge040 | 1,1,3,1 | A,A,B,A | 1 | 1.5 | 0,0,0,0 | 0 |
| 5 | 4 | astro_geo_0306_sep_venus_uranus_ge020 & NOT_astro_geo_0906_sep_sun_moon_ge140 & NOT_sports_mlb_ws_winner_franchise_philadelphia_phillies & astro_geo_0201_sep_venus_pluto_ge060 | 1,1,3,1 | A,A,B,A | 1 | 1.5 | 0,0,0,0 | 0 |
| 6 | 4 | astro_geo_0306_sep_venus_uranus_ge020 & NOT_astro_geo_0906_sep_sun_moon_ge140 & NOT_sports_nfl_sb_winner_franchise_pittsburgh_steelers & astro_geo_0121_sep_venus_pluto_ge040 | 1,1,3,1 | A,A,B,A | 1 | 1.5 | 0,0,0,0 | 0 |
| 7 | 4 | astro_geo_0306_sep_venus_uranus_ge020 & NOT_astro_geo_0906_sep_sun_moon_ge140 & NOT_sports_nfl_sb_winner_franchise_pittsburgh_steelers & astro_geo_0201_sep_venus_pluto_ge060 | 1,1,3,1 | A,A,B,A | 1 | 1.5 | 0,0,0,0 | 0 |
| 8 | 4 | astro_geo_1021_sep_mercury_venus_ge020 & NOT_astro_geo_0121_sep_mars_jupiter_ge160 & NOT_sports_nfl_sb_winner_franchise_pittsburgh_steelers & NOT_astro_geo_0701_sep_mercury_pluto_ge160 | 1,1,3,1 | A,A,B,A | 1 | 1.5 | 0,0,0,0 | 0 |
| 9 | 4 | astro_geo_1021_sep_mercury_venus_ge020 & NOT_astro_geo_0121_sep_mars_jupiter_ge160 & NOT_sports_nfl_sb_winner_franchise_pittsburgh_steelers & astro_geo_0201_sep_venus_pluto_ge060 | 1,1,3,1 | A,A,B,A | 1 | 1.5 | 0,0,0,0 | 0 |
| 10 | 4 | astro_geo_1021_sep_mercury_venus_ge020 & NOT_astro_geo_0206_sep_mercury_jupiter_ge160 & NOT_sports_nba_loser_franchise_phoenix_suns & NOT_astro_geo_0701_sep_mercury_pluto_ge160 | 1,1,3,1 | A,A,B,A | 1 | 1.5 | 0,0,0,0 | 0 |

**T3: top 10 of 50 by the frozen ranking** (full frontier: `frontier_primary_ec_T3.csv`, 126 rules)

| rank | k | literals | F | O | min F | mean F | tz flags | # tz |
|---|---|---|---|---|---|---|---|---|
| 1 | 4 | NOT_astro_geo_0101_sep_mercury_mars_ge120 & astro_geo_0426_sep_mercury_uranus_ge020 & NOT_sports_nhl_loser_franchise_toronto_maple_leafs & NOT_astro_geo_0821_sep_mercury_saturn_ge160 | 1,1,3,1 | A,A,B,A | 1 | 1.5 | 0,0,0,0 | 0 |
| 2 | 4 | NOT_astro_geo_0101_sep_mercury_mars_ge120 & astro_geo_0501_sep_mercury_uranus_ge020 & NOT_sports_nhl_loser_franchise_toronto_maple_leafs & NOT_astro_geo_0821_sep_mercury_saturn_ge160 | 1,1,3,1 | A,A,B,A | 1 | 1.5 | 0,0,0,0 | 0 |
| 3 | 4 | NOT_astro_geo_0101_sep_mercury_mars_ge120 & astro_geo_0511_sep_moon_pluto_ge020 & NOT_sports_nhl_loser_franchise_toronto_maple_leafs & NOT_astro_geo_0821_sep_mercury_saturn_ge160 | 1,1,3,1 | A,B,B,A | 1 | 1.5 | 0,1,0,0 | 1 |
| 4 | 4 | NOT_astro_geo_0101_sep_mercury_mars_ge120 & NOT_astro_geo_0101_saturn_lon270 & NOT_astro_geo_0821_sep_mercury_saturn_ge160 & NOT_astro_geo_0401_sep_moon_pluto_ge160 | 1,1,1,1 | A,A,A,A | 1 | 1.0 | 0,0,0,0 | 0 |
| 5 | 4 | NOT_astro_geo_0101_sep_mercury_mars_ge120 & NOT_astro_geo_0201_sep_mars_neptune_ge140 & NOT_astro_geo_0101_saturn_lon270 & NOT_astro_geo_0821_sep_mercury_saturn_ge160 | 1,1,1,1 | A,A,A,A | 1 | 1.0 | 0,0,0,0 | 0 |
| 6 | 4 | NOT_astro_geo_0101_sep_mercury_mars_ge120 & NOT_astro_geo_0201_sep_mars_neptune_ge140 & NOT_astro_geo_0721_sep_mercury_jupiter_ge140 & NOT_astro_geo_0821_sep_mercury_saturn_ge160 | 1,1,1,1 | A,A,A,A | 1 | 1.0 | 0,0,0,0 | 0 |
| 7 | 4 | NOT_astro_geo_0101_sep_mercury_mars_ge120 & NOT_astro_geo_0201_sep_mars_neptune_ge140 & NOT_astro_geo_0721_sep_sun_saturn_ge160 & NOT_astro_geo_0121_mars_lon300 | 1,1,1,1 | A,A,A,A | 1 | 1.0 | 0,0,0,0 | 0 |
| 8 | 4 | NOT_astro_geo_0101_sep_mercury_mars_ge120 & NOT_astro_geo_0201_sep_mars_neptune_ge140 & NOT_astro_geo_0721_sep_sun_saturn_ge160 & NOT_astro_geo_0201_sep_mercury_venus_ge060 | 1,1,1,1 | A,A,A,A | 1 | 1.0 | 0,0,0,0 | 0 |
| 9 | 4 | NOT_astro_geo_0101_sep_mercury_mars_ge120 & NOT_astro_geo_0201_sep_mars_neptune_ge140 & NOT_astro_geo_0721_sep_sun_saturn_ge160 & NOT_astro_geo_0821_sep_mercury_saturn_ge160 | 1,1,1,1 | A,A,A,A | 1 | 1.0 | 0,0,0,0 | 0 |
| 10 | 4 | NOT_astro_geo_0101_sep_mercury_mars_ge120 & NOT_astro_geo_0201_sep_mars_neptune_ge140 & NOT_astro_geo_0821_sep_mercury_saturn_ge160 & NOT_astro_geo_0721_saturn_lon270 | 1,1,1,1 | A,A,A,A | 1 | 1.0 | 0,0,0,0 | 0 |

## 2. SENSITIVITY (labeled separately): popular-vote coding

### Labels and frontier summary

| target | true yrs | false yrs | label | min k | candidate vectors | minimal perfect rules | pareto rules | rules by k | perfect k-subsets (incl. non-minimal) |
|---|---|---|---|---|---|---|---|---|---|
| T1 | 20 | 12 | conjB | 4 | 71 | 150 | 24 | {'4': 150} | {'1': 0, '2': 0, '3': 0, '4': 150} |
| T2 | 17 | 15 | conjB | 4 | 155 | 199 | 5 | {'4': 199} | {'1': 0, '2': 0, '3': 0, '4': 199} |
| T3 | 15 | 17 | conjB | 4 | 197 | 3 | 1 | {'4': 3} | {'1': 0, '2': 0, '3': 0, '4': 3} |

**T1: top 10 of 50 by the frozen ranking** (full frontier: `frontier_sensitivity_popvote_T1.csv`, 150 rules)

| rank | k | literals | F | O | min F | mean F | tz flags | # tz |
|---|---|---|---|---|---|---|---|---|
| 1 | 4 | NOT_astro_geo_0221_sep_mars_jupiter_ge140 & NOT_astro_geo_0101_saturn_lon150 & NOT_astro_geo_0906_sep_sun_moon_ge140 & NOT_sports_nfl_sb_loser_franchise_san_francisco_49ers | 1,1,1,3 | A,A,A,B | 1 | 1.5 | 0,0,0,0 | 0 |
| 2 | 4 | NOT_astro_geo_0221_sep_mars_jupiter_ge140 & NOT_astro_geo_0101_saturn_lon150 & astro_geo_0626_sep_moon_mercury_ge020 & NOT_sports_nfl_sb_loser_franchise_san_francisco_49ers | 1,1,1,3 | A,A,A,B | 1 | 1.5 | 0,0,0,0 | 0 |
| 3 | 4 | NOT_astro_geo_0221_sep_mars_jupiter_ge140 & NOT_astro_geo_0206_sep_mercury_jupiter_ge160 & NOT_astro_geo_0906_sep_sun_moon_ge140 & NOT_sports_nfl_sb_loser_franchise_san_francisco_49ers | 1,1,1,3 | A,A,A,B | 1 | 1.5 | 0,0,0,0 | 0 |
| 4 | 4 | NOT_astro_geo_0221_sep_mars_jupiter_ge140 & NOT_astro_geo_0206_sep_mercury_jupiter_ge160 & astro_geo_0626_sep_moon_mercury_ge020 & NOT_sports_nfl_sb_loser_franchise_san_francisco_49ers | 1,1,1,3 | A,A,A,B | 1 | 1.5 | 0,0,0,0 | 0 |
| 5 | 4 | NOT_astro_geo_0221_sep_mars_jupiter_ge140 & NOT_astro_geo_0316_sep_sun_saturn_ge160 & NOT_astro_geo_0906_sep_sun_moon_ge140 & NOT_sports_nfl_sb_loser_franchise_san_francisco_49ers | 1,1,1,3 | A,A,A,B | 1 | 1.5 | 0,0,0,0 | 0 |
| 6 | 4 | NOT_astro_geo_0221_sep_mars_jupiter_ge140 & NOT_astro_geo_0316_sep_sun_saturn_ge160 & astro_geo_0626_sep_moon_mercury_ge020 & NOT_sports_nfl_sb_loser_franchise_san_francisco_49ers | 1,1,1,3 | A,A,A,B | 1 | 1.5 | 0,0,0,0 | 0 |
| 7 | 4 | NOT_astro_geo_0221_sep_mars_jupiter_ge140 & NOT_astro_geo_0326_sep_mercury_saturn_ge160 & NOT_astro_geo_0906_sep_sun_moon_ge140 & NOT_sports_nfl_sb_loser_franchise_san_francisco_49ers | 1,1,1,3 | A,A,A,B | 1 | 1.5 | 0,0,0,0 | 0 |
| 8 | 4 | NOT_astro_geo_0221_sep_mars_jupiter_ge140 & NOT_astro_geo_0326_sep_mercury_saturn_ge160 & astro_geo_0626_sep_moon_mercury_ge020 & NOT_sports_nfl_sb_loser_franchise_san_francisco_49ers | 1,1,1,3 | A,A,A,B | 1 | 1.5 | 0,0,0,0 | 0 |
| 9 | 4 | NOT_astro_geo_0221_sep_mars_jupiter_ge140 & astro_geo_0901_sep_mercury_saturn_ge020 & NOT_astro_geo_0906_sep_sun_moon_ge140 & NOT_sports_nfl_sb_loser_franchise_san_francisco_49ers | 1,1,1,3 | A,A,A,B | 1 | 1.5 | 0,0,0,0 | 0 |
| 10 | 4 | NOT_astro_geo_0221_sep_mars_jupiter_ge140 & astro_geo_0901_sep_mercury_saturn_ge020 & astro_geo_0626_sep_moon_mercury_ge020 & NOT_sports_nfl_sb_loser_franchise_san_francisco_49ers | 1,1,1,3 | A,A,A,B | 1 | 1.5 | 0,0,0,0 | 0 |

**T2: top 10 of 50 by the frozen ranking** (full frontier: `frontier_sensitivity_popvote_T2.csv`, 199 rules)

| rank | k | literals | F | O | min F | mean F | tz flags | # tz |
|---|---|---|---|---|---|---|---|---|
| 1 | 4 | astro_geo_0511_sep_sun_neptune_ge060 & NOT_astro_geo_0116_moon_lon270 & NOT_astro_geo_0411_sep_venus_mars_ge120 & NOT_sports_mlb_ws_loser_franchise_st__louis_cardinals | 1,1,1,3 | A,A,A,B | 1 | 1.5 | 0,0,0,0 | 0 |
| 2 | 4 | astro_geo_0511_sep_sun_neptune_ge060 & NOT_astro_geo_0301_sep_moon_mercury_ge160 & NOT_astro_geo_0411_sep_venus_mars_ge120 & NOT_sports_mlb_ws_loser_franchise_st__louis_cardinals | 1,1,1,3 | A,A,A,B | 1 | 1.5 | 0,0,0,0 | 0 |
| 3 | 4 | astro_geo_0511_sep_sun_neptune_ge060 & NOT_astro_geo_0411_sep_venus_mars_ge120 & NOT_sports_mlb_ws_loser_franchise_st__louis_cardinals & NOT_astro_geo_0101_sep_sun_moon_ge160 | 1,1,3,1 | A,A,B,A | 1 | 1.5 | 0,0,0,0 | 0 |
| 4 | 4 | astro_geo_0521_sep_mercury_neptune_ge040 & NOT_astro_geo_0116_moon_lon270 & NOT_astro_geo_0411_sep_venus_mars_ge120 & NOT_sports_mlb_ws_loser_franchise_st__louis_cardinals | 1,1,1,3 | A,A,A,B | 1 | 1.5 | 0,0,0,0 | 0 |
| 5 | 4 | astro_geo_0521_sep_mercury_neptune_ge040 & NOT_astro_geo_0301_sep_moon_mercury_ge160 & NOT_astro_geo_0411_sep_venus_mars_ge120 & NOT_sports_mlb_ws_loser_franchise_st__louis_cardinals | 1,1,1,3 | A,A,A,B | 1 | 1.5 | 0,0,0,0 | 0 |
| 6 | 4 | astro_geo_0511_sep_sun_neptune_ge060 & NOT_astro_geo_0411_sep_venus_mars_ge120 & NOT_astro_geo_0601_sep_moon_venus_ge160 & NOT_sports_mlb_ws_loser_franchise_st__louis_cardinals | 1,1,1,3 | A,A,B,B | 1 | 1.5 | 0,0,1,0 | 1 |
| 7 | 4 | astro_geo_0511_sep_sun_neptune_ge060 & NOT_astro_geo_0411_sep_venus_mars_ge120 & NOT_sports_mlb_ws_loser_franchise_st__louis_cardinals & NOT_astro_geo_0921_sep_moon_venus_ge160 | 1,1,3,1 | A,A,B,B | 1 | 1.5 | 0,0,0,1 | 1 |
| 8 | 4 | astro_geo_0511_sep_sun_neptune_ge060 & NOT_astro_geo_0411_sep_venus_mars_ge120 & NOT_sports_mlb_ws_loser_franchise_st__louis_cardinals & NOT_astro_geo_1021_sep_moon_venus_ge160 | 1,1,3,1 | A,A,B,B | 1 | 1.5 | 0,0,0,1 | 1 |
| 9 | 4 | sports_mlb_ws_held & astro_geo_0921_sep_mars_jupiter_ge020 & NOT_astro_geo_0401_sep_venus_mars_ge120 & NOT_astro_geo_0601_sep_moon_venus_ge160 | 3,1,1,1 | B,A,A,B | 1 | 1.5 | 0,0,0,1 | 1 |
| 10 | 4 | sports_mlb_ws_held & astro_geo_0921_sep_mars_jupiter_ge020 & NOT_astro_geo_0411_sep_venus_mars_ge120 & NOT_astro_geo_0601_sep_moon_venus_ge160 | 3,1,1,1 | B,A,A,B | 1 | 1.5 | 0,0,0,1 | 1 |

**T3: top 10 of 50 by the frozen ranking** (full frontier: `frontier_sensitivity_popvote_T3.csv`, 3 rules)

| rank | k | literals | F | O | min F | mean F | tz flags | # tz |
|---|---|---|---|---|---|---|---|---|
| 1 | 4 | astro_geo_0221_sep_venus_uranus_ge020 & sports_wimbledon_held & NOT_astro_geo_0721_sep_mercury_jupiter_ge140 & NOT_astro_geo_0701_sep_jupiter_neptune_ge160 | 1,3,1,1 | A,B,A,A | 1 | 1.5 | 0,0,0,0 | 0 |
| 2 | 4 | NOT_astro_geo_0101_sep_mercury_mars_ge120 & NOT_astro_geo_0101_uranus_lon000 & NOT_astro_geo_0821_sep_mercury_saturn_ge160 & astro_geo_0301_sep_jupiter_saturn_ge020 | 1,1,1,1 | A,A,A,A | 1 | 1.0 | 0,0,0,0 | 0 |
| 3 | 4 | NOT_astro_geo_0101_sep_mercury_mars_ge120 & astro_geo_0326_sep_mercury_uranus_ge020 & NOT_astro_geo_0821_sep_mercury_saturn_ge160 & astro_geo_0301_sep_jupiter_saturn_ge020 | 1,1,1,1 | A,A,A,A | 1 | 1.0 | 0,0,0,0 | 0 |

## 3. N3: fit 1900-1980 (21 elections), score 1984-2024 (11 elections)

| target | real label (train) | min k | # training-perfect rules | top-ranked rule, test correct | test correct, all rules (hist) | null perms | null label counts | null perms with a conjunction | null: top-rule test correct >= real top | null: top rule 11/11 |
|---|---|---|---|---|---|---|---|---|---|---|
| T1 | conjB | 2 | 7969 | 6/11 | {'0': 25, '1': 279, '2': 679, '3': 982, '4': 1321, '5': 1240, '6': 2035, '7': 1073, '8': 251, '9': 83, '10': 1} | 2000 | {'conjB': 1723, 'conjA': 277} | 2000 | 996/2000 (0.4980) | 2/2000 |
| T2 | conjB | 3 | 70379 | 6/11 | {'0': 172, '1': 803, '2': 3220, '3': 8217, '4': 15190, '5': 20770, '6': 15051, '7': 6111, '8': 807, '9': 38} | 2000 | {'conjB': 1808, 'conjA': 192} | 2000 | 911/2000 (0.4555) | 0/2000 |
| T3 | conjB | 3 | 36800 | 5/11 | {'1': 23, '2': 1097, '3': 3295, '4': 5950, '5': 8286, '6': 8147, '7': 5989, '8': 3347, '9': 616, '10': 50} | 2000 | {'conjB': 1774, 'conjA': 226} | 2000 | 1442/2000 (0.7210) | 0/2000 |

**T1 null: top-ranked rule test-correct histogram (of 11):** {0: 3, 1: 10, 2: 59, 3: 146, 4: 303, 5: 483, 6: 455, 7: 333, 8: 141, 9: 56, 10: 9, 11: 2}

**T2 null: top-ranked rule test-correct histogram (of 11):** {0: 2, 1: 19, 2: 74, 3: 173, 4: 375, 5: 446, 6: 436, 7: 284, 8: 133, 9: 53, 10: 5}

**T3 null: top-ranked rule test-correct histogram (of 11):** {0: 1, 1: 7, 2: 54, 3: 157, 4: 339, 5: 456, 6: 464, 7: 290, 8: 174, 9: 47, 10: 11}

Outputs: `labels_*.json`, `frontier_*_T*.csv` (every perfect rule), `top50_*_T*.csv`, `n3_rules_T*.csv` (every training-perfect rule with its test score), `n3_null_T*.csv`, `n3_summary.json`.
