# Provenance

This repository is a **fresh, single-commit copy** of a local working repository. The local history is not published: it
carried raw source pages and a personal email address. Verifiability does not depend on it: the file hashes in `freeze.yaml`
cover the configuration, literal pool, astronomy grid, search and solver code, cutoffs and seeds, and they can be recomputed here.

## The local commits this tree replaces

They were made on one day, 2026-10-25, in this order. `Spec` marks the commits that changed `CLAUDE.md`.

| Commit | Date | Spec | Subject |
|---|---|---|---|
| `19760c0` | 2026-10-25 | yes | Add project spec |
| `d73cdb2` | 2026-10-25 | yes | Phase 0: scaffold, config, verified outcomes, CLAUDE.md corrections |
| `7d5b44c` | 2026-10-25 | yes | Phase 1/1b: literal library, astronomy family, tiered procedure, noise-only nulls |
| `104520c` | 2026-10-25 |  | Freeze: hashes of config, pools, astronomy grid, search/solver code, cutoffs |
| `2f3166e` | 2026-10-25 |  | Gate-2 runner (unfrozen orchestrator over frozen functions), N3, whole-procedure null results |
| `968c64a` | 2026-10-25 |  | Gate 2 results and Phase 4 prep: real search outputs, rank-8 checks, display layer |
| `9e137bd` | 2026-10-25 |  | Site step 1: exporter with hash gate, rule-card data, and tests |
| `33aeebf` | 2026-10-25 |  | Site step 2: Astro project and the rule card page |
| `7ef07b3` | 2026-10-25 |  | Site step 3: home page, site name, and history strip |
| `eb4bdbe` | 2026-10-25 |  | Site step 4: /how/ page with null figures, data tables, and the popular-vote exhibit |
| `2da7b62` | 2026-10-25 |  | Fix stale quarantine count in the Phase 1 report text (6 -> 7, with the net change from 10) |
| `e4a469c` | 2026-10-25 |  | Site step 5: shuffle demo with TypeScript search port and Python/TS parity tests |
| `0dcd8cf` | 2026-10-25 |  | Site step 6: N3 look-ahead exhibit with best-constant-guess baselines and top-20 rule tables |
| `106e20a` | 2026-10-25 |  | Site step 7: human check record, downloads list with source manifest, limitations page |
| `3c58041` | 2026-10-25 |  | Site step 8: 2028 reading in the same frame as its disclaimer |
| `9ff77ed` | 2026-10-25 |  | Release prep: base path build setting, licences, public-export script, privacy tests |
| `06b73f5` | 2026-10-25 |  | Release prep 2: paraphrase copied third-party text, provenance checks, licence scope |
| `e61c1e9` | 2026-10-25 |  | Export builds from tracked files only |
| `45f3106` | 2026-10-25 |  | Format paraphrase script |
| `087cb89` | 2026-10-25 |  | Provenance wording |
| `ab9d74a` | 2026-10-25 |  | Pages workflow: Node 26 via .nvmrc, engines field, newer action majors |

The published tree is the content of the last commit above (`ab9d74a`) with these changes made at export: the 68 raw source pages
and the ephemeris binary are absent, one large report file (`reports/real_search/n3_rules_T2.csv`) is gzipped, working files are excluded
(a profiling script, review notes), and the release files are added (README, licences, data-source notes, the Pages workflow, this note,
and `data/raw/MANIFEST_with_urls.csv`). The export script checks that the 24 files covered by `freeze.yaml` are identical to their
state at the freeze commit.

## The spec was amended during the project

`CLAUDE.md` is the spec and working agreement. It was **not** fixed in advance. It changed in the commits marked `Spec` above, all
before the freeze (`104520c`). The version at the freeze commit is byte-identical to the version in this tree (the export
script checks this and refuses to build otherwise). What changed, from the commit diffs:

- First amendment (`Phase 0` commit): the Electoral College coding was recorded as confirmed; the popular-vote split was corrected from 19/13 to
  20/12 (2000 and 2016 both flip); the reasoning for leaving T4 ("incumbent loses") off was added; the rule that an incomplete event is False
  and the era-indicator rule were added; the exact count of distinct circular shifts for the structured null (N2) was added; and a freeze
  rule (hash the pool and `config.yaml` before the real search) was added.
- Second amendment (`Phase 1/1b` commit): the conjunction-then-optional-keys procedure was replaced by the tiered procedure (tier 1a on the
  main pool, tier 1b adding the astronomy family, tier 2 keys with frozen caps N* = 4 and m* = 2); the whole-procedure definitions of the
  nulls (N1, N1-party, N2) were written; the timezone tie-break and the search-size disclosure were added; and the one-shot rule for the real search.

No amendment was made after the freeze, and none of the frozen files changed after it. What was left unfrozen is listed on the site's
limitations page (the Gate-2 runner and the N3 shortcut).

## The freeze

- Freeze commit (local): `104520c`
- Freeze hash: `475aba0811048404051d238c3ccdcb368f9e8e075b992e50738b604363965c1a`
- To check: run the one-line freeze check in `README.md`; it must print `True`.

## What is omitted

- Raw source pages and the ephemeris binary. Manifests with URL, retrieval date and sha256 are in `data/raw/`; the combined file is
  `data/raw/MANIFEST_with_urls.csv`. The 68 pages for the election outcomes (National Archives and UCSB) were saved with file name and
  sha256 only, so their URLs there are rebuilt from the URL patterns in `data/raw/SOURCES.md` and carry the batch date 2026-10-25.
  The ephemeris is fetched by `scripts/fetch_ephemeris.py` and checked against the frozen hash.
- The local commit history (above).
- Working notes and the Gate 5 review package.
