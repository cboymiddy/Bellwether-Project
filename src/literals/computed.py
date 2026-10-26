"""Computed literals: calendar and astronomy. No scraping; everything derives from rules or DE421.

Deterministic facts about the calendar or about Election Day itself resolve on Jan 1 of the
election year (knowable years ahead; CLAUDE.md C1). Astronomical events carry their own date.
"""

from __future__ import annotations

import datetime as dt
import hashlib
from zoneinfo import ZoneInfo

import numpy as np
from skyfield import almanac, eclipselib
from skyfield.api import Loader

from src.config import ROOT, election_day
from src.literals.core import YEARS, Literal, Pool, cutoff

TODAY = "2026-10-25"
RAW_ASTRO = ROOT / "data" / "raw" / "astronomy"
EPH_URL = "https://ssd.jpl.nasa.gov/ftp/eph/planets/bsp/de421.bsp"
EPH_SHA = hashlib.sha256((RAW_ASTRO / "de421.bsp").read_bytes()).hexdigest()
CITE_ASTRO = f"JPL DE421 ephemeris (sha256 {EPH_SHA[:12]}...) via Skyfield; times in UTC"
ZONES = {"US/Eastern": ZoneInfo("America/New_York"), "US/Pacific": ZoneInfo("America/Los_Angeles")}
MONTH = {3: "March", 4: "April", 6: "June", 9: "September", 12: "December", 11: "November"}


def _mk(pool, id_, statement, category, family, definition, values, resolves, F, O,
        src="computed", cite="Computed from calendar rules", flags=None):
    pool.add(Literal(
        id=id_, statement=statement, category=category, family=family, definition=definition,
        source_url=src, dataset_citation=cite, retrieval_date=TODAY, F=F, O=O,
        values=[bool(v) for v in values], resolves_by=resolves, flags=flags or [],
    ))


def _jan1(y: int) -> dt.date:
    return dt.date(y, 1, 1)


