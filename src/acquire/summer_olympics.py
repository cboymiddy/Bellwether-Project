"""Build data/processed/events/summer_olympics.csv from fetched raw pages (never from memory).

Primary source: Wikipedia per-edition pages (infobox: caption, Location, Opening, Closing).
Second source: Olympedia per-edition pages (host city, opening/closing ceremony, competition
dates) and the Olympedia editions list (cancellation remarks).
Run: uv run python -m src.acquire.summer_olympics
"""

import datetime as dt
import hashlib
import re
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup, NavigableString, Tag

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "summer_olympics"
OUT = ROOT / "data" / "processed" / "events"
RETRIEVED = "2026-10-25"
YEARS = list(range(1900, 2025, 4))
OLYMPEDIA_ID = {
    1900: 2, 1904: 3, 1908: 5, 1912: 6, 1916: 50, 1920: 7, 1924: 8, 1928: 9, 1932: 10, 1936: 11,
    1940: 51, 1944: 52, 1948: 12, 1952: 13, 1956: 14, 1960: 15, 1964: 16, 1968: 17, 1972: 18,
    1976: 19, 1980: 20, 1984: 21, 1988: 22, 1992: 23, 1996: 24, 2000: 25, 2004: 26, 2008: 53,
    2012: 54, 2016: 59, 2020: 61, 2024: 63,
}
MONTHS = {
    m: i for i, m in enumerate(
        ["January", "February", "March", "April", "May", "June", "July", "August", "September",
         "October", "November", "December"], 1)
}
MON = "|".join(MONTHS)
DMY = re.compile(rf"(\d{{1,2}})\s+({MON})\s+(\d{{4}})")
MDY = re.compile(rf"({MON})\s+(\d{{1,2}}),\s+(\d{{4}})")
DM = re.compile(rf"(\d{{1,2}})\s+({MON})")


def election_day(year: int) -> dt.date:
    d = dt.date(year, 11, 1)
    while d.weekday() != 0:
        d += dt.timedelta(days=1)
    return d + dt.timedelta(days=1)


def soup(path: Path) -> BeautifulSoup:
    return BeautifulSoup(path.read_text(encoding="utf-8"), "lxml")


def first_date(text: str) -> dt.date | None:
    m = DMY.search(text)
    if m:
        return dt.date(int(m.group(3)), MONTHS[m.group(2)], int(m.group(1)))
    m = MDY.search(text)
    if m:
        return dt.date(int(m.group(3)), MONTHS[m.group(1)], int(m.group(2)))
    return None


def day_month(text: str, year: int) -> dt.date | None:
    """Olympedia dates are 'D Month' (year implied) or 'D Month YYYY'."""
    d = first_date(text)
    if d:
        return d
    m = DM.search(text or "")
    return dt.date(year, MONTHS[m.group(2)], int(m.group(1))) if m else None


def comp_range(text: str, year: int) -> tuple[dt.date | None, dt.date | None]:
    """'14 May – 28 October', '1 – 16 August', '21 July – 8 August 2021'."""
    parts = [p.strip() for p in re.split(r"[–—-]", text or "") if p.strip()]
    if len(parts) != 2:
        return None, None
    end = day_month(parts[1], year)
    if end is None:
        return None, None
    ym = re.search(r"(\d{4})", parts[1])
    yr = int(ym.group(1)) if ym else year
    if re.fullmatch(r"\d{1,2}", parts[0]):  # 'D – D Month'
        start = dt.date(yr, end.month, int(parts[0]))
    else:
        start = day_month(parts[0], yr)
    return start, end


def infobox(s: BeautifulSoup) -> tuple[Tag, dict[str, Tag]]:
    ib = s.find("table", class_="infobox")
    rows = {}
    for tr in ib.find_all("tr"):
        th, td = tr.find("th"), tr.find("td")
        if th and td:
            rows[th.get_text(" ", strip=True)] = td
    return ib, rows


def location(td: Tag) -> list[tuple[str, str]]:
    """Split an infobox Location cell on <br>; return [(city, country), ...] as sourced."""
    segs, cur = [], []
    for node in td.children:
        if isinstance(node, Tag) and node.name == "br":
            segs.append(cur)
            cur = []
        else:
            cur.append(node)
    segs.append(cur)
    out = []
    for seg in segs:
        text = "".join(n.get_text("") if isinstance(n, Tag) and "flagicon" not in (n.get("class") or [])
                       else (str(n) if isinstance(n, NavigableString) else "") for n in seg)
        text = re.sub(r"\s+", " ", text).strip()
        city, _, country = text.partition(",")
        out.append((city.strip(), country.strip()))
    return out


def footnote_text(s: BeautifulSoup, td: Tag) -> str:
    notes = []
    for a in td.find_all("a", href=True):
        if a["href"].startswith("#cite_note-") and re.fullmatch(r"\[\s*[a-z]\s*\]", a.get_text(" ", strip=True)):
            li = s.find(id=a["href"][1:])
            if li:
                body = li.get_text(" ", strip=True)
                notes.append(re.sub(r"^[\^↑\d\s]+", "", body))
    return " ".join(dict.fromkeys(notes))


