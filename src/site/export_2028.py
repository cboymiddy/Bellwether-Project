"""The 2028 reading: what the featured rule, and its equally perfect rivals, say about Election Day 2028.

Sky facts are computed from JPL DE421 (which covers 2028) with the same conventions as the pool: apparent geocentric
ecliptic longitude of date at 00:00 UTC; "separation" is the folded difference of longitudes. Nothing else is resolvable
today: every sports fact for 2028 is pending, and so is any rule that depends on one.
Read-only on frozen files; imports only helpers. Run via src.site.export.
"""

from __future__ import annotations

import csv
import re
from itertools import product
from math import prod

import numpy as np

from src.config import ROOT, election_day
from src.literals import astro_family as af
from src.verify.gate2_margins import hours_equivalent

YEAR = 2028
RS = ROOT / "reports" / "real_search"
SEP = re.compile(r"astro_geo_(\d{2})(\d{2})_sep_([a-z]+)_([a-z]+)_ge(\d{3})$")
LON = re.compile(r"astro_geo_(\d{2})(\d{2})_([a-z]+)_lon(\d{3})$")
NAMES = {k.lower(): k for k in af.BODIES}


def longitudes_at(year: int, md: tuple[int, int]) -> dict[str, float]:
    t = af.ts.utc(year, md[0], md[1])
    out = {}
    for name, key in af.BODIES.items():
        _lat, lon, _ = af.earth.at(t).observe(af.eph[key]).apparent().ecliptic_latlon(epoch="date")
        out[name] = float(lon.degrees % 360)
    return out


def is_sky(lit: str) -> bool:
    return lit.removeprefix("NOT_").startswith("astro_geo_")


def eval_sky(lit: str, year: int = YEAR) -> dict:
    """Value of a sky literal (negation applied) with its measured quantity and signed margin.

    Margin follows the base condition: positive means the base condition holds, with that many degrees to spare.
    """
    neg = lit.startswith("NOT_")
    base = lit.removeprefix("NOT_")
    m = SEP.match(base)
    if m:
        mo, d = int(m[1]), int(m[2])
        lon = longitudes_at(year, (mo, d))
        meas = float(af.separation(np.array(lon[NAMES[m[3]]]), np.array(lon[NAMES[m[4]]])))
        thr = float(int(m[5]))
        truth, margin = meas >= thr, meas - thr
    else:
        m = LON.match(base)
        if not m:
            raise ValueError(lit)
        mo, d = int(m[1]), int(m[2])
        v = longitudes_at(year, (mo, d))[NAMES[m[3]]]
        p = int(m[4])
        lo = abs(((v - p + 180) % 360) - 180)
        hi = abs(((v - (p + 30) + 180) % 360) - 180)
        truth = p <= v < p + 30
        meas, thr, margin = v, float(p), min(lo, hi) * (1 if truth else -1)
    return {"base_truth": bool(truth), "value": bool(truth != neg), "measured_deg": meas, "threshold_deg": thr,
            "margin_deg": float(margin), "instant_utc": f"{year}-{mo:02d}-{d:02d}T00:00:00Z",
            "margin_hours": round(hours_equivalent(base, year, abs(float(margin))), 2)}


def state(lit: str) -> str:
    """'true' / 'false' for sky facts; 'pending' for anything that has not happened yet."""
    return ("true" if eval_sky(lit)["value"] else "false") if is_sky(lit) else "pending"


def verdict(states: list[str]) -> str:
    if "false" in states:
        return "no_win"
    return "pending" if "pending" in states else "win"


def rule_status(lits: list[str]) -> str:
    """Prediction for 2028 given what is known today: all literals must hold for the rule to say WIN."""
    return verdict([state(x) for x in lits])


def alias_range(alias_groups: list[list[str]]) -> set[str]:
    """Every verdict reachable by choosing one equally good alias per position (they agree on 1900-2024 only)."""
    per = [{state(a) for a in g} for g in alias_groups]
    out = set()
    for combo in product(*[sorted(s) for s in per]):
        out.add(verdict(list(combo)))
    return out


