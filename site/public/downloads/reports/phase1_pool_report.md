# Phase 1 pool report (no search run)

- config.yaml sha256: `17350119fff5ee544f343d12b5b9dff20573f6f9ea0a111527c6c32e0b8e0ceb`
- **pool + config hash: `8d3656cdd6c560552bb514ea10f32687508492283a1d64413dbb98f6f0454386`**
- pool files: `literals_era_indicator.yaml`, `literals_main.yaml`, `matrix_era_indicator.csv`, `matrix_main.csv`, `resolves_by_era_indicator.csv`, `resolves_by_main.csv`

## Counts by category (main pool; era indicators excluded)

| category | positive literals | with negations | distinct vectors | era-indicator literals (excluded) |
|---|---|---|---|---|
| calendar | 26 | 52 | 38 | 0 |
| astronomy | 9 | 18 | 16 | 12 |
| sports | 376 | 752 | 210 | 8 |
| weather | 20 | 40 | 36 | 0 |
| **total** | 431 | 862 | 288 | 20 |

Raw literal count vs distinct 32-bit vectors is the honest search-size input (CLAUDE.md Section 5). Distinct vectors are counted over all polarities in the main pool.

## Counts by family (positives)

| family | positive literals |
|---|---|
| easter | 5 |
| election_day_date | 13 |
| indy_500 | 50 |
| jan1_weekday | 7 |
| kentucky_derby | 88 |
| leap_year | 1 |
| lunar_eclipse | 2 |
| masters | 21 |
| mlb_world_series | 36 |
| moon_phase_event | 2 |
| moon_state | 2 |
| nba_finals | 25 |
| nfl_super_bowl | 26 |
| nhl_stanley_cup | 37 |
| planet_motion | 1 |
| season_0 | 2 |
| season_1 | 2 |
| season_2 | 2 |
| season_3 | 2 |
| summer_olympics | 42 |
| triple_crown | 1 |
| wimbledon_mens_singles | 54 |
| wx_USC00190736_jja | 7 |
| wx_USW00094728_jja | 12 |
| wx_USW00094728_snow | 1 |

## Quality grades (positives in main pool)

| familiarity | objectivity | count |
|---|---|---|
| F=1 | O=B | 112 |
| F=2 | O=A | 3 |
| F=2 | O=B | 121 |
| F=3 | O=A | 26 |
| F=3 | O=B | 169 |

Flagged literals (positives): 63; timezone-sensitive (graded O=B): 6.

## Era-indicator literals (reported separately; excluded from the main pool)

Frozen rule: at most two value changes across the 32 elections and every run at least 3 elections long. Negations of these are also era indicators.

| literal | family | true in |
|---|---|---|
| astro_season0_dom20 | season_0 | 29 years (1912-2024) |
| astro_season0_dom21 | season_0 | 1900, 1904, 1908 |
| astro_season1_dom20 | season_1 | 2008, 2012, 2016, 2020, 2024 |
| astro_season1_dom21 | season_1 | 27 years (1900-2004) |
| astro_season2_dom22 | season_2 | 15 years (1968-2024) |
| astro_season2_dom23 | season_2 | 17 years (1900-1964) |
| sports_derby_winner_trainer_ben_jones | kentucky_derby | 1944, 1948, 1952 |
| sports_indy500_winner_car_make_watson_offenhauser | indy_500 | 1956, 1960, 1964 |
| sports_nfl_sb_held | nfl_super_bowl | 15 years (1968-2024) |
| sports_nba_held | nba_finals | 20 years (1948-2024) |

## Exclusions with reasons