def lede_sentences(s: BeautifulSoup, pattern: str) -> str:
    div = s.find("div", class_="mw-content-ltr") or s
    paras = [re.sub(r"\[\s*[^\]]*\]", "", p.get_text(" ", strip=True)) for p in div.find_all("p")[:3]]
    sents = re.split(r"(?<=[.!?])\s+(?=[A-Z])", " ".join(paras))
    hit = [x.strip() for x in sents if re.search(pattern, x, re.IGNORECASE)]
    return " ".join(re.sub(r"\s+([,.)])", r"\1", re.sub(r"\(\s+", "(", x)) for x in hit[:3])


def olympedia_table(s: BeautifulSoup) -> dict[str, str]:
    d = {}
    for tr in s.find("table").find_all("tr"):
        c = [x.get_text(" ", strip=True) for x in tr.find_all(["td", "th"])]
        if len(c) == 2:
            d[c[0]] = c[1]
    return d


def olympedia_list_remarks() -> dict[int, str]:
    s = soup(RAW / "olympedia_editions.html")
    out = {}
    for tr in s.find("table").find_all("tr"):
        c = [x.get_text(" ", strip=True) for x in tr.find_all(["td", "th"])]
        if len(c) >= 8 and c[1].isdigit():
            out[int(c[1])] = f"Olympedia editions list: dates '{c[6]}', remark '{c[7]}'"
    return out


def iso(d: dt.date | None) -> str:
    return d.isoformat() if d else ""


def build() -> tuple[pd.DataFrame, list[str]]:
    remarks = olympedia_list_remarks()
    rows, gaps = [], []
    for y in YEARS:
        w = soup(RAW / "wiki" / f"{y}.html")
        o = soup(RAW / "olympedia" / f"{y}.html")
        ib, info = infobox(w)
        cap = ib.find("caption")
        edition = cap.get_text(" ", strip=True) if cap else ""
        od = olympedia_table(o)
        wopen = first_date(info["Opening"].get_text(" ", strip=True)) if "Opening" in info else None
        wclose = first_date(info["Closing"].get_text(" ", strip=True)) if "Closing" in info else None
        o_open = day_month(od.get("Opening ceremony", ""), y)
        o_close = day_month(od.get("Closing ceremony", ""), y)
        c_start, c_end = comp_range(od.get("Competition dates", ""), y)
        locs = location(info["Location"])
        urls = (f"https://en.wikipedia.org/wiki/{y}_Summer_Olympics; "
                f"https://www.olympedia.org/editions/{OLYMPEDIA_ID[y]}")
        held = int(bool(wopen and wclose and wopen.year == y and wclose.year == y))
        notes = []
        extra = lede_sentences(w, r"ceremon|cancel|postpon|rescheduled|except")
        if extra:
            notes.append(f"Wikipedia lede: {extra}")
        for key in ("Opening", "Closing"):
            if key in info:
                ft = footnote_text(w, info[key])
                if ft:
                    notes.append(f"Wikipedia {key.lower()} footnote: {ft}")
        if len(locs) > 1:
            notes.append("Wikipedia infobox lists additional location(s): "
                         + "; ".join(f"{c}, {k}" for c, k in locs[1:]))
        rec = {
            "year": y, "held": held, "completed_date": "", "start_date": "", "edition_name": "",
            "host_city": "", "host_country": "", "opening_date": "", "closing_date": "",
            "olympedia_host": "", "olympedia_opening_ceremony": "", "olympedia_closing_ceremony": "",
            "olympedia_competition_start": "", "olympedia_competition_end": "",
            "source_url": urls,
        }
        if held:
            ed = election_day(y)
            rec.update({
                "completed_date": iso(wclose), "start_date": iso(wopen), "edition_name": edition,
                "host_city": locs[0][0], "host_country": locs[0][1],
                "opening_date": iso(wopen), "closing_date": iso(wclose),
                "olympedia_host": od.get("Host city", "").split("\n")[0].strip(),
                "olympedia_opening_ceremony": iso(o_open), "olympedia_closing_ceremony": iso(o_close),
                "olympedia_competition_start": iso(c_start), "olympedia_competition_end": iso(c_end),
            })
            latest = max(d for d in (wclose, o_close, c_end) if d)
            if wclose >= ed:
                notes.append(f"COMPLETED ON/AFTER ELECTION DAY ({ed}) per Wikipedia closing date")
            elif latest >= ed:
                notes.append(f"A secondary-source end date ({latest}) is on/after Election Day ({ed})")
            if wopen > ed:
                notes.append(f"Wikipedia opening date is after Election Day ({ed})")
            elif wopen < ed <= wclose:
                notes.append(f"Straddles Election Day ({ed})")
            if (c_start and c_start < wopen) or (c_end and c_end > wclose):
                notes.append(f"Olympedia competition dates {iso(c_start)} to {iso(c_end)} extend beyond "
                             "Wikipedia opening/closing dates")
            # disagreements between sources (reported, not resolved)
            for lab, wv, ov, oc in (("opening", wopen, o_open, c_start), ("closing", wclose, o_close, c_end)):
                if ov is None:
                    gaps.append(f"- {y}: Olympedia has no {lab} ceremony date (Wikipedia {lab} = {iso(wv)}; "
                                f"Olympedia competition {'start' if lab == 'opening' else 'end'} = {iso(oc)}).")
                elif ov != wv:
                    gaps.append(f"- {y}: {lab} disagreement: Wikipedia infobox {iso(wv)} vs Olympedia "
                                f"{lab} ceremony {iso(ov)} (Olympedia competition "
                                f"{'start' if lab == 'opening' else 'end'} {iso(oc)}). Unresolved.")
                elif oc and oc != wv:
                    gaps.append(f"- {y}: Wikipedia and Olympedia agree on {lab} ceremony {iso(wv)} but Olympedia "
                                f"competition {'start' if lab == 'opening' else 'end'} is {iso(oc)}.")
            ow = od.get("Host city", "").split("\n")[0].strip()
            if ow and locs[0][1] and ow.split(",")[-1].strip() != locs[0][1]:
                gaps.append(f"- {y}: host country naming differs: Wikipedia '{locs[0][1]}' vs Olympedia "
                            f"'{ow.split(',')[-1].strip()}' (both retained; Wikipedia in host_country).")
        else:
            notes.append(f"held=0 for {y}. Wikipedia infobox opening/closing: "
                         f"{iso(wopen) or 'none'} / {iso(wclose) or 'none'}. {remarks.get(y, '')}")
            if wopen or wclose:
                notes.append(f"Games bearing the {y} name were held in {wopen.year if wopen else '?'}; "
                             "nominal-year Games not held in the calendar year")
                gaps.append(f"- {y}: nominal edition postponed; Wikipedia opening {iso(wopen)}, closing "
                            f"{iso(wclose)}; Olympedia competition dates '{od.get('Competition dates')}', "
                            f"ceremonies {od.get('Opening ceremony')} / {od.get('Closing ceremony')}. held=0.")
            if "Not held" not in remarks.get(y, "") and not (wopen or wclose):
                gaps.append(f"- {y}: held=0 but Olympedia list shows no 'Not held' remark; check manually.")
        rec["notes"] = " | ".join(n for n in notes if n.strip())
        rows.append(rec)
    return pd.DataFrame(rows), gaps