def tally(frontier_rows: list[dict], featured: list[str]) -> dict:
    cache: dict[str, str] = {}

    def st(x: str) -> str:
        if x not in cache:
            cache[x] = state(x)
        return cache[x]

    def verdict_of(ls):
        return verdict([st(x) for x in ls])

    counts = {"no_win": 0, "pending": 0, "win": 0}
    alias_vary = 0
    others = []
    lvl = {"total": 0, "no_win": 0, "win": 0, "pending": 0, "rules_with_a_wording_that_is_not_no_win": 0}
    per_rule: dict[int, dict] = {}
    for r in frontier_rows:  # every interchangeable wording of every rule (they agree on 1900-2024, not on 2028)
        cnt = [{s: sum(1 for a in g.split("/") if st(a) == s) for s in ("true", "false", "pending")}
               for g in r["aliases"].split(" | ")]
        total = prod(sum(c.values()) for c in cnt)
        win = prod(c["true"] for c in cnt)
        live = prod(c["true"] + c["pending"] for c in cnt)
        per_rule[int(r["rank"])] = {"total": total, "win": win, "pending": live - win, "no_win": total - live}
        lvl["total"] += total
        lvl["win"] += win
        lvl["pending"] += live - win
        lvl["no_win"] += total - live
        lvl["rules_with_a_wording_that_is_not_no_win"] += live > 0
    for r in frontier_rows:
        ls = [x.strip() for x in r["literals"].split(" & ")]
        if sorted(ls) == sorted(featured):
            continue
        v = verdict_of(ls)
        counts[v] += 1
        groups = [g.split("/") for g in r["aliases"].split(" | ")]
        per = [{st(a) for a in g} for g in groups]
        reach = {verdict([s for s in c]) for c in product(*[sorted(s) for s in per])}
        alias_vary += len(reach) > 1
        others.append({"rank": int(r["rank"]), "literals": ls, "verdict": v, "alias_verdicts": sorted(reach),
                       "wordings": per_rule[int(r["rank"])]})
    return {"n_rules": len(frontier_rows), "n_others": len(others), "counts": counts, "alias_changes_verdict": alias_vary,
            "wordings": lvl, "others": others}


def roman(n: int) -> str:
    out = ""
    for v, r in ((1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"), (50, "L"), (40, "XL"), (10, "X"),
                 (9, "IX"), (5, "V"), (4, "IV"), (1, "I")):
        while n >= v:
            out, n = out + r, n - v
    return out


def unroman(s: str) -> int:
    vals = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    tot = 0
    for a, b in zip(s, s[1:] + " ", strict=False):
        tot += -vals[a] if vals.get(b, 0) > vals[a] else vals[a]
    return tot


def next_super_bowl() -> str:
    """Game number for 2028 from the event table: the 2024 game number plus the four annual games since."""
    with (ROOT / "data" / "processed" / "events" / "nfl_super_bowl.csv").open() as fh:
        g = next(r["game_number"] for r in csv.DictReader(fh) if r["year"] == "2024")
    return roman(unroman(g) + (YEAR - 2024))


def build_2028(rule: dict, glosses_for) -> dict:
    """rule: the exported rule dict (for literal ids/glosses); glosses_for: callable id -> display gloss."""
    ed = election_day(YEAR)
    lits = rule["literals"]
    cells = []
    for l in lits:
        if is_sky(l["id"]):
            e = eval_sky(l["id"])
            cells.append({"id": l["id"], "gloss": l["gloss"], "kind": "sky", "state": "true" if e["value"] else "false", **e,
                          "negated": l["id"].startswith("NOT_")})
        else:
            cells.append({"id": l["id"], "gloss": l["gloss"], "kind": "event", "state": "pending",
                          "event": f"Super Bowl {next_super_bowl()}, played in early {YEAR}", "negated": l["id"].startswith("NOT_")})
    sky_ok = all(c["state"] == "true" for c in cells if c["kind"] == "sky")
    branches = []
    for steelers_win in (False, True):
        values = [(c["state"] == "true") if c["kind"] == "sky" else (not steelers_win) for c in cells]
        branches.append({"steelers_win": steelers_win, "prediction_hold_party_wins": all(values)})
    rows = list(csv.DictReader((RS / "frontier_primary_ec_T1.csv").open()))
    tied = {int(r["rank"]) for r in rows if int(r["rank"]) <= rule["selection"]["tied_top_key_rules"]}
    t = tally(rows, [c["id"] for c in cells])
    tied_rows = []
    for o in t["others"] + [{"rank": rule["selection"]["featured_rank"], "literals": [c["id"] for c in cells],
                             "verdict": "pending" if sky_ok else "no_win", "alias_verdicts": [], "featured": True}]:
        if o["rank"] in tied:
            tied_rows.append({"rank": o["rank"], "verdict": o["verdict"], "featured": bool(o.get("featured")),
                              "literals": [{"id": x, "gloss": glosses_for(x), "state": state(x)} for x in o["literals"]]})
    tied_rows.sort(key=lambda r: r["rank"])
    t_out = {k: v for k, v in t.items() if k != "others"}
    t_out["wording_sensitive"] = [
        {"rank": o["rank"], "verdict_as_listed": o["verdict"], "reachable": o["alias_verdicts"], "wordings": o["wordings"],
         "literals": [{"id": x, "gloss": glosses_for(x), "state": state(x)} for x in o["literals"]]}
        for o in t["others"] if len(o["alias_verdicts"]) > 1]
    return {"year": YEAR, "election_day": ed.isoformat(), "election_weekday": ed.strftime("%A"),
            "ephemeris": "JPL DE421 via Skyfield (covers through 2053)", "featured": {"cells": cells, "sky_conditions_hold": sky_ok,
                                                                                       "branches": branches},
            "tally": t_out, "tied_top_key": tied_rows}
