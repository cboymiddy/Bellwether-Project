"""Build data/processed/events/mlb_world_series.csv from raw pages in data/raw/mlb_world_series/.

Primary: Wikipedia "List of World Series champions" (series result, winner/loser) and each
"<year> World Series" page (game dates and scores). Cross-check: Baseball-Reference
(world-series index with AL/NL winner columns, plus per-year page game list).
Nothing is entered from memory; the franchise lineage dict below only maps *names that appear in the
fetched pages* to the Wikipedia franchise-row label, and the script asserts that each (year, name)
appearance falls in that row's listed appearance years.
Disagreements between sources go to data/processed/events/mlb_world_series_gaps.md.
"""

import csv
import datetime as dt
import hashlib
import re
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "mlb_world_series"
OUT = ROOT / "data" / "processed" / "events"
YEARS = list(range(1900, 2025, 4))
RETRIEVED = "2026-10-25"
WP = "https://en.wikipedia.org/wiki/"
LIST_URL = WP + "List_of_World_Series_champions"
BR_IDX = "https://www.baseball-reference.com/postseason/world-series.shtml"

# source name -> (franchise row label in Wikipedia's "Records by franchise" table, canonical name)
LINEAGE = {
    "Boston Red Sox": ("Boston Americans / Red Sox", "Boston Red Sox"),
    "Chicago Cubs": ("Chicago Cubs", "Chicago Cubs"),
    "Detroit Tigers": ("Detroit Tigers", "Detroit Tigers"),
    "New York Giants": ("New York / San Francisco Giants", "San Francisco Giants"),
    "San Francisco Giants": ("New York / San Francisco Giants", "San Francisco Giants"),
    "Brooklyn Robins": ("Brooklyn / Los Angeles Dodgers", "Los Angeles Dodgers"),
    "Brooklyn Dodgers": ("Brooklyn / Los Angeles Dodgers", "Los Angeles Dodgers"),
    "Los Angeles Dodgers": ("Brooklyn / Los Angeles Dodgers", "Los Angeles Dodgers"),
    "Cleveland Indians": ("Cleveland Indians / Guardians", "Cleveland Guardians"),
    "Washington Senators": ("Washington Senators / Minnesota Twins", "Minnesota Twins"),
    "Washington Nationals": ("Washington Senators / Minnesota Twins", "Minnesota Twins"),
    "New York Yankees": ("New York Yankees", "New York Yankees"),
    "St. Louis Cardinals": ("St. Louis Cardinals", "St. Louis Cardinals"),
    "Cincinnati Reds": ("Cincinnati Reds", "Cincinnati Reds"),
    "St. Louis Browns": ("Milwaukee Brewers / St. Louis Browns / Baltimore Orioles", "Baltimore Orioles"),
    "Boston Braves": ("Boston / Milwaukee / Atlanta Braves", "Atlanta Braves"),
    "Atlanta Braves": ("Boston / Milwaukee / Atlanta Braves", "Atlanta Braves"),
    "Pittsburgh Pirates": ("Pittsburgh Pirates", "Pittsburgh Pirates"),
    "Oakland Athletics": ("Philadelphia / Kansas City / Oakland / Athletics", "Athletics"),
    "Philadelphia Phillies": ("Philadelphia Phillies", "Philadelphia Phillies"),
    "Kansas City Royals": ("Kansas City Royals", "Kansas City Royals"),
    "San Diego Padres": ("San Diego Padres", "San Diego Padres"),
    "Toronto Blue Jays": ("Toronto Blue Jays", "Toronto Blue Jays"),
    "New York Mets": ("New York Mets", "New York Mets"),
    "Tampa Bay Rays": ("Tampa Bay Devil Rays / Rays", "Tampa Bay Rays"),
}
LINEAGE_NOTE = {
    "Washington Senators": "Original (1901-60) Washington Senators = Minnesota Twins; the 1961+ expansion "
    "Senators became the Texas Rangers (separate Wikipedia row). 1924 appearance verified against the Twins row.",
    "Washington Nationals": "Baseball-Reference's name for the early Washington Senators.",
    "Oakland Athletics": "Philadelphia (1901-54), Kansas City (1955-67), Oakland (1968-2024) Athletics; one franchise. "
    "Wikipedia row label shortens to 'Athletics'.",
    "Brooklyn Robins": "Brooklyn Dodgers' name in 1914-31 (Wilbert Robinson era); same franchise.",
    "New York Giants": "Moved to San Francisco in 1958.",
    "St. Louis Browns": "Moved to Baltimore in 1954 (Orioles). Wikipedia row also lists the 1901 Milwaukee Brewers (AL).",
    "Boston Braves": "Boston -> Milwaukee (1953) -> Atlanta (1966).",
    "Cleveland Indians": "Renamed Guardians in 2022.",
    "Tampa Bay Rays": "Appears as 2008, 2020 (Devil Rays until 2007).",
}