def manifest() -> None:
    urls = {
        "olympedia_editions.html": "https://www.olympedia.org/editions",
        "wiki_summer_olympics.html": "https://en.wikipedia.org/wiki/Summer_Olympic_Games",
        "wiki_list_of_olympic_games.html": "https://en.wikipedia.org/wiki/List_of_Olympic_Games_host_cities",
    }
    for y in YEARS:
        urls[f"wiki/{y}.html"] = f"https://en.wikipedia.org/wiki/{y}_Summer_Olympics"
        urls[f"olympedia/{y}.html"] = f"https://www.olympedia.org/editions/{OLYMPEDIA_ID[y]}"
    lines = ["file,url,retrieved,sha256"]
    for f, u in urls.items():
        h = hashlib.sha256((RAW / f).read_bytes()).hexdigest()
        lines.append(f"{f},{u},{RETRIEVED},{h}")
    (RAW / "MANIFEST.csv").write_text("\n".join(lines) + "\n")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest()
    df, gaps = build()
    df.to_csv(OUT / "summer_olympics.csv", index=False)
    head = [
        "# summer_olympics gaps and disagreements",
        "",
        "Primary = Wikipedia per-edition infobox (Opening/Closing). Second = Olympedia edition pages.",
        "Disagreements are reported, not resolved; table values follow Wikipedia.",
        ("Olympedia host country names differ in style from Wikipedia (e.g. 'Great Britain' vs "
         "'United Kingdom'); host_country is the Wikipedia string, olympedia_host keeps Olympedia's."),
        ("Olympedia ceremony columns are blank where Olympedia gives none (1900: it lists no ceremonies; "
         "1904: no closing ceremony). Wikipedia's 1900 lede states no opening or closing ceremonies were held "
         "(tagged citation needed on the page); the infobox 1900 dates are therefore start/end of the "
         "event programme, not ceremonies."),
        ("1904 spans 1 July to 23 Nov (Wikipedia) / 26 Nov (Olympedia competition end), straddling Election "
         "Day 1904-11-08 under both sources. Olympedia also lists a 14 May 1904 opening ceremony."),
        "",
    ]
    (OUT / "summer_olympics_gaps.md").write_text("\n".join(head + gaps) + "\n")
    print(df[df.held == 1][["year", "start_date", "completed_date", "host_city", "host_country"]].to_string())
    print("held=1:", int(df.held.sum()), "rows:", len(df), "gaps:", len(gaps))


if __name__ == "__main__":
    main()
