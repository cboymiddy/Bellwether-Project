# Data sources, and what is known about their terms

This is a record, not legal advice.

**What the data licence covers.** The CC BY-SA 4.0 licence (`LICENSE-DATA`) covers only the project's own compilation (selection,
arrangement, coding, grading), its computed values (astronomy, literal vectors, search and null results, rankings) and its own
wording. It does **not** cover third-party content: anything from the sources below that a file quotes, reproduces or derives from.
That content remains under its owner's terms. For most sources below, **their terms have not been reviewed**.

Raw source pages are not in this repository: only manifests (URL, retrieval date, sha256) are. The combined manifest is
`data/raw/MANIFEST_with_urls.csv`; the per-family manifests are `data/raw/<family>/MANIFEST.csv`.

Counts are rows in the combined manifest (one per saved page).

| Source | Pages | Used for | What is known about its terms |
|---|---:|---|---|
| en.wikipedia.org | 307 | Event lists for every sports family; second source for election outcomes | Text is CC BY-SA 4.0. Attribution here is by page URL and retrieval date; revision ids were not recorded. |
| www.archives.gov (National Archives) | 34 | Electoral College results | US government work; generally public domain. |
| www.ncei.noaa.gov (NOAA NCEI) | 15 | Daily weather (GHCN-Daily) | US government data; generally public domain. |
| ssd.jpl.nasa.gov (JPL) | 1 | DE421 ephemeris (the binary is not redistributed) | US government (NASA/JPL); terms not checked here. |
| www.presidency.ucsb.edu (UCSB American Presidency Project) | 34 | Popular vote; cross-check of Electoral College winners | Terms not reviewed. Only winner party and vote counts are used. |
| www.baseball-reference.com | 31 | MLB World Series | Sports Reference has its own terms of use; not reviewed. |
| www.hockey-reference.com | 27 | Stanley Cup | Same family of terms as above; not reviewed. |
| www.basketball-reference.com | 21 | NBA Finals | Same family of terms as above; not reviewed. |
| www.olympedia.org | 33 | Summer Olympics hosts and dates | Not reviewed. |
| www.rsssf.org | 24 | FIFA World Cup | Not reviewed. |
| www.champcarstats.com, indianapolismotorspeedway.com, indymotorspeedway.com | 30 | Indianapolis 500 | Not reviewed. |
| www.espn.com | 3 | Super Bowl, Kentucky Derby and Masters checks | Not reviewed. Only winners, dates and scores are used. |
| www.kentuckyderby.com, thefreepps.com, www.nyra.com, www.horseracingnation.com | 6 | Kentucky Derby and Triple Crown | Not reviewed. |
| www.golfchannel.com, www.nbcsports.com | 2 | Masters | Not reviewed. |
| www.topendsports.com | 1 | Wimbledon | Not reviewed. |
| threadex.rcc-acis.org, data.rcc-acis.org | 3 | A Chicago station-record check (not part of the pool) | Not reviewed. |

## Flags, mainly for Wikipedia-derived data

1. **Facts versus expression.** Winners, dates and scores are facts, which copyright does not protect, but a table's selection and
   arrangement can be. Licensing our tables CC BY-SA 4.0 is consistent with the ShareAlike term of the Wikipedia text they draw on.
2. **Attribution is thinner than ideal.** The manifest gives the page URL and the retrieval date. It does not give the revision
   (`oldid`) or an author list; a permalink per page would be better.
3. **Free text was audited, with limits.** Every free-text cell in the published CSV, Markdown, YAML and JSON files was compared with the saved
   source pages, looking for runs of 7 or more identical words (and 5 or more in short note cells). It found 13 Olympic notes that quoted
   Wikipedia introductions, and about 20 shorter cells and lines that repeated a source phrase; all were rewritten in the project's own words
   (`scripts/paraphrase_notes.py`, which changes only note text, never a value). What remains: URLs, table-row fragments quoted as
   evidence in the `*_lineage.csv` notes (names and counts), score lines such as "New York Giants 17, New England 14", and a few generic
   phrases (for example, that Games were cancelled because of a world war). The scan cannot see close paraphrase, copying from pages
   that were not saved, or short phrases, so it lowers the risk and does not remove it.
4. **Mixed-source tables.** Some event tables combine Wikipedia with a second source from the list above. If one of those sources
   restricts redistribution of its data, the CC BY-SA label overstates what can be reused for that table. Each table's `source`
   column and its family manifest say where the values came from.
5. **No raw pages.** Nothing here redistributes a source page. To check a value, fetch the URL from the manifest and compare the
   sha256 (a page may have changed since retrieval on 2026-10-25).