def clean(s):
    s = re.sub(r"\[[^\]]*\]", "", s)
    return re.sub(r"\s+", " ", s).strip()


def election_day(y):
    d = dt.date(y, 11, 1)
    while d.weekday() != 0:
        d += dt.timedelta(days=1)
    return d + dt.timedelta(days=1)


def soup(name):
    return BeautifulSoup((RAW / name).read_text(), "lxml")


def franchise_rows():
    t = soup("list.html").find_all("table")[2]
    rows = {}
    for r in t.find_all("tr")[1:]:
        c = [x.get_text(" ", strip=True) for x in r.find_all(["th", "td"])]
        rows[c[0]] = {int(y) for y in re.findall(r"\d{4}", c[5])}
    return rows


def wp_list():
    out = {}
    t = soup("list.html").find_all("table")[1]
    for r in t.find_all("tr"):
        c = [clean(x.get_text(" ", strip=True)) for x in r.find_all(["th", "td"])]
        m = re.match(r"(\d{4})", c[0])
        if not m or int(m.group(1)) not in YEARS:
            continue
        y = int(m.group(1))
        if "not played" in " ".join(c[1:]):
            out[y] = None
            continue
        teams = [re.sub(r"\s*\(\d+, \d+–\d+\)", "", x) for x in c[1:] if re.search(r"\(\d+, \d+–\d+\)", x)]
        ser = next(x for x in c[1:] if re.fullmatch(r"\d–\d(–\d)?", x))
        out[y] = {"winner": teams[0], "loser": teams[1], "series": [int(v) for v in ser.split("–")]}
    return out


GAME_RE = re.compile(r"^(.+?)(?: –)? (\d+), (.+?)(?: –)? (\d+)(?: \(\d+\))?$")


def wp_games(y):
    for t in soup(f"wp_{y}.html").find_all("table"):
        if t.get_text(" ", strip=True).startswith("Game Date"):
            games = []
            for r in t.find_all("tr")[1:]:
                c = [clean(x.get_text(" ", strip=True)) for x in r.find_all(["th", "td"])]
                m = GAME_RE.match(c[2])
                if not (c[0].isdigit() and m):
                    continue
                dm = re.fullmatch(r"(\w+) (\d+)\s*†?(?:/(\d+))?", c[1])
                start = dt.datetime.strptime(f"{dm.group(1)} {dm.group(2)} {y}", "%B %d %Y").date()
                d = start.replace(day=int(dm.group(3))) if dm.group(3) else start
                games.append((d, m.group(1), int(m.group(2)), m.group(3), int(m.group(4)), start))
            return games
    raise ValueError(y)


BR_RE = re.compile(r"Game (\d+), (\w+ \d+) (.+?) (\d+) F inal (.+?) (\d+)(?: \(\d+\))?(?= W | L | S |$|Game )")


