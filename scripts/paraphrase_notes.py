"""Replace verbatim third-party sentences in published event notes with short notes in the project's own words.

Found by a word-overlap scan of every free-text cell against the saved source pages (7 consecutive words, then 5 for short cells).
Only note and gap text is touched: no value column, no key, no literal. Idempotent. Run from the repository root:
    uv run python scripts/paraphrase_notes.py
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EV = ROOT / "data" / "processed" / "events"

OLYMPIC_LEDES = {
    "1900": "Per Wikipedia, no ceremonies marked the start or end of the 1900 Games.",
    "1912": "Per Wikipedia, the official opening was 6 July; tennis began 5 May, and football and shooting began 29 June.",
    "1916": "Per Wikipedia, the Berlin Games were cancelled because of World War I.",
    "1924": "Per Wikipedia, the official opening was 5 July, though some events began 4 May.",
    "1940": "Per Wikipedia, the Games planned for Tokyo and then Helsinki were cancelled because of World War II.",
    "1944": "Per Wikipedia, the Games were cancelled because of World War II.",
    "1948": "Per Wikipedia, 1948 was the only Summer Games held in the 1940s.",
    "1952": "Per Wikipedia, Helsinki had earlier been chosen for the cancelled 1940 Games.",
    "1956": "Per Wikipedia, the Games were held in Melbourne from 22 November to 8 December 1956, with the equestrian events in Stockholm in June.",
    "1964": "Per Wikipedia, Tokyo had been awarded the 1940 Games, which passed to Helsinki and were then cancelled.",
    "2020": "Per Wikipedia, the Tokyo Games were postponed on 24 March 2020 because of COVID-19 and held in 2021.",
    "2024": "Per Wikipedia, the 2024 Games returned to the usual four-year cycle after the 2020 Games were postponed.",
}
OLYMPIC_FOOTNOTES = [
    (
        re.compile(
            r"Wikipedia closing footnote: Originally scheduled for 10 September[^|]*?(?= \||$)"
        ),
        "Per a Wikipedia footnote, the closing date moved from 10 to 11 September after the Games were suspended.",
    ),
    (
        re.compile(
            r"Wikipedia opening footnote: Equestrian events held in Stockholm[^|]*?(?= \||$)"
        ),
        "Wikipedia opening footnote: the equestrian events were in Stockholm, 11-17 June 1956.",
    ),
    (
        re.compile(
            r"Wikipedia closing footnote: Equestrian events held in Stockholm[^|]*?(?= \||$)"
        ),
        "Wikipedia closing footnote: the same Stockholm dates.",
    ),
]

TEXT = {  # (file, old, new): exact substring replacements
    "indy_500.csv": [
        (
            "Not held: Not held as a result of World War II",
            "Not held: the Wikipedia list gives World War II as the reason",
        )
    ],
    "indy_500_gaps.md": [
        ("(Not held as a result of World War II)", "(the list gives World War II as the reason)")
    ],
    "mlb_world_series.csv": [
        (
            "the World Series was first played in 1903 and has been played every year since except 1904 and 1994",
            "the first World Series was in 1903; the only later years without one are 1904 and 1994",
        ),
        (
            "the first World Series was in 1903, and 1904 and 1994 are the only later years without one",
            "the first World Series was in 1903; the only later years without one are 1904 and 1994",
        ),
    ],
    "nhl_stanley_cup.csv": [
        (
            "Best-of-three; Montreal wins best-of-three series 2 games to 0",
            "best-of-three series; Montreal 2 games to 0",
        ),
        (
            "Best-of-three; Ottawa wins best-of-three series 2 games to 0",
            "best-of-three series; Ottawa 2 games to 0",
        ),
        (
            "Best-of-three; Quebec wins best-of-three series 2 games to 0",
            "best-of-three series; Quebec 2 games to 0",
        ),
        (
            "Two-game total goals; Montreal wins total goals series 13 goals to 10",
            "two-game total-goals series; Montreal 13 goals to 10",
        ),
    ],
    "nhl_stanley_cup_lineage.csv": [
        (
            "matched /The Chicago Blackhawks were known as the Chicago Black Hawks prior to/",
            "a footnote there says the club's name was spelled differently in earlier years",
        ),
        (
            "matched /records for the two teams are kept separately/",
            "that page says the two clubs' records are kept apart",
        ),
    ],
    "triple_crown.csv": [
        (
            "Belmont not run: No races held due to the Hart–Agnew Law..",
            "Belmont not run: the source attributes this to the Hart–Agnew Law.",
        ),
        (
            "(year from 'At age three in 1932')",
            "(the year is taken from what it says about the horse at age three)",
        ),
        (
            "computed: Swale article says death on June 17, 1984 was eight days after the Belmont",
            "computed: the Belmont date is the death date the Swale article gives (June 17, 1984) minus the eight days it states",
        ),
    ],
    "triple_crown_gaps.md": [
        (
            "(No races held due to the Hart–Agnew Law.)",
            "(the list attributes this to the Hart–Agnew Law)",
        ),
        (
            "says that prior to 1931/1932 the Preakness was run before the Derby eleven times; Preakness and Derby were run the same day on "
            "1917-05-12 and 1922-05-13; the Belmont was run before the Preakness on eleven occasions; since 1931 the order is Derby, "
            "Preakness, Belmont.",
            "report that the order of the three races was not always Derby, Preakness, Belmont: the Preakness came first eleven times before "
            "1931/1932, the Derby and Preakness shared a day on 1917-05-12 and 1922-05-13, and the Belmont came before the Preakness eleven times; "
            "since 1931 the order is fixed.",
        ),
        (
            "merely cites a 'May 25, 1900 New York Times article' (a publication date, not stated as the race date)",
            "cites a New York Times article dated 25 May 1900 (a publication date, not stated as the race date)",
        ),
    ],
    "wimbledon_mens_singles.csv": [
        (
            "Not held: No competition (due to World War I)",
            "Not held: the list gives World War I as the reason",
        ),
        (
            "Not held: No competition (due to World War II)",
            "Not held: the list gives World War II as the reason",
        ),
        (
            "Not held: No competition (due to COVID-19 pandemic)",
            "Not held: the list gives the COVID-19 pandemic as the reason",
        ),
    ],
    "wimbledon_mens_singles_gaps.md": [
        ("(No competition (due to World War I))", "(the list gives World War I as the reason)"),
        ("(No competition (due to World War II))", "(the list gives World War II as the reason)"),
        (
            "(No competition (due to COVID-19 pandemic))",
            "(the list gives the COVID-19 pandemic as the reason)",
        ),
    ],
    "summer_olympics_gaps.md": [
        (
            "Wikipedia's 1900 lede states no opening or closing ceremonies were held (tagged citation needed on the page)",
            "Wikipedia's 1900 introduction says there were no ceremonies at the start or end of the Games (the page tags that statement 'citation needed')",
        ),
    ],
}


def fix_olympics() -> int:
    p = EV / "summer_olympics.csv"
    rows = list(csv.DictReader(p.open(newline="")))
    n = 0
    for r in rows:
        old = r["notes"]
        new = old
        if r["year"] in OLYMPIC_LEDES:
            new = re.sub(r"Wikipedia lede: .*?(?= \| |$)", OLYMPIC_LEDES[r["year"]], new)
        for rx, rep in OLYMPIC_FOOTNOTES:
            new = rx.sub(rep, new)
        if new != old:
            r["notes"], n = new, n + 1
    with p.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    return n


def main() -> None:
    print("summer_olympics.csv: cells changed", fix_olympics())
    for name, pairs in TEXT.items():
        p = EV / name
        t = p.read_bytes().decode()  # keep the file's own line endings
        hits = 0
        for old, new in pairs:
            hits += t.count(old)
            t = t.replace(old, new)
        p.write_bytes(t.encode())
        print(f"{name}: replacements {hits}")


if __name__ == "__main__":
    main()
