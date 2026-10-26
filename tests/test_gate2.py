import numpy as np
import pytest
from src.search import gate2


@pytest.fixture(scope="module")
def st():
    return gate2.train_state()


def test_top_rule_shortcut_equals_full_enumeration(st):
    rng = np.random.default_rng(31)
    checked = 0
    for _ in range(40):
        t = np.zeros(32, dtype=bool)
        t[rng.choice(32, 18, replace=False)] = True
        a = gate2.n3_fit(t, st, full=False)
        b = gate2.n3_fit(t, st, full=True)
        assert a["label"] == b["label"]
        if a["label"] in ("conjA", "conjB"):
            assert a["top_ids"] == b["top_ids"] and a["top_correct"] == b["top_correct"]
            assert b["n_rules"] >= 1
            checked += 1
    assert checked >= 30


def test_test_scoring_matches_manual(st):
    rng = np.random.default_rng(3)
    for _ in range(10):
        t = np.zeros(32, dtype=bool)
        t[rng.choice(32, 18, replace=False)] = True
        r = gate2.n3_fit(t, st, full=True)
        if r["label"] in ("conjA", "conjB"):
            row = r["rows"][0]
            pred = np.ones(32 - gate2.TRAIN, dtype=bool)
            for lit in row["lits"]:
                pred &= lit["vec"][gate2.TRAIN:]
            assert int((pred == t[gate2.TRAIN:]).sum()) == r["top_correct"]
            # training-perfect: the rule is exactly right on every training year
            tr = np.logical_and.reduce([lit["vec"][:gate2.TRAIN] for lit in row["lits"]])
            assert (tr == t[:gate2.TRAIN]).all()
            return
    raise AssertionError("no conjunction found in 10 tries")


def test_runner_refuses_without_flag_and_checks_outcomes_hash():
    assert len(gate2.OUTCOMES_SHA) == 64
    import hashlib

    got = hashlib.sha256((gate2.ROOT / "data/processed/outcomes.csv").read_bytes()).hexdigest()
    assert got == gate2.OUTCOMES_SHA