def br_games(y):
    txt = soup(f"br_{y}.html").find("div", id="content").get_text(" ", strip=True)
    i = txt.index("Series Scores")
    seg = txt[i : txt.index("Series Batting Stats", i)]
    games = []
    for part in re.split(r"(?=Game \d+, )", seg)[1:]:
        m = BR_RE.match(part.strip())
        if not m:
            raise ValueError((y, part[:80]))
        d = dt.datetime.strptime(f"{m.group(2)} {y}", "%B %d %Y").date()
        games.append((d, m.group(3), int(m.group(4)), m.group(5), int(m.group(6)), d))
    return games


def br_index():
    t = soup("br.html").find(id="world_series_winners_al_nl")
    out = {}
    for r in t.find_all("tr"):
        c = [x.get_text(" ", strip=True) for x in r.find_all(["th", "td"])]
        if c[0].isdigit() and int(c[0]) in YEARS:
            out[int(c[0])] = {"al": c[1], "alw": int(c[2]), "nlw": int(c[3]), "nl": c[4]}
    return out


def tally(games):
    w = {}
    for _, a, sa, b, sb, _s in games:
        if sa != sb:
            k = a if sa > sb else b
            w[k] = w.get(k, 0) + 1
    ties = sum(1 for g in games if g[2] == g[4])
    return w, ties


