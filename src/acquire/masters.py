"""Masters Tournament event table (32 election years). Parses raw files only.

Run: uv run python -m src.acquire.masters
Primary: Wikipedia list of champions + per-year infobox 'Dates' (final round = last day).
Cross-check (champion only): Golf Channel and NBC Sports year-by-year lists; ESPN list.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from datetime import date, datetime
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "masters"
OUT = ROOT / "data" / "processed" / "events"
YEARS = list(range(1900, 2025, 4))
RETRIEVED = "2026-10-25"
WIKI = "https://en.wikipedia.org/wiki/"
LIST_URL = WIKI + "List_of_Masters_Tournament_champions"

FILES = {
    "wiki_masters_champions.html": LIST_URL,
    "wiki_masters_tournament.html": WIKI + "Masters_Tournament",
    "golfchannel.html": "https://www.golfchannel.com/pga-tour/masters-winners-champions-results-scores-records-every-year",
    "nbc_masters.html": "https://www.nbcsports.com/golf/news/complete-list-past-champions-masters-tournament",
    "espn_masters.html": "https://www.espn.com/golf/story/_/id/39894241/who-won-masters-all-augusta-winners-list",
    **{f"years/{y}.html": f"{WIKI}{y}_Masters_Tournament" for y in range(1936, 2025, 4)},
}


def clean(s: object) -> str:
    s = re.sub(r"\[[^\]]*\]", "", str(s))
    s = re.sub(r"\(\d+\)", "", s)  # '(2)' career-title counters
    return re.sub(r"[†‡*#]+", "", s).strip()


def key(s: str) -> str:
    s = unicodedata.normalize("NFKD", clean(s)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z]", "", s.lower())


def election_day(y: int) -> date:
    d = date(y, 11, 1)
    return date(y, 11, d.day + (7 - d.weekday()) % 7 + 1)


def write_manifest() -> None:
    rows = []
    for rel, url in FILES.items():
        p = RAW / rel
        if p.exists() and p.stat().st_size > 0:
            rows.append((rel, url, RETRIEVED, hashlib.sha256(p.read_bytes()).hexdigest()))
    pd.DataFrame(rows, columns=["file", "url", "retrieved", "sha256"]).to_csv(
        RAW / "MANIFEST.csv", index=False
    )


def infobox_dates(path: Path) -> tuple[str | None, str | None, str | None]:
    """(start, end, raw text) from the infobox 'Dates' row."""
    ib = BeautifulSoup(path.read_bytes(), "lxml").find("table", class_="infobox")
    if ib is None:
        return None, None, None
    for tr in ib.find_all("tr"):
        th = tr.find("th")
        if th and th.get_text(strip=True) in ("Dates", "Date"):
            raw = re.sub(r"\[[^\]]*\]", "", tr.find("td").get_text(" ", strip=True)).strip()
            txt = re.sub(r"\s*\(.*$", "", raw).strip()
            m = re.match(
                r"^([A-Za-z]+)\s+(\d{1,2})\s*[–-]\s*(?:([A-Za-z]+)\s+)?(\d{1,2}),\s*(\d{4})$", txt
            )
            if not m:
                return None, None, raw
            m1, d1, m2, d2, yy = m.groups()
            s = datetime.strptime(f"{m1} {d1} {yy}", "%B %d %Y").date()
            e = datetime.strptime(f"{m2 or m1} {d2} {yy}", "%B %d %Y").date()
            return s.isoformat(), e.isoformat(), raw
    return None, None, None


def wiki_champs() -> dict[int, str | None]:
    t = None
    for cand in pd.read_html(RAW / "wiki_masters_champions.html"):
        if {"Year", "Champion"} <= set(map(str, cand.columns)) and len(cand) > 80:
            t = cand
            break
    if t is None:
        raise RuntimeError("champions table not found")
    out: dict[int, str | None] = {}
    for _, r in t.iterrows():
        try:
            y = int(float(r["Year"]))
        except ValueError:
            continue
        c = r["Champion"]
        out[y] = None if pd.isna(c) or clean(c).lower().startswith("none") else clean(c)
    return out


def list_champs(fname: str) -> dict[int, str]:
    out = {}
    for t in pd.read_html(RAW / fname):
        for _, r in t.iterrows():
            m = re.match(r"^\s*(\d{4})\s*$", str(r.iloc[0]))
            if m:
                out[int(m[1])] = clean(r.iloc[1])
    return out


def espn_champs() -> dict[int, str]:
    txt = BeautifulSoup((RAW / "espn_masters.html").read_bytes(), "lxml").get_text(" ")
    out = {}
    for m in re.finditer(r"(\d{4})\s+([A-Z][A-Za-z.' -]+?)\*?(?=\s+\d{4}\s|\s*\*Won|\s*$)", txt):
        if not m[2].lower().startswith("no tournament"):
            out.setdefault(int(m[1]), clean(m[2]))
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    champs = wiki_champs()
    gc, nbc, espn = list_champs("golfchannel.html"), list_champs("nbc_masters.html"), espn_champs()
    gaps = ["# masters gaps / cross-check log", ""]
    rows = []
    for y in YEARS:
        src = LIST_URL
        if y not in champs:
            rows.append(
                {
                    "year": y,
                    "held": 0,
                    "source_url": src,
                    "notes": f"Not held: tournament first held in {min(champs)} per Wikipedia list",
                }
            )
            continue
        if champs[y] is None:
            rows.append(
                {
                    "year": y,
                    "held": 0,
                    "source_url": src,
                    "notes": "Not held (no champion in Wikipedia list; wartime cancellation noted there)",
                }
            )
            gaps.append(f"- {y}: not held per Wikipedia list (no champion).")
            for lbl, d in (("golfchannel", gc), ("nbc", nbc), ("espn", espn)):
                if d.get(y):
                    gaps.append(
                        f"- {y}: DISAGREEMENT {lbl} lists champion {d[y]!r} for a year Wikipedia says not held."
                    )
            continue
        start, end, raw = infobox_dates(RAW / "years" / f"{y}.html")
        notes = []
        if end is None:
            gaps.append(f"- {y}: dates not parseable from infobox (raw {raw!r}); left empty.")
        else:
            notes.append(f"Wikipedia infobox dates: {raw}")
            if date.fromisoformat(end) >= election_day(y):
                notes.append("COMPLETED ON/AFTER ELECTION DAY (postponed)")
            if end[:7] != f"{y}-04":
                notes.append(f"final round not in April: {end}")
        for lbl, d in (("golfchannel", gc), ("nbc", nbc), ("espn", espn)):
            if y not in d:
                if lbl != "nbc" or y < 2026:
                    gaps.append(f"- {y}: champion missing from {lbl} list.")
            elif key(d[y]) != key(champs[y]):
                gaps.append(f"- {y}: champion DISAGREEMENT wikipedia={champs[y]!r} {lbl}={d[y]!r}")
        rows.append(
            {
                "year": y,
                "held": 1 if end else 0,
                "completed_date": end,
                "start_date": start,
                "winner": champs[y],
                "source_url": f"{src}; {WIKI}{y}_Masters_Tournament; {FILES['golfchannel.html']}",
                "notes": "; ".join(notes),
            }
        )
    gaps += [
        "",
        (
            "- Dates are single-source (Wikipedia per-year infobox); golfchannel/NBC/ESPN lists "
            "give champions only. completed_date = last day of the infobox date range (final round)."
        ),
    ]
    cols = ["year", "held", "completed_date", "start_date", "winner", "source_url", "notes"]
    df = pd.DataFrame(rows).reindex(columns=cols)
    df.to_csv(OUT / "masters.csv", index=False)
    (OUT / "masters_gaps.md").write_text("\n".join(gaps) + "\n")
    write_manifest()
    print(df[["year", "held", "completed_date", "winner"]].to_string(index=False))
    print("\n".join(gaps))


if __name__ == "__main__":
    main()