| family | what | reason |
|---|---|---|
| astronomy | solar eclipses | Skyfield has no solar-eclipse finder; would need a fetched NASA catalog. Deferred. |
| astronomy | December solstice of the election year | Occurs after Election Day (C1); only the preceding year's solstice is used. |
| weather | USC00190736 snow literals | snow window incomplete in some year |
| weather | USC00305816 NY WORLD TRADE CTR (New York City) | incomplete coverage: JJA TMAX missing/incomplete in 16/32 election years, snow window in 16/32 (no splicing applied) |
| weather | USW00013743 VA WASHINGTON REAGAN NATL AP (Washington DC) | incomplete coverage: JJA TMAX missing/incomplete in 11/32 election years, snow window in 11/32 (no splicing applied) |
| weather | USW00014734 NJ NEWARK LIBERTY INTL AP (New York City (Newark NJ)) | incomplete coverage: JJA TMAX missing/incomplete in 2/32 election years, snow window in 4/32 (no splicing applied) |
| weather | USW00014739 MA BOSTON (Boston) | incomplete coverage: JJA TMAX missing/incomplete in 10/32 election years, snow window in 9/32 (no splicing applied) |
| weather | USW00014819 IL CHICAGO MIDWAY AP (Chicago) | incomplete coverage: JJA TMAX missing/incomplete in 25/32 election years, snow window in 32/32 (no splicing applied) |
| weather | USW00014881 IL FORT DEARBORN (Chicago) | incomplete coverage: JJA TMAX missing/incomplete in 23/32 election years, snow window in 25/32 (no splicing applied) |
| weather | USW00093134 CA LOS ANGELES DOWNTOWN/USC (Los Angeles) | incomplete coverage: JJA TMAX missing/incomplete in 5/32 election years, snow window in 20/32 (no splicing applied) |
| weather | USW00093725 DC WASHINGTON (Washington DC) | incomplete coverage: JJA TMAX missing/incomplete in 15/32 election years, snow window in 17/32 (no splicing applied) |
| weather | USW00094701 MA BOSTON CITY WSO (Boston) | incomplete coverage: JJA TMAX missing/incomplete in 23/32 election years, snow window in 23/32 (no splicing applied) |
| weather | USW00094846 IL CHICAGO OHARE INTL AP (Chicago) | incomplete coverage: JJA TMAX missing/incomplete in 15/32 election years, snow window in 15/32 (no splicing applied) |
| sports | Heisman Trophy | Presented in December, after Election Day: every literal would be constant False. (Reason stated from general knowledge; not verified from a fetched source.) |
| sports | Belmont Stakes / Preakness winner literals | Belmont run date unsourced for 20 of 31 held election years (see triple_crown_gaps.md); completion before Election Day cannot be established from fetched data. Only the computed 'won the Triple Crown' literal is built, True only in a dated year. |
| sports | pre-1936 college-football champions | Disputed; no official dataset cited (CLAUDE.md). |
| other | Academy Awards, Nobel categories | Optional series (CLAUDE.md Section 4.4): not built in Phase 1. |
| markets | Markets/macro series | Off by Open Decision #4. |

Constant literals dropped (15): `astro_lunar_eclipse_any` (True); `astro_moon_new_moon_on_election_day` (False); `astro_moon_first_quarter_moon_on_election_day` (False); `sports_fifa_wc_held` (False); `sports_derby_held` (True); `sports_nba_sweep` (False); `sports_nhl_held` (True); `wx_USC00190736_jja_tmax_mean_ge84` (False); `wx_USC00190736_jja_tmax_max_ge100` (False); `wx_USC00190736_jja_tmax_max_ge102` (False); `wx_USC00190736_jja_n90_ge30` (False); `wx_USC00190736_jja_n100_ge1` (False); `wx_USC00190736_jja_n100_ge2` (False); `wx_USW00094728_jja_tmax_mean_ge78` (True); `wx_USW00094728_snow_ge1p0_by_eve` (False)

## Quarantined (O=C, judgment-dependent; forbidden unless Carson approves)

| literal | statement | true in |
|---|---|---|
| sports_nhl_loser_franchise_brandon_wheat_city | Brandon Wheat City lost the Stanley Cup final in the election year | 1904 |
| sports_nhl_loser_franchise_edmonton_hc | Edmonton HC lost the Stanley Cup final in the election year | 1908 |
| sports_nhl_loser_franchise_halifax_crescents | Halifax Crescents lost the Stanley Cup final in the election year | 1900 |
| sports_nhl_loser_franchise_moncton_victorias | Moncton Victorias lost the Stanley Cup final in the election year | 1912 |
| sports_nhl_went_7 | The Stanley Cup final went 7 games | 1964, 2004, 2024 |
| sports_nhl_games_ge6 | The Stanley Cup final went at least 6 games | 11 years (1940-2024) |
| sports_nhl_sweep | The Stanley Cup final was a sweep | 14 years (1900-1996) |

Cause: Stanley Cup 1900-1912 challenge era. Several challenge series occurred per calendar year; the table uses the last opposed series (agent judgment), and the 1908 final series ended 1908-12-30, after Election Day. Any literal whose value depends on which series counts is graded C.

## Pool structure (no outcomes used)