def main():
    gaps = []
    fr = franchise_rows()
    lst, bri = wp_list(), br_index()
    used = {}

    def canon(name, y):
        label, c = LINEAGE[name]
        if y not in fr[label]:
            gaps.append(f"- {y}: '{name}' mapped to row '{label}' but year not in that row's appearance years.")
        used[name] = (label, c)
        return c

    rows = []
    for y in YEARS:
        e = lst.get(y, "absent")
        base = {"year": y, "held": 0, "completed_date": "", "start_date": "", "winner_franchise": "",
                "loser_franchise": "", "winner_league": "", "games_played": "", "sweep": "",
                "source_url": LIST_URL, "notes": ""}
        if e is None or e == "absent":
            if e is None:
                base["source_url"] = f"{LIST_URL}; {WP}{y}_World_Series"
                base["notes"] = "Not played: the list marks 1904 '(not played)'; the year page says the NL champion Giants declined to play."
                assert y not in bri
            else:
                base["notes"] = ("No World Series: the list page states the World Series was first played in 1903 "
                                 "and has been played every year since except 1904 and 1994; no row for this year.")
                assert y not in bri
            rows.append(base)
            continue
        g = wp_games(y)
        gb = br_games(y)
        w, ties = tally(g)
        wb, tiesb = tally(gb)
        win = e["winner"]
        # cross-checks
        if max(w, key=w.get) != win:
            gaps.append(f"- {y}: WP game table winner {max(w, key=w.get)} != WP list winner {win}.")
        exp = e["series"]
        if (sorted(w.values(), reverse=True) + [0, 0])[:2] != exp[:2] or ties != (exp[2] if len(exp) > 2 else 0):
            gaps.append(f"- {y}: WP game-table tally {w} ties={ties} != list series {exp}.")
        if len(g) != len(gb) or [x[5] for x in g] != [x[0] for x in gb]:
            gaps.append(f"- {y}: WP vs BR game dates/count differ: WP {[str(x[0]) for x in g]} BR {[str(x[0]) for x in gb]}.")
        susp = [x for x in g if x[0] != x[5]]
        for x in susp:
            gaps.append(f"- {y}: a game was suspended and completed later (WP: started {x[5]}, completed {x[0]}); BR lists only the start date {x[5]}. completed_date uses the completion date.")
        if sorted(wb.values()) != sorted(w.values()) or tiesb != ties:
            gaps.append(f"- {y}: WP vs BR per-game tallies differ: {w}/{ties} vs {wb}/{tiesb}.")
        b = bri[y]
        if (b["alw"], b["nlw"]) not in {(w.get(b['al'], 0), w.get(b['nl'], 0))} and sorted([b["alw"], b["nlw"]]) != sorted((list(w.values()) + [0])[:2]):
            gaps.append(f"- {y}: BR index wins {b['alw']}-{b['nlw']} differ from WP tally {w}.")
        league = "AL" if b["alw"] > b["nlw"] else "NL"
        bwin = b["al"] if league == "AL" else b["nl"]
        bl = b["nl"] if league == "AL" else b["al"]
        cw, cl = canon(win, y), canon(e["loser"], y)
        if canon(bwin, y) != cw or canon(bl, y) != cl:
            gaps.append(f"- {y}: BR winner/loser {bwin}/{bl} map to different franchises than WP {win}/{e['loser']}.")
        if bwin != win:
            gaps.append(f"- {y} (name only): WP '{win}' vs BR '{bwin}' (same franchise per lineage).")
        n = len(g)
        won = max(w.values())
        done = g[-1][0]
        ed = election_day(y)
        rows.append({**base, "held": 1, "completed_date": done.isoformat(), "start_date": g[0][0].isoformat(),
                     "winner_franchise": cw, "loser_franchise": cl, "winner_league": league, "games_played": n,
                     "sweep": int(won == n),
                     "source_url": f"{LIST_URL}; {WP}{y}_World_Series; https://www.baseball-reference.com/postseason/{y}_WS.shtml",
                     "notes": (f"includes {ties} tied game(s); " if ties else "")
                     + (f"FINAL GAME ON/AFTER ELECTION DAY {ed}" if done >= ed else "")})
    cols = list(rows[0])
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "mlb_world_series.csv", "w", newline="") as f:
        wr = csv.DictWriter(f, cols)
        wr.writeheader()
        wr.writerows(rows)
    with open(OUT / "mlb_world_series_lineage.csv", "w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["source_name", "canonical_name", "note"])
        for k, (label, c) in sorted(used.items()):
            wr.writerow([k, c, f"Wikipedia franchise row '{label}' ({LIST_URL}, 'Records by franchise'; appearance years checked "
                         f"against each use). {LINEAGE_NOTE.get(k, '')}".strip()])
    gp = ["# mlb_world_series gaps and cross-check disagreements", "",
          f"Sources: Wikipedia list + year pages vs Baseball-Reference (retrieved {RETRIEVED}).", ""]
    gp += gaps or ["No disagreements between sources on winners, losers, game counts, game dates, or tallies."]
    gp += ["", "Notes:",
           ("- 1900: no row on the list page; page text says the Series was first played in 1903. "
            "No second independent source was fetched for 1900 specifically except BR's index, which also begins at 1903."),
           "- Franchise canonical names are current names; the mapping is judged from Wikipedia's row labels, not an MLB-published lineage page."]
    (OUT / "mlb_world_series_gaps.md").write_text("\n".join(gp) + "\n")
    urls = {"list.html": LIST_URL, "br.html": BR_IDX}
    for p in sorted(RAW.glob("wp_*.html")):
        urls[p.name] = f"{WP}{p.stem[3:]}_World_Series"
    for p in sorted(RAW.glob("br_*.html")):
        if p.name != "br.html":
            urls[p.name] = f"https://www.baseball-reference.com/postseason/{p.stem[3:]}_WS.shtml"
    with open(RAW / "MANIFEST.csv", "w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["file", "url", "retrieved", "sha256"])
        for n, u in urls.items():
            wr.writerow([n, u, RETRIEVED, hashlib.sha256((RAW / n).read_bytes()).hexdigest()])
    print("gaps:", len(gaps))
    for r in rows:
        print(r["year"], r["held"], r["start_date"], r["completed_date"], r["winner_franchise"], r["loser_franchise"],
              r["winner_league"], r["games_played"], r["sweep"], r["notes"][:40])


if __name__ == "__main__":
    main()
