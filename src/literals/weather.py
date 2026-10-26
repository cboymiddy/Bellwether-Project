"""Weather literals from NOAA GHCN-Daily station tables (data/processed/events/weather_*.csv).

Thresholds below form a grid fixed before any outcome vector was examined. A station-window
is eligible only if every one of the 32 election years has complete data for that window
(CLAUDE.md C4); otherwise the station is recorded as an exclusion with the coverage failure.
"""

from __future__ import annotations

import datetime as dt

import pandas as pd

from src.config import ROOT
from src.literals.core import YEARS, Literal, Pool, cutoff

TODAY = "2026-10-25"
TABLE = ROOT / "data" / "processed" / "events" / "weather_station_years.csv"
DLY = "https://www.ncei.noaa.gov/pub/data/ghcn/daily/all/{sid}.dly"
CITE = ("NOAA NCEI GHCN-Daily station {sid} ({name}); observations with quality flags treated as "
        "missing; raw files and sha256 in data/raw/weather/MANIFEST.csv")

SNOW_GRID = {"0p1": 0.1, "1p0": 1.0}  # inches
JJA_MEAN_GRID = [78, 80, 82, 84]
JJA_MAX_GRID = [95, 98, 100, 102]
N90_GRID = [10, 20, 30]
N100_GRID = [1, 2]
# station id -> (short label, F). Every station present in the table is considered below.
FAMILIES = {"USW00094728": ("NYC Central Park", 2, 3), "USC00190736": ("Blue Hill, MA", 1, 1)}


def _add(pool, sid, name, city, id_, statement, family, defn, vals, res, F, flags):
    pool.add(Literal(
        id=id_, statement=statement, category="weather", family=family, definition=defn,
        source_url=DLY.format(sid=sid), dataset_citation=CITE.format(sid=sid, name=name),
        retrieval_date=TODAY, F=F, O="B", values=[bool(v) for v in vals], resolves_by=res,
        flags=flags,
    ))


def add_weather(pool: Pool) -> None:
    df = pd.read_csv(TABLE)
    for sid, g in df.groupby("station_id"):
        g = g.set_index("year").reindex(YEARS)
        name, city = g.station_name.iloc[0], g.city.iloc[0]
        jja_ok = bool((g.jja_complete == 1).all())
        snow_ok = bool((g.snow_window_complete == 1).all() and (g.snow_window_complete_1p0in == 1).all())
        if sid not in FAMILIES:
            bad_j = [y for y in YEARS if g.loc[y, "jja_complete"] != 1]
            bad_s = [y for y in YEARS if g.loc[y, "snow_window_complete"] != 1]
            pool.exclude("weather", f"{sid} {name} ({city})",
                         f"incomplete coverage: JJA TMAX missing/incomplete in {len(bad_j)}/32 "
                         f"election years, snow window in {len(bad_s)}/32 (no splicing applied)")
            continue
        f_jja, f_snow = FAMILIES[sid][1], FAMILIES[sid][2]
        if jja_ok:
            ress = [dt.date(y, 8, 31) for y in YEARS]
            w = "June 1 - August 31 of the election year (complete for all 32 years)"
            for t in JJA_MEAN_GRID:
                _add(pool, sid, name, city, f"wx_{sid}_jja_tmax_mean_ge{t}",
                     f"{FAMILIES[sid][0]}: mean daily high for Jun-Aug is at least {t} F",
                     f"wx_{sid}_jja", f"Mean GHCN-D TMAX, {w}; whole-degree F.",
                     g.jja_tmax_mean_f >= t, ress, f_jja, ["tmax_rounded_whole_f"])
            for t in JJA_MAX_GRID:
                _add(pool, sid, name, city, f"wx_{sid}_jja_tmax_max_ge{t}",
                     f"{FAMILIES[sid][0]}: the Jun-Aug high reaches at least {t} F",
                     f"wx_{sid}_jja", f"Max GHCN-D TMAX, {w}.", g.jja_tmax_max_f >= t, ress,
                     f_jja, ["tmax_rounded_whole_f"])
            for t in N90_GRID:
                _add(pool, sid, name, city, f"wx_{sid}_jja_n90_ge{t}",
                     f"{FAMILIES[sid][0]}: at least {t} days with a high of 90 F or more in Jun-Aug",
                     f"wx_{sid}_jja", f"Count of days TMAX >= 90 F, {w}.", g.n_days_tmax_ge_90f >= t,
                     ress, f_jja, ["tmax_rounded_whole_f"])
            for t in N100_GRID:
                _add(pool, sid, name, city, f"wx_{sid}_jja_n100_ge{t}",
                     f"{FAMILIES[sid][0]}: at least {t} day(s) with a high of 100 F or more in Jun-Aug",
                     f"wx_{sid}_jja", f"Count of days TMAX >= 100 F, {w}.",
                     g.n_days_tmax_ge_100f >= t, ress, f_jja, ["tmax_rounded_whole_f"])
        else:
            pool.exclude("weather", f"{sid} JJA literals", "JJA TMAX incomplete in some election year")
        if snow_ok:
            for key, inch in SNOW_GRID.items():
                col = f"first_snow_date_ge_{key}in"
                first = pd.to_datetime(g[col], errors="coerce")
                vals = first.notna()
                res = [first[y].date() if vals[y] else cutoff(y) for y in YEARS]
                _add(pool, sid, name, city, f"wx_{sid}_snow_ge{key}_by_eve",
                     f"{FAMILIES[sid][0]}: measurable snow of at least {inch} inch fell between "
                     "August 1 and the day before Election Day", f"wx_{sid}_snow",
                     f"GHCN-D SNOW >= {inch} in on any day Aug 1 .. Election Day - 1 (complete "
                     "daily coverage for all 32 election years; >= 0.1 in tested as >= 2.5 mm "
                     "because GHCN stores whole mm).", vals, res, f_snow,
                     ["snow_threshold_mm_rounding"])
        else:
            pool.exclude("weather", f"{sid} snow literals", "snow window incomplete in some year")