```
main-pool literals (with negations): 862
distinct vectors: 288; distinct up to complement: 144

Minimum-support (min(#True, 32-#True)) histogram of distinct-up-to-complement vectors, by family (a vector shared by two families counts in each):

                family  category  literals  distinct  distinct/compl  min-support 1  min-support 2  3-4  5-8  9-12  13-16
                easter  calendar        10        10               5              0              0    1    2     1      1
     election_day_date  calendar        26        22              11              0              0    3    4     2      2
              indy_500    sports        98        66              33             28              3    2    0     0      0
          jan1_weekday  calendar        14        14               7              0              0    4    3     0      0
        kentucky_derby    sports       174        74              37             32              5    0    0     0      0
             leap_year  calendar         2         2               1              1              0    0    0     0      0
         lunar_eclipse astronomy         4         4               2              0              0    0    0     2      0
               masters    sports        42        42              21             19              1    0    0     1      0
      mlb_world_series    sports        72        70              35             12              8    8    2     1      4
      moon_phase_event astronomy         4         4               2              1              1    0    0     0      0
            moon_state astronomy         4         4               2              0              0    0    0     0      2
            nba_finals    sports        48        48              24             12              4    2    4     0      2
        nfl_super_bowl    sports        50        38              19             11              6    0    2     0      0
       nhl_stanley_cup    sports        74        68              34             20              9    4    1     0      0
         planet_motion astronomy         2         2               1              0              0    0    1     0      0
              season_3 astronomy         4         2               1              1              0    0    0     0      0
       summer_olympics    sports        84        46              23             18              1    3    1     0      0
          triple_crown    sports         2         2               1              1              0    0    0     0      0
wimbledon_mens_singles    sports       108        62              31             27              3    1    0     0      0
    wx_USC00190736_jja   weather        14        14               7              2              0    0    2     1      2
    wx_USW00094728_jja   weather        24        20              10              0              1    2    4     2      1
   wx_USW00094728_snow   weather         2         2               1              1              0    0    0     0      0

TOTAL: family=ALL (unique)  category=-  literals=862  distinct=288  distinct/compl=144  min-support 1=32  min-support 2=37  3-4=27  5-8=24  9-12=10  13-16=14

Full support histogram of distinct main-pool vectors (all polarities, #True):
1:32 2:37 3:17 4:10 5:7 6:6 7:10 8:1 9:4 11:3 12:3 13:5 14:4 15:5 17:5 18:4 19:5 20:3 21:3 23:4 24:1 25:10 26:6 27:7 28:10 29:17 30:37 31:32

Family x F-grade (positive main-pool literals):

                        F=1  F=2  F=3  total
family                                      
easter                    0    0    5      5
election_day_date         0    0   13     13
indy_500                 23   25    1     49
jan1_weekday              0    0    7      7
kentucky_derby           55   32    0     87
leap_year                 0    0    1      1
lunar_eclipse             0    2    0      2
masters                   0   20    1     21
mlb_world_series          0    1   35     36
moon_phase_event          0    1    1      2
moon_state                0    2    0      2
nba_finals                0    2   22     24
nfl_super_bowl            0    0   25     25
nhl_stanley_cup           0    0   37     37
planet_motion             0    1    0      1
season_3                  0    0    2      2
summer_olympics           0    0   42     42
triple_crown              0    0    1      1
wimbledon_mens_singles   27   26    1     54
wx_USC00190736_jja        7    0    0      7
wx_USW00094728_jja        0   12    0     12
wx_USW00094728_snow       0    0    1      1

Column totals: F=1=112, F=2=124, F=3=195, total=431
```

## NHL 1900-1912 judgment check

Parsed from the fetched challenge-games list (all opposed series in 1900, 1904, 1908, 1912): every year's series were all won by one club (1900 Montreal Shamrocks; 1904 Ottawa HC/Silver Seven; 1908 Montreal Wanderers; 1912 Quebec Bulldogs), so *winner* literals do not depend on which series is called the final. Losers, series length, and sweep do (1904 had four different opponents, 1908 four, 1900 two): the 7 quarantined literals (four `loser` literals: Brandon Wheat City, Edmonton HC, Halifax Crescents, Moncton Victorias; plus the 7-game, 6-game and sweep literals) stay quarantined (O=C). Net change from the first Gate-1 report (10 quarantined): the Shamrocks, Ottawa and Quebec winner literals were re-graded B, `sports_nhl_held` became constant True (dropped as a constant), and `Edmonton HC lost` became non-constant after the winner-date fix and was quarantined. Two corrections made while checking: (1) the fetched Ottawa Senators (original) page says the Ottawa Hockey Club was the Silver Seven 1903-07 and the Senators from 1908, so 'Ottawa Silver Seven' (1904) and 'Ottawa Senators' (1920) are now one franchise (it was wrongly split); (2) the winner's event date is now the latest series completed before Election Day, so the 1908 Wanderers (series ending 1908-03-14, and a Dec 30 series after Election Day) are no longer silently dropped as a constant. No remaining B-graded NHL literal names a club that appears in any 1900-1912 series other than those winner literals (src/verify/nhl_judgment_check.py). Caveat: literals that an alternative selection would create (e.g. 'Montreal Wanderers lost') are simply absent from the pool.

