"""Build the Stanley Cup event table from fetched raw pages (never from memory).

Treatment of the Cup's history (all from the sources, see notes in the output):
- 1893-1914 challenge era: the Cup was held by amateur/pro league champions and defended in
  challenge series; several awards per year are normal. For the election years 1900, 1904, 1908
  and 1912 the row is the LAST challenge series of that calendar year that had an opposing team
  (a champion's no-challenger league-title "defence" is not a series). The champion at the end of
  the year is the winner. 1908's last series ended Dec 30, after Election Day (flagged).
- 1915-1926: prearranged inter-league finals (NHA/NHL vs PCHA/WCHL champions). The winner may
  be a non-NHL club (none in the election years of this table: 1916 Canadiens, 1920 Senators,
  1924 Canadiens all NHA/NHL clubs).
- 1927+: final between NHL playoff champions.
`winner_franchise_current` is empty when the champion belongs to no current NHL franchise.

Primary: Wikipedia "List of Stanley Cup champions", "List of Stanley Cup challenge games",
per-year "<year> Stanley Cup Final" pages (game dates), franchise articles (lineage).
Cross-check: Hockey-Reference playoff index and per-year playoff pages (winner/loser/score for
1918+). No independent non-Wikipedia source was reachable for 1900-1916 (see gaps file).
Run: uv run python -m src.acquire.nhl_stanley_cup
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
RAW = ROOT / "data" / "raw" / "nhl_stanley_cup"
OUT_DIR = ROOT / "data" / "processed" / "events"
YEARS = list(range(1900, 2025, 4))
CHALLENGE_YEARS = [1900, 1904, 1908, 1912]
FINAL_YEARS = [y for y in YEARS if y >= 1916]

LIST_FILE = "wiki_list_of_stanley_cup_champions.html"
LIST_URL = "https://en.wikipedia.org/wiki/List_of_Stanley_Cup_champions"
CH_FILE = "wiki_list_of_stanley_cup_challenge_games.html"
CH_URL = "https://en.wikipedia.org/wiki/List_of_Stanley_Cup_challenge_games"
HR_INDEX = "hr_playoffs_index.html"
HR_INDEX_URL = "https://www.hockey-reference.com/playoffs/"
FRANCHISE_PAGES = {
    "wiki_franchise_Colorado_Avalanche.html": "Colorado_Avalanche",
    "wiki_franchise_New_Jersey_Devils.html": "New_Jersey_Devils",
    "wiki_franchise_Calgary_Flames.html": "Calgary_Flames",
    "wiki_franchise_Dallas_Stars.html": "Dallas_Stars",
    "wiki_franchise_Chicago_Blackhawks.html": "Chicago_Blackhawks",
    "wiki_franchise_Toronto_Maple_Leafs.html": "Toronto_Maple_Leafs",
    "wiki_franchise_Montreal_Canadiens.html": "Montreal_Canadiens",
    "wiki_franchise_Ottawa_Senators_original.html": "Ottawa_Senators_(original)",
    "wiki_franchise_Quebec_Bulldogs.html": "Quebec_Bulldogs",
}
MONTH = {m: i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July", "August", "September",
     "October", "November", "December"], 1)}


def final_file(y: int) -> str:
    return f"wiki_{y}_stanley_cup_final.html"


def final_url(y: int) -> str:
    return f"https://en.wikipedia.org/wiki/{y}_Stanley_Cup_Final"


def hr_file(y: int) -> str:
    return f"hr_{y}.html"


def hr_url(y: int) -> str:
    return f"https://www.hockey-reference.com/playoffs/NHL_{y}.html"


def files() -> dict[str, str]:
    d = {LIST_FILE: LIST_URL, CH_FILE: CH_URL, HR_INDEX: HR_INDEX_URL}
    for f, page in FRANCHISE_PAGES.items():
        d[f] = f"https://en.wikipedia.org/wiki/{page}"
    for y in FINAL_YEARS:
        d[final_file(y)] = final_url(y)
        if y >= 1924:
            d[hr_file(y)] = hr_url(y)
    return d


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


def page_text(name: str) -> str:
    return re.sub(r"\s+", " ", BeautifulSoup((RAW / name).read_text(), "lxml").get_text(" "))


def tables(name: str) -> list[pd.DataFrame]:
    return pd.read_html(io.StringIO((RAW / name).read_text()))


def split_team(cell: str) -> tuple[str, str]:
    """'Montreal Canadiens (NHA) (1, 1-0)' -> ('Montreal Canadiens', 'NHA')."""
    s = re.sub(r"\[[^\]]*\]", "", str(cell)).strip()
    groups = re.findall(r"\(([^()]*)\)", s)
    name = re.sub(r"\s*\([^()]*\)", "", s).strip()
    tag = groups[0] if groups and re.fullmatch(r"[A-Za-z]{1,6}", groups[0]) else ""
    return name, tag


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


# ---------------------------------------------------------------- challenge era (1900-1912)
def challenge_rows() -> list[dict]:
    t0 = tables(LIST_FILE)[0]
    rows = []
    for _, r in t0.iterrows():
        d = str(r["Date"])
        m = re.search(r"(\d{4})$", d)
        if not m:
            continue
        loser = str(r["Losing team"])
        rows.append({"year": int(m.group(1)), "date_str": d, "winner": str(r["Winning team"]),
                     "loser": loser, "format": str(r["Playoff format"]), "score": str(r["Score"]),
                     "opposed": not re.search(r"champion|challenger", loser, re.IGNORECASE)})
    return rows


def challenge_series(year: int) -> dict:
    """Last series of `year` on the challenge-games page: games + summary."""
    last = None
    for t in tables(CH_FILE):
        if t.shape[1] != 5 or not len(t):
            continue
        m = re.match(r"([A-Z][a-z]+) (\d{1,2}), (\d{4})", str(t.iloc[0, 0]))
        if not m or int(m.group(3)) != year:
            continue
        games = []
        for _, r in t.iterrows():
            gm = re.match(r"([A-Z][a-z]+) (\d{1,2}), (\d{4})$", str(r.iloc[0]))
            if gm:
                games.append({"date": dt.date(year, MONTH[gm.group(1)], int(gm.group(2))),
                              "w": str(r.iloc[1]), "score": str(r.iloc[2]), "l": str(r.iloc[3])})
        summary = str(t.iloc[-1, 0])
        last = {"games": games, "summary": summary}
    assert last, year
    return last


# ---------------------------------------------------------------- final era (1916+)
def list_finals() -> dict:
    ts = tables(LIST_FILE)
    out = {}
    for t in ts:
        if "Games" not in t.columns or "Winning team" not in t.columns:
            continue
        for _, r in t.iterrows():
            ym = re.match(r"\d{4}", str(r["Year"]))
            if not ym:
                continue
            y = int(ym.group(0))
            gm = re.findall(r"\d+", str(r["Games"]))
            if len(gm) < 2:
                continue
            w, wt = split_team(r["Winning team"])
            lo, lt = split_team(r["Losing team"])
            out[y] = {"winner": w, "wtag": wt, "loser": lo, "ltag": lt,
                      "wg": int(gm[0]), "lg": int(gm[1])}
    return out


def final_games(y: int) -> tuple[list[dt.date], list[dt.date], str, str]:
    """Completed-game dates, tied/suspended-game dates, infobox 'Dates', infobox 'Format'."""
    dates, ties, box_dates, box_fmt = [], [], "", ""
    for t in tables(final_file(y)):
        col0 = t.iloc[:, 0].astype(str).tolist()
        if "Dates" in col0 and not box_dates:
            box_dates = str(t.iloc[col0.index("Dates"), 1])
        if "Format" in col0 and not box_fmt:
            box_fmt = str(t.iloc[col0.index("Format"), 1])
        if t.shape[1] >= 7:
            m = re.match(r"^([A-Z][a-z]+) (\d{1,2})$", str(t.iloc[0, 0]))
            sc = re.fullmatch(r"(\d+)–(\d+)", str(t.iloc[0, 3]))
            if m and m.group(1) in MONTH and sc:
                d = dt.date(y, MONTH[m.group(1)], int(m.group(2)))
                (ties if sc.group(1) == sc.group(2) else dates).append(d)
    return dates, ties, box_dates, box_fmt


def infobox_end(y: int, s: str) -> dt.date | None:
    s = re.sub(r"\[[^\]]*\]", "", s).strip()
    s = re.sub(r",\s*\d{4}$", "", s)
    parts = re.split(r"\s*[–-]\s*", s)
    m = re.search(r"(?:([A-Z][a-z]+)\s+)?(\d{1,2})$", parts[-1])
    first = re.match(r"([A-Z][a-z]+)", s.strip())
    if not m:
        return None
    month = m.group(1) or (first.group(1) if first else "")
    return dt.date(y, MONTH[month], int(m.group(2))) if month in MONTH else None


def hr_final(y: int) -> tuple[str, str, int, int] | None:
    soup = BeautifulSoup((RAW / hr_file(y)).read_text(), "lxml")
    for tr in soup.select("tr"):
        t = re.sub(r"\s+", " ", tr.get_text(" ", strip=True))
        m = re.match(r"Final (\d+)-(\d+) (.+?) over (.+?) View Matchup", t)
        if m:
            return m.group(3), m.group(4), int(m.group(1)), int(m.group(2))
    return None


def hr_index() -> dict:
    out = {}
    for t in pd.read_html(io.StringIO((RAW / HR_INDEX).read_text())):
        for _, r in t.iterrows():
            if str(r["Year"]).isdigit() and r["Lg"] == "NHL":
                out[int(r["Year"])] = (str(r["Champion"]), str(r["Runner-Up"]))
    return out


# ---------------------------------------------------------------- lineage
def current_franchises() -> set[str]:
    for t in tables(LIST_FILE):
        if "Team" in t.columns and "Wins" in t.columns and any(
                "Montreal Canadiens" in str(x) for x in t["Team"]):
            return {re.sub(r"\[[^\]]*\]", "", str(x)).strip() for x in t["Team"]}
    raise AssertionError("current franchise table not found")


# name as printed -> (current NHL franchise or None, page file, evidence regex, note)
ALIAS = {
    "Chicago Black Hawks": ("Chicago Blackhawks", LIST_FILE,
                            r"The Chicago Blackhawks were known as the Chicago Black Hawks prior to",
                            "renamed (list-page footnote)"),
    "Montreal Canadiens": ("Montreal Canadiens", "wiki_franchise_Montreal_Canadiens.html",
                           r"Montreal Canadiens 1910 – 1917 \( NHA \) 1917 –present \( NHL \)",
                           ("one continuous franchise NHA 1910-17 then NHL (club infobox); 1916 "
                           "winner was the NHA-era club")),
    "Ottawa Senators": (None, "wiki_franchise_Ottawa_Senators_original.html",
                        r"records for the two teams are kept separately",
                        ("the 1920 'Ottawa Senators (NHL)' is the ORIGINAL franchise (folded/moved "
                        "1934 as St. Louis Eagles, ceased 1935); the current Ottawa Senators "
                        "(1992) is a separate franchise whose records are kept separately")),
    "Quebec Bulldogs": (None, "wiki_franchise_Quebec_Bulldogs.html",
                        r"Quebec Athletic Club 1919–1920 \( NHL \) Hamilton Tigers 1920–1925",
                        ("NHA club; franchise rights moved to Hamilton Tigers 1920-25 (defunct); "
                        "no current NHL franchise")),
}
DEFUNCT_OTHER = ["Montreal Shamrocks", "Ottawa Silver Seven", "Montreal Wanderers",
                 "Portland Rosebuds", "Seattle Metropolitans", "Calgary Tigers",
                 "Montreal Maroons", "Halifax Crescents", "Brandon Wheat City", "Edmonton HC",
                 "Moncton Victorias"]


def lineage_for(name: str, cur: set[str], list_text: str) -> dict:
    if name in ALIAS:
        canon, fname, rx, note = ALIAS[name]
        text = list_text if fname == LIST_FILE else page_text(fname)
        assert re.search(rx, text), f"lineage evidence missing: {name} /{rx}/"
        src = LIST_URL if fname == LIST_FILE else files()[fname]
        return {"source_name": name, "canonical_name": canon or "",
                "note": f"{note}; evidence: {src} matched /{rx}/"}
    if name in cur:
        extra = ""
        for f, page in FRANCHISE_PAGES.items():
            if page.replace("_", " ").startswith(name):
                extra = f"; background page {files()[f]} fetched"
        return {"source_name": name, "canonical_name": name,
                "note": f"listed as a current NHL franchise in the Wikipedia list table ({LIST_URL})"
                        f"{extra}"}
    assert name in DEFUNCT_OTHER, f"unmapped team {name}"
    assert name not in cur
    assert name in list_text, name
    return {"source_name": name, "canonical_name": "",
            "note": "no current NHL franchise: club is not in the current-franchise table of "
                    f"{LIST_URL}; it appears there only among challenge-era / non-NHL / defunct clubs"}


# ---------------------------------------------------------------- main
def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_manifest()
    cur = current_franchises()
    list_text = page_text(LIST_FILE)
    finals = list_finals()
    ch_rows = challenge_rows()
    hidx = hr_index()
    gaps = ["# nhl_stanley_cup gaps and cross-check log", ""]
    gaps.append("- 1900-1916: no independent non-Wikipedia source reachable (Britannica 403, "
                "hockeydb 404, NHL records API has no pre-1917 data, Hockey-Reference has no "
                "pre-1918 pages). Cross-checked only between three Wikipedia articles (champions "
                "list, challenge-games list, per-year page) - NOT independent of each other.")
    gaps.append("- Hockey-Reference's 'Final' row for 1918-1926 is the NHL championship series, "
                "not the Cup final (e.g. 1924: Canadiens-Senators vs Cup final Canadiens-Calgary "
                "Tigers); only the winner is compared for those years.")
    gaps.append("- Completed dates are single-sourced from Wikipedia (game tables; challenge-games "
                "list for 1900-1912) and checked against the infobox 'Dates' line / champions-list "
                "date string; no second source for dates.")
    n0 = len(gaps)
    recs, used = [], set()
    for y in YEARS:
        rec = {"year": y, "held": 1, "completed_date": "", "start_date": "", "winner_franchise": "",
               "winner_franchise_current": "", "loser_franchise": "",
               "loser_franchise_current": "", "games_played": "", "sweep": "",
               "series_format_note": "", "winner_name_at_time": "", "loser_name_at_time": "",
               "winner_league_at_time": "", "loser_league_at_time": "", "series_score": "",
               "source_url": "", "notes": ""}
        notes = []
        if y in CHALLENGE_YEARS:
            rows = [r for r in ch_rows if r["year"] == y]
            last = [r for r in rows if r["opposed"]][-1]
            ser = challenge_series(y)
            wname, wtag = split_team(last["winner"])
            lname, ltag = split_team(last["loser"])
            word = ser["summary"].split()[0]
            gws = sum(g["w"].startswith(word) for g in ser["games"])
            gls = sum(g["l"].startswith(word) for g in ser["games"])
            n = len(ser["games"])
            end = max(g["date"] for g in ser["games"])
            if not re.search(rf"{end.day}, {y}$", last["date_str"]) or end.strftime("%B") not in (
                    last["date_str"]):
                gaps.append(f"- {y}: DISAGREEMENT end date champions-list '{last['date_str']}' vs "
                            f"challenge-games list {end}")
            if norm(lname) not in norm(ser["games"][0]["l"]) + norm(ser["games"][0]["w"]):
                gaps.append(f"- {y}: DISAGREEMENT loser list '{lname}' vs games page "
                            f"'{ser['games'][0]['l']}'")
            used.update([wname, lname])
            fmt = re.sub(r"\[[^\]]*\]", "", last["format"])
            rec.update({
                "completed_date": end.isoformat(), "start_date": min(g["date"] for g in ser["games"]).isoformat(),
                "games_played": n, "sweep": int(gws == n), "winner_name_at_time": wname,
                "loser_name_at_time": lname, "winner_league_at_time": wtag,
                "loser_league_at_time": ltag, "series_score": f"{gws}-{gls}",
                "series_format_note": f"{fmt}; {ser['summary']}",
                "source_url": f"{LIST_URL}; {CH_URL}",
            })
            notes.append("challenge era: last opposed challenge series of the calendar year; "
                         "winner is the Cup holder at year end")
            later = [r for r in rows if not r["opposed"] and rows.index(r) > rows.index(last)]
            if later:
                notes.append(f"a later no-challenger league-title entry ('{later[0]['date_str']}') "
                             "exists and is not a series")
            if gws != n:
                notes.append("two-game total-goals series: winner lost one game but won on goals "
                             "(sweep=0 by 'won all games played' rule)")
        else:
            f = finals[y]
            dates, ties, box, fmt = final_games(y)
            n = f["wg"] + f["lg"]
            end = infobox_end(y, box) if box else None
            if ties:
                notes.append("tied/suspended game table(s) dated "
                             + ", ".join(d.isoformat() for d in ties)
                             + " excluded from games_played and dates")
            if len(dates) == n - 1 and end and end > max(dates):
                gaps.append(f"- {y}: the Wikipedia page has only {len(dates)} of {n} game tables; "
                            f"completed_date taken from the infobox 'Dates' line '{box}' "
                            f"({end}) - single source, no second source for the last game date")
                notes.append("completed_date from infobox 'Dates' (last game table missing)")
                dates.append(end)
            elif len(dates) != n:
                gaps.append(f"- {y}: parsed {len(dates)} game dates but list score implies {n}")
            if dates and end and end != max(dates):
                gaps.append(f"- {y}: DISAGREEMENT last game date {max(dates)} vs infobox "
                            f"'Dates' '{box}'")
            if not box:
                gaps.append(f"- {y}: no infobox 'Dates' line to cross-check")
            used.update([f["winner"], f["loser"]])
            era = ("prearranged inter-league final" if y <= 1926
                   else "final between NHL playoff champions")
            rec.update({
                "completed_date": max(dates).isoformat(), "start_date": min(dates).isoformat(),
                "games_played": n, "sweep": int(f["lg"] == 0), "winner_name_at_time": f["winner"],
                "loser_name_at_time": f["loser"], "winner_league_at_time": f["wtag"] if y <= 1926 else "NHL",
                "loser_league_at_time": f["ltag"] if y <= 1926 else "NHL",
                "series_score": f"{f['wg']}-{f['lg']}",
                "series_format_note": f"{fmt or 'format not stated in source infobox'}; {era}",
                "source_url": f"{LIST_URL}; {final_url(y)}",
            })
            if y >= 1918:
                rec["source_url"] += f"; {HR_INDEX_URL}"
                champ, runner = hidx.get(y, ("", ""))
                if y == 1920:
                    ok = "Ottawa" in champ and "Seattle" in champ
                    if not ok:
                        gaps.append(f"- {y}: DISAGREEMENT Hockey-Reference index text '{champ}'")
                elif norm(champ) != norm(f["winner"]):
                    gaps.append(f"- {y}: DISAGREEMENT winner wiki {f['winner']} vs HR index {champ}")
                elif y >= 1927 and norm(runner) != norm(f["loser"]):
                    gaps.append(f"- {y}: DISAGREEMENT loser wiki {f['loser']} vs HR index {runner}")
            if y >= 1927:
                hf = hr_final(y)
                if hf is None:
                    gaps.append(f"- {y}: Hockey-Reference page has no Final row")
                elif (norm(hf[0]), norm(hf[1]), hf[2], hf[3]) != (
                        norm(f["winner"]), norm(f["loser"]), f["wg"], f["lg"]):
                    gaps.append(f"- {y}: DISAGREEMENT wiki {f['winner']} {f['wg']}-{f['lg']} "
                                f"{f['loser']} vs HR {hf}")
                rec["source_url"] += f"; {hr_url(y)}"
            if y == 1920:
                notes.append("no NHL playoff final in 1920; Ottawa (NHL champion) met PCHA champion "
                             "Seattle for the Cup")
            if y == 1924:
                notes.append("Cup final vs WCHL champion Calgary (2-game total-goals); Montreal "
                             "also had the NHL title series vs Ottawa")
            if "total goals" in (fmt + box).lower():
                notes.append("total-goals series")
        if dt.date.fromisoformat(rec["completed_date"]) >= election_day(y):
            notes.append("COMPLETED ON/AFTER ELECTION DAY")
        rec["notes"] = "; ".join(notes)
        recs.append(rec)

    lin = {n: lineage_for(n, cur, list_text) for n in sorted(used)}
    for rec in recs:
        for side in ("winner", "loser"):
            nm = rec[f"{side}_name_at_time"]
            canon = lin[nm]["canonical_name"]
            rec[f"{side}_franchise"] = canon or nm
            rec[f"{side}_franchise_current"] = canon
    if len(gaps) == n0:
        gaps.append("- No disagreements found.")
    pd.DataFrame(recs).to_csv(OUT_DIR / "nhl_stanley_cup.csv", index=False)
    pd.DataFrame(list(lin.values())).to_csv(OUT_DIR / "nhl_stanley_cup_lineage.csv", index=False)
    (OUT_DIR / "nhl_stanley_cup_gaps.md").write_text("\n".join(gaps) + "\n")
    print(f"nhl_stanley_cup: {len(recs)} rows; gap lines beyond preamble: {len(gaps) - n0}")


if __name__ == "__main__":
    main()
