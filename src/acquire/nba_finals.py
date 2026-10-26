"""Build the NBA/BAA Finals event table from fetched raw pages (never from memory).

Primary: Wikipedia "List of NBA champions" (winner, loser, series score, Western/Eastern
champion column, team-lineage footnotes) + per-year Finals pages (game dates).
Cross-check: Basketball-Reference playoffs index and per-year playoff pages (winner, loser,
series games). Game dates are single-sourced (Wikipedia) except for the infobox consistency check.
Run: uv run python -m src.acquire.nba_finals
"""

import csv
import datetime as dt
import hashlib
import io
import re
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "nba_finals"
OUT = ROOT / "data" / "processed" / "events"
YEARS = list(range(1900, 2025, 4))
FINAL_YEARS = [y for y in YEARS if y >= 1948]

LIST_FILE = "wiki_list_of_nba_champions.html"
LIST_URL = "https://en.wikipedia.org/wiki/List_of_NBA_champions"
BREF_INDEX = "bref_playoffs_index.html"
BREF_INDEX_URL = "https://www.basketball-reference.com/playoffs/"


def wiki_file(y: int) -> str:
    return f"wiki_{y}_finals.html"


def wiki_url(y: int) -> str:
    return f"https://en.wikipedia.org/wiki/{y}_{'BAA' if y <= 1949 else 'NBA'}_Finals"


def bref_file(y: int) -> str:
    return f"bref_{y}.html"


def bref_url(y: int) -> str:
    return f"https://www.basketball-reference.com/playoffs/{'BAA' if y <= 1949 else 'NBA'}_{y}.html"


def files() -> dict[str, str]:
    d = {LIST_FILE: LIST_URL, BREF_INDEX: BREF_INDEX_URL}
    for y in FINAL_YEARS:
        d[wiki_file(y)] = wiki_url(y)
        d[bref_file(y)] = bref_url(y)
    return d


# source name (as printed in the list) -> (current franchise name or None if folded,
# regex that must match the list page text as evidence)
LINEAGE = {
    "Baltimore Bullets": (None, r"Baltimore Bullets \(original\) \( folded in 1954\)"),
    "Philadelphia Warriors": ("Golden State Warriors", r"Includes record as Philadelphia and San Francisco Warriors"),
    "San Francisco Warriors": ("Golden State Warriors", r"Includes record as Philadelphia and San Francisco Warriors"),
    "Golden State Warriors": ("Golden State Warriors", r"Golden State Warriors ?\[ ii \]"),
    "Minneapolis Lakers": ("Los Angeles Lakers", r"Includes record as Minneapolis Lakers"),
    "Los Angeles Lakers": ("Los Angeles Lakers", r"Los Angeles Lakers ?\[ i \]"),
    "New York Knicks": ("New York Knicks", r"New York Knicks 3 6 9"),
    "Fort Wayne Pistons": ("Detroit Pistons", r"Includes record as Fort Wayne Pistons"),
    "Detroit Pistons": ("Detroit Pistons", r"Detroit Pistons ?\[ iv \]"),
    "St. Louis Hawks": ("Atlanta Hawks", r"Includes record as St\. Louis Hawks"),
    "Boston Celtics": ("Boston Celtics", r"Boston Celtics 18 5 23"),
    "Phoenix Suns": ("Phoenix Suns", r"Phoenix Suns 0 3 3"),
    "Philadelphia 76ers": ("Philadelphia 76ers", r"Includes record as Syracuse Nationals"),
    "Chicago Bulls": ("Chicago Bulls", r"Chicago Bulls 6 0 6"),
    "Portland Trail Blazers": ("Portland Trail Blazers", r"Portland Trail Blazers 1 2 3"),
    "Seattle SuperSonics": ("Oklahoma City Thunder", r"Includes record as Seattle SuperSonics"),
    "Indiana Pacers": ("Indiana Pacers", r"Indiana Pacers 0 2 2"),
    "Miami Heat": ("Miami Heat", r"Miami Heat 3 4 7"),
    "Oklahoma City Thunder": ("Oklahoma City Thunder", r"Oklahoma City Thunder ?\[ v \]"),
    "Cleveland Cavaliers": ("Cleveland Cavaliers", r"Cleveland Cavaliers 1 4 5"),
    "Dallas Mavericks": ("Dallas Mavericks", r"Dallas Mavericks 1 2 3"),
}


