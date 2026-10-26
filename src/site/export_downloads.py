"""Download list for the limitations page: derived files and source MANIFESTS only, never raw source pages.

Copies each listed file into site/public/downloads/<group>/ and writes site/src/data/downloads.json with
size and sha256. Refuses any .html page, the ephemeris binary, or any raw-data file other than a manifest.
Run: uv run python -m src.site.export_downloads
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

from src.config import ROOT

PUB = ROOT / "site" / "public" / "downloads"
DATA = ROOT / "site" / "src" / "data"
RS = ROOT / "reports" / "real_search"
EV = ROOT / "data" / "processed" / "events"
LIT = ROOT / "data" / "processed" / "literals"
MAX_TOTAL_BYTES = 20_000_000

GROUPS = {
    "provenance": "Provenance and hashes",
    "outcomes": "Election outcomes",
    "manifests": "Raw-source manifests (URL, retrieval date, sha256; the source pages themselves are not redistributed)",
    "pool": "The pool of facts",
    "events": "Event tables built from the sources (sports and weather), with gaps and lineage notes",
    "search": "The real search: frontiers, labels and N3",
    "verification": "Verification",
    "reports": "Reports",
}


def entries() -> list[tuple[str, Path, str, str]]:
    """(group, source path, destination name, description)."""
    e: list[tuple[str, Path, str, str]] = [
        ("provenance", ROOT / "freeze.yaml", "freeze.yaml", "Hashes of config, pools, astronomy grid, search code, cutoffs and seeds, frozen before the real search"),
        ("outcomes", ROOT / "data/processed/outcomes.csv", "outcomes.csv", "Incumbent party, Electoral College winner and popular-vote winner for 1900-2024"),
        ("outcomes", RS / "outcomes_second_source_check.csv", "outcomes_second_source_check.csv", "Year-by-year comparison of outcomes.csv with a second source"),
        ("manifests", ROOT / "data/raw/MANIFEST.csv", "phase0_MANIFEST.csv", "National Archives and UCSB pages for the outcomes (file and sha256 only; URL patterns are in phase0_SOURCES.md)"),
        ("manifests", ROOT / "data/raw/SOURCES.md", "phase0_SOURCES.md", "URL patterns and retrieval date for the Phase 0 outcome pages"),
        ("pool", LIT / "matrix_main.csv", "matrix_main.csv", "Main pool: 32-year truth values for each literal and its negation"),
        ("pool", LIT / "literals_main.yaml", "literals_main.yaml", "Main pool: one record per literal (definition, grades, sources, flags)"),
        ("pool", LIT / "astro/matrix.csv", "astro_matrix.csv", "Astronomy family: 32-year truth values (positive literals; negations are complements)"),
        ("pool", LIT / "astro/family.yaml", "astro_family.yaml", "Astronomy family: bodies, dates, thresholds, conventions, counts"),
        ("pool", ROOT / "display/year_names.csv", "year_names.csv", "Club names used in each election year (MLB, NFL, NBA, NHL)"),
        ("search", RS / "frontier_primary_ec_T1.csv", "frontier_ec_T1.csv", "All 446 perfect rules for the incumbent party (Electoral College coding), including the flagged Quebec Bulldogs rules"),
        ("search", RS / "frontier_primary_ec_T3.csv", "frontier_ec_T3.csv", "All 126 perfect rules for the Republican Party (Electoral College coding)"),
        ("search", RS / "frontier_sensitivity_popvote_T1.csv", "frontier_popvote_T1.csv", "Perfect rules for the incumbent party under popular-vote coding (sensitivity run)"),
        ("search", RS / "frontier_sensitivity_popvote_T2.csv", "frontier_popvote_T2.csv", "Perfect rules for the Democratic Party under popular-vote coding"),
        ("search", RS / "frontier_sensitivity_popvote_T3.csv", "frontier_popvote_T3.csv", "Perfect rules for the Republican Party under popular-vote coding"),
        ("search", RS / "labels_primary_ec.json", "labels_ec.json", "Result label per target, Electoral College coding (T2 = none)"),
        ("search", RS / "labels_sensitivity_popvote.json", "labels_popvote.json", "Result label per target, popular-vote coding"),
        ("search", RS / "top50_primary_ec_T1.csv", "top50_ec_T1.csv", "Top 50 incumbent-party rules in the frozen ranking's order (ties are alphabetical)"),
        ("search", RS / "n3_summary.json", "n3_summary.json", "N3 look-ahead results: real fit, test scores, shuffled-history comparison"),
        ("search", DATA / "nulls.json", "nulls_summary.json", "Summaries of the shuffled-history runs (per-permutation files are omitted for size; they regenerate from the seeds)"),
        ("verification", RS / "verification_sheet.csv", "verification_sheet_rank8.csv", "Featured rule: every literal, every year, with sources and check status (2 of 128 rows human-checked)"),
        ("verification", RS / "verification_sheet_ranks2-4.csv", "verification_sheet_ranks2-4.csv", "Earlier sheet for tied ranks 2-4 (automated checks only)"),
        ("verification", RS / "human_checks.csv", "human_checks.csv", "The human sign-offs, with who, when and the source"),
        ("verification", RS / "horizons_rank8/horizons_rank8_comparison.csv", "horizons_rank8_comparison.csv", "Skyfield vs JPL Horizons for the three sky conditions, 32 years each"),
        ("verification", RS / "horizons_rank8/MANIFEST.csv", "horizons_rank8_MANIFEST.csv", "sha256 of the saved Horizons responses"),
        ("verification", RS / "HORIZONS_CONVENTION.md", "HORIZONS_CONVENTION.md", "Exact Skyfield conventions and the matching Horizons settings, with the pilot comparison"),
        ("reports", RS / "REPORT.md", "gate2_report.md", "Report of the real search (primary, popular-vote sensitivity, N3)"),
        ("reports", RS / "quebec_bulldogs_writeup.md", "quebec_bulldogs_note.md", "Why one top-ranked rule's club literal was re-graded, and why it still fails the defunct-entity criterion"),
        ("reports", ROOT / "reports/phase1_pool_report.md", "phase1_pool_report.md", "Pool report: counts, exclusions, quarantined literals, coverage failures"),
        ("reports", ROOT / "reports/phase1b_report.md", "phase1b_report.md", "Noise-only power curve, keys null and the tiered procedure proposal"),
        ("reports", ROOT / "reports/phase1c_report.md", "phase1c_report.md", "Whole-procedure shuffled-history results and the freeze"),
    ]
    for p in sorted(EV.glob("*")):
        e.append(("events", p, p.name, f"Event table or notes: {p.stem.replace('_', ' ')}"))
    for d in sorted((ROOT / "data" / "raw").iterdir()):
        if d.is_dir() and (d / "MANIFEST.csv").exists():
            e.append(("manifests", d / "MANIFEST.csv", f"{d.name}_MANIFEST.csv", f"Sources for {d.name.replace('_', ' ')}: file, URL, retrieval date, sha256"))
    return e


PHASE0_URLS = {"archives": "https://www.archives.gov/electoral-college/{y}",
               "ucsb": "https://www.presidency.ucsb.edu/statistics/elections/{y}",
               "www_archives_gov_electoral-college_results.html": "https://www.archives.gov/electoral-college/results",
               "www_presidency_ucsb_edu_statistics_elections.html": "https://www.presidency.ucsb.edu/statistics/elections"}
PHASE0_RETRIEVED = "2026-10-25"  # batch date from the header of data/raw/SOURCES.md; no per-file dates were recorded


def all_sources_manifest() -> str:
    """One CSV over every raw source file: family, file, url, retrieved, sha256, url_basis.

    Phase 0 pages (National Archives, UCSB) were saved with file+sha256 only. Their URLs are rebuilt from the
    patterns in data/raw/SOURCES.md and their date is the batch date in that file's header; url_basis says so.
    """
    import csv
    import io

    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["family", "file", "url", "retrieved", "sha256", "url_basis"])
    raw = ROOT / "data" / "raw"
    with (raw / "MANIFEST.csv").open() as fh:
        for r in csv.DictReader(fh):
            f = r["file"]
            fam, _, leaf = f.partition("/")
            if leaf:
                url = PHASE0_URLS[fam].format(y=leaf.removesuffix(".html"))
            else:
                url = PHASE0_URLS[f]
            w.writerow(["phase0_outcomes", f, url, PHASE0_RETRIEVED, r["sha256"], "reconstructed from the pattern in SOURCES.md; date is the batch date"])
    for d in sorted(raw.iterdir()):
        m = d / "MANIFEST.csv"
        if d.is_dir() and m.exists():
            with m.open() as fh:
                for r in csv.DictReader(fh):
                    w.writerow([d.name, r["file"], r["url"], r["retrieved"], r["sha256"], "recorded at download"])
    return buf.getvalue()


def build_downloads(pub: Path = PUB, data: Path = DATA) -> list[dict]:
    if pub.exists():
        shutil.rmtree(pub)
    out, total = [], 0
    dest = pub / "manifests" / "ALL_SOURCES_MANIFEST.csv"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(all_sources_manifest())
    b = dest.read_bytes()
    total += len(b)
    out.append({"group": "manifests", "group_title": GROUPS["manifests"], "name": dest.name, "path": f"downloads/manifests/{dest.name}",
                "bytes": len(b), "sha256": hashlib.sha256(b).hexdigest(),
                "description": "Every source page behind the data, one row each: URL, retrieval date, sha256. Phase 0 URLs are rebuilt from patterns and carry the batch date (see the url_basis column)",
                "origin": "generated from data/raw/*/MANIFEST.csv and data/raw/SOURCES.md"})
    for group, src, name, desc in entries():
        rel = src.relative_to(ROOT).as_posix()
        if src.suffix in (".html", ".bsp") or (rel.startswith("data/raw/") and src.name not in ("MANIFEST.csv", "SOURCES.md")):
            raise SystemExit(f"refusing to publish {rel}")
        if not src.exists():
            raise SystemExit(f"missing download source: {rel}")
        dest = pub / group / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)
        b = dest.read_bytes()
        total += len(b)
        out.append({"group": group, "group_title": GROUPS[group], "name": name, "path": f"downloads/{group}/{name}",
                    "bytes": len(b), "sha256": hashlib.sha256(b).hexdigest(), "description": desc, "origin": rel})
    if total > MAX_TOTAL_BYTES:
        raise SystemExit(f"downloads total {total} bytes exceeds the budget")
    data.mkdir(parents=True, exist_ok=True)
    (data / "downloads.json").write_text(json.dumps({"groups": GROUPS, "total_bytes": total, "files": out}, indent=1, sort_keys=True) + "\n")
    return out


if __name__ == "__main__":
    base = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    res = build_downloads() if base is None else build_downloads(base / "pub", base / "data")
    print(len(res), "files,", sum(r["bytes"] for r in res), "bytes")
