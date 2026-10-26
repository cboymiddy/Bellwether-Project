"""Build data/processed/outcomes.csv from fetched raw pages (never from memory).

Sources: National Archives per-year pages (EC winner party + EV) and UCSB American Presidency
Project per-year pages (EV and popular vote by nominee). Incumbent party for year Y is the
EC-winning party of Y-4 (no president changed party in office during 1900-2024).
"""

import hashlib
import re
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup

RAW = Path(__file__).resolve().parents[2] / "data" / "raw"
OUT = Path(__file__).resolve().parents[2] / "data" / "processed"
PARTY = {"Republican": "R", "Democratic": "D", "Democratic-Republican": "D"}


def archives_winner(year: int) -> tuple[str, int]:
    text = BeautifulSoup((RAW / "archives" / f"{year}.html").read_text(), "lxml").get_text(" ", strip=True)
    party = re.search(r"President .+? \[(\w+)\] Main Opponent", text).group(1)
    ev = int(re.search(r"Electoral Vote\*?\s+Winner:\s+(\d+)", text).group(1))
    return party, ev


def ucsb_rows(year: int) -> list[dict]:
    soup = BeautifulSoup((RAW / "ucsb" / f"{year}.html").read_text(), "lxml")
    for table in soup.find_all("table"):
        if "Nominees" not in table.get_text():
            continue
        rows = []
        for tr in table.find_all("tr"):
            c = [x.get_text(" ", strip=True) for x in tr.find_all("td")]
            if len(c) in (8, 9) and c[-4].isdigit() and c[-2].replace(",", "").isdigit():
                party = next(x for x in c if x.replace(" ", "").replace("-", "").isalpha())
                rows.append({"party": party, "ev": int(c[-4]), "pop": int(c[-2].replace(",", ""))})
        if rows:
            return rows
    raise ValueError(f"no summary table for {year}")


def main() -> None:
    recs = {}
    for y in range(1896, 2025, 4):
        a_party, a_ev = archives_winner(y)
        rows = ucsb_rows(y)
        ev_win = max(rows, key=lambda r: r["ev"])
        pv_win = max(rows, key=lambda r: r["pop"])
        recs[y] = {
            "ec_party": a_party, "ec_ev": a_ev, "ucsb_ec_party": PARTY.get(ev_win["party"], ev_win["party"]),
            "ucsb_ec_ev": ev_win["ev"], "pv_party": PARTY.get(pv_win["party"], pv_win["party"]),
        }
        assert a_party == recs[y]["ucsb_ec_party"], (y, recs[y])
        if a_ev != ev_win["ev"]:
            print(f"NOTE {y}: EV count differs, archives={a_ev} ucsb={ev_win['ev']} (party agrees)")
    out = []
    for y in range(1900, 2025, 4):
        inc = recs[y - 4]["ec_party"]
        out.append({
            "year": y, "incumbent_party": inc, "ec_winner_party": recs[y]["ec_party"],
            "pv_winner_party": recs[y]["pv_party"],
            "incumbent_party_won": int(recs[y]["ec_party"] == inc),
            "incumbent_party_won_popvote": int(recs[y]["pv_party"] == inc),
        })
    df = pd.DataFrame(out)
    OUT.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT / "outcomes.csv", index=False)
    print(df.to_string(index=False))
    print("EC wins/losses:", df.incumbent_party_won.sum(), (1 - df.incumbent_party_won).sum())
    pv = df.incumbent_party_won_popvote
    print("PV wins/losses:", pv.sum(), (1 - pv).sum())
    print("PV-vs-EC flips:", df.loc[df.incumbent_party_won != pv, "year"].tolist())


def manifest() -> None:
    lines = ["file,sha256"]
    for p in sorted(RAW.rglob("*.html")):
        lines.append(f"{p.relative_to(RAW)},{hashlib.sha256(p.read_bytes()).hexdigest()}")
    (RAW / "MANIFEST.csv").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
    manifest()
