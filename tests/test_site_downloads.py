import hashlib
import json

import pytest
from src.config import ROOT
from src.site.export_downloads import GROUPS, MAX_TOTAL_BYTES, build_downloads
from tests.privacy import private_strings


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    d = tmp_path_factory.mktemp("dl")
    files = build_downloads(d / "pub", d / "data")
    return d, files


def test_files_exist_with_matching_hashes_and_groups(built):
    d, files = built
    assert len(files) > 40
    for f in files:
        p = d / "pub" / f["group"] / f["name"]
        assert hashlib.sha256(p.read_bytes()).hexdigest() == f["sha256"] and p.stat().st_size == f["bytes"]
        assert f["group"] in GROUPS and f["description"]
    j = json.loads((d / "data" / "downloads.json").read_text())
    assert j["total_bytes"] == sum(f["bytes"] for f in files) < MAX_TOTAL_BYTES


def test_no_raw_pages_only_manifests(built):
    d, files = built
    assert not [f for f in files if f["name"].endswith((".html", ".bsp"))]
    raw = [f for f in files if f["origin"].startswith("data/raw/")]
    assert raw and all(f["name"].endswith(("MANIFEST.csv", "SOURCES.md")) for f in raw)
    assert not list((d / "pub").rglob("*.html"))


def test_key_files_present_and_match_sources(built):
    _, files = built
    by = {f["name"]: f for f in files}
    for must in ("freeze.yaml", "frontier_ec_T1.csv", "frontier_ec_T3.csv", "verification_sheet_rank8.csv", "human_checks.csv",
                 "nhl_stanley_cup_MANIFEST.csv", "mlb_world_series_MANIFEST.csv", "phase0_MANIFEST.csv"):
        assert must in by, must
    assert by["freeze.yaml"]["sha256"] == hashlib.sha256((ROOT / "freeze.yaml").read_bytes()).hexdigest()


def test_combined_source_manifest_has_url_date_hash(built):
    import csv

    d, files = built
    rows = list(csv.DictReader((d / "pub" / "manifests" / "ALL_SOURCES_MANIFEST.csv").open()))
    assert len(rows) > 500
    for r in rows:
        assert r["url"].startswith(("https://", "http://")) and r["retrieved"] and len(r["sha256"]) == 64 and r["url_basis"]
    p0 = [r for r in rows if r["family"] == "phase0_outcomes"]
    assert len(p0) == 68 and all("reconstructed" in r["url_basis"] for r in p0)
    assert any(f["name"] == "ALL_SOURCES_MANIFEST.csv" for f in files)


def test_downloads_have_no_local_paths_or_contact_details(built):
    d, _ = built
    for p in (d / "pub").rglob("*"):
        if p.is_file():
            t = p.read_text(errors="ignore")
            for bad in private_strings():
                assert bad.lower() not in t.lower(), (p.name, "private string")