def election_day(year: int) -> dt.date:
    d = dt.date(year, 11, 1)
    return d + dt.timedelta(days=(0 - d.weekday()) % 7) + dt.timedelta(days=1)


def write_manifest() -> None:
    with open(RAW / "MANIFEST.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["file", "url", "retrieved", "sha256"])
        for name, url in files().items():
            p = RAW / name
            w.writerow([name, url, dt.date.fromtimestamp(p.stat().st_mtime).isoformat(),
                        hashlib.sha256(p.read_bytes()).hexdigest()])


def team(cell: str) -> str:
    name = re.sub(r"\s*\(.*$", "", str(cell))
    return re.sub(r"[†‡*]|\[[^\]]*\]", "", name).strip()


def list_rows() -> tuple[dict, str]:
    html = (RAW / LIST_FILE).read_text()
    tables = pd.read_html(io.StringIO(html))
    t = next(x for x in tables if "Western champion" in x.columns)
    text = re.sub(r"\s+", " ", BeautifulSoup(html, "lxml").get_text(" "))
    rows = {}
    for _, r in t.iterrows():
        y = int(re.match(r"\d{4}", str(r["Year"])).group(0))
        w_score, e_score = (int(v) for v in re.split(r"[–-]", str(r["Result"])))
        west, east = team(r["Western champion"]), team(r["Eastern champion"])
        win_west = w_score > e_score
        rows[y] = {
            "winner": west if win_west else east, "loser": east if win_west else west,
            "conf": "West" if win_west else "East",
            "wins": max(w_score, e_score), "losses": min(w_score, e_score),
        }
    return rows, text


MONTH = {m: i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July", "August", "September",
     "October", "November", "December"], 1)}


def game_dates(y: int) -> tuple[list[dt.date], str]:
    """Dates of the games actually played (rows with a result) + infobox 'Dates' string."""
    html = (RAW / wiki_file(y)).read_text()
    tables = pd.read_html(io.StringIO(html))
    dates, infobox = [], ""
    for t in tables:
        if t.shape[1] >= 2 and str(t.iloc[0, 0]) == "Dates" or (
                t.shape[0] > 3 and "Dates" in t.iloc[:, 0].astype(str).tolist()):
            col0 = t.iloc[:, 0].astype(str).tolist()
            infobox = str(t.iloc[col0.index("Dates"), 1])
        cols = [str(c) for c in t.columns]
        if "Game" in cols and "Date" in cols and "Result" in cols:
            for _, r in t.iterrows():
                if not str(r["Game"]).startswith("Game") or pd.isna(r["Result"]):
                    continue
                m = re.search(r"([A-Z][a-z]+)\s+(\d{1,2})", str(r["Date"]))
                dates.append(dt.date(y, MONTH[m.group(1)], int(m.group(2))))
    return dates, infobox


def infobox_end(y: int, s: str) -> dt.date | None:
    m = re.search(r"(?:([A-Z][a-z]+)\s+)?(\d{1,2})\s*$", s.split("–")[-1].strip())
    if not m:
        return None
    first_month = re.match(r"([A-Z][a-z]+)", s.strip())
    month = m.group(1) or (first_month.group(1) if first_month else None)
    return dt.date(y, MONTH[month], int(m.group(2))) if month in MONTH else None


def bref_index() -> dict:
    t = pd.read_html(io.StringIO((RAW / BREF_INDEX).read_text()))[0]
    t.columns = [c[1] for c in t.columns]
    out = {}
    for _, r in t.iterrows():
        if pd.notna(r["Year"]) and r["Lg"] in ("NBA", "BAA"):
            out[int(r["Year"])] = (str(r["Champion"]), str(r["Runner-Up"]))
    return out


