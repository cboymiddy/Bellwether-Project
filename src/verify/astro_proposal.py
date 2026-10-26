"""SCRATCH feasibility check for a PROPOSED astronomy family. Builds nothing into the pool.

Series per fixed pre-election date (00:00 UTC): geocentric apparent ecliptic longitude of 7 bodies
(Sun, Moon, Mercury..Saturn) and pairwise angular separations. Literals: 12 thirty-degree sectors per
longitude; "separation >= c" for c in 30,60,90,120,150 per pair (negations come with the pool).
Reports vector counts, a DE421 range check, tz-sensitivity counts, and noise-only power by N1.
Run: uv run python -m src.verify.astro_proposal
"""

from __future__ import annotations

import datetime as dt
import itertools

import numpy as np
from skyfield.api import Loader
from skyfield.errors import EphemerisRangeError

from src.config import ROOT, election_day, election_years
from src.nulls.n1 import SEED_INDEX, TARGET_COUNTS, load_config, load_pool
from src.nulls.search_core import conj_exists

YEARS = election_years()
BODIES = {"Sun": "sun", "Moon": "moon", "Mercury": "mercury barycenter", "Venus": "venus barycenter",
          "Mars": "mars barycenter", "Jupiter": "jupiter barycenter", "Saturn": "saturn barycenter"}
SEP_GRID = [30, 60, 90, 120, 150]
load = Loader(str(ROOT / "data" / "raw" / "astronomy"))
eph, ts = load("de421.bsp"), load.timescale()
earth = eph["earth"]


def dates(days: list[int]) -> list[tuple[int, int]]:
    return [(m, d) for m in range(1, 11) for d in days]


EXTRA = {"Uranus": "uranus barycenter", "Neptune": "neptune barycenter",
         "Pluto": "pluto barycenter"}


def longitudes(md: tuple[int, int], shift_hours: float = 0.0,
               bodies: dict | None = None) -> dict[str, np.ndarray]:
    t = ts.utc(np.array(YEARS), md[0], md[1], shift_hours)
    out = {}
    for name, key in (bodies or BODIES).items():
        _lat, lon, _ = earth.at(t).observe(eph[key]).apparent().ecliptic_latlon()
        out[name] = lon.degrees % 360
    return out


def sep(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    d = np.abs(a - b) % 360
    return np.where(d > 180, 360 - d, d)


def family(days: list[int], shift: float = 0.0, bodies: dict | None = None,
           grid: list[int] | None = None) -> tuple[np.ndarray, list[str]]:
    rows, names = [], []
    bodies = bodies or BODIES
    grid = grid or SEP_GRID
    for md in dates(days):
        lon = longitudes(md, shift, bodies)
        for b, v in lon.items():
            for k in range(12):
                rows.append((v >= 30 * k) & (v < 30 * k + 30))
                names.append(f"{md[0]:02d}-{md[1]:02d} {b} in sector {k}")
        for a, b in itertools.combinations(bodies, 2):
            s = sep(lon[a], lon[b])
            for c in grid:
                rows.append(s >= c)
                names.append(f"{md[0]:02d}-{md[1]:02d} sep({a},{b})>={c}")
    return np.array(rows), names


def _ok(y: int, m: int, d: int) -> bool:
    try:
        earth.at(ts.utc(y, m, d)).observe(eph["moon"]).apparent()
        return True
    except EphemerisRangeError:
        return False


def range_check() -> str:
    """Probe kernel coverage at the edges rather than trusting the documented 1899-2053 range."""
    need = [(1900, 1, 1), (1900, 11, 1), (2024, 10, 31), (2028, 10, 31)]
    edges = {"1899-07-27": _ok(1899, 7, 27), "1899-08-02": _ok(1899, 8, 2),
             "2053-10-07": _ok(2053, 10, 7), "2053-10-14": _ok(2053, 10, 14)}
    return (f"DE421 probes {edges}; needed dates all evaluable: "
            f"{all(_ok(*d) for d in need)}")


def main() -> None:
    print(range_check())
    lat_ok = all(dt.date(y, 10, 31) < election_day(y) for y in YEARS)
    print("latest fixed date (Oct 31) precedes Election Day in all 32 years:", lat_ok)
    base = load_pool()
    seed = load_config()["seed"]
    for label, days in [("D=10 (1st)", [1]), ("D=20 (1st,15th)", [1, 15]),
                        ("D=40 (1,8,15,22)", [1, 8, 15, 22]), ("D=60 (every 5d)", [1, 6, 11, 16, 21, 26])]:
        A, _ = family(days)
        full = np.concatenate([A, ~A])  # both polarities, as in the pool
        sup = full.sum(axis=1)
        distinct = np.unique(full, axis=0)
        useful = int(((sup >= 14) & (sup <= 31)).sum())
        # tz sensitivity: shift the instant by +/- 8h; flag series whose literal value changes
        A5, _ = family(days, shift=-5)
        A8, _ = family(days, shift=8)
        flagged = int(((A != A5).any(axis=1) | (A != A8).any(axis=1)).sum())
        V = np.concatenate([base, full])
        res = []
        for tname in ("T1", "T2", "T3"):
            rng = np.random.default_rng(np.random.SeedSequence(seed).spawn(4)[SEED_INDEX[tname]])
            hits = 0
            B = 3000
            for _ in range(B):
                t = np.zeros(32, dtype=bool)
                t[rng.choice(32, TARGET_COUNTS[tname], replace=False)] = True
                hits += conj_exists(V, t)["found"]
            res.append(f"{tname}={hits / B:.3f}")
        print(f"{label}: positives={len(A)} with-neg={len(full)} distinct={len(distinct)} "
              f"up-to-complement~{len(distinct) // 2} tz-flagged-positives={flagged} "
              f"candidate-useful-vectors(support 14-31 of 32)={useful} | N1 power (B=3000): "
              + ", ".join(res))





def variants() -> None:
    """Size search: which scratch family reaches ~90% N1 power (T1 only, B=2000)."""
    base = load_pool()
    seed = load_config()["seed"]
    ten = {**BODIES, **EXTRA}
    g15 = list(range(15, 166, 15))
    d100 = [1, 4, 7, 10, 13, 16, 19, 22, 25, 28]
    d60 = [1, 6, 11, 16, 21, 26]
    for label, kw in [("7 bodies, D=100, sep step 30", {"days": d100}),
                      ("10 bodies, D=60, sep step 30", {"days": d60, "bodies": ten}),
                      ("10 bodies, D=60, sep step 15", {"days": d60, "bodies": ten, "grid": g15}),
                      ("10 bodies, D=100, sep step 15", {"days": d100, "bodies": ten, "grid": g15})]:
        A, _ = family(kw["days"], bodies=kw.get("bodies"), grid=kw.get("grid"))
        full = np.concatenate([A, ~A])
        V = np.concatenate([base, full])
        rng = np.random.default_rng(np.random.SeedSequence(seed).spawn(4)[SEED_INDEX["T1"]])
        hits, B = 0, 2000
        for _ in range(B):
            t = np.zeros(32, dtype=bool)
            t[rng.choice(32, TARGET_COUNTS["T1"], replace=False)] = True
            hits += conj_exists(V, t)["found"]
        print(f"{label}: positives={len(A)} distinct(with neg)={len(np.unique(full, axis=0))} "
              f"N1 T1 power={hits / B:.3f}")


if __name__ == "__main__":
    import sys

    if "variants" in sys.argv:
        variants()
    else:
        main()
