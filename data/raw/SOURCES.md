# Raw sources (retrieved 2026-10-25 via curl; sha256 per file in MANIFEST.csv)

| Source | URL pattern | Used for |
|---|---|---|
| U.S. National Archives, Electoral College Results | https://www.archives.gov/electoral-college/{year} (1896, 1900-2024) | EC winner party and EV count (authoritative for EC) |
| UCSB American Presidency Project, Election Statistics | https://www.presidency.ucsb.edu/statistics/elections/{year} (1896, 1900-2024) | Popular vote; independent cross-check of EC winner party |
| Index pages | https://www.archives.gov/electoral-college/results, https://www.presidency.ucsb.edu/statistics/elections | Link discovery |

Notes:
- Incumbent party for year Y is derived as the EC-winning party of Y-4 (no president changed party in office, 1900-2024).
- 2016: Archives records 304 EV for the winner; UCSB shows 306 (pre-faithless-elector estimate). Winner party agrees. Archives is authoritative.
- Cross-check: EC winner party matches between the two sources in all 33 elections (asserted in src/acquire/outcomes.py).