def bref_series(y: int) -> tuple[str, str, int, int] | None:
    soup = BeautifulSoup((RAW / bref_file(y)).read_text(), "lxml")
    for tr in soup.select("tr"):
        c = [x.get_text(" ", strip=True) for x in tr.find_all(["td", "th"])]
        if c and c[0] == "Finals" and len(c) > 1:
            m = re.match(r"(.+?) over (.+?)\s*\((\d+)-(\d+)\)", c[1])
            if m:
                return m.group(1), m.group(2), int(m.group(3)), int(m.group(4))
    return None


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    write_manifest()
    rows, list_text = list_rows()
    bidx = bref_index()
    gaps = ["# nba_finals gaps and cross-check log", ""]
    gaps.append("- Completed dates are single-sourced from Wikipedia per-year Finals game tables "
                "(Basketball-Reference per-year pages were used for winner/loser/series score only). "
                "Each date was additionally checked against that page's infobox 'Dates' line.")
    n0 = len(gaps)
    used, recs = set(), []
    for y in YEARS:
        rec = {"year": y, "held": 0, "completed_date": "", "start_date": "", "winner_franchise": "",
               "loser_franchise": "", "games_played": "", "sweep": "", "winner_conference": "",
               "winner_name_at_time": "", "loser_name_at_time": "", "series_score": "",
               "source_url": LIST_URL, "notes": ""}
        if y < 1948:
            rec["notes"] = "No NBA/BAA Finals held: first Finals were in 1947 (per source list)"
            recs.append(rec)
            continue
        r = rows[y]
        used.update([r["winner"], r["loser"]])
        dates, box = game_dates(y)
        n_games = r["wins"] + r["losses"]
        if len(dates) != n_games:
            gaps.append(f"- {y}: parsed {len(dates)} game dates but series score implies {n_games}")
        end = infobox_end(y, box)
        if dates and end != max(dates):
            gaps.append(f"- {y}: DISAGREEMENT last game table date {max(dates)} vs infobox "
                        f"'Dates' '{box}'")
        b = bref_series(y)
        if b is None:
            gaps.append(f"- {y}: Basketball-Reference per-year page has no Finals row")
        elif (b[0], b[1], b[2], b[3]) != (r["winner"], r["loser"], r["wins"], r["losses"]):
            gaps.append(f"- {y}: DISAGREEMENT wiki {r['winner']} over {r['loser']} "
                        f"{r['wins']}-{r['losses']} vs bref {b}")
        bi = bidx.get(y)
        if bi != (r["winner"], r["loser"]):
            gaps.append(f"- {y}: DISAGREEMENT bref index {bi} vs wiki {(r['winner'], r['loser'])}")
        rec.update({
            "held": 1, "completed_date": max(dates).isoformat() if dates else "",
            "start_date": min(dates).isoformat() if dates else "",
            "games_played": n_games, "sweep": int(r["losses"] == 0), "winner_conference": r["conf"],
            "winner_name_at_time": r["winner"], "loser_name_at_time": r["loser"],
            "series_score": f"{r['wins']}-{r['losses']}",
            "source_url": f"{LIST_URL}; {wiki_url(y)}; {bref_url(y)}",
        })
        notes = []
        if y <= 1970:
            notes.append("winner_conference is the source's 'Western/Eastern champion' column "
                         "(pre-1971 these were division champions)")
        if dates and max(dates) >= election_day(y):
            notes.append("COMPLETED ON/AFTER ELECTION DAY")
        if y == 2020:
            notes.append("2019-20 season resumed in Orlando bubble; Finals ran Sept 30-Oct 11, 2020")
        rec["notes"] = "; ".join(notes)
        recs.append(rec)

    lineage = []
    for src in sorted(used):
        cur, ev = LINEAGE[src]
        assert re.search(ev, list_text), f"lineage evidence missing for {src}: /{ev}/"
        note = f"evidence on {LIST_URL} matched /{ev}/ (Wikipedia team table row/footnote)"
        if cur is None:
            cur_name = f"{src} (original, folded 1954)"
            note += ("; franchise folded in 1954 per source - no current NBA franchise; the "
                     "later Baltimore Bullets (1963) / Washington Wizards are a different franchise")
        else:
            cur_name = cur
        lineage.append({"source_name": src, "canonical_name": cur_name, "note": note})
    lmap = {x["source_name"]: x["canonical_name"] for x in lineage}
    for rec in recs:
        if rec["held"]:
            rec["winner_franchise"] = lmap[rec["winner_name_at_time"]]
            rec["loser_franchise"] = lmap[rec["loser_name_at_time"]]
    if len(gaps) == n0:
        gaps.append("- No disagreements found in winner, loser, series score or dates.")
    pd.DataFrame(recs).to_csv(OUT / "nba_finals.csv", index=False)
    pd.DataFrame(lineage).to_csv(OUT / "nba_finals_lineage.csv", index=False)
    (OUT / "nba_finals_gaps.md").write_text("\n".join(gaps) + "\n")
    print(f"nba_finals: {len(recs)} rows, held=1: {sum(r['held'] for r in recs)}; "
          f"gap lines: {len(gaps) - n0}")


if __name__ == "__main__":
    main()
