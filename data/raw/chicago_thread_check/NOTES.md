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
