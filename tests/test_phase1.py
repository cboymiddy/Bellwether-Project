import datetime as dt

import numpy as np
import pandas as pd
import pytest
from src.config import election_day, election_years
from src.literals.core import OUT, Literal, cutoff, era_indicator_rule

YEARS = election_years()


def _lit(values, res=None):
    res = res or [cutoff(y) for y in YEARS]
    return Literal(
        id="t", statement="s", category="calendar", family="f", definition="d", source_url="u",
        dataset_citation="c", retrieval_date="2026-10-25", F=3, O="A", values=values,
        resolves_by=res,
    )


def test_era_indicator_rule():
    step = np.array([False] * 17 + [True] * 15)
    assert era_indicator_rule(step)
    assert era_indicator_rule(~step)
    assert era_indicator_rule(np.array([False] * 10 + [True] * 12 + [False] * 10))
    single = np.zeros(32, dtype=bool)
    single[5] = True
    assert not era_indicator_rule(single)
    zigzag = np.array([True, False] * 16)
    assert not era_indicator_rule(zigzag)


def test_negation_flips_values_and_keeps_resolves_by():
    lit = _lit([True, False] * 16)
    neg = lit.negation()
    assert neg.values == [not v for v in lit.values]
    assert neg.resolves_by == lit.resolves_by and neg.base_id == "t" and neg.polarity == "neg"


def test_resolves_by_must_precede_election_day():
    bad = [election_day(y) for y in YEARS]
    with pytest.raises(AssertionError):
        _lit([True] * 32, res=bad)


def _matrices():
    for name in ("main", "era_indicator"):
        yield (
            pd.read_csv(OUT / f"matrix_{name}.csv"),
            pd.read_csv(OUT / f"resolves_by_{name}.csv"),
        )


def test_every_literal_has_32_values_and_resolves_before_election_day():
    seen = 0
    for m, r in _matrices():
        assert list(m.columns[1:]) == [str(y) for y in YEARS]
        assert m.iloc[:, 1:].notna().all().all() and m.iloc[:, 1:].isin([0, 1]).all().all()
        assert list(m.id) == list(r.id)
        for y in YEARS:
            ed = pd.Timestamp(election_day(y))
            assert (pd.to_datetime(r[str(y)]) < ed).all(), y
        seen += len(m)
    assert seen > 0


def test_no_constant_literals_in_pool():
    for m, _ in _matrices():
        s = m.iloc[:, 1:].sum(axis=1)
        assert ((s > 0) & (s < 32)).all()


def test_ids_unique():
    ids = [i for m, _ in _matrices() for i in m.id]
    assert len(ids) == len(set(ids))


def test_1904_world_series_absence_logic():
    m = pd.concat([m for m, _ in _matrices()]).set_index("id")
    ws = [i for i in m.index if i.startswith(("sports_mlb_ws_", "NOT_sports_mlb_ws_"))]
    if not ws:
        pytest.skip("sports literals not built yet")
    assert dt.date(1904, 1, 1).year == 1904
    # No positive World Series literal (winner/league/length/sweep) may be True in 1904.
    pos = [i for i in ws if i.startswith("sports_mlb_ws_")]
    assert pos and (m.loc[pos, "1904"] == 0).all()
    neg = [i for i in ws if i.startswith("NOT_")]
    assert (m.loc[neg, "1904"] == 1).all()
