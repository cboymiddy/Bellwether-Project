"""Build men's FIFA World Cup event tables from fetched raw pages (never from memory).

Primary: Wikipedia per-edition pages (infobox host/dates/champions/runners-up; final date = date of
the last match box on the page). Edition list is taken from the Wikipedia main-page table and the
RSSSF palmares independently, then compared with the downloaded edition set.
Second source: RSSSF palmares (winner/runner-up/host) and RSSSF per-edition full pages (final date).
Run: uv run python -m src.acquire.fifa_world_cup
"""

import datetime as dt
import hashlib
import re
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "fifa_world_cup"
OUT = ROOT / "data" / "processed" / "events"
RETRIEVED = "2026-10-25"
ELECTION_YEARS = list(range(1900, 2025, 4))
RSSSF_FULL = {
    1930: "30full", 1934: "34full", 1938: "38full", 1950: "50full", 1954: "54full", 1958: "58full",
    1962: "62full", 1966: "66full", 1970: "70full", 1974: "74full", 1978: "78full", 1982: "82full",
    1986: "86full", 1990: "90full", 1994: "94full", 1998: "98full", 2002: "2002full",
    2006: "2006full", 2010: "2010full", 2014: "2014full", 2018: "2018full", 2022: "2022f",
    2026: "2026f",
}
ISO = re.compile(r"\(\s*(\d{4}-\d{2}-\d{2})\s*\)")


def election_day(year: int) -> dt.date:
    d = dt.date(year, 11, 1)
    while d.weekday() != 0:
        d += dt.timedelta(days=1)
    return d + dt.timedelta(days=1)


def soup(path: Path) -> BeautifulSoup:
    return BeautifulSoup(path.read_text(encoding="utf-8"), "lxml")


def clean_team(text: str) -> str:
    text = re.sub(r"\[[^\]]*\]", "", text)
    return re.sub(r"\s*\(.*?\)\s*", " ", text).strip()


def wiki_edition(y: int) -> dict:
    s = soup(RAW / "wiki" / f"{y}.html")
    info = {}
    for tr in s.find("table", class_="infobox").find_all("tr"):
        th, td = tr.find("th"), tr.find("td")
        if th and td:
            info[th.get_text(" ", strip=True)] = td
    host_td = info.get("Host country") or info.get("Host countries")
    boxes = s.find_all("div", class_="footballbox")
    last = boxes[-1].get_text(" ", strip=True) if boxes else ""
    m = ISO.search(last)
    return {
        "host": " / ".join(host_td.stripped_strings) if host_td else "",
        "dates": info["Dates"].get_text(" ", strip=True) if "Dates" in info else "",
        "winner": clean_team(info["Champions"].get_text(" ", strip=True)),
        "runner_up": clean_team(info["Runners-up"].get_text(" ", strip=True)),
        "last_match_date": m.group(1) if m else "",
        "last_match_text": last[:160],
    }


future: dict[int, str] = {}


def wiki_main_years() -> dict[int, tuple[str, str, str]]:
    s = soup(RAW / "wiki_fifa_world_cup.html")
    for tb in s.find_all("table"):
        t = tb.get_text(" ", strip=True)
        if "Runners-up" in t and "Third place game" in t:
            out = {}
            for tr in tb.find_all("tr"):
                c = [x.get_text(" ", strip=True) for x in tr.find_all(["th", "td"])]
                if len(c) >= 6 and c[0].isdigit() and c[1].isdigit():
                    if not c[3]:  # scheduled edition with no champion yet (TBA)
                        future[int(c[1])] = c[2]
                        continue
                    out[int(c[1])] = (c[2], clean_team(c[3]), clean_team(c[5]))
            return out
    raise ValueError("main table not found")


