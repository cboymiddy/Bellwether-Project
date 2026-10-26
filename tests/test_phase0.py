import datetime as dt

import pandas as pd
import pytest
from src.config import ROOT, election_day, election_years

OUTCOMES = ROOT / "data" / "processed" / "outcomes.csv"


def test_election_years():
    ys = election_years()
    assert len(ys) == 32 and ys[0] == 1900 and ys[-1] == 2024


@pytest.mark.parametrize(
    "year,expected",
    [(1900, dt.date(1900, 11, 6)), (2020, dt.date(2020, 11, 3)), (2024, dt.date(2024, 11, 5))],
)
def test_election_day(year, expected):
    assert election_day(year) == expected


def test_election_day_range_and_weekday():
    for y in election_years():
        d = election_day(y)
        assert d.weekday() == 1 and 2 <= d.day <= 8 and d.month == 11


def test_outcomes_ec_split():
    df = pd.read_csv(OUTCOMES)
    assert len(df) == 32
    assert df.incumbent_party_won.sum() == 18


def test_outcomes_popular_vote_split():
    # Derived from fetched data (UCSB): 2000 and 2016 flip. CLAUDE.md's original 19/13 was wrong.
    df = pd.read_csv(OUTCOMES)
    assert df.incumbent_party_won_popvote.sum() == 20
    flips = df.loc[df.incumbent_party_won != df.incumbent_party_won_popvote, "year"].tolist()
    assert flips == [2000, 2016]


def test_2000_coded_as_loss():
    df = pd.read_csv(OUTCOMES).set_index("year")
    assert df.loc[2000, "incumbent_party_won"] == 0


# Later phases (literal library, search, nulls). Live once those modules exist.
@pytest.mark.skip(reason="Phase 1")
def test_every_literal_has_32_values(): ...


@pytest.mark.skip(reason="Phase 1")
def test_resolves_by_before_election_day(): ...


@pytest.mark.skip(reason="Phase 1")
def test_1904_world_series_absence_logic(): ...


@pytest.mark.skip(reason="Phase 2")
def test_planted_rule_recovery(): ...


@pytest.mark.skip(reason="Phase 3")
def test_null_harness_reproducible_from_seed(): ...
