"""Wimbledon gentlemen's singles event table (32 election years). Raw files only.

Run: uv run python -m src.acquire.wimbledon_mens_singles
Primary: Wikipedia list of champions (champion, runner-up) + per-year championships
infobox date range. Cross-check: topendsports.com winners list (champion, runner-up).
completed_date is the LAST DAY OF THE TOURNAMENT per the infobox (a proxy for the final;
no source fetched states the men's final date separately).
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
RAW = ROOT / "data" / "raw" / "wimbledon_mens_singles"
OUT = ROOT / "data" / "processed" / "events"
YEARS = list(range(1900, 2025, 4))
RETRIEVED = "2026-10-25"
WIKI = "https://en.wikipedia.org/wiki/"
LIST_URL = WIKI + "List_of_Wimbledon_gentlemen%27s_singles_champions"

FILES = {
    "wiki_champions.html": LIST_URL,
    "topend_winners.html": "https://www.topendsports.com/events/tennis-grand-slam/wimbledon/winners-men.htm",
    **{
        f"years/{y}.html": f"{WIKI}{y}_Wimbledon_Championships_%E2%80%93_Men%27s_singles"
        for y in YEARS
    },
    **{f"years/{y}_championships.html": f"{WIKI}{y}_Wimbledon_Championships" for y in YEARS},
}


def clean(s: object) -> str:
    s = re.sub(r"\[[^\]]*\]", "", str(s))
    s = re.sub(r"\((?:\d+/\d+|[A-Za-z ]+)\)", "", s)  # '(4/4)' title counters, '(Italy)' countries
    return re.sub(r"[†‡*#◊]+", "", s).strip()


def key(s: str) -> str:
    s = unicodedata.normalize("NFKD", clean(s)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z]", "", s.lower())


def surname(s: str) -> str:
    s = unicodedata.normalize("NFKD", clean(s)).encode("ascii", "ignore").decode().lower()
    toks = re.findall(r"[a-z']+", s)
    return toks[-1] if toks else ""


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


def tournament_dates(y: int) -> tuple[str | None, str | None, str | None]:
    p = RAW / "years" / f"{y}_championships.html"
    if not p.exists() or p.stat().st_size == 0:
        return None, None, None
    ib = BeautifulSoup(p.read_bytes(), "lxml").find("table", class_="infobox")
    if ib is None:
        return None, None, None
    for tr in ib.find_all("tr"):
        th = tr.find("th")
        if th and th.get_text(strip=True) == "Date":
            raw = re.sub(r"\[[^\]]*\]", "", tr.find("td").get_text(" ", strip=True)).strip()
            txt = re.sub(r"\(.*?\)", "", raw).strip()
            txt = re.sub(r"\s+\d{4}$", "", txt)
            m = re.match(r"^(\d{1,2})(?:\s+([A-Za-z]+))?\s*[–-]\s*(\d{1,2})\s+([A-Za-z]+)$", txt)
            if not m:
                return None, None, raw
            d1, m1, d2, m2 = m.groups()
            s = datetime.strptime(f"{d1} {m1 or m2} {y}", "%d %B %Y").date()
            e = datetime.strptime(f"{d2} {m2} {y}", "%d %B %Y").date()
            return s.isoformat(), e.isoformat(), raw
    return None, None, None


def wiki_champs() -> tuple[dict[int, tuple[str, str]], dict[int, str]]:
    held: dict[int, tuple[str, str]] = {}
    nothing: dict[int, str] = {}
    for t in pd.read_html(RAW / "wiki_champions.html"):
        cols = list(map(str, t.columns))
        if not ({"Year", "Champion", "Runner-up"} <= set(cols)) or len(t) < 30:
            continue
        for _, r in t.iterrows():
            m = re.match(r"^\s*(\d{4})", str(r["Year"]))
            if not m:
                continue
            y = int(m[1])
            if "no competition" in str(r["Champion"]).lower():
                nothing[y] = re.sub(r"\[[^\]]*\]", "", str(r["Champion"]))
            else:
                held[y] = (clean(r["Champion"]), clean(r["Runner-up"]))
    return held, nothing


def topend() -> tuple[dict[int, tuple[str, str]], dict[int, str]]:
    t = pd.read_html(RAW / "topend_winners.html")[0]
    out, nh = {}, {}
    for _, r in t.iterrows():
        yt = str(r.iloc[0])
        if re.fullmatch(r"\d{4}", yt) and re.search(
            r"cancel|not held", str(r.iloc[1]), re.IGNORECASE
        ):
            nh[int(yt)] = str(r.iloc[1])
        elif re.fullmatch(r"\d{4}", yt):
            out[int(yt)] = (clean(r.iloc[1]), clean(r.iloc[2]))
        elif m := re.match(r"(\d{4})-(\d{2,4})", yt):
            a, b = int(m[1]), m[2]
            for yy in range(a, int(str(a)[: 4 - len(b)] + b) + 1):
                nh[yy] = str(r.iloc[1])
    return out, nh


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    held, nothing = wiki_champs()
    tp, tp_nh = topend()
    gaps = ["# wimbledon_mens_singles gaps / cross-check log", ""]
    rows = []
    for y in YEARS:
        if y not in held:
            why = nothing.get(y, "no row in Wikipedia list")
            rows.append({"year": y, "held": 0, "source_url": LIST_URL, "notes": f"Not held: {why}"})
            gaps.append(f"- {y}: not held per Wikipedia list ({why}).")
            if y in tp:
                gaps.append(
                    f"- {y}: DISAGREEMENT topendsports lists a final for a year Wikipedia says not held."
                )
            elif y not in tp_nh:
                gaps.append(f"- {y}: topendsports has no explicit 'not held' entry.")
            continue
        champ, ru = held[y]
        start, end, raw = tournament_dates(y)
        notes = []
        if end is None:
            gaps.append(f"- {y}: tournament dates not parseable (raw {raw!r}); left empty.")
        else:
            notes.append(
                f"completed_date = tournament end per Wikipedia infobox ({raw}); men's final date not separately sourced"
            )
            if date.fromisoformat(end) >= election_day(y):
                notes.append("COMPLETED ON/AFTER ELECTION DAY")
        if y in tp:
            if surname(tp[y][0]) != surname(champ):
                gaps.append(
                    f"- {y}: champion DISAGREEMENT wikipedia={champ!r} topendsports={tp[y][0]!r}"
                )
            if surname(tp[y][1]) != surname(ru):
                gaps.append(
                    f"- {y}: runner-up DISAGREEMENT wikipedia={ru!r} topendsports={tp[y][1]!r}"
                )
        else:
            gaps.append(f"- {y}: missing from topendsports list.")
        rows.append(
            {
                "year": y,
                "held": 1 if end else 0,
                "completed_date": end,
                "start_date": start,
                "champion": champ,
                "runner_up": ru,
                "source_url": f"{LIST_URL}; {WIKI}{y}_Wimbledon_Championships; {FILES['topend_winners.html']}",
                "notes": "; ".join(notes),
            }
        )
    gaps += [
        "",
        (
            "- Challenge-round era (through 1921): the reigning champion was exempt until the 'challenge round'; "
            "the Wikipedia list's 'runner-up' is the challenge-round loser/finalist. Exact final dates are not "
            "stated in any fetched source; the tournament end date is used as a proxy."
        ),
        "- Dates are single-source (Wikipedia infobox); topendsports gives no dates.",
    ]
    cols = [
        "year",
        "held",
        "completed_date",
        "start_date",
        "champion",
        "runner_up",
        "source_url",
        "notes",
    ]
    df = pd.DataFrame(rows).reindex(columns=cols)
    df.to_csv(OUT / "wimbledon_mens_singles.csv", index=False)
    (OUT / "wimbledon_mens_singles_gaps.md").write_text("\n".join(gaps) + "\n")
    write_manifest()
    print(df[["year", "held", "completed_date", "champion", "runner_up"]].to_string(index=False))
    print("\n".join(gaps))


if __name__ == "__main__":
    main()
