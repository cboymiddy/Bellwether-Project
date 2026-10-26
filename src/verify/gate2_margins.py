"""Margins and verification sheet for the Gate-2 T1 (EC) frontier. Read-only: no re-ranking, no pool changes.

Margin = distance in degrees from the measured quantity to the literal's threshold in a given year.
For `sep` literals the measured quantity is the folded difference of apparent geocentric ecliptic
longitudes (what the pool computes); `true_sep` columns give the full 3-D angular separation for
comparison. Sector literals (`lon in [p, p+30)`) have margin = distance to the nearest sector edge.
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd

from src.config import ROOT
from src.literals import astro_family as af

RS = ROOT / "reports" / "real_search"
YEARS = af.YEARS
SEP = re.compile(r"astro_geo_(\d{2})(\d{2})_sep_([a-z]+)_([a-z]+)_ge(\d{3})$")
LON = re.compile(r"astro_geo_(\d{2})(\d{2})_([a-z]+)_lon(\d{3})$")
NAMES = {k.lower(): k for k in af.BODIES}


def strip(lit: str) -> tuple[str, bool]:
    return (lit[4:], True) if lit.startswith("NOT_") else (lit, False)


def true_separation(md: tuple[int, int], a: str, b: str) -> np.ndarray:
    t = af.ts.utc(np.array(YEARS), md[0], md[1])
    pa = af.earth.at(t).observe(af.eph[af.BODIES[a]]).apparent()
    pb = af.earth.at(t).observe(af.eph[af.BODIES[b]]).apparent()
    return pa.separation_from(pb).degrees


def astro_series(base: str) -> dict:
    m = SEP.match(base)
    if m:
        mo, d, a, b, c = int(m[1]), int(m[2]), NAMES[m[3]], NAMES[m[4]], int(m[5])
        lon = af.longitudes((mo, d))
        meas = af.separation(lon[a], lon[b])
        return {"kind": "sep", "md": (mo, d), "a": a, "b": b, "threshold": c, "value": meas,
                "truth": meas >= c, "margin": meas - c, "true_sep": true_separation((mo, d), a, b)}
    m = LON.match(base)
    if m:
        mo, d, a, p = int(m[1]), int(m[2]), NAMES[m[3]], int(m[4])
        v = af.longitudes((mo, d))[a]
        lo = np.abs(((v - p + 180) % 360) - 180)
        hi = np.abs(((v - (p + 30) + 180) % 360) - 180)
        return {"kind": "sector", "md": (mo, d), "a": a, "b": "", "threshold": p, "value": v,
                "truth": (v >= p) & (v < p + 30), "margin": np.minimum(lo, hi) * np.where(
                    (v >= p) & (v < p + 30), 1, -1), "true_sep": None}
    raise ValueError(base)


def measure_at(base: str, year: int, offset_h: float) -> float:
    """Measured quantity for one year at 00:00 UTC + offset_h hours (finite-difference helper)."""
    m = SEP.match(base) or LON.match(base)
    mo, d = int(m[1]), int(m[2])
    t = af.ts.utc(year, mo, d, offset_h)
    pos = {}
    names = (NAMES[m[3]], NAMES[m[4]]) if SEP.match(base) else (NAMES[m[3]],)
    for n in names:
        _la, lo, _ = af.earth.at(t).observe(af.eph[af.BODIES[n]]).apparent().ecliptic_latlon(epoch="date")
        pos[n] = float(lo.degrees % 360)
    if SEP.match(base):
        d_ = abs(pos[names[0]] - pos[names[1]]) % 360
        return 360 - d_ if d_ > 180 else d_
    return pos[names[0]]


def hours_equivalent(base: str, year: int, margin_deg: float) -> float:
    """Hours of clock error that would use up the margin, from the local rate of change."""
    rate = (measure_at(base, year, 0.5) - measure_at(base, year, -0.5)) / 1.0  # deg per hour
    rate = ((rate + 180) % 360) - 180
    return float(margin_deg / abs(rate)) if rate else float("inf")


def ranks(top: pd.DataFrame, lo: int, hi: int) -> dict[str, list[int]]:
    used: dict[str, list[int]] = {}
    for _, r in top[(top["rank"] >= lo) & (top["rank"] <= hi)].iterrows():
        for lit in r.literals.split(" & "):
            used.setdefault(lit.strip(), []).append(int(r["rank"]))
    return used


def margins_table(top: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for lit, rk in ranks(top, 2, 10).items():
        base, neg = strip(lit)
        rec = {"literal": lit, "used_in_ranks": ",".join(map(str, sorted(set(rk))))}
        if base.startswith("astro_geo_"):
            s = astro_series(base)
            i = int(np.argmin(np.abs(s["margin"])))
            rec |= {"kind": s["kind"], "quantity": ("ecliptic-longitude difference" if s["kind"] == "sep"
                    else "ecliptic longitude"), "threshold_deg": s["threshold"],
                    "min_abs_margin_deg": round(float(abs(s["margin"][i])), 6), "year_of_min": YEARS[i],
                    "value_at_min_deg": round(float(s["value"][i]), 6),
                    "literal_truth_at_min": bool(s["truth"][i] != neg),
                    "hours_of_clock_error_to_flip_at_min": round(hours_equivalent(
                        base, YEARS[i], float(abs(s["margin"][i]))), 2),
                    "n_years_margin_lt_1deg": int((np.abs(s["margin"]) < 1).sum()),
                    "n_years_margin_lt_0p1deg": int((np.abs(s["margin"]) < 0.1).sum())}
            if s["true_sep"] is not None:
                ts_truth = s["true_sep"] >= s["threshold"]
                j = int(np.argmin(np.abs(s["true_sep"] - s["threshold"])))
                rec |= {"true_sep_min_abs_margin_deg": round(float(abs(s["true_sep"][j] - s["threshold"])), 6),
                        "true_sep_year_of_min": YEARS[j],
                        "years_truth_differs_if_true_sep": int((ts_truth != s["truth"]).sum())}
        else:
            rec |= {"kind": "event", "quantity": "categorical event outcome", "threshold_deg": "n/a",
                    "min_abs_margin_deg": "n/a"}
        rows.append(rec)
    return pd.DataFrame(rows)


if __name__ == "__main__":
    top = pd.read_csv(RS / "top50_primary_ec_T1.csv")
    mt = margins_table(top)
    mt.to_csv(RS / "t1_margins_ranks2_10.csv", index=False)
    pd.set_option("display.width", 250, "display.max_columns", 30, "display.max_colwidth", 60)
    print(mt.to_string(index=False))