def easter(y: int) -> dt.date:
    """Gregorian Easter (Meeus/Jones/Butcher algorithm)."""
    a, b, c = y % 19, y // 100, y % 100
    d, e = b // 4, b % 4
    g = (b - (b + 8) // 25 + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    el = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * el) // 451
    mo, da = divmod(h + el - 7 * m + 114, 31)
    return dt.date(y, mo, da + 1)


def _calendar(pool: Pool) -> None:
    res = [_jan1(y) for y in YEARS]
    eds = [election_day(y) for y in YEARS]
    for d in range(2, 9):
        _mk(pool, f"cal_election_day_nov{d}", f"Election Day falls on November {d}", "calendar",
            "election_day_date", "Election Day = first Tuesday after the first Monday in November.",
            [e.day == d for e in eds], res, 3, "A")
    for d in range(3, 9):
        _mk(pool, f"cal_election_day_ge_nov{d}", f"Election Day falls on or after November {d}",
            "calendar", "election_day_date", "Election Day date threshold.",
            [e.day >= d for e in eds], res, 3, "A")
    wd = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    for i, name in enumerate(wd):
        _mk(pool, f"cal_jan1_{name.lower()}", f"January 1 of the election year is a {name}",
            "calendar", "jan1_weekday", "Weekday of January 1 (Gregorian).",
            [dt.date(y, 1, 1).weekday() == i for y in YEARS], res, 3, "A")
    _mk(pool, "cal_leap_year", "The election year is a leap year", "calendar", "leap_year",
        "Gregorian leap-year rule (1900 was not a leap year).",
        [(y % 4 == 0 and y % 100 != 0) or y % 400 == 0 for y in YEARS], res, 3, "A")
    ea = [easter(y) for y in YEARS]
    for md in [(3, 31), (4, 5), (4, 10), (4, 15), (4, 20)]:
        _mk(pool, f"cal_easter_le_{md[0]:02d}{md[1]:02d}",
            f"Easter Sunday falls on or before {MONTH[md[0]]} {md[1]}", "calendar", "easter",
            "Western (Gregorian) Easter via the Meeus/Jones/Butcher algorithm.",
            [e <= dt.date(e.year, *md) for e in ea], res, 3, "A")


def _t(ts, d: dt.date, hour: int = 0):
    return ts.utc(d.year, d.month, d.day, hour)


def _local_date(t, tzname: str) -> dt.date:
    return t.utc_datetime().astimezone(ZONES[tzname]).date()


def _astronomy(pool: Pool) -> None:
    load = Loader(str(RAW_ASTRO))
    eph, ts = load("de421.bsp"), load.timescale()
    earth = eph["earth"]
    res_jan = [_jan1(y) for y in YEARS]
    src = EPH_URL

    # Seasons: March equinox, June solstice, September equinox, previous December solstice (UTC).
    names = {0: ("March equinox", 2), 1: ("June solstice", 3), 2: ("September equinox", 2),
             3: ("December solstice of the preceding year", 3)}
    season: dict[int, dict[int, tuple[dt.date, bool]]] = {k: {} for k in names}
    f = almanac.seasons(eph)
    for y in YEARS:
        t, ev = almanac.find_discrete(ts.utc(y - 1, 12, 1), ts.utc(y, 10, 1), f)
        for ti, e in zip(t, ev, strict=True):
            e = int(e)
            utc = ti.utc_datetime().date()
            if e == 3 and utc.year == y:
                continue  # December solstice of the election year occurs after Election Day
            flag = any(_local_date(ti, z) != utc for z in ZONES)
            season[e][y] = (utc, flag)
    for e, (nm, fam) in names.items():
        doms = sorted({d.day for d, _ in season[e].values()})
        flagged = any(fl for _, fl in season[e].values())
        for dom in doms:
            mon = next(d.month for d, _ in season[e].values() if d.day == dom)
            _mk(pool, f"astro_season{e}_dom{dom}", f"The {nm} falls on day {dom} of its month (UTC date)",
                "astronomy", f"season_{e}", f"Date of the {nm} in UTC; DE421 via Skyfield "
                f"almanac.seasons. Month varies only for the preceding-December case ({MONTH[mon]}).",
                [season[e][y][0].day == dom for y in YEARS],
                [season[e][y][0] for y in YEARS], fam, "B" if flagged else "A",
                src, CITE_ASTRO, ["tz_sensitive"] if flagged else [])

    # Lunar eclipses between Jan 1 (UTC) and Election Day 00:00 UTC of the election year.
    kinds = {"any": lambda k: True, "partial_or_total": lambda k: k >= 1,
             "total": lambda k: k == 2}
    ecl: dict[int, list[tuple[dt.date, int]]] = {}
    ecl_flag = False
    for y in YEARS:
        ed = election_day(y)
        t, kind, _ = eclipselib.lunar_eclipses(ts.utc(y, 1, 1), _t(ts, ed), eph)
        ecl[y] = [(ti.utc_datetime().date(), int(k)) for ti, k in zip(t, kind, strict=True)]
        t2, _, _ = eclipselib.lunar_eclipses(_t(ts, ed), _t(ts, ed + dt.timedelta(days=1)), eph)
        near_jan = eclipselib.lunar_eclipses(ts.utc(y - 1, 12, 31, 12), ts.utc(y, 1, 1, 12), eph)[0]
        ecl_flag |= len(t2) > 0 or len(near_jan) > 0
    for kname, test in kinds.items():
        _mk(pool, f"astro_lunar_eclipse_{kname}",
            f"A {'total' if kname == 'total' else kname.replace('_', ' ')} lunar eclipse occurs in "
            "the election year before Election Day", "astronomy", "lunar_eclipse",
            "Geocentric lunar eclipse found by Skyfield eclipselib between Jan 1 00:00 UTC and "
            "Election Day 00:00 UTC; visibility from the US is not considered.",
            [any(test(k) for _, k in ecl[y]) for y in YEARS],
            [min([d for d, k in ecl[y] if test(k)], default=cutoff(y)) for y in YEARS],
            2, "B" if ecl_flag else "A", src, CITE_ASTRO, ["tz_sensitive"] if ecl_flag else [])

    # Moon phase events on Election Day (UTC date), and instantaneous state at 12:00 UTC.
    fm = almanac.moon_phases(eph)
    pname = ["new moon", "first quarter moon", "full moon", "last quarter moon"]
    on_day = {k: [] for k in range(4)}
    flag_p = {k: False for k in range(4)}
    for y in YEARS:
        ed = election_day(y)
        t, ev = almanac.find_discrete(_t(ts, ed - dt.timedelta(days=1)),
                                      _t(ts, ed + dt.timedelta(days=2)), fm)
        for k in range(4):
            u = any(ti.utc_datetime().date() == ed and int(e) == k for ti, e in zip(t, ev, strict=True))
            on_day[k].append(u)
            for z in ZONES:
                loc = any(_local_date(ti, z) == ed and int(e) == k for ti, e in zip(t, ev, strict=True))
                flag_p[k] |= loc != u
    for k in range(4):
        _mk(pool, f"astro_moon_{pname[k].replace(' ', '_')}_on_election_day",
            f"A {pname[k]} occurs on Election Day (UTC date)", "astronomy", "moon_phase_event",
            "Instant of the phase event (DE421 via Skyfield almanac.moon_phases) falls on the "
            "UTC calendar date of Election Day.", on_day[k], res_jan, 3 if k in (0, 2) else 2,
            "B" if flag_p[k] else "A", src, CITE_ASTRO, ["tz_sensitive"] if flag_p[k] else [])

    def angle(d, hour):
        return almanac.moon_phase(eph, _t(ts, d, hour)).degrees

    def local_noon_utc_hours(d, z):
        off = dt.datetime(d.year, d.month, d.day, 12, tzinfo=ZONES[z]).utcoffset()
        return 12 - int(off.total_seconds() // 3600)

    def hrs(d, z):  # hour offsets may exceed 23 for Pacific noon (UTC next day); handle via t arith
        return _t(ts, d, 0) + (local_noon_utc_hours(d, z) / 24.0)

    for nm, fn, st in [
        ("waxing", lambda a: 0 < a < 180, "The Moon is waxing at 12:00 UTC on Election Day"),
        ("gibbous_or_full", lambda a: 90 < a < 270,
         "More than half the Moon's disc is illuminated at 12:00 UTC on Election Day"),
    ]:
        base = [fn(angle(election_day(y), 12)) for y in YEARS]
        flag = any(
            fn(almanac.moon_phase(eph, hrs(election_day(y), z)).degrees) != b
            for y, b in zip(YEARS, base, strict=True) for z in ZONES
        )
        _mk(pool, f"astro_moon_{nm}_noon_election_day", st, "astronomy", "moon_state",
            "Moon phase angle (Skyfield almanac.moon_phase) at 12:00 UTC on Election Day.",
            base, res_jan, 2, "B" if flag else "A", src, CITE_ASTRO,
            ["tz_sensitive"] if flag else [])

    # Mercury retrograde at 12:00 UTC on Election Day (apparent geocentric ecliptic longitude).
    merc = eph["mercury barycenter"]

    def retro(t):
        la = earth.at(t).observe(merc).apparent().ecliptic_latlon()[1].degrees
        t2 = t + 1.0 / 24
        lb = earth.at(t2).observe(merc).apparent().ecliptic_latlon()[1].degrees
        return ((lb - la + 180) % 360 - 180) < 0

    vals = [retro(_t(ts, election_day(y), 12)) for y in YEARS]
    flag = any(retro(hrs(election_day(y), z)) != v for y, v in zip(YEARS, vals, strict=True)
               for z in ZONES)
    _mk(pool, "astro_mercury_retrograde_election_day",
        "Mercury is in apparent retrograde motion at 12:00 UTC on Election Day", "astronomy",
        "planet_motion", "Geocentric apparent ecliptic longitude of Mercury decreasing over the "
        "following hour (DE421, Skyfield); a geometric fact, not an astrological claim.",
        vals, res_jan, 2, "B" if flag else "A", src, CITE_ASTRO, ["tz_sensitive"] if flag else [])
    pool.exclude("astronomy", "solar eclipses",
                 "Skyfield has no solar-eclipse finder; would need a fetched NASA catalog. Deferred.")
    pool.exclude("astronomy", "December solstice of the election year",
                 "Occurs after Election Day (C1); only the preceding year's solstice is used.")


def add_computed(pool: Pool) -> None:
    _calendar(pool)
    _astronomy(pool)
    _ = np  # keep numpy import for downstream vector use
