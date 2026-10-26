"""Parse NOAA GHCN-Daily .dly files into per-station, per-election-year weather windows.

Run: uv run python -m src.acquire.weather   (offline; reads data/raw/weather/)

Source units (GHCN-Daily readme, data/raw/weather/readme.txt):
  TMAX = tenths of degrees Celsius; SNOW = millimetres; -9999 = missing.
Output units: degrees F (rounded to whole F, the precision the observations
were originally taken at) and inches.
Observations carrying a non-blank quality-control flag are treated as MISSING
(never as zero); counts of such days are not hidden: they reduce *_with_* counts.
Thresholds: SNOW >= 0.1 in <=> >= 2.5 mm; >= 1.0 in <=> >= 25 mm (GHCN stores whole mm,
so 1 in is stored as 25 mm and 0.1 in as 2 or 3 mm -> we use 2.5 mm; see coverage notes).
Station files are NEVER spliced.
"""

import csv
import datetime as dt
from pathlib import Path

RAW = Path("data/raw/weather")
OUT = Path("data/processed/events")
YEARS = list(range(1900, 2025, 4))

# (station_id, city); names are read from ghcnd-stations.txt, not typed here.
STATIONS = [
    ("USW00094728", "New York City"),
    ("USC00305816", "New York City"),
    ("USW00014734", "New York City (Newark NJ)"),
    ("USW00014881", "Chicago"),
    ("USW00094846", "Chicago"),
    ("USW00014819", "Chicago"),
    ("USW00093725", "Washington DC"),
    ("USW00013743", "Washington DC"),
    ("USW00094701", "Boston"),
    ("USW00014739", "Boston"),
    ("USC00190736", "Boston (Blue Hill)"),
    ("USW00093134", "Los Angeles"),
]


def election_day(y: int) -> dt.date:
    """First Tuesday after the first Monday in November."""
    d = dt.date(y, 11, 1)
    while d.weekday() != 0:
        d += dt.timedelta(days=1)
    return d + dt.timedelta(days=1)


def read_dly(path: Path, elements: set[str]) -> dict[str, dict[dt.date, int]]:
    """Return {element: {date: raw_value}}; missing/flagged values are omitted.

    Also returns flagged days separately via the 'FLAGGED:<el>' key.
    """
    out: dict[str, dict[dt.date, int]] = {}
    for el in elements:
        out[el] = {}
        out["FLAGGED:" + el] = {}
    for line in path.read_text().splitlines():
        el = line[17:21]
        if el not in elements:
            continue
        y, m = int(line[11:15]), int(line[15:17])
        for i in range(31):
            off = 21 + 8 * i
            v = int(line[off : off + 5])
            qflag = line[off + 6]
            try:
                d = dt.date(y, m, i + 1)
            except ValueError:
                continue
            if v == -9999:
                continue
            if qflag != " ":
                out["FLAGGED:" + el][d] = v
                continue
            out[el][d] = v
    return out


def daterange(a: dt.date, b: dt.date):
    d = a
    while d <= b:
        yield d
        d += dt.timedelta(days=1)


def tmax_f(v: int) -> int:
    return round(v / 10 * 9 / 5 + 32)


