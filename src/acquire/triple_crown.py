"""US Triple Crown event table (32 election years). Parses raw files only.

Run: uv run python -m src.acquire.triple_crown
triple_crown_won is COMPUTED: the same horse appears as winner of the Derby,
Preakness and Belmont in that year. Cross-checked against Wikipedia's list of
US Triple Crown winners.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from datetime import date as _date
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "triple_crown"
OUT = ROOT / "data" / "processed" / "events"
YEARS = list(range(1900, 2025, 4))
RETRIEVED = "2026-10-25"
WIKI = "https://en.wikipedia.org/wiki/"
BEL_YEAR_PAGES = [1920, 1948, 2000, 2004, 2008, 2012, 2016, 2020, 2024]

HORSE_PAGES = {
    1900: "Ildrim_(horse)",
    1904: "Delhi_(horse)",
    1908: "Colin_(horse)",
    1916: "Friar_Rock",
    1924: "Mad_Play",
    1928: "Vito_(horse)",
    1932: "Faireno",
    1936: "Granville_(horse)",
    1940: "Bimelech",
    1944: "Bounding_Home",
    1952: "One_Count",
    1956: "Needles_(horse)",
    1960: "Celtic_Ash",
    1964: "Quadrangle_(horse)",
    1968: "Stage_Door_Johnny",
    1972: "Riva_Ridge",
    1976: "Bold_Forbes",
    1980: "Temperence_Hill",
    1984: "Swale_(horse)",
    1988: "Risen_Star",
    1992: "A.P._Indy",
    1996: "Editor's_Note",
}

FILES = {
    "wiki_kentucky_derby.html": WIKI + "Kentucky_Derby",
    "kdb_past_winners.html": "https://www.kentuckyderby.com/past-winners/",
    "wiki_preakness.html": WIKI + "Preakness_Stakes",
    "wiki_belmont.html": WIKI + "Belmont_Stakes",
    "wiki_triple_crown.html": WIKI + "Triple_Crown_of_Thoroughbred_Racing",
    "nyra_belmont.html": "https://www.nyra.com/belmont-stakes/history/past-winners/",
    "freepps_belmont.html": "https://thefreepps.com/horse-racing/belmont-stakes-winners/",
    "freepps_preakness.html": "https://thefreepps.com/horse-racing/preakness-stakes-winners/",
    **{f"horse_pages/{y}.html": f"{WIKI}{n}" for y, n in HORSE_PAGES.items()},
    "hrn_belmont.html": "https://www.horseracingnation.com/stakes/Belmont_Stakes",
    **{f"belmont_years/{y}.html": f"{WIKI}{y}_Belmont_Stakes" for y in range(1900, 2025, 4)},
}


def clean(s: object) -> str:
    s = re.sub(r"\[[^\]]*\]", "", str(s))
    return re.sub(r"[†‡*#]+", "", s).strip()


def key(s: str) -> str:
    s = unicodedata.normalize("NFKD", clean(s)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z]", "", s.lower())


def write_manifest() -> None:
    rows = []
    for rel, url in FILES.items():
        p = RAW / rel
        if p.exists() and p.stat().st_size > 0:
            rows.append((rel, url, RETRIEVED, hashlib.sha256(p.read_bytes()).hexdigest()))
    pd.DataFrame(rows, columns=["file", "url", "retrieved", "sha256"]).to_csv(
        RAW / "MANIFEST.csv", index=False
    )


def table_by_cols(fname: str, cols: set[str], minlen: int = 100) -> pd.DataFrame:
    for t in pd.read_html(RAW / fname):
        if cols <= set(map(str, t.columns)) and len(t) >= minlen:
            return t
    raise RuntimeError(f"table with {cols} not found in {fname}")


def by_year(t: pd.DataFrame, namecol: str) -> dict[int, list[str]]:
    out: dict[int, list[str]] = {}
    for _, r in t.iterrows():
        m = re.match(r"^\s*(\d{4})", str(r["Year"]))
        if not m:
            continue
        name = clean(r[namecol])
        if name and not name.lower().startswith("no race"):
            out.setdefault(int(m[1]), []).append(name)
    return out


def not_held_years(t: pd.DataFrame) -> dict[int, str]:
    out = {}
    for _, r in t.iterrows():
        m = re.match(r"^\s*(\d{4})", str(r["Year"]))
        if m and re.search(r"no race|not held|not run", str(r.iloc[1]), re.IGNORECASE):
            out[int(m[1])] = clean(r.iloc[1])
    return out


def infobox_date(path: Path) -> str | None:
    if not path.exists() or path.stat().st_size == 0:
        return None
    ib = BeautifulSoup(path.read_bytes(), "lxml").find("table", class_="infobox")
    if ib is None:
        return None
    for tr in ib.find_all("tr"):
        th = tr.find("th")
        if th and th.get_text(strip=True) == "Date":
            txt = re.sub(r"\[[^\]]*\]", "", tr.find("td").get_text(" ", strip=True))
            txt = re.sub(r"\s*\(.*$", "", txt).strip()
            for fmt in ("%B %d, %Y", "%d %B %Y"):
                try:
                    return datetime.strptime(txt, fmt).date().isoformat()
                except ValueError:
                    pass
    return None


def horse_page_date(y: int) -> tuple[str | None, str]:
    """Belmont date from the winner's Wikipedia article, only where the text states it."""
    p = RAW / "horse_pages" / f"{y}.html"
    if not p.exists():
        return None, ""
    t = re.sub(r"\[[^\]]*\]", "", BeautifulSoup(p.read_bytes(), "lxml").get_text(" ", strip=True))
    t = re.sub(r"\s+", " ", t)
    if y == 1932:
        m = re.search(
            r"At age three in 1932,.*?then on June (\d{1,2}) led virtually all the way to win the third leg of the U\.S\. Triple Crown series, the Belmont Stakes",
            t,
        )
        if m:
            return _date(
                1932, 6, int(m[1])
            ).isoformat(), "stated in Faireno article (year from 'At age three in 1932')"
    if y == 1984:
        m = re.search(r"On June (\d{1,2}), 1984, eight days after the Belmont Stakes", t)
        if m:
            return (
                (_date(1984, 6, int(m[1])) - timedelta(days=8)).isoformat(),
                "computed: Swale article says death on June 17, 1984 was eight days after the Belmont",
            )
    return None, ""


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    gaps = ["# triple_crown gaps / cross-check log", ""]

    derby = by_year(
        table_by_cols("wiki_kentucky_derby.html", {"Year", "Winner", "Jockey"}), "Winner"
    )
    preak = by_year(table_by_cols("wiki_preakness.html", {"Year", "Horse", "Jockey"}), "Horse")
    bel_t = table_by_cols("wiki_belmont.html", {"Year", "Winner", "Jockey"})
    belmont = by_year(bel_t, "Winner")
    bel_not_held = not_held_years(bel_t)

    # second sources
    nyra_t = pd.read_html(RAW / "nyra_belmont.html")[0]
    nyra = by_year(nyra_t, "Horse")
    fpb = by_year(pd.read_html(RAW / "freepps_belmont.html")[0], "Winner")
    fpp = by_year(pd.read_html(RAW / "freepps_preakness.html")[0], "Winner")
    off_t = (
        pd.read_html(RAW / "kdb_past_winners.html")[0]
        if (RAW / "kdb_past_winners.html").exists()
        else None
    )
    off_derby = by_year(off_t, "Winner") if off_t is not None else {}

    # published Triple Crown list (Wikipedia, US table)
    tc_pub: dict[int, str] = {}
    for t in pd.read_html(RAW / "wiki_triple_crown.html"):
        if list(t.columns)[:3] == ["Year", "Winner", "Jockey"] and 1919 in set(
            pd.to_numeric(t["Year"], errors="coerce").dropna().astype(int)
        ):
            for _, r in t.dropna(subset=["Year"]).iterrows():
                tc_pub[int(float(r["Year"]))] = clean(r["Winner"])

    def cmp(label: str, y: int, a: list[str], b: list[str] | None, other: str) -> None:
        if b is None:
            gaps.append(f"- {y}: {label} missing from {other}.")
        elif {key(x) for x in a} != {key(x) for x in b}:
            gaps.append(f"- {y}: {label} DISAGREEMENT wikipedia={a} {other}={b}")

    rows = []
    computed_tc: dict[int, str] = {}
    for y in range(1900, 2025):  # all years, for the cross-check against the published list
        d, p, b = derby.get(y, []), preak.get(y, []), belmont.get(y, [])
        common = {key(x) for x in d} & {key(x) for x in p} & {key(x) for x in b}
        if common:
            computed_tc[y] = next(x for x in d if key(x) in common)
    if {y: key(v) for y, v in computed_tc.items()} != {y: key(v) for y, v in tc_pub.items()}:
        gaps.append(
            f"- Computed Triple Crown years {sorted(computed_tc)} != Wikipedia list {sorted(tc_pub)}"
        )
    else:
        gaps.append(
            f"- Computed Triple Crown years 1900-2024 {sorted(computed_tc)} match Wikipedia's "
            "published list of US Triple Crown winners exactly."
        )

    for y in YEARS:
        d, p, b = derby.get(y, []), preak.get(y, []), belmont.get(y, [])
        src = "; ".join(
            [
                FILES["wiki_kentucky_derby.html"],
                FILES["wiki_preakness.html"],
                FILES["wiki_belmont.html"],
            ]
        )
        if y not in belmont:
            why = bel_not_held.get(y, "no Belmont row")
            rows.append(
                {
                    "year": y,
                    "held": 0,
                    "source_url": src,
                    "notes": f"Belmont not run: {why}. Derby winner {d}, Preakness winner {p} "
                    "(not recorded in columns because held=0). triple_crown_won=0 by absence logic.",
                }
            )
            gaps.append(f"- {y}: Belmont Stakes not run per Wikipedia ({why}).")
            continue
        cmp("derby", y, d, off_derby.get(y), "kentuckyderby.com")
        cmp("preakness", y, p, fpp.get(y), "thefreepps")
        cmp("belmont", y, b, nyra.get(y), "nyra")
        cmp("belmont", y, b, fpb.get(y), "thefreepps")
        date = infobox_date(RAW / "belmont_years" / f"{y}.html")
        hp_note = ""
        if date is None:
            date, hp_note = horse_page_date(y)
        if date is None:
            gaps.append(
                f"- {y}: Belmont date not sourced (no Wikipedia per-year page, no date in the winner's Wikipedia article; NYRA/FreePPs/HRN lists have no "
                "dates). completed_date left empty although held=1."
            )
        won = y in computed_tc
        dd = infobox_date(RAW.parent / "kentucky_derby" / "years" / f"{y}.html")
        note = hp_note if date else "Belmont date not sourced (see gaps)"
        if date and dd and dd > date:
            note = f"Belmont ({date}) was run BEFORE the Derby ({dd}); order odd that year"
            gaps.append(f"- {y}: {note}.")
        rows.append(
            {
                "year": y,
                "held": 1,
                "completed_date": date,
                "triple_crown_won": int(won),
                "winner_horse": computed_tc.get(y),
                "derby_winner": " / ".join(d),
                "preakness_winner": " / ".join(p),
                "belmont_winner": " / ".join(b),
                "source_url": src
                + f"; {FILES['wiki_triple_crown.html']}; {FILES['nyra_belmont.html']}; "
                + f"{FILES['freepps_belmont.html']}; {FILES['freepps_preakness.html']}"
                + (f"; {WIKI}{y}_Belmont_Stakes" if date and not hp_note else "")
                + (f"; {FILES[f'horse_pages/{y}.html']}" if hp_note else ""),
                "notes": note,
            }
        )
    gaps += [
        "",
        (
            "- Ordering: Wikipedia (Preakness and Belmont pages) says that prior to 1931/1932 the Preakness was run "
            "before the Derby eleven times; Preakness and Derby were run the same day on 1917-05-12 and 1922-05-13; "
            "the Belmont was run before the Preakness on eleven occasions; since 1931 the order is Derby, "
            "Preakness, Belmont. triple_crown_won here only requires the same horse to win all three in the "
            "calendar year, regardless of order."
        ),
        (
            "- 1918: Wikipedia lists two Preakness winners (War Cloud and Jack Hare Jr., two divisions) and one "
            "Belmont winner (Johren); both Preakness names are joined with ' / ' in preakness_winner."
        ),
        "- Belmont per-year Wikipedia pages exist only for "
        + ", ".join(map(str, BEL_YEAR_PAGES))
        + " among "
        "election years; all other Belmont dates are unsourced.",
    ]
    gaps.append(
        "- Follow-up search: Wikipedia articles for each winner were fetched (raw/horse_pages); only 1932 and "
        "1984 state a usable date. The 1900 Ildrim article merely cites a 'May 25, 1900 New York Times "
        "article' (a publication date, not stated as the race date), so 1900 is left empty. Daily Racing Form "
        "archive (drf.uky.edu) and the Wikipedia top-three-finishers page were not fetchable. Preakness dates "
        "were not pursued."
    )
    cols = [
        "year",
        "held",
        "completed_date",
        "start_date",
        "triple_crown_won",
        "winner_horse",
        "derby_winner",
        "preakness_winner",
        "belmont_winner",
        "source_url",
        "notes",
    ]
    df = pd.DataFrame(rows).reindex(columns=cols)
    df["triple_crown_won"] = df["triple_crown_won"].astype("Int64")
    df.to_csv(OUT / "triple_crown.csv", index=False)
    (OUT / "triple_crown_gaps.md").write_text("\n".join(gaps) + "\n")
    write_manifest()
    print(
        df[["year", "held", "completed_date", "triple_crown_won", "belmont_winner"]].to_string(
            index=False
        )
    )


if __name__ == "__main__":
    main()
