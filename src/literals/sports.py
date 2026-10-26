"""Sports literals from the event tables in data/processed/events/<family>.csv.

Truth rule (CLAUDE.md C1/C4 + Gate 0 decision): an event-based literal can be True only if the
event was held AND completed before Election Day; otherwise it is False, uniformly across years.
resolves_by is the completion date when that event completed before Election Day, else the day
before Election Day.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable
from dataclasses import dataclass, field

import pandas as pd

from src.config import ROOT, election_day
from src.literals.core import YEARS, Literal, Pool, cutoff

TODAY = "2026-10-25"
EV = ROOT / "data" / "processed" / "events"


@dataclass
class Family:
    name: str  # table basename
    prefix: str  # literal id prefix
    label: str  # human label, e.g. "the MLB World Series"
    F: int  # familiarity of the event itself
    entity_cols: dict[str, tuple[str, int]] = field(default_factory=dict)  # col -> (verb, F)
    cat_cols: dict[str, tuple[str, int]] = field(default_factory=dict)  # col -> (phrase, F)
    extras: list[tuple[str, str, Callable[[pd.Series], bool], int]] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    O: str = "B"
    skip_held: bool = False
    # Years whose event identity needed a judgment call (e.g. Stanley Cup challenge era). Literals
    # whose value depends on that judgment are graded O=C and quarantined (CLAUDE.md C5).
    judgment_years: frozenset = frozenset()
    patch: Callable[[pd.DataFrame], pd.DataFrame] | None = None
    robust_cols: frozenset = frozenset()  # entity columns whose values do not depend on judgment
    allow_undated: bool = False  # held rows with no sourced date; a True value then raises


def _complete(row: pd.Series, y: int, allow_undated: bool = False) -> bool:
    """Held and completed strictly before Election Day."""
    if not int(row["held"]):
        return False
    if pd.isna(row["completed_date"]):
        assert allow_undated, f"{y}: held but no completed_date"
        return True
    return dt.date.fromisoformat(str(row["completed_date"])) < election_day(y)


def _res(row: pd.Series, y: int, ok: bool) -> dt.date:
    if ok and pd.notna(row["completed_date"]):
        return dt.date.fromisoformat(str(row["completed_date"]))
    return cutoff(y)


def _slug(s: str) -> str:
    return "".join(c.lower() if c.isalnum() else "_" for c in s).strip("_")


def build_family(pool: Pool, fam: Family) -> None:
    df = pd.read_csv(EV / f"{fam.name}.csv").set_index("year").reindex(YEARS)
    if fam.patch:
        df = fam.patch(df)
    assert df["held"].notna().all(), f"{fam.name}: missing election-year rows"
    rows = [df.loc[y].copy() for y in YEARS]
    ok = [_complete(r, y, fam.allow_undated) for r, y in zip(rows, YEARS, strict=True)]
    res = [_res(r, y, k) for r, y, k in zip(rows, YEARS, ok, strict=True)]
    urls = df["source_url"].dropna()
    src = str(urls.iloc[0]).split(";")[0].strip() if len(urls) else ""
    cite = (f"Event table {fam.name}.csv built from fetched sources; raw files and sha256 in "
            f"data/raw/{fam.name}/MANIFEST.csv")

    def add(suffix, statement, fn, F, defn, entity=False, robust=False):
        vals = [bool(k and fn(r)) for r, k in zip(rows, ok, strict=True)]
        grade = fam.O
        if fam.judgment_years:
            hit = any(v for v, y in zip(vals, YEARS, strict=True) if y in fam.judgment_years)
            grade = fam.O if robust else ("C" if (not entity or hit) else fam.O)
        for v, r, y in zip(vals, rows, YEARS, strict=True):
            assert not (v and pd.isna(r["completed_date"])), f"{suffix} {y}: True without a date"
        pool.add(Literal(
            id=f"{fam.prefix}_{suffix}", statement=statement, category="sports", family=fam.name,
            definition=(f"{defn} True only if the event was held and completed before Election Day "
                        "of that year; otherwise False (event not completed = False)."),
            source_url=src, dataset_citation=cite, retrieval_date=TODAY, F=F, O=grade,
            values=vals, resolves_by=res, flags=list(fam.flags),
        ))

    if not fam.skip_held:
        add("held", f"{fam.label.capitalize()} is completed before Election Day of the election year",
            lambda r: True, fam.F, f"{fam.label.capitalize()} held in the calendar year.",
            robust=fam.name == "nhl_stanley_cup")
    for col, (verb, f) in fam.entity_cols.items():
        names = sorted({str(v) for r, k in zip(rows, ok, strict=True) if k
                        for v in [r[col]] if pd.notna(v)})
        for n in names:
            add(f"{col}_{_slug(n)}", f"{n} {verb} in the election year", lambda r, c=col, n=n: r[c] == n,
                f, f"Column {col} of {fam.name}.csv equals '{n}'.", entity=True,
                robust=col in fam.robust_cols)
    for col, (phrase, f) in fam.cat_cols.items():
        vals = sorted({str(r[col]) for r, k in zip(rows, ok, strict=True) if k and pd.notna(r[col])})
        for v in vals:
            add(f"{col}_{_slug(v)}", f"{phrase.format(v=v)}", lambda r, c=col, v=v: str(r[c]) == v,
                f, f"Column {col} of {fam.name}.csv equals '{v}'.", entity=True)
    for suffix, statement, fn, f in fam.extras:
        add(suffix, statement, fn, f, f"Derived from {fam.name}.csv columns.")


def _ge(col: str, n: float) -> Callable[[pd.Series], bool]:
    return lambda r: pd.notna(r[col]) and float(r[col]) >= n


def _month(n: int) -> Callable[[pd.Series], bool]:
    return lambda r: dt.date.fromisoformat(str(r["completed_date"])).month == n


def patch_nhl(df: pd.DataFrame) -> pd.DataFrame:
    """Challenge-era (1900-1912) winners, made robust to which series is called 'the final'.

    Every opposed series in those calendar years was won by the same club (asserted below from the
    fetched challenge-games list), so the *winner* does not depend on series selection. The event
    date used is the latest series completed before Election Day. The fetched club page says the
    Ottawa Hockey Club was the 'Silver Seven' 1903-07 and the 'Senators' from 1908, so both names
    map to one franchise (CLAUDE.md franchise-lineage rule). Loser/length literals stay
    series-dependent and are quarantined (O=C).
    """
    import re

    from src.acquire import nhl_stanley_cup as nhl

    df = df.copy()
    df["winner_franchise"] = df["winner_franchise"].replace({"Ottawa Silver Seven": "Ottawa Senators"})
    df["loser_franchise"] = df["loser_franchise"].replace({"Ottawa Silver Seven": "Ottawa Senators"})
    rows = [r for r in nhl.challenge_rows() if r["opposed"]]
    for y in nhl.CHALLENGE_YEARS:
        ys = [r for r in rows if r["year"] == y]
        names = {nhl.split_team(re.sub(r"\[[^\]]*\]", "", r["winner"]))[0] for r in ys}
        names = {"Ottawa Senators" if n == "Ottawa Silver Seven" else n for n in names}
        assert len(names) == 1, (y, names)
        ends = []
        for r in ys:
            m = re.search(r"([A-Z][a-z]+) (?:\d{1,2}[\u2013-])?(\d{1,2}), (\d{4})$", r["date_str"])
            ends.append(dt.date(int(m.group(3)), nhl.MONTH[m.group(1)], int(m.group(2))))
        ok = [e for e in ends if e < election_day(y)]
        assert ok, y
        df.loc[y, "winner_franchise"] = next(iter(names))
        df.loc[y, "completed_date"] = max(ok).isoformat()
        df.loc[y, "held"] = 1
    return df


def families() -> list[Family]:
    ws = Family(
        "mlb_world_series", "sports_mlb_ws", "the MLB World Series", 3,
        entity_cols={"winner_franchise": ("won the MLB World Series", 3),
                     "loser_franchise": ("lost the MLB World Series", 3)},
        cat_cols={"winner_league": ("An {v} team won the MLB World Series", 3)},
        extras=[
            ("went_7_or_more", "The MLB World Series went at least 7 games", _ge("games_played", 7), 3),
            ("sweep", "The MLB World Series was a sweep", lambda r: pd.notna(r["sweep"]) and float(r["sweep"]) == 1.0, 3),
            ("games_ge6", "The MLB World Series went at least 6 games", _ge("games_played", 6), 3),
            ("ended_before_oct20", "The MLB World Series ended before October 20",
             lambda r: dt.date.fromisoformat(str(r["completed_date"])) < dt.date(
                 dt.date.fromisoformat(str(r["completed_date"])).year, 10, 20), 2),
        ],
    )
    oly = Family(
        "summer_olympics", "sports_olympics", "the Summer Olympics", 3,
        entity_cols={"host_country": ("hosted the Summer Olympics (country as named then)", 3),
                     "host_city": ("hosted the Summer Olympics (city)", 3)},
    )
    wc = Family("fifa_world_cup", "sports_fifa_wc", "the men's FIFA World Cup final", 3)
    derby = Family("kentucky_derby", "sports_derby", "the Kentucky Derby", 3,
                   entity_cols={"winner_horse": ("won the Kentucky Derby", 2),
                                "winner_jockey": ("rode the Kentucky Derby winner", 1),
                                "winner_trainer": ("trained the Kentucky Derby winner", 1)})
    indy = Family("indy_500", "sports_indy500", "the Indianapolis 500", 3,
                  entity_cols={"winner_driver": ("won the Indianapolis 500", 2),
                               "winner_car_make": ("won the Indianapolis 500 in a car built by", 1)})
    masters = Family("masters", "sports_masters", "the Masters Tournament", 3,
                     entity_cols={"winner": ("won the Masters Tournament", 2)})
    wimb = Family("wimbledon_mens_singles", "sports_wimbledon", "the Wimbledon men's singles final", 3,
                  entity_cols={"champion": ("won Wimbledon men's singles", 2),
                               "runner_up": ("was the Wimbledon men's singles runner-up", 1)})
    tc = Family("triple_crown", "sports_triple_crown", "the US Triple Crown", 3, skip_held=True,
                allow_undated=True,
                extras=[("won", "A horse won the US Triple Crown in the election year",
                         lambda r: pd.notna(r["triple_crown_won"]) and float(r["triple_crown_won"]) == 1.0, 3)])
    nfl = Family(
        "nfl_super_bowl", "sports_nfl_sb", "the Super Bowl", 3,
        entity_cols={"winner_franchise": ("won the Super Bowl", 3),
                     "loser_franchise": ("lost the Super Bowl", 3)},
        cat_cols={"winner_conference": ("A team from the {v} won the Super Bowl", 3)},
    )
    nba = Family(
        "nba_finals", "sports_nba", "the NBA Finals", 3,
        entity_cols={"winner_franchise": ("won the NBA Finals", 3),
                     "loser_franchise": ("lost the NBA Finals", 3)},
        cat_cols={"winner_conference": ("The {v} champion won the NBA Finals", 2)},
        extras=[("went_7", "The NBA Finals went 7 games", _ge("games_played", 7), 3),
                ("games_ge6", "The NBA Finals went at least 6 games", _ge("games_played", 6), 3),
                ("sweep", "The NBA Finals was a sweep",
                 lambda r: pd.notna(r["sweep"]) and float(r["sweep"]) == 1.0, 3)],
    )
    nhl = Family(
        "nhl_stanley_cup", "sports_nhl", "the Stanley Cup final", 3,
        entity_cols={"winner_franchise": ("won the Stanley Cup", 3),
                     "loser_franchise": ("lost the Stanley Cup final", 3)},
        extras=[("went_7", "The Stanley Cup final went 7 games", _ge("games_played", 7), 3),
                ("games_ge6", "The Stanley Cup final went at least 6 games", _ge("games_played", 6), 3),
                ("sweep", "The Stanley Cup final was a sweep",
                 lambda r: pd.notna(r["sweep"]) and float(r["sweep"]) == 1.0, 3)],
        judgment_years=frozenset({1900, 1904, 1908, 1912}),
        flags=["challenge_era_judgment"], patch=patch_nhl,
        robust_cols=frozenset({"winner_franchise"}),
    )
    return [ws, oly, wc, derby, indy, masters, wimb, tc, nfl, nba, nhl]


def add_sports(pool: Pool) -> None:
    for fam in families():
        if (EV / f"{fam.name}.csv").exists():
            build_family(pool, fam)
        else:
            pool.exclude(fam.name, fam.name, "event table not available")