def rsssf_palmares() -> dict[int, dict]:
    t = re.sub(r"<[^>]+>", "", (RAW / "rsssf_wc.html").read_text(encoding="latin-1"))
    part = t[t.index("Finals\n"):]
    out = {}
    pat = re.compile(r"^(\d{4})\s+(.+?)\s+(\d+-\d+)\s+(.+?)\s{2,}.*\n\s+\[Final tournament in (.+?)\]", re.MULTILINE)
    for m in pat.finditer(part + "\n"):
        out[int(m.group(1))] = {"winner": m.group(2).strip(), "runner_up": m.group(4).strip(),
                                "host": m.group(5).strip()}
    for m in re.finditer(r"^(\d{4})\s+(\S.*?)\s{2,}(?:\d+-\d+\s)?(.+?)\s+\[Final tournament in (.+?)\]", part, re.MULTILINE):
        out.setdefault(int(m.group(1)), {})
    # editions whose final line has trailing text (e.g. penalties) on the same line
    for m in re.finditer(r"^(\d{4})\s+(.+?)\s+(\d+-\d+)\s+(.+?)(?:\s{2,}.*)?\n\s+\[Final tournament in (.+?)\]",
                         part, re.MULTILINE):
        out[int(m.group(1))] = {"winner": m.group(2).strip(), "runner_up": m.group(4).strip(),
                                "host": m.group(5).strip()}
    return out


def rsssf_final_date(y: int, winner: str, runner_up: str) -> str:
    f = RAW / "rsssf" / f"{RSSSF_FULL[y]}.html"
    raw = f.read_bytes()
    text = raw.decode("utf-16") if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else raw.decode("latin-1")
    text = re.sub(r"<[^>]+>", "", text)
    heads = [h.end() for h in re.finditer(r"(?im)^\s*final\s*$", text)]
    for end in reversed(heads):  # last 'Final' heading that is followed by a date
        seg = text[end:end + 160]
        m = re.search(r"(\d{2})[./](\d{2})[./](\d{2,4})\b", seg)
        if m:
            yy = int(m.group(3))
            return dt.date(yy if yy > 99 else 1900 + yy, int(m.group(2)), int(m.group(1))).isoformat()
        m = re.search(r"\[(\w{3}) (\d{1,2})\]", seg)
        if m:
            return dt.datetime.strptime(f"{m.group(1)} {m.group(2)} {y}", "%b %d %Y").date().isoformat()
    m = re.search(r"FINAL\s*\n\s*\n[^\n]*?,\s+(\w+) (\d{1,2}), (\d{4})", text)  # 2022 layout
    if m:
        return dt.datetime.strptime(f"{m.group(1)} {m.group(2)} {m.group(3)}", "%B %d %Y").date().isoformat()
    if y == 1950:  # no final match; decisive final-pool match (URU-BRA)
        m = re.search(r"(\d{2})\.(\d{2})\.(\d{2})\s+\([\d.]+\)[^\n]*\n\s*\nURU - BRA", text)
        if m:
            return f"19{m.group(3)}-{m.group(2)}-{m.group(1)}"
    for line in text.splitlines():  # 2026 layout: 'DD- M-YY Venue  Team  s-s Team'
        mm = re.match(r"\s*(\d{1,2})-\s*(\d{1,2})-(\d{2})\s+.*", line)
        if mm and winner in line and runner_up in line:
            return dt.date(2000 + int(mm.group(3)), int(mm.group(2)), int(mm.group(1))).isoformat()
    return ""


