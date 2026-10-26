# Event-table spec (Phase 1 data acquisition)

Read CLAUDE.md first (especially Sections 2, 4, 7). Phase 1 only: **no searching for rules, no literal construction, no outcome vectors.** Your job is to produce clean, sourced *event tables*; the literal library is built from them separately.

## Non-negotiable data integrity rules (CLAUDE.md Section 7)
- **Never enter a historical fact from model memory.** Every value comes from a fetched page/file. Download raw files with `curl -sL -A "Mozilla/5.0"` into `data/raw/<family>/`, then parse them offline with a script in `src/acquire/<family>.py`, runnable with `uv run python -m src.acquire.<family>`.
- Write `data/raw/<family>/MANIFEST.csv` with columns `file,url,retrieved,sha256` (retrieved = today's date, ISO).
- If a domain is blocked or a value cannot be sourced, **leave the cell empty, record it in `data/processed/events/<family>_gaps.md`, and say so in your report.** Do not fill from recollection. Cross-check against a second independent source where cheap; record disagreements in the gaps file rather than silently choosing.
- Use `uv run` (a venv exists; pandas, numpy, bs4, lxml, requests, pyyaml, skyfield are installed; do not add dependencies). `uv run ruff check .` must pass on your files.
- Touch only your own files (`src/acquire/<family>*.py`, `data/raw/<family>/`, `data/processed/events/<family>*`). Do not edit CLAUDE.md, config.yaml, tests, or other families' files. **Do not commit or push.**

## Table format
`data/processed/events/<family>.csv`, **exactly one row for each of the 32 election years** (1900, 1904, ..., 2024):
- `year`
- `held` : 1 if the event was held and completed within that calendar year, else 0. Dating is by actual event dates (e.g. an event postponed into the next year is `held=0` for its nominal year and `held=1` for the year it actually occurred).
- `completed_date` : ISO date the event was *completed* (final game / closing day / final round). Fill it even if that date is after Election Day (the literal builder applies the Election Day cutoff). Empty when `held=0`.
- `start_date` where sourced and relevant (else empty)
- family-specific columns (below), empty when `held=0`
- `source_url` : the page(s) the row came from; `notes` : anything odd (cancelled, postponed, split season, disputed, straddles Election Day, etc.)
When an event is not held, `held=0` and every other event field is empty (this is the absence logic in CLAUDE.md C4).

Also write `data/processed/events/<family>_lineage.csv` (`source_name,canonical_name,note`) for every franchise/entity you map (relocations/renames = same franchise per the league's official lineage; cite the source of each mapping), where applicable.

## Report back (<= 250 words)
Rows with `held=1`, any gaps/disagreements, lineage mappings that needed judgment, any event completed on or after Election Day, files written, and anything surprising. State plainly what you verified versus what a source merely says.
