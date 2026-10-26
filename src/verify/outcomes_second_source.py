"""Re-verify data/processed/outcomes.csv (all 32 years) against a second, independent source.

Phase 0 used the National Archives (primary) and UCSB (cross-check). This uses Wikipedia pages
fetched into data/raw/outcomes_second_source/: the List of presidents (term dates and party, giving
the sitting president's party on Election Day and the winner's party) and the list of elections in
which the Electoral College winner lost the popular vote. Read-only: outcomes.csv is not modified.
"""

import datetime as dt
import hashlib
import re

import pandas as pd
from bs4 import BeautifulSoup

from src.config import ROOT, election_day, election_years

RAW = ROOT / "data" / "raw" / "outcomes_second_source"
DATE = re.compile(r"([A-Z][a-z]+) (\d{1,2}), (\d{4})")
PARTY = {"Republican": "R", "Democratic": "D"}


def soup(name: str) -> BeautifulSoup:
    return BeautifulSoup((RAW / name).read_text(), "lxml")


def presidents() -> list[dict]:
    tb = soup("List_of_presidents_of_the_United_States.html").find_all("table")[0]
    out = []
    for tr in tb.find_all("tr"):
        c = [x.get_text(" ", strip=True) for x in tr.find_all(["td", "th"])]
        if len(c) >= 6 and c[0].isdigit():
            dates = [dt.datetime.strptime(" ".join(m), "%B %d %Y").date() for m in DATE.findall(re.sub(r"\[[^\]]*\]", "", c[3]))]
            party = re.sub(r"\[[^\]]*\]|\s+", " ", c[5]).strip()
            out.append({"name": re.sub(r"\s*\(.*", "", c[2]).strip(), "start": dates[0],
                        "end": dates[1] if len(dates) > 1 else dt.date(2100, 1, 1), "party": party})
    return out


def in_office(pres: list[dict], day: dt.date) -> dict:
    hit = [p for p in pres if p["start"] <= day < p["end"]]
    assert len(hit) == 1, (day, hit)
    return hit[0]


def lost_pv_table() -> pd.DataFrame:
    page = soup("List_of_United_States_presidential_elections_in_which_the_winner_lost_the_popular_vote.html")
    tb = next(t for t in page.find_all("table") if "sortable" in (t.get("class") or []))
    rows = []
    for tr in tb.find_all("tr"):
        c = [x.get_text(" ", strip=True) for x in tr.find_all(["td", "th"])]
        yr = re.sub(r"\[[^\]]*\]", "", c[0]).strip() if c else ""
        if re.fullmatch(r"\d{4}", yr):
            rows.append({"year": int(yr), "winner": c[1], "winner_party": c[3], "runner_up": c[10], "runner_up_party": c[12]})
    return pd.DataFrame(rows)


def main() -> None:
    o = pd.read_csv(ROOT / "data" / "processed" / "outcomes.csv").set_index("year")
    pres = presidents()
    lost = lost_pv_table()
    out = []
    for y in election_years():
        inc = in_office(pres, election_day(y))
        win = in_office(pres, dt.date(y + 1, 4, 1))
        ip, wp = PARTY[inc["party"]], PARTY[win["party"]]
        lp = lost[lost.year == y]
        pv = (lp.runner_up_party.iloc[0] if len(lp) else wp)
        r = o.loc[y]
        out.append({"year": y, "sitting_president": inc["name"], "second_incumbent_party": ip,
                    "outcomes_incumbent_party": r.incumbent_party, "winner_taking_office": win["name"],
                    "second_ec_winner_party": wp, "outcomes_ec_winner_party": r.ec_winner_party,
                    "second_pv_winner_party": pv, "outcomes_pv_winner_party": r.pv_winner_party,
                    "second_incumbent_won": int(ip == wp), "outcomes_incumbent_won": int(r.incumbent_party_won),
                    "second_incumbent_won_pv": int(ip == pv), "outcomes_incumbent_won_pv": int(r.incumbent_party_won_popvote)})
    df = pd.DataFrame(out)
    df["all_agree"] = ((df.second_incumbent_party == df.outcomes_incumbent_party)
                       & (df.second_ec_winner_party == df.outcomes_ec_winner_party)
                       & (df.second_pv_winner_party == df.outcomes_pv_winner_party)
                       & (df.second_incumbent_won == df.outcomes_incumbent_won)
                       & (df.second_incumbent_won_pv == df.outcomes_incumbent_won_pv))
    df.to_csv(ROOT / "reports" / "real_search" / "outcomes_second_source_check.csv", index=False)
    man = ["file,url,retrieved,sha256"]
    for p in sorted(RAW.glob("*.html")):
        man.append(f"{p.name},https://en.wikipedia.org/wiki/{p.stem},2026-10-25,{hashlib.sha256(p.read_bytes()).hexdigest()}")
    (RAW / "MANIFEST.csv").write_text("\n".join(man) + "\n")
    print("lost-popular-vote elections in range:", lost[lost.year.between(1900, 2024)].year.tolist())
    print("years checked:", len(df), "| all five fields agree in:", int(df.all_agree.sum()))
    bad = df[~df.all_agree]
    if len(bad):
        print(bad.to_string(index=False))
    print(df[["year", "sitting_president", "outcomes_incumbent_party", "winner_taking_office", "outcomes_ec_winner_party", "outcomes_pv_winner_party"]].to_string(index=False))


if __name__ == "__main__":
    main()
