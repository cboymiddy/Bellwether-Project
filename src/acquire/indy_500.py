"""Indianapolis 500 event table (32 election years). Parses raw files only.

Run: uv run python -m src.acquire.indy_500
Primary: Wikipedia list of Indianapolis 500 winners (date, driver, make/model, laps).
Cross-checks: IMS official winners table (driver, car/chassis) and champcarstats.com
season pages (race date, winner).
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
RAW = ROOT / "data" / "raw" / "indy_500"
OUT = ROOT / "data" / "processed" / "events"
YEARS = list(range(1900, 2025, 4))
RETRIEVED = "2026-10-25"
WIKI_URL = "https://en.wikipedia.org/wiki/List_of_Indianapolis_500_winners"
IMS_URL = (
    "https://www.indianapolismotorspeedway.com/events/indy500/history/historical-stats/"
    "race-stats/summaries/indianapolis-500-race-winners"
)

FILES = {
    "wiki_indy_winners.html": WIKI_URL,
    "wiki_indy_500.html": "https://en.wikipedia.org/wiki/Indianapolis_500",
    "ims_winners.html": IMS_URL,
    "indymotorspeedway_500wins.html": "https://www.indymotorspeedway.com/500wins.html",
    **{
        f"champcar/{y}.html": f"https://www.champcarstats.com/year/{y}.htm"
        for y in range(1912, 2025, 4)
    },
}


def clean(s: object) -> str:
    s = re.sub(r"\[[^\]]*\]", "", str(s))
    s = re.sub(r"\((?:[A-Z]{3}|R)\)", "", s)  # country codes, rookie flag
    return re.sub(r"[†‡*#]+", "", s).strip()


def surname(s: str) -> str:
    s = unicodedata.normalize("NFKD", clean(s)).encode("ascii", "ignore").decode().lower()
    toks = [t for t in re.findall(r"[a-z']+", s) if t not in {"jr", "sr", "ii", "iii"}]
    return toks[-1] if toks else ""


def write_manifest() -> None:
    rows = []
    for rel, url in FILES.items():
        p = RAW / rel
        if p.exists() and p.stat().st_size > 0:
            rows.append((rel, url, RETRIEVED, hashlib.sha256(p.read_bytes()).hexdigest()))
    pd.DataFrame(rows, columns=["file", "url", "retrieved", "sha256"]).to_csv(
        RAW / "MANIFEST.csv", index=False
    )


def parse_wiki_date(txt: str, year: int) -> tuple[str | None, str | None]:
    """Return (start_date, end_date) ISO strings from e.g. 'May 30', 'May 28–30', 'August 23'."""
    txt = re.sub(r"\[[^\]]*\]", "", txt).strip()
    m = re.match(r"^([A-Za-z]+)\s+(\d{1,2})(?:\s*[–-]\s*(?:([A-Za-z]+)\s+)?(\d{1,2}))?$", txt)
    if not m:
        return None, None
    mon1, d1, mon2, d2 = m.groups()
    start = datetime.strptime(f"{mon1} {d1} {year}", "%B %d %Y").date()
    end = datetime.strptime(f"{mon2 or mon1} {d2 or d1} {year}", "%B %d %Y").date()
    return start.isoformat(), end.isoformat()


def election_day(y: int) -> date:
    d = date(y, 11, 1)
    first_monday = d.day + (7 - d.weekday()) % 7  # Monday == 0
    return date(y, 11, first_monday + 1)


def wiki_rows() -> tuple[dict[int, list[dict]], dict[int, str]]:
    t = None
    for cand in pd.read_html(RAW / "wiki_indy_winners.html"):
        flat = [
            "_".join(dict.fromkeys(c)) if isinstance(c, tuple) else str(c) for c in cand.columns
        ]
        if "Date" in flat and "Make/Model" in flat and len(cand) > 100:
            cand.columns = flat
            t = cand
            break
    if t is None:
        raise RuntimeError("winners table not found")
    rows: dict[int, list[dict]] = {}
    not_held: dict[int, str] = {}
    for _, r in t.iterrows():
        ytxt = re.sub(r"\[[^\]]*\]", "", str(r["Year"]))
        if "not held" in str(r["Date"]).lower():
            m = re.match(r"(\d{4})\s*[–-]\s*(\d{4})", ytxt)
            if m:
                for yy in range(int(m[1]), int(m[2]) + 1):
                    not_held[yy] = clean(r["Date"])
            continue
        m = re.match(r"^(\d{4})(\*?)", ytxt.strip())
        if not m:
            continue
        rows.setdefault(int(m[1]), []).append(
            {
                "star": bool(m[2]),
                "date": str(r["Date"]),
                "driver": clean(r["Driver"]),
                "make": clean(r["Make/Model"]),
                "team": clean(r["Team"]),
                "laps": r["Distance_Laps"],
            }
        )
    return rows, not_held


def ims_rows() -> dict[int, str]:
    t = pd.read_html(RAW / "ims_winners.html")[0]
    out: dict[int, list[str]] = {}
    for _, r in t.iterrows():
        out.setdefault(int(r["Year"]), []).append(clean(r["Driver"]))
    return {y: " / ".join(v) for y, v in out.items()}


def champcar_race(y: int) -> tuple[str | None, str | None]:
    p = RAW / "champcar" / f"{y}.html"
    if not p.exists():
        return None, None
    s = BeautifulSoup(p.read_bytes(), "lxml")
    for x in s(["script", "style"]):
        x.decompose()
    t = re.sub(r"\s+", " ", s.get_text(" ", strip=True))
    parts = re.split(r"(\b\d{1,2}/\d{1,2}/\d{2}\b)", t)
    for i in range(1, len(parts) - 1, 2):
        seg = parts[i + 1]
        if (
            not re.search(r"Indy 500|Indianapolis 500|\d00 Mile Sweepstakes", seg)
            or "Grand Prix" in seg
        ):
            continue
        m = re.search(r"Indianapolis\s+\d+(?:\.\d+)?\s+[A-Z]{2}\s+(.+?)\s*$", seg)
        mo, da, yy = (int(x) for x in parts[i].split("/"))
        if yy != y % 100:
            continue
        return date(y, mo, da).isoformat(), (m[1] if m else None)
    return None, None


def names(s: str) -> set[str]:
    return {surname(x) for x in re.split(r"\s*(?:/|-|&| and )\s*", s) if x.strip()}


def agree(y: int, wiki: str, other: str, label: str, gaps: list[str]) -> None:
    a, b = names(wiki), names(other)
    if a == b:
        return
    if a < b or b < a:
        gaps.append(
            f"- {y}: driver partly differs (relief/co-driver credit): wikipedia={wiki!r} {label}={other!r}"
        )
    else:
        gaps.append(f"- {y}: driver DISAGREEMENT wikipedia={wiki!r} {label}={other!r}")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    wiki, not_held = wiki_rows()
    ims = ims_rows()
    gaps = ["# indy_500 gaps / cross-check log", ""]
    out = []
    for y in YEARS:
        base = {"year": y, "source_url": WIKI_URL + "; " + IMS_URL}
        if y not in wiki:
            why = not_held.get(y)
            if why is None:
                why = f"no row in Wikipedia winners list (first running listed is {min(wiki)})"
            out.append({**base, "held": 0, "notes": f"Not held: {why}"})
            gaps.append(f"- {y}: not held per Wikipedia list ({why}).")
            if y in ims:
                gaps.append(
                    f"- {y}: DISAGREEMENT IMS table lists a winner for a year Wikipedia says not held."
                )
            continue
        rs = wiki[y]
        start, end = parse_wiki_date(rs[0]["date"], y)
        notes = []
        if end is None:
            gaps.append(f"- {y}: date {rs[0]['date']!r} not parseable; left empty.")
        if start != end:
            notes.append(f"race spanned {start} to {end} per Wikipedia ({rs[0]['date']})")
        laps = rs[0]["laps"]
        if any(r["star"] for r in rs) or (str(laps).isdigit() and int(laps) < 200):
            notes.append(
                f"shortened/unusual race (asterisk or <200 laps in Wikipedia list; {laps} laps)"
            )
        if end and date.fromisoformat(end) >= election_day(y):
            notes.append("COMPLETED ON/AFTER ELECTION DAY")
        if end and end[:7] not in (f"{y}-05",):
            notes.append(f"not run in May: {end}")
        driver = " / ".join(r["driver"] for r in rs)
        if len(rs) > 1:
            notes.append("multiple credited winners (relief driver)")
        # cross-checks
        if y in ims:
            agree(y, driver, ims[y], "IMS", gaps)
        else:
            gaps.append(f"- {y}: missing from IMS winners table.")
        cdate, cwin = champcar_race(y)
        if cdate is None:
            gaps.append(
                f"- {y}: no Indianapolis 500 entry parsed from champcarstats.com (date not cross-checked)."
            )
        else:
            if cdate != end:
                notes.append(f"date disputed: champcarstats says {cdate}")
                gaps.append(f"- {y}: date DISAGREEMENT wikipedia={end} champcarstats={cdate}")
            if cwin:
                agree(y, driver, cwin, "champcarstats", gaps)
        out.append(
            {
                **base,
                "held": 1 if end else 0,
                "completed_date": end,
                "start_date": start,
                "winner_driver": driver,
                "winner_car_make": " / ".join(dict.fromkeys(r["make"] for r in rs)),
                "notes": "; ".join(notes),
            }
        )
    cols = [
        "year",
        "held",
        "completed_date",
        "start_date",
        "winner_driver",
        "winner_car_make",
        "source_url",
        "notes",
    ]
    df = pd.DataFrame(out).reindex(columns=cols)
    df.to_csv(OUT / "indy_500.csv", index=False)
    (OUT / "indy_500_gaps.md").write_text("\n".join(gaps) + "\n")
    write_manifest()
    print(
        df[["year", "held", "completed_date", "winner_driver", "winner_car_make"]].to_string(
            index=False
        )
    )
    print("\n".join(gaps))


if __name__ == "__main__":
    main()
