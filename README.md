# The Great Presidential Bellwether (Bellwether Project)

**This is a satire of how easy it is to find a perfect-fit rule by chance. Nothing here predicts anything.**

A rule built from four facts (three about the sky, one about football) gets all 32 U.S. presidential elections from 1900 to 2024
right. The same search, run on histories whose winners have been shuffled, finds a perfect rule in about 98% of them. The site
shows the rule, how it was found, that control, a look-ahead test, and what the rule says for 2028, each with its caveats.

Site: built from `site/` (Astro, static). Start with the home page, then "Limitations and downloads".

## What is in here

| Path | What |
|---|---|
| `CLAUDE.md` | The project spec and working agreement. It was amended during the project; see `PROVENANCE.md`. |
| `config.yaml`, `freeze.yaml` | Locked configuration, and the hashes that froze the pool, the astronomy grid, the search code, the cutoffs and the seeds before the real search ran |
| `src/` | Literal construction, search, nulls, verification, exporters |
| `data/` | Processed event tables and the literal pool; raw sources as manifests only |
| `reports/` | Reports, the real-search outputs, the null-run results |
| `site/` | The website (data it shows is exported into `site/src/data/`) |
| `PROVENANCE.md` | Where this tree came from, and the dated local commits it replaces |
| `DATA_SOURCES.md` | Sources and what is known about their terms |

## Reproduce

```bash
uv sync
uv run python scripts/fetch_ephemeris.py   # downloads JPL DE421 and checks it against the frozen sha256 (needed before anything imports the pool)
uv run pytest
uv run python -c "import yaml; from src.nulls.freeze import build; fz = yaml.safe_load(open('freeze.yaml')); print(build(fz['null_plan'])['freeze_sha256'] == fz['freeze_sha256'])"   # True if the frozen files are unchanged
uv run python -m src.site.export          # rebuild the data behind the pages (refuses if hashes differ)
cd site && npm ci && npx vitest run && npm run build   # Node >= 26 (see .nvmrc); Astro itself needs >= 22.23.4
```

Raw source pages and the ephemeris binary are not included. The ephemeris is needed by the code that builds and checks the pool
(`scripts/fetch_ephemeris.py` fetches it and refuses a file whose hash differs from `freeze.yaml`). The tests do not need the raw source
pages; the five skipped tests are Phase 0 placeholders. The manifests (`data/raw/MANIFEST_with_urls.csv`) give each source URL and
sha256 so any page can be fetched again and compared. Do not run `python -m src.nulls.freeze` directly: it rewrites `freeze.yaml`.

## Base path

The site's base path is a build setting. For a GitHub Pages project site:

```bash
SITE_BASE=/Bellwether-Project/ SITE_URL=https://<owner>.github.io npm run build
```

## Honest status

- One rule was chosen by the author after seeing the results, from among 22 rules tied at the top of the frozen ranking.
- Human verification covers 2 of 128 rows of the featured rule's sheet, and used the same source as the automated check.
- Site copy is marked as draft until approved.

## Licences

Code: MIT (`LICENSE`). Data files, reports and written text: CC BY-SA 4.0 (`LICENSE-DATA`), covering **only the project's own compilation,
computed values and wording, not third-party content**; the sources and what is known about their terms are in `DATA_SOURCES.md`.
