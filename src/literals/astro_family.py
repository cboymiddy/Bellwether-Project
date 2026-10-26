"""Astronomy geometry family (tier-1b expansion). Computed with Skyfield + JPL DE421; no scraping.

Frozen grid (chosen from the noise-power table, never from real outcomes): 10 bodies, 60 fixed
00:00-UTC instants (days 1,6,11,16,21,26 of Jan..Oct of each election year), 12 thirty-degree
longitude sectors per body, and pairwise separation >= c for c = 20,40,...,160 degrees.
Literals are stored positive-only; each negation is the complement vector (id prefix NOT_).
Deterministic astronomy facts: resolves_by is the instant's own date, always before Election Day.
Run: uv run python -m src.literals.astro_family
"""

from __future__ import annotations

import datetime as dt
import hashlib
import itertools
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import yaml
from skyfield.api import Loader

from src.config import ROOT, election_day, election_years
from src.literals.core import era_indicator_rule

YEARS = election_years()
RAW = ROOT / "data" / "raw" / "astronomy"
OUT = ROOT / "data" / "processed" / "literals" / "astro"
TODAY = "2026-10-25"
MONTHS = list(range(1, 11))
DAYS = [1, 6, 11, 16, 21, 26]
SEP_GRID = list(range(20, 161, 20))
BODIES = {"Sun": "sun", "Moon": "moon", "Mercury": "mercury barycenter", "Venus": "venus barycenter",
          "Mars": "mars barycenter", "Jupiter": "jupiter barycenter", "Saturn": "saturn barycenter",
          "Uranus": "uranus barycenter", "Neptune": "neptune barycenter", "Pluto": "pluto barycenter"}
ZONES = {"US/Eastern": ZoneInfo("America/New_York"), "US/Pacific": ZoneInfo("America/Los_Angeles")}
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct"]
EPH_SHA = hashlib.sha256((RAW / "de421.bsp").read_bytes()).hexdigest()

_load = Loader(str(RAW))
eph, ts = _load("de421.bsp"), _load.timescale()
earth = eph["earth"]


def date_grid() -> list[tuple[int, int]]:
    return [(m, d) for m in MONTHS for d in DAYS]


def _times(md: tuple[int, int], zone: str | None):
    if zone is None:
        return ts.utc(np.array(YEARS), md[0], md[1])
    z = ZONES[zone]
    dts = [dt.datetime(y, md[0], md[1], tzinfo=z) for y in YEARS]  # local midnight
    return ts.from_datetimes(dts)


def longitudes(md: tuple[int, int], zone: str | None = None) -> dict[str, np.ndarray]:
    t = _times(md, zone)
    out = {}
    for name, key in BODIES.items():
        _lat, lon, _ = earth.at(t).observe(eph[key]).apparent().ecliptic_latlon(epoch="date")
        out[name] = lon.degrees % 360
    return out


