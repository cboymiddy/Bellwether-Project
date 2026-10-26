"""Fetch the JPL DE421 ephemeris (not redistributed here) and check it against the frozen sha256.

The URL and expected hash come from data/raw/astronomy/MANIFEST.csv; the hash must also equal ephemeris_sha256 in freeze.yaml.
Run from the repository root: uv run python scripts/fetch_ephemeris.py
"""

from __future__ import annotations

import csv
import hashlib
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "astronomy"


def main() -> None:
    row = next(csv.DictReader((RAW / "MANIFEST.csv").open()))
    frozen = yaml.safe_load((ROOT / "freeze.yaml").read_text())["ephemeris_sha256"]
    if row["sha256"] != frozen:
        raise SystemExit("manifest hash differs from freeze.yaml: refusing")
    dest = RAW / row["file"]
    if dest.exists() and hashlib.sha256(dest.read_bytes()).hexdigest() == frozen:
        print("already present and matching:", dest)
        return
    with urllib.request.urlopen(row["url"], timeout=120) as r:
        data = r.read()
    got = hashlib.sha256(data).hexdigest()
    if got != frozen:
        raise SystemExit(
            f"downloaded file hash {got} does not match the frozen {frozen}: not saving"
        )
    dest.write_bytes(data)
    print("saved and verified:", dest)


if __name__ == "__main__":
    main()