## Chicago threaded record check (report only)

# Chicago threaded record check (report only; nothing spliced, nothing used in the pool)
Retrieved 2026-10-25.
- ACIS StnMeta bbox query around Chicago (stnmeta_bbox.json) lists only the single stations already evaluated
  (Chicago WB City 2 = GHCN USW00014881 Fort Dearborn, Midway, O'Hare, University, etc.); no threaded id appeared.
- ACIS StnData/StnMeta lookups for "CHIthr", "CHIthr 9", "CHIthr 8", "CHICAGO AREA" returned Unknown sId / empty.
- ThreadEx docs (threadex_*.html): public ThreadEx text files are per-calendar-day extremes records
  (ThreadEx_xx_data.txt, ThreadEx_xx_inv.txt), not a daily series; the inventory URL guess returned 404.
- Web search: NWS describes the Chicago thread as CRB 1871-1895 ... O'Hare 1958-present, and ThreadEx as
  general-public, not research-grade, with no homogeneity adjustment.
Verdict: a citable threaded daily Chicago series was NOT fetchable in this session.


## N1 on the frozen pool, before any real search

pool files sha256: `659669db4430315ff375b4035eb6984553fc177dfec2f93d829ba174da8a021a`

| target | perms | P(perfect conj k<=4) | 95% CI | min-k hist | P(perfect keys N<=13) | keys infeasible | keys unknown | median candidates |
|---|---|---|---|---|---|---|---|---|
| T1 | 10000 | 0.0002 | [0.0001, 0.0007] | {4: 2} | 1.0000 | 0 | 0 | 22 |
| T2 | 10000 | 0.0002 | [0.0001, 0.0007] | {4: 2} | 1.0000 | 0 | 0 | 30 |
| T3 | 10000 | 0.0002 | [0.0001, 0.0007] | {3: 1, 4: 1} | 1.0000 | 0 | 0 | 25 |

## Coverage failures and data caveats

- Weather: only NYC Central Park (USW00094728) is complete for the snow window; Central Park and Blue Hill (USC00190736) are complete for Jun-Aug TMAX. Chicago, Washington DC, Los Angeles, Boston Logan, Newark and Battery have no single complete station; nothing was spliced. Blue Hill misses the 1984 snow window by one day.
- Weather: single source (GHCN-D .dly), no second source yet; quality-flagged values treated as missing; 0.1 in tested as >= 2.5 mm (GHCN whole mm), a boundary sensitivity.
- Triple Crown: Belmont dates unsourced for 20 of 31 held years (1900, 1904, 1908, 1916, 1924, 1928, 1936, 1940, 1944, 1952, 1956, 1960, 1964, 1968, 1972, 1976, 1980, 1988, 1992, 1996).
- Olympics: closing dates differ between Wikipedia and Olympedia for 1904, 1908, 1912, 1920; checked that no disagreement changes any before-Election-Day truth value (1904 and 1956 end after Election Day under every source; 1900 ends 28 Oct). 2020 Games are held=0 (held 2021).
- Masters 2020 final round 2020-11-15 (after Election Day), so all 2020 Masters literals are False.
- Single-source dates: Derby, Masters, Wimbledon (Wikipedia infoboxes); Wimbledon completed_date is the tournament end date, a proxy for the final. Indy dates checked against champcarstats except 1916, 1996, 2000, 2004.
- NFL second source is ESPN only (PFR and footballdb returned 403). NBA game dates are Wikipedia-only. NHL 1900-1916 has no independent non-Wikipedia source.
- MLB: 1900 and 1904 have no Series (sources: Wikipedia list, Baseball-Reference index); lineage mappings come from Wikipedia row labels, not an MLB-published page.
- FIFA men's World Cup: every edition year is 2 mod 4, so none falls in an election year; the 'held' literal is constant False and excluded.
- Solar eclipses and the optional series (Academy Awards, Nobel) are not built.
- Everything above is what the sources say or what agents report; none of it is yet human_verified (Phase 4).