def separation(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    d = np.abs(a - b) % 360
    return np.where(d > 180, 360 - d, d)


def vectors(md: tuple[int, int], zone: str | None = None):
    """Yield (key, vector) for the date's literals, in a fixed order."""
    lon = longitudes(md, zone)
    for b, v in lon.items():
        for k in range(12):
            yield ("sector", b, "", k * 30), (v >= 30 * k) & (v < 30 * k + 30)
    for a, b in itertools.combinations(BODIES, 2):
        s = separation(lon[a], lon[b])
        for c in SEP_GRID:
            yield ("sep", a, b, c), s >= c


def build() -> dict:
    recs, vecs = [], []
    for md in date_grid():
        utc = list(vectors(md))
        loc = {z: dict(vectors(md, z)) for z in ZONES}
        for (key, v) in utc:
            kind, a, b, p = key
            tz = any((loc[z][key] != v).any() for z in ZONES)
            tag = f"{md[0]:02d}{md[1]:02d}"
            if kind == "sector":
                id_ = f"astro_geo_{tag}_{a.lower()}_lon{p:03d}"
                stmt = (f"On {MON[md[0] - 1]} {md[1]} (00:00 UTC) of the election year, {a}'s ecliptic "
                        f"longitude is in [{p}, {p + 30}) degrees")
            else:
                id_ = f"astro_geo_{tag}_sep_{a.lower()}_{b.lower()}_ge{p:03d}"
                stmt = (f"On {MON[md[0] - 1]} {md[1]} (00:00 UTC) of the election year, the {a}-{b} "
                        f"angular separation is at least {p} degrees")
            recs.append({"id": id_, "statement": stmt, "kind": kind, "body_a": a, "body_b": b,
                         "param": p, "month": md[0], "day": md[1], "F": 1,
                         "O": "B" if tz else "A", "tz_sensitive": int(tz)})
            vecs.append(v)
    M = np.array(vecs, dtype=bool)
    const = M.all(axis=1) | ~M.any(axis=1)
    era = np.array([era_indicator_rule(r) for r in M])
    idx = pd.DataFrame(recs)
    idx["constant"] = const.astype(int)
    idx["era_indicator"] = era.astype(int)
    idx["included"] = (~const & ~era).astype(int)
    classes: dict[bytes, int] = {}
    idx["equiv_class"] = [classes.setdefault(r.tobytes(), len(classes)) for r in M]
    return {"index": idx, "matrix": M}


def write(res: dict) -> dict[str, str]:
    OUT.mkdir(parents=True, exist_ok=True)
    idx, M = res["index"], res["matrix"]
    idx.to_csv(OUT / "index.csv", index=False)
    inc = idx.included.to_numpy(bool)
    mat = pd.DataFrame(M[inc].astype(int), columns=YEARS)
    mat.insert(0, "id", idx.id[inc].to_numpy())
    mat.to_csv(OUT / "matrix.csv", index=False)
    fam = {
        "family": "astro_geometry", "category": "astronomy", "polarity_storage": "positives only; "
        "negation = complement vector, id prefix NOT_", "F": 1, "O": "A, or B when tz_sensitive",
        "definition": "Geocentric apparent ecliptic longitude (true equinox of date) of ten bodies "
        "at 00:00 UTC on frozen dates; sector literals and pairwise separation thresholds.",
        "bodies": list(BODIES), "months": MONTHS, "days": DAYS, "sep_grid_deg": SEP_GRID,
        "sector_width_deg": 30, "instant": "00:00 UTC",
        "tz_sensitivity": "flag set when the value changes at US/Eastern or US/Pacific local "
        "midnight of the same date (zoneinfo, historical offsets) in any election year",
        "resolves_by": "date of the instant (month/day of the election year); all <= Oct 26",
        "source_url": "https://ssd.jpl.nasa.gov/ftp/eph/planets/bsp/de421.bsp",
        "dataset_citation": f"JPL DE421 (sha256 {EPH_SHA}) via Skyfield",
        "retrieval_date": TODAY, "status": "auto", "era_indicator_rule": "src/literals/core.py",
        "counts": {"positives_built": len(idx), "constant": int(idx.constant.sum()),
                   "era_indicator": int(idx.era_indicator.sum()),
                   "included_positives": int(inc.sum())},
    }
    (OUT / "family.yaml").write_text(yaml.safe_dump(fam, sort_keys=False, width=100))
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(OUT.glob("*.*"))}


def load_matrix() -> pd.DataFrame:
    return pd.read_csv(OUT / "matrix.csv").set_index("id")


def check_resolves_by() -> int:
    """Every included literal's per-year resolves_by (instant date) precedes Election Day."""
    idx = pd.read_csv(OUT / "index.csv")
    idx = idx[idx.included == 1]
    n = 0
    for y in YEARS:
        ed = election_day(y)
        for md in date_grid():
            assert dt.date(y, md[0], md[1]) < ed
            n += 1
    return n * len(idx)


if __name__ == "__main__":
    res = build()
    hashes = write(res)
    idx = res["index"]
    print(idx[["constant", "era_indicator", "included", "tz_sensitive"]].sum().to_dict())
    print("positives", len(idx), "distinct (positive vectors)", len({r.tobytes() for r in res["matrix"]}))
    print(hashes)
