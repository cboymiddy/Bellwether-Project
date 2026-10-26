"""Build the Super Bowl event table from fetched raw pages (never from memory).

Primary: Wikipedia "List of Super Bowl champions" (game table + franchise table + footnotes).
Cross-check: ESPN "Super Bowl Winners by Year" (date, winner, loser, score).
Pro-Football-Reference and footballdb returned HTTP 403 (Cloudflare) and were not used.
Run: uv run python -m src.acquire.nfl_super_bowl
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
RAW = ROOT / "data" / "raw" / "nfl_super_bowl"
OUT = ROOT / "data" / "processed" / "events"
YEARS = list(range(1900, 2025, 4))

WIKI_FILE = "wiki_list_of_super_bowl_champions.html"
WIKI_URL = "https://en.wikipedia.org/wiki/List_of_Super_Bowl_champions"
ESPN_FILE = "espn_winners.html"
ESPN_URL = "https://www.espn.com/nfl/superbowl/history/winners"
FILES = {WIKI_FILE: WIKI_URL, ESPN_FILE: ESPN_URL}

MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}
MARKER = {"A": "AFC", "N": "NFC", "a": "AFL", "n": "NFL"}

# source name (as printed in the game table) -> row of the Wikipedia franchise table that
# contains it, and the current franchise name. Each mapping is machine-checked against the page
# (city and nickname must both appear in the franchise row), see check_lineage().
LINEAGE = {
    "Green Bay Packers": ("Green Bay Packers", "Green Bay Packers"),
    "Kansas City Chiefs": ("Kansas City Chiefs", "Kansas City Chiefs"),
    "Oakland Raiders": ("Oakland / Los Angeles / Las Vegas Raiders", "Las Vegas Raiders"),
    "Los Angeles Raiders": ("Oakland / Los Angeles / Las Vegas Raiders", "Las Vegas Raiders"),
    "New York Jets": ("New York Jets", "New York Jets"),
    "Baltimore Colts": ("Baltimore / Indianapolis Colts", "Indianapolis Colts"),
    "Indianapolis Colts": ("Baltimore / Indianapolis Colts", "Indianapolis Colts"),
    "Dallas Cowboys": ("Dallas Cowboys", "Dallas Cowboys"),
    "Miami Dolphins": ("Miami Dolphins", "Miami Dolphins"),
    "Minnesota Vikings": ("Minnesota Vikings", "Minnesota Vikings"),
    "Washington Redskins": ("Washington Redskins / Football Team / Commanders", "Washington Commanders"),
    "Pittsburgh Steelers": ("Pittsburgh Steelers", "Pittsburgh Steelers"),
    "San Francisco 49ers": ("San Francisco 49ers", "San Francisco 49ers"),
    "Los Angeles Rams": ("St. Louis / Los Angeles Rams", "Los Angeles Rams"),
    "St. Louis Rams": ("St. Louis / Los Angeles Rams", "Los Angeles Rams"),
    "Philadelphia Eagles": ("Philadelphia Eagles", "Philadelphia Eagles"),
    "Chicago Bears": ("Chicago Bears", "Chicago Bears"),
    "New England Patriots": ("Boston / New England Patriots", "New England Patriots"),
    "Denver Broncos": ("Denver Broncos", "Denver Broncos"),
    "Buffalo Bills": ("Buffalo Bills", "Buffalo Bills"),
    "San Diego Chargers": ("San Diego / Los Angeles Chargers", "Los Angeles Chargers"),
    "Tennessee Titans": ("Houston / Tennessee Oilers / Titans", "Tennessee Titans"),
    "Baltimore Ravens": ("Baltimore Ravens", "Baltimore Ravens"),
    "New York Giants": ("New York Giants", "New York Giants"),
    "Tampa Bay Buccaneers": ("Tampa Bay Buccaneers", "Tampa Bay Buccaneers"),
    "Carolina Panthers": ("Carolina Panthers", "Carolina Panthers"),
    "Arizona Cardinals": ("St. Louis / Phoenix / Arizona Cardinals", "Arizona Cardinals"),
    "Seattle Seahawks": ("Seattle Seahawks", "Seattle Seahawks"),
    "Atlanta Falcons": ("Atlanta Falcons", "Atlanta Falcons"),
    "New Orleans Saints": ("New Orleans Saints", "New Orleans Saints"),
    "Cincinnati Bengals": ("Cincinnati Bengals", "Cincinnati Bengals"),
    "Houston Oilers": ("Houston / Tennessee Oilers / Titans", "Tennessee Titans"),
}
# Footnote evidence (regex over page text) for mappings that need more than the franchise row.
EXTRA_EVIDENCE = {
    "Baltimore Ravens": r"the Ravens, for historical purposes, are considered a separate franchise",
    "Baltimore Colts": r"Baltimore / Indianapolis Colts",
}


def election_day(year: int) -> dt.date:
    d = dt.date(year, 11, 1)
    first_monday = d + dt.timedelta(days=(0 - d.weekday()) % 7)
    return first_monday + dt.timedelta(days=1)


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write_manifest() -> None:
    with open(RAW / "MANIFEST.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["file", "url", "retrieved", "sha256"])
        for name, url in FILES.items():
            p = RAW / name
            retrieved = dt.date.fromtimestamp(p.stat().st_mtime).isoformat()
            w.writerow([name, url, retrieved, sha256(p)])


def clean_name(cell: str) -> tuple[str, str]:
    """'Green Bay Packersn (1, 1-0)' -> ('Green Bay Packers', 'n')."""
    name = re.sub(r"\s*\(.*$", "", str(cell)).strip()
    name = re.sub(r"\[[^\]]*\]", "", name).strip()
    marker = name[-1]
    assert marker in MARKER, cell
    return name[:-1], marker


def wiki_games() -> tuple[dict, pd.DataFrame, str]:
    html = (RAW / WIKI_FILE).read_text()
    tables = pd.read_html(io.StringIO(html))
    games = next(t for t in tables if "Winning team" in t.columns)
    franchise = next(t for t in tables if "Franchise" in t.columns)
    page_text = re.sub(r"\s+", " ", BeautifulSoup(html, "lxml").get_text(" "))
    rows = {}
    for _, r in games.iterrows():
        m = re.search(r"([A-Z][a-z]{2}) (\d{1,2}), (\d{4})", str(r["Date (season)"]))
        d = dt.date(int(m.group(3)), MONTHS[m.group(1)], int(m.group(2)))
        w, wm = clean_name(r["Winning team"])
        lo, lm = clean_name(r["Losing team"])
        rows[d.year] = {
            "date": d,
            "game": re.sub(r"\s*\[.*?\]", "", str(r["Game"])).strip(),
            "season": re.search(r"\((.*)\)", str(r["Date (season)"])).group(1),
            "winner": w, "wm": wm, "loser": lo, "lm": lm,
            "ws": int(r["Score"]), "ls": int(r["Score.1"]),
        }
    return rows, franchise, page_text


def espn_games() -> dict:
    soup = BeautifulSoup((RAW / ESPN_FILE).read_text(), "lxml")
    out = {}
    for tr in soup.select("tr"):
        c = [x.get_text(" ", strip=True) for x in tr.select("td")]
        if len(c) != 4 or not re.match(r"^[IVXL]+$", c[0]):
            continue
        m = re.match(r"([A-Z][a-z]{2})[a-z]*\.? (\d{1,2}), (\d{4})", c[1])
        d = dt.date(int(m.group(3)), MONTHS[m.group(1)], int(m.group(2)))
        r = re.match(r"(.+?) (\d+), (.+?) (\d+)$", c[3])
        out[d.year] = {"date": d, "game": c[0], "winner": r.group(1), "ws": int(r.group(2)),
                       "loser": r.group(3), "ls": int(r.group(4))}
    return out


def roman(game: str) -> str:
    """Wikipedia prints Super Bowl 50 as '50'; ESPN prints 'L'. Compare in roman numerals."""
    if not game.isdigit():
        return game
    n, out = int(game), ""
    for val, sym in [(50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]:
        while n >= val:
            out, n = out + sym, n - val
    return out


def loose_match(espn_name: str, our_name: str) -> bool:
    a = re.sub(r"[^a-z0-9 ]", "", espn_name.lower().replace("l.a.", "los angeles"))
    b = re.sub(r"[^a-z0-9 ]", "", our_name.lower())
    return b.startswith(a) or a.startswith(b) or a.split()[-1] == b.split()[-1]


def check_lineage(used: set[str], franchise: pd.DataFrame, page_text: str) -> list[dict]:
    out = []
    for src in sorted(used):
        row, canon = LINEAGE[src]
        city, nick = src.rsplit(" ", 1)
        # franchise cells carry a trailing league marker / footnote, so match on prefix
        ok = any(str(x).startswith(row) for x in franchise["Franchise"])
        ok = ok and city.split()[-1] in row and nick in row
        assert ok, f"lineage not evidenced on page: {src} -> {row}"
        note = (f"Wikipedia franchise table row '{row}' ({WIKI_URL}) lists this name; "
                f"current franchise name taken as '{canon}'")
        if src in EXTRA_EVIDENCE:
            assert re.search(EXTRA_EVIDENCE[src], page_text), src
            note += f"; footnote text matched: /{EXTRA_EVIDENCE[src]}/"
        if src in ("Baltimore Ravens",):
            note += ("; Ravens are NOT the Cleveland Browns franchise (Browns history stayed in "
                     "Cleveland) - judgment follows the page's footnote")
        if src in ("Baltimore Colts", "Indianapolis Colts"):
            note += "; Baltimore Colts and Indianapolis Colts are one franchise (relocated 1984)"
        out.append({"source_name": src, "canonical_name": canon, "note": note})
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    write_manifest()
    wiki, franchise, page_text = wiki_games()
    espn = espn_games()
    gaps = ["# nfl_super_bowl gaps and cross-check log", ""]
    gaps.append("- Pro-Football-Reference (HTTP 403 Cloudflare) and footballdb (HTTP 403) were "
                "unreachable; ESPN is the second source for date, winner, loser and score.")
    used, recs = set(), []
    for y in YEARS:
        g = wiki.get(y)
        rec = {"year": y, "held": 0, "completed_date": "", "start_date": "", "winner_franchise": "",
               "loser_franchise": "", "winner_conference": "", "game_number": "",
               "winner_name_at_time": "", "loser_name_at_time": "", "score": "",
               "source_url": WIKI_URL, "notes": ""}
        if g is None:
            rec["notes"] = "No Super Bowl held: first game was January 1967 (per source table)"
        else:
            used.update([g["winner"], g["loser"]])
            rec.update({
                "held": 1, "completed_date": g["date"].isoformat(),
                "start_date": g["date"].isoformat(),
                "winner_franchise": LINEAGE[g["winner"]][1], "loser_franchise": LINEAGE[g["loser"]][1],
                "winner_conference": MARKER[g["wm"]], "game_number": g["game"],
                "winner_name_at_time": g["winner"], "loser_name_at_time": g["loser"],
                "score": f"{g['ws']}-{g['ls']}", "source_url": f"{WIKI_URL}; {ESPN_URL}",
                "notes": f"season {g['season']}; played in calendar year {y} for the prior season",
            })
            if g["wm"] in "an":
                rec["notes"] += ("; winner_conference is the league at the time as sourced "
                                 f"({MARKER[g['wm']]}), pre-AFC/NFC merger alignment")
            if g["date"] >= election_day(y):
                rec["notes"] += "; COMPLETED ON/AFTER ELECTION DAY"
            e = espn.get(y)
            if e is None:
                gaps.append(f"- {y}: ESPN has no row for the game")
            else:
                bad = []
                if e["date"] != g["date"]:
                    bad.append(f"date wiki={g['date']} espn={e['date']}")
                if e["game"] != roman(g["game"]):
                    bad.append(f"game wiki={g['game']} espn={e['game']}")
                if not loose_match(e["winner"], g["winner"]):
                    bad.append(f"winner wiki={g['winner']} espn={e['winner']}")
                if not loose_match(e["loser"], g["loser"]):
                    bad.append(f"loser wiki={g['loser']} espn={e['loser']}")
                if (e["ws"], e["ls"]) != (g["ws"], g["ls"]):
                    bad.append(f"score wiki={g['ws']}-{g['ls']} espn={e['ws']}-{e['ls']}")
                if bad:
                    gaps.append(f"- {y}: DISAGREEMENT " + "; ".join(bad))
        recs.append(rec)
    if len(gaps) == 3:
        gaps.append("- No disagreements between Wikipedia and ESPN for any held election-year game.")
    pd.DataFrame(recs).to_csv(OUT / "nfl_super_bowl.csv", index=False)
    pd.DataFrame(check_lineage(used, franchise, page_text)).to_csv(
        OUT / "nfl_super_bowl_lineage.csv", index=False)
    (OUT / "nfl_super_bowl_gaps.md").write_text("\n".join(gaps) + "\n")
    held = sum(r["held"] for r in recs)
    print(f"nfl_super_bowl: {len(recs)} rows, held=1: {held}; gaps lines: {len(gaps) - 3}")


if __name__ == "__main__":
    main()
