"""Kentucky Derby event table (32 election years). Parses raw files only.

Run: uv run python -m src.acquire.kentucky_derby
Primary: Wikipedia (winners table + per-year infobox dates).
Cross-check: kentuckyderby.com past winners (official) and ESPN list.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from datetime import datetime
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "kentucky_derby"
OUT = ROOT / "data" / "processed" / "events"
YEARS = list(range(1900, 2025, 4))
RETRIEVED = "2026-10-25"
WIKI = "https://en.wikipedia.org/wiki/"

FILES = {
    "wiki_kentucky_derby.html": WIKI + "Kentucky_Derby",
    "kdb_past_winners.html": "https://www.kentuckyderby.com/past-winners/",
    "espn_derby.html": "https://www.espn.com/horse-racing/story/_/id/44933880/who-won-kentucky-derby-all-winners-list",
    **{f"years/{y}.html": f"{WIKI}{y}_Kentucky_Derby" for y in YEARS},
}


def clean(s: object) -> str:
    s = re.sub(r"\[[^\]]*\]", "", str(s))
    return re.sub(r"[†‡*#]+", "", s).strip()


def key(s: str) -> str:
    s = unicodedata.normalize("NFKD", clean(s)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z]", "", s.lower())


def surname(s: str) -> str:
    s = unicodedata.normalize("NFKD", clean(s)).encode("ascii", "ignore").decode().lower()
    toks = [t for t in re.findall(r"[a-z']+", s) if t not in {"jr", "sr", "ii", "iii", "iv"}]
    return toks[-1] if toks else ""


def write_manifest() -> None:
    rows = []
    for rel, url in FILES.items():
        p = RAW / rel
        if p.exists():
            rows.append((rel, url, RETRIEVED, hashlib.sha256(p.read_bytes()).hexdigest()))
    pd.DataFrame(rows, columns=["file", "url", "retrieved", "sha256"]).to_csv(
        RAW / "MANIFEST.csv", index=False
    )


def infobox_date(path: Path) -> str | None:
    ib = BeautifulSoup(path.read_bytes(), "lxml").find("table", class_="infobox")
    if ib is None:
        return None
    for tr in ib.find_all("tr"):
        th = tr.find("th")
        if th and th.get_text(strip=True) == "Date":
            txt = tr.find("td").get_text(" ", strip=True)
            txt = re.sub(r"\[[^\]]*\]", "", txt).strip()
            return txt
    return None


def parse_date(txt: str | None) -> str | None:
    if not txt:
        return None
    txt = re.sub(r"\s*\(.*$", "", txt).strip()
    for fmt in ("%B %d, %Y", "%d %B %Y"):
        try:
            return datetime.strptime(txt, fmt).date().isoformat()
        except ValueError:
            pass
    return None


def wiki_winners() -> dict[int, dict]:
    for t in pd.read_html(RAW / "wiki_kentucky_derby.html"):
        if {"Year", "Winner", "Jockey", "Trainer"} <= set(map(str, t.columns)) and len(t) > 100:
            out = {}
            for _, r in t.iterrows():
                try:
                    y = int(float(r["Year"]))
                except ValueError:
                    continue
                out[y] = {
                    "horse": clean(r["Winner"]),
                    "jockey": clean(r["Jockey"]),
                    "trainer": clean(r["Trainer"]),
                }
            return out
    raise RuntimeError("winners table not found")


def official_winners() -> dict[int, dict]:
    t = pd.read_html(RAW / "kdb_past_winners.html")[0]
    return {
        int(r["Year"]): {
            "horse": clean(r["Winner"]),
            "jockey": clean(r["Jockey"]),
            "trainer": clean(r["Trainer"]),
        }
        for _, r in t.iterrows()
    }


def espn_winners() -> dict[int, tuple[str, str]]:
    txt = BeautifulSoup((RAW / "espn_derby.html").read_bytes(), "lxml").get_text("\n")
    out = {}
    for m in re.finditer(r"^\s*(\d{4}):\s*([^,\n]+),\s*([^\n]+?)\s*$", txt, re.MULTILINE):
        out[int(m[1])] = (m[2].strip(), m[3].strip())
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    wiki, off, espn = wiki_winners(), official_winners(), espn_winners()
    gaps = ["# kentucky_derby gaps / cross-check log", ""]
    rows = []
    for y in YEARS:
        txt = infobox_date(RAW / "years" / f"{y}.html")
        d = parse_date(txt)
        w = wiki.get(y)
        notes = []
        if d is None:
            gaps.append(
                f"- {y}: date not parseable from Wikipedia infobox (raw text: {txt!r}); left empty."
            )
        if w is None:
            gaps.append(f"- {y}: not in Wikipedia winners table.")
            rows.append({"year": y, "held": 0, "source_url": FILES["wiki_kentucky_derby.html"]})
            continue
        o = off.get(y)
        if o is None:
            gaps.append(f"- {y}: missing from kentuckyderby.com table.")
        else:
            for f, kf in (("horse", key), ("jockey", surname), ("trainer", surname)):
                if kf(w[f]) != kf(o[f]):
                    gaps.append(
                        f"- {y}: {f} DISAGREEMENT wikipedia={w[f]!r} kentuckyderby.com={o[f]!r}"
                    )
        e = espn.get(y)
        if e is None:
            gaps.append(f"- {y}: missing from ESPN list.")
        else:
            if key(e[0]) != key(w["horse"]):
                gaps.append(f"- {y}: horse DISAGREEMENT wikipedia={w['horse']!r} espn={e[0]!r}")
            if surname(e[1]) != surname(w["jockey"]):
                gaps.append(f"- {y}: jockey DISAGREEMENT wikipedia={w['jockey']!r} espn={e[1]!r}")
        rows.append(
            {
                "year": y,
                "held": 1 if d else 0,
                "completed_date": d,
                "start_date": d,
                "winner_horse": w["horse"],
                "winner_jockey": w["jockey"],
                "winner_trainer": w["trainer"],
                "source_url": f"{WIKI}{y}_Kentucky_Derby; {FILES['wiki_kentucky_derby.html']}; {FILES['kdb_past_winners.html']}",
                "notes": "; ".join(notes),
            }
        )
    gaps += [
        "",
        (
            "- Dates: single source (Wikipedia per-year infobox). kentuckyderby.com and "
            "ESPN lists give no dates, so dates are NOT independently cross-checked."
        ),
    ]
    df = pd.DataFrame(rows)
    cols = [
        "year",
        "held",
        "completed_date",
        "start_date",
        "winner_horse",
        "winner_jockey",
        "winner_trainer",
        "source_url",
        "notes",
    ]
    df = df.reindex(columns=cols)
    df.to_csv(OUT / "kentucky_derby.csv", index=False)
    (OUT / "kentucky_derby_gaps.md").write_text("\n".join(gaps) + "\n")
    write_manifest()
    print(df[["year", "held", "completed_date", "winner_horse"]].to_string(index=False))
    print(len(gaps) - 4, "gap/disagreement lines")


if __name__ == "__main__":
    main()
