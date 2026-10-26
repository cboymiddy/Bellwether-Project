"""Check which NHL literals depend on the 1900-1912 challenge-era series-selection judgment."""

import re

import pandas as pd

from src.acquire import nhl_stanley_cup as nhl
from src.literals.core import OUT

RENAME = {"Ottawa Silver Seven": "Ottawa Senators", "Ottawa HC": "Ottawa Senators"}


def main() -> None:
    rows = [r for r in nhl.challenge_rows() if r["opposed"] and r["year"] in nhl.CHALLENGE_YEARS]
    teams = {}
    for r in rows:
        w = nhl.split_team(re.sub(r"\[[^\]]*\]", "", r["winner"]))[0]
        lo = nhl.split_team(re.sub(r"\[[^\]]*\]", "", r["loser"]))[0]
        teams.setdefault(r["year"], {"winners": set(), "losers": set()})
        teams[r["year"]]["winners"].add(RENAME.get(w, w))
        teams[r["year"]]["losers"].add(RENAME.get(lo, lo))
    for y, t in teams.items():
        print(y, "winners:", sorted(t["winners"]), "| losers:", sorted(t["losers"]))
    named = {n for t in teams.values() for n in t["winners"] | t["losers"]}
    ids = pd.read_csv(OUT / "matrix_main.csv").id.tolist() + pd.read_csv(OUT / "matrix_era_indicator.csv").id.tolist()
    nhl_ids = [i for i in ids if "sports_nhl_" in i and not i.startswith("NOT_")]
    clash = []
    for i in nhl_ids:
        slug = i.split("franchise_")[-1] if "franchise_" in i else None
        if slug and any(re.sub(r"[^a-z0-9]", "_", n.lower()).strip("_") == slug for n in named):
            clash.append(i)
    print("remaining NHL positive literals:", len(nhl_ids))
    print("literals naming a team that appears in any 1900-1912 series:", clash)


if __name__ == "__main__":
    main()
