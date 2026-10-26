import datetime as dt

import numpy as np
import pandas as pd
from skyfield import almanac
from src.config import election_day, election_years
from src.literals import astro_family as af

YEARS = election_years()


def test_date_grid_frozen():
    g = af.date_grid()
    assert len(g) == 60 and g[0] == (1, 1) and g[-1] == (10, 26)
    assert af.SEP_GRID == [20, 40, 60, 80, 100, 120, 140, 160]


def test_resolves_by_before_election_day_for_every_year_and_date():
    for y in YEARS:
        for m, d in af.date_grid():
            assert dt.date(y, m, d) < election_day(y)
    assert af.check_resolves_by() > 0


def test_de421_covers_every_instant_including_local_midnights_and_2028():
    for md in [(1, 1), (10, 26)]:
        for zone in (None, "US/Eastern", "US/Pacific"):
            lon = af.longitudes(md, zone)
            assert all(len(v) == 32 and np.isfinite(v).all() for v in lon.values())
    # 2028 evaluation (the instant the forecast would use) is inside the kernel
    t = af.ts.utc(2028, 10, 26)
    af.earth.at(t).observe(af.eph["pluto barycenter"]).apparent()
    # beyond documented coverage must fail loudly, not return garbage
    try:
        af.earth.at(af.ts.utc(2060, 1, 1)).observe(af.eph["moon"]).apparent()
        raise AssertionError("expected range error")
    except Exception as e:  # noqa: BLE001
        assert "ephemeris" in type(e).__name__.lower() or "range" in str(e).lower()


def test_longitude_convention_sun_is_zero_at_march_equinox():
    f = almanac.seasons(af.eph)
    for y in (1900, 1960, 2024):
        t, ev = almanac.find_discrete(af.ts.utc(y, 3, 1), af.ts.utc(y, 4, 1), f)
        te = t[list(ev).index(0)]
        _l, lon, _ = af.earth.at(te).observe(af.eph["sun"]).apparent().ecliptic_latlon(epoch="date")
        ang = lon.degrees
        assert min(ang, 360 - ang) < 0.01


def test_built_family_is_consistent_with_files():
    idx = pd.read_csv(af.OUT / "index.csv")
    mat = af.load_matrix()
    assert len(idx) == 28800 and list(mat.columns) == [str(y) for y in YEARS]
    inc = idx[idx.included == 1]
    assert list(mat.index) == list(inc.id)
    s = mat.sum(axis=1)
    assert ((s > 0) & (s < 32)).all()  # no constants
    assert inc.tz_sensitive.sum() > 0 and set(inc.O) <= {"A", "B"}
    assert (inc[inc.tz_sensitive == 1].O == "B").all() and (inc[inc.tz_sensitive == 0].O == "A").all()