def manifest() -> None:
    urls = {
        "wiki_fifa_world_cup.html": "https://en.wikipedia.org/wiki/FIFA_World_Cup",
        "rsssf_wc.html": "https://www.rsssf.org/tablesw/worldcup.html",
    }
    for y, name in RSSSF_FULL.items():
        urls[f"wiki/{y}.html"] = f"https://en.wikipedia.org/wiki/{y}_FIFA_World_Cup"
        urls[f"rsssf/{name}.html"] = f"https://www.rsssf.org/tables/{name}.html"
    lines = ["file,url,retrieved,sha256"]
    for f, u in urls.items():
        lines.append(f"{f},{u},{RETRIEVED},{hashlib.sha256((RAW / f).read_bytes()).hexdigest()}")
    (RAW / "MANIFEST.csv").write_text("\n".join(lines) + "\n")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest()
    main_years = wiki_main_years()
    pal = rsssf_palmares()
    dl = set(RSSSF_FULL)
    gaps = [
        "# fifa_world_cup gaps and disagreements",
        "",
        ("- Britannica (https://www.britannica.com/sports/World-Cup-football) returned a Cloudflare challenge; "
        "not used. fifa.com was not used (no usable static content was captured); the second source is RSSSF."),
        ("- Final dates: Wikipedia = date of the last match box on each edition page; RSSSF = date under its "
        "'Final' heading (1950: decisive final-pool match, since no final was played)."),
    ]
    for fy, fh in sorted(future.items()):
        gaps.append(f"- {fy}: listed on the Wikipedia main table with host '{fh}' and no champion (TBA); "
                    "not yet held per that page, excluded from the all-years table.")
    if set(main_years) != dl:
        gaps.append(f"- EDITION SET MISMATCH: Wikipedia main table {sorted(set(main_years) ^ dl)} vs downloaded.")
    if set(pal) != dl:
        gaps.append(f"- EDITION SET MISMATCH: RSSSF palmares {sorted(set(pal) ^ dl)} vs downloaded.")
    rows = []
    for y in sorted(dl):
        w = wiki_edition(y)
        p = pal.get(y, {})
        rdate = rsssf_final_date(y, p.get("winner", ""), p.get("runner_up", ""))
        notes = []
        if y == 1950:
            notes.append("1950 had a final round (pool) with no final match; date = last match, Uruguay-Brazil")
        if not rdate:
            gaps.append(f"- {y}: RSSSF final date could not be parsed.")
        elif rdate != w["last_match_date"]:
            gaps.append(f"- {y}: final date disagreement: Wikipedia {w['last_match_date']} vs RSSSF {rdate}.")
        for k in ("winner", "runner_up"):
            a, b = w[k], p.get(k, "")
            if a.lower() != b.lower() and a.replace("West ", "") != b.replace("West ", ""):
                gaps.append(f"- {y}: {k} naming/disagreement: Wikipedia '{a}' vs RSSSF '{b}'.")
        if w["winner"] not in w["last_match_text"] or w["runner_up"] not in w["last_match_text"]:
            gaps.append(f"- {y}: last Wikipedia match box does not name both finalists ('{w['last_match_text'][:90]}').")
        rows.append({
            "year": y, "host": w["host"], "final_date": w["last_match_date"], "winner": w["winner"],
            "runner_up": w["runner_up"], "wikipedia_dates": w["dates"], "rsssf_final_date": rdate,
            "rsssf_host": p.get("host", ""), "rsssf_winner": p.get("winner", ""),
            "rsssf_runner_up": p.get("runner_up", ""),
            "source_url": (f"https://en.wikipedia.org/wiki/{y}_FIFA_World_Cup; "
                           f"https://www.rsssf.org/tables/{RSSSF_FULL[y]}.html; https://www.rsssf.org/tablesw/worldcup.html"),
            "notes": "; ".join(notes),
        })
    allp = pd.DataFrame(rows)
    allp.to_csv(OUT / "fifa_world_cup_all_years.csv", index=False)

    table = []
    for y in ELECTION_YEARS:
        hit = allp[pd.to_datetime(allp.final_date).dt.year == y]
        if len(hit):
            r = hit.iloc[0]
            ed = election_day(y)
            fd = dt.date.fromisoformat(r.final_date)
            note = f"Final on/after Election Day {ed}" if fd >= ed else ""
            table.append({"year": y, "held": 1, "completed_date": r.final_date, "start_date": "",
                          "winner_team": r.winner, "runner_up_team": r.runner_up, "host_country": r.host,
                          "final_date": r.final_date, "source_url": r.source_url, "notes": note})
        else:
            table.append({"year": y, "held": 0, "completed_date": "", "start_date": "", "winner_team": "",
                          "runner_up_team": "", "host_country": "", "final_date": "", "source_url": (
                              "https://en.wikipedia.org/wiki/FIFA_World_Cup; "
                              "https://www.rsssf.org/tablesw/worldcup.html"),
                          "notes": ("No men's World Cup edition in the all-years table has a final in this year; "
                                    "see fifa_world_cup_all_years.csv")})
    pd.DataFrame(table).to_csv(OUT / "fifa_world_cup.csv", index=False)

    names = sorted(set(allp.winner) | set(allp.runner_up))
    lin = [{"source_name": n, "canonical_name": "Germany" if n == "West Germany" else n,
            "note": ("RSSSF palmares counts '(West) Germany' as one entry (4 titles)"
                     if n == "West Germany" else "identity; no mapping")} for n in names]
    pd.DataFrame(lin).to_csv(OUT / "fifa_world_cup_lineage.csv", index=False)
    (OUT / "fifa_world_cup_gaps.md").write_text("\n".join(gaps) + "\n")
    print(allp[["year", "host", "final_date", "winner", "runner_up", "rsssf_final_date"]].to_string())
    print("election-year rows held=1:", [t["year"] for t in table if t["held"]], "gaps lines:", len(gaps))


if __name__ == "__main__":
    main()
