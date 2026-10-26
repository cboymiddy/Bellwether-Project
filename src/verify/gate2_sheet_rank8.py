"""verification_sheet.csv for T1 EC frontier rank 8 (all 32 years). Read-only; no pool/ranking changes."""

import re

import pandas as pd

from src.config import ROOT
from src.literals.astro_family import EPH_SHA, YEARS
from src.verify.gate2_margins import RS, astro_series, ranks, strip

SKY = (f"Skyfield 1.55 + JPL DE421 (sha256 {EPH_SHA[:12]}...), src/literals/astro_family.py; "
       "convention in HORIZONS_CONVENTION.md")
HOR = "JPL Horizons API, quantity 31, geocentric, UT, settings in HORIZONS_CONVENTION.md"
ESPN = "https://www.espn.com/nfl/superbowl/history/winners"
WIKI = "https://en.wikipedia.org/wiki/List_of_Super_Bowl_champions"
TOL = 0.001


def espn_rows() -> dict:
    from bs4 import BeautifulSoup

    s = BeautifulSoup((ROOT / "data/raw/nfl_super_bowl/espn_winners.html").read_text(), "lxml")
    out = {}
    for tr in s.find_all("tr"):
        c = [x.get_text(" ", strip=True) for x in tr.find_all(["td", "th"])]
        if len(c) >= 4 and re.match(r"[A-Z][a-z]{2,4}\.? \d{1,2}, \d{4}", c[1]):
            m = re.match(r"(.+?) (\d+), (.+?) (\d+)$", c[3])
            if m:
                out[pd.to_datetime(c[1].replace(".", "")).date().isoformat()] = {
                    "no": c[0], "winner": m[1], "w": int(m[2]), "loser": m[3], "l": int(m[4])}
    return out


def human_checks() -> dict[tuple[str, int], str]:
    """Human sign-offs recorded by hand in human_checks.csv; only the rows listed there are marked."""
    f = RS / "human_checks.csv"
    if not f.exists():
        return {}
    d = pd.read_csv(f)
    return {(r.literal, int(r.year)): f"yes: {r.checked_by}, {r.checked_on}, {r.source_url}" for r in d.itertuples()}


def main() -> None:
    human = human_checks()
    top = pd.read_csv(RS / "top50_primary_ec_T1.csv")
    row8 = top[top["rank"] == 8].iloc[0]
    lits = [x.strip() for x in row8.literals.split(" & ")]
    assert ranks(top, 8, 8).keys() == set(lits)
    hz = pd.read_csv(RS / "horizons_rank8" / "horizons_rank8_comparison.csv")
    nfl = pd.read_csv(ROOT / "data/processed/events/nfl_super_bowl.csv").set_index("year")
    espn = espn_rows()
    rows = []
    for lit in lits:
        base, neg = strip(lit)
        if base.startswith("astro_geo_"):
            s = astro_series(base)
            h = hz[hz.literal == lit].set_index("year")
            qty = "ecliptic-longitude difference folded to [0,180] deg (apparent, geocentric, true equinox of date)"
            for i, y in enumerate(YEARS):
                gap = float(h.loc[y, "gap_deg"])
                ok = (gap <= TOL) and not bool(h.loc[y, "truth_differs"])
                rows.append({"literal": lit, "year": y, "date_or_instant": f"{y}-{s['md'][0]:02d}-{s['md'][1]:02d}T00:00:00Z",
                             "quantity": qty, "value": round(float(s["value"][i]), 6), "threshold": s["threshold"],
                             "margin": round(float(s["margin"][i]), 6),
                             "literal_value": bool(s["truth"][i]) != neg, "rule_ranks": 8, "source": SKY,
                             "second_source": HOR, "second_source_value": float(h.loc[y, "horizons_diff_deg"]),
                             "second_source_detail": f"gap {gap:.7f} deg; Horizons literal {bool(h.loc[y, 'horizons_literal'])}",
                             "checked": "auto-OK (Horizons within 0.001 deg, same truth)" if ok else "auto-MISMATCH",
                             "human_checked": human.get((lit, y), "")})
        else:
            for y in YEARS:
                r = nfl.loc[y]
                if int(r["held"]) != 1:
                    rows.append({"literal": lit, "year": y, "date_or_instant": "", "quantity": "Super Bowl winner",
                                 "value": "no Super Bowl held (first game Jan. 15, 1967 per ESPN)", "threshold": "n/a",
                                 "margin": "n/a", "literal_value": True, "rule_ranks": 8, "source": WIKI,
                                 "second_source": ESPN, "second_source_value": "no game listed in the year",
                                 "second_source_detail": "", "checked": "auto-OK" if not any(k.startswith(str(y)) for k in espn) else "auto-MISMATCH",
                                 "human_checked": human.get((lit, y), "")})
                    continue
                e = espn.get(r["completed_date"])
                agree = bool(e) and e["w"] == int(str(r["score"]).split("-")[0]) and e["l"] == int(
                    str(r["score"]).split("-")[1]) and str(r["winner_name_at_time"]).startswith(
                    e["winner"].split(",")[0]) and str(r["loser_name_at_time"] or r["loser_franchise"]).split()[0] in (
                    e["loser"] + " " + str(r["loser_franchise"]))
                win_canon = r["winner_franchise"]
                rows.append({"literal": lit, "year": y, "date_or_instant": r["completed_date"],
                             "quantity": f"Super Bowl {r['game_number']} winner (name at the time)",
                             "value": f"{r['winner_name_at_time']} {r['score']} over {r['loser_name_at_time']}",
                             "threshold": "n/a", "margin": "n/a",
                             "literal_value": (win_canon != "Pittsburgh Steelers"), "rule_ranks": 8, "source": WIKI,
                             "second_source": ESPN,
                             "second_source_value": f"{e['no']} {r['completed_date']}: {e['winner']} {e['w']}, {e['loser']} {e['l']}" if e else "not found",
                             "second_source_detail": "", "checked": "auto-OK (ESPN date, winner, loser, score agree)" if agree else "auto-MISMATCH",
                             "human_checked": human.get((lit, y), "")})
    df = pd.DataFrame(rows)
    df.to_csv(RS / "verification_sheet.csv", index=False)
    print(len(df), "rows;", df.literal.nunique(), "literals")
    print(df.groupby("literal").agg(true_years=("literal_value", "sum"), n=("year", "count")))
    print(df.checked.value_counts())


if __name__ == "__main__":
    main()
