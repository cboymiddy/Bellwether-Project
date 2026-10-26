# Write-up note: `NOT_sports_nhl_winner_franchise_quebec_bulldogs` (T1 EC rank 1) grading

**Question.** Why is it graded O=B, F=3 when the first Phase 1 report quarantined it as O=C, and does it pass C2.3?

**Timeline.**
1. First Gate-1 pool report: `sports_nhl_winner_franchise_quebec_bulldogs` was quarantined (O=C). The rule I had applied graded any NHL literal that was true in a 1900-1912 "challenge-era" year as C, because several challenge series were played per calendar year and I had picked the last opposed one.
2. When asked to check the dependence, I parsed the fetched challenge-games list (`data/raw/nhl_stanley_cup/wiki_list_of_stanley_cup_challenge_games.html`). In each of 1900, 1904, 1908 and 1912 every opposed series was won by the same club (1912: Quebec Bulldogs beat Moncton Victorias 9-3 and 8-0 on March 11 and 13; the March 5 entry had no opponent). The *winner* therefore does not depend on which series is called the final, and 1912-03-13 is before Election Day (1912-11-05). Losers, series length and sweep do depend on the selection, and those literals stay quarantined.
3. I changed the code before the pool was frozen and before any outcome vector was scored (`patch_nhl` plus `robust_cols={"winner_franchise"}` in `src/literals/sports.py`): winner literals are graded B and keep the `challenge_era_judgment` flag. This is recorded in the "NHL 1900-1912 judgment check" section of `reports/phase1_pool_report.md` and in `src/verify/nhl_judgment_check.py`.

**Caveats that belong in the write-up.**
- F=3 was assigned at the event level (the Stanley Cup final is F=3), not per club, so obscure and defunct clubs inherited F=3. That overstates familiarity for this literal.
- **C2.3 (no dependence on a defunct entity or name): it fails.** The Quebec Bulldogs have no current NHL franchise (the lineage file says so). I did not build an automated C2.3 gate in Phase 1; the pool contains 11 positive literals naming a defunct entity or name (8 NHL clubs counting the original Ottawa Senators, Baltimore Bullets (original), the Soviet Union, West Germany). In the saved frontiers only 3 of 446 T1 EC rules contain one (all via Quebec Bulldogs); none appear in T3 EC or in the popular-vote frontiers.
- Ranks 1-22 of the T1 EC frontier tie on every frozen criterion (min F 1, mean F 1.5, k 4, no tz-sensitive literal). Their order is a string tie-break on literal ids, so rank 1 carries no meaning beyond that.

**Rank 8** (Mercury-Venus Oct 21; NOT Mars-Jupiter Jan 21; NOT Steelers Super Bowl; NOT Mercury-Pluto Jul 1) uses no defunct entity and no Moon literal.