def main() -> None:
    names = {}
    for line in (RAW / "ghcnd-stations.txt").read_text().splitlines():
        names[line[:11]] = line[38:40] + " " + line[41:71].strip()
    OUT.mkdir(parents=True, exist_ok=True)
    cols = [
        "station_id",
        "station_name",
        "city",
        "year",
        "election_day",
        "snow_window_days_expected",
        "snow_window_days_with_snow_obs",
        "first_snow_date_ge_0p1in",
        "first_snow_date_ge_1p0in",
        "snow_window_complete",
        "snow_window_complete_1p0in",
        "jja_days_expected",
        "jja_days_with_tmax",
        "jja_tmax_mean_f",
        "jja_tmax_max_f",
        "n_days_tmax_ge_90f",
        "n_days_tmax_ge_100f",
        "jja_complete",
    ]
    rows = []
    for sid, city in STATIONS:
        data = read_dly(RAW / f"{sid}.dly", {"TMAX", "SNOW"})
        snow, tmax = data["SNOW"], data["TMAX"]
        for y in YEARS:
            ed = election_day(y)
            s0, s1 = dt.date(y, 8, 1), ed - dt.timedelta(days=1)
            sdays = list(daterange(s0, s1))
            have = [d for d in sdays if d in snow]
            f01 = next((d for d in sdays if d in snow and snow[d] >= 2.5), None)
            f10 = next((d for d in sdays if d in snow and snow[d] >= 25), None)
            full = len(have) == len(sdays)
            jdays = list(daterange(dt.date(y, 6, 1), dt.date(y, 8, 31)))
            tv = [tmax_f(tmax[d]) for d in jdays if d in tmax]
            rows.append(
                {
                    "station_id": sid,
                    "station_name": names[sid],
                    "city": city,
                    "year": y,
                    "election_day": ed.isoformat(),
                    "snow_window_days_expected": len(sdays),
                    "snow_window_days_with_snow_obs": len(have),
                    "first_snow_date_ge_0p1in": f01 or "",
                    "first_snow_date_ge_1p0in": f10 or "",
                    "snow_window_complete": int(full or f01 is not None),
                    "snow_window_complete_1p0in": int(full or f10 is not None),
                    "jja_days_expected": len(jdays),
                    "jja_days_with_tmax": len(tv),
                    "jja_tmax_mean_f": round(sum(tv) / len(tv), 2) if tv else "",
                    "jja_tmax_max_f": max(tv) if tv else "",
                    "n_days_tmax_ge_90f": sum(t >= 90 for t in tv) if tv else "",
                    "n_days_tmax_ge_100f": sum(t >= 100 for t in tv) if tv else "",
                    "jja_complete": int(len(tv) == len(jdays)),
                }
            )
    with open(OUT / "weather_station_years.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    write_coverage(rows)


def write_coverage(rows: list[dict]) -> None:
    by: dict[str, list[dict]] = {}
    for r in rows:
        by.setdefault(r["station_id"], []).append(r)
    L = [
        "# Weather coverage summary (generated by src/acquire/weather.py)",
        "",
        "Source: NOAA NCEI GHCN-Daily .dly by-station files (see data/raw/weather/MANIFEST.csv).",
        "Quality-flagged observations are treated as missing. Windows end the day before Election Day.",
        "SNOW window = Aug 1 .. Election Day - 1. JJA = Jun 1 .. Aug 31.",
        (
            "`snow_window_complete` = every window day has a SNOW obs OR a >=0.1 in snowfall was found "
            "(existence of snow is then certain; the *date* of first snow is only certain if no earlier day is missing)."
        ),
        "",
        "| station | city | jja complete yrs | snow>=0.1in-complete yrs | snow>=1.0in-complete yrs | all-32 JJA | all-32 snow |",
        "|---|---|---|---|---|---|---|",
    ]
    detail = []
    for sid, rs in by.items():
        j = [r["year"] for r in rs if r["jja_complete"]]
        s = [r["year"] for r in rs if r["snow_window_complete"]]
        s1 = [r["year"] for r in rs if r["snow_window_complete_1p0in"]]
        L.append(
            f"| {sid} {rs[0]['station_name']} | {rs[0]['city']} | {len(j)}/32 | {len(s)}/32 | {len(s1)}/32 "
            f"| {'YES' if len(j) == 32 else 'no'} | {'YES' if len(s) == 32 else 'no'} |"
        )
        detail.append(f"### {sid} {rs[0]['station_name']} ({rs[0]['city']})")
        detail.append(
            "- JJA incomplete years: "
            + (
                ", ".join(
                    f"{r['year']} ({r['jja_days_with_tmax']}/{r['jja_days_expected']})"
                    for r in rs
                    if not r["jja_complete"]
                )
                or "none"
            )
        )
        detail.append(
            "- Snow(>=0.1in) incomplete years: "
            + (
                ", ".join(
                    f"{r['year']} ({r['snow_window_days_with_snow_obs']}/{r['snow_window_days_expected']})"
                    for r in rs
                    if not r["snow_window_complete"]
                )
                or "none"
            )
        )
        detail.append(
            "- Snow(>=1.0in) incomplete years: "
            + (
                ", ".join(str(r["year"]) for r in rs if not r["snow_window_complete_1p0in"])
                or "none"
            )
        )
        detail.append("")
    full_j = [k for k, rs in by.items() if all(r["jja_complete"] for r in rs)]
    full_s = [k for k, rs in by.items() if all(r["snow_window_complete"] for r in rs)]
    full_s1 = [k for k, rs in by.items() if all(r["snow_window_complete_1p0in"] for r in rs)]
    L += [
        "",
        "## Verdict (computed)",
        f"- JJA TMAX complete for all 32 election years: {', '.join(full_j) or 'none'}",
        f"- Snow window (>=0.1 in) complete for all 32 years: {', '.join(full_s) or 'none'}",
        f"- Snow window (>=1.0 in) complete for all 32 years: {', '.join(full_s1) or 'none'}",
        (
            "- Stations are never spliced. Cities with no single complete station: any city whose "
            "stations are absent from the lists above. A merge (e.g. Fort Dearborn -> O'Hare/Midway "
            "for Chicago, Washington -> Reagan) would need sourced move dates and is NOT applied."
        ),
        "- Caveat: SNOW >= 0.1 in uses >= 2.5 mm (GHCN stores whole mm); a stored 2 mm is excluded.",
    ]
    L += ["", "## Per-station detail (days with obs / days expected)", ""] + detail
    (OUT / "weather_coverage.md").write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
