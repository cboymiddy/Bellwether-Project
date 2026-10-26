"""Display-layer mapping ONLY. Reads the frozen pool and event tables; writes display/*.csv.

Nothing here feeds search, ranking, or hashes: the frozen pool files are never modified.
- display/literal_labels.csv : corrected wording (and era names) for every positive pool literal;
  the negation of a literal is displayed as "NOT: <positive display statement>".
- display/year_names.csv     : the club name used in each election year (name at the time), per role.
"""

from __future__ import annotations

import pandas as pd
import yaml

from src.acquire import mlb_world_series as mlb
from src.config import ROOT
from src.literals import astro_family as af
from src.literals.core import OUT

EV = ROOT / "data" / "processed" / "events"
DISP = ROOT / "display"
MON = af.MON


def year_names() -> pd.DataFrame:
    rows = []
    wp = mlb.wp_list()
    for y, e in wp.items():
        if y in af.YEARS and e:
            rows += [("mlb_world_series", y, "winner", e["winner"]), ("mlb_world_series", y, "loser", e["loser"])]
    t = pd.read_csv(EV / "mlb_world_series.csv").set_index("year")
    out = []
    for fam, y, role, era in rows:
        canon = t.loc[y, f"{role}_franchise"]
        out.append({"family": fam, "year": y, "role": role, "canonical": canon, "name_at_time": era})
    for fam, cols in (("nfl_super_bowl", ("winner", "loser")), ("nba_finals", ("winner", "loser")),
                      ("nhl_stanley_cup", ("winner", "loser"))):
        d = pd.read_csv(EV / f"{fam}.csv")
        for _, r in d[d.held == 1].iterrows():
            for role in cols:
                era = r.get(f"{role}_name_at_time")
                out.append({"family": fam, "year": int(r["year"]), "role": role,
                            "canonical": r[f"{role}_franchise"], "name_at_time": era if pd.notna(era) else r[f"{role}_franchise"]})
    return pd.DataFrame(out).sort_values(["family", "year", "role"]).reset_index(drop=True)


def astro_label(rec: pd.Series) -> str:
    when = f"On {MON[int(rec.month) - 1]} {int(rec.day)} (00:00 UTC) of the election year"
    note = "apparent geocentric ecliptic longitudes, true equinox of date"
    if rec.kind == "sep":
        return (f"{when}, the difference in ecliptic longitude between {rec.body_a} and {rec.body_b} "
                f"(folded to 0-180 degrees; {note}) is at least {int(rec.param)} degrees")
    p = int(rec.param)
    return f"{when}, {rec.body_a}'s ecliptic longitude ({note}) is in [{p}, {p + 30}) degrees"


def main() -> None:
    DISP.mkdir(exist_ok=True)
    yn = year_names()
    yn.to_csv(DISP / "year_names.csv", index=False)
    meta = pd.DataFrame(yaml.safe_load((OUT / "literals_main.yaml").read_text()))
    meta = meta[meta.polarity == "pos"]
    mat = pd.read_csv(OUT / "matrix_main.csv").set_index("id")
    rows = []
    for _, r in meta.iterrows():
        stmt = r.statement
        note = ""
        m = None
        if r.family in ("nfl_super_bowl", "nba_finals", "nhl_stanley_cup", "mlb_world_series"):
            role = "winner" if "_winner_" in r.id else ("loser" if "_loser_" in r.id else None)
            if role:
                true_years = [int(c) for c in mat.columns if mat.loc[r.id, c] == 1]
                sub = yn[(yn.family == r.family) & (yn.role == role) & yn.year.isin(true_years)]
                eras = [f"{int(y)}: {n}" for y, n, c in zip(sub.year, sub.name_at_time, sub.canonical, strict=True) if n != c]
                if eras:
                    note = "era names in the years this is true: " + "; ".join(eras)
        rows.append({"id": r.id, "display_statement": stmt, "display_note": note, "source_of_change": "era names" if note else ""})
        _ = m
    idx = pd.read_csv(af.OUT / "index.csv")
    idx = idx[idx.included == 1]
    for _, r in idx.iterrows():
        rows.append({"id": r.id, "display_statement": astro_label(r),
                     "display_note": "wording corrected: the pool's text says 'angular separation'" if r.kind == "sep" else "",
                     "source_of_change": "wording" if r.kind == "sep" else ""})
    pd.DataFrame(rows).to_csv(DISP / "literal_labels.csv", index=False)
    (DISP / "README.md").write_text(
        "# Display-layer mapping (not part of the frozen pipeline)\n\n"
        "- `literal_labels.csv`: display wording for every positive literal. A negation is shown as `NOT: <display_statement>`.\n"
        "  Astronomy 'separation' literals are the folded difference in ecliptic longitude (the pool's own text says "
        "'angular separation', which is inaccurate); the mapping corrects the wording only.\n"
        "- `year_names.csv`: the club name used in each election year for MLB, NFL, NBA and NHL, from the event tables and "
        "the Wikipedia champions list as fetched in Phase 1.\n"
        "- The frozen pool files, matrices, ranking and hashes are untouched (checked against `freeze.yaml`).\n"
        "- Not covered: Olympic host names are already the names used then (e.g. Soviet Union, West Germany) in the event table.\n")
    print(len(rows), "labels;", len(yn), "year-name rows;", int((pd.DataFrame(rows).source_of_change == "era names").sum()), "with era notes")


if __name__ == "__main__":
    main()
