import itertools

import numpy as np
from ortools.sat.python import cp_model
from src.nulls.search_core import conj_search, keys_feasible


def brute_counts(V, target, k_max=4):
    P, N = np.flatnonzero(target), np.flatnonzero(~target)
    cand = [i for i in range(len(V)) if V[i, P].all()]
    out = {}
    for k in range(1, k_max + 1):
        out[k] = sum(
            1 for c in itertools.combinations(cand, k) if (~V[list(c)][:, N]).any(axis=0).all()
        )
    return out


def test_conj_counts_match_brute_force():
    rng = np.random.default_rng(7)
    for _ in range(25):
        V = rng.random((14, 32)) < 0.8
        target = np.zeros(32, bool)
        target[rng.choice(32, 14, replace=False)] = True
        V[:, target] |= rng.random((14, 14)) < 0.9  # make candidates plentiful
        assert conj_search(V, target)["counts"] == brute_counts(V, target)


def test_planted_rule_recovery():
    rng = np.random.default_rng(3)
    target = np.zeros(32, bool)
    target[rng.choice(32, 14, replace=False)] = True
    V = rng.random((60, 32)) < 0.5
    # plant 3 literals: all true on target years, jointly false on every non-target year
    N = np.flatnonzero(~target)
    parts = np.array_split(rng.permutation(N), 3)
    for j, part in enumerate(parts):
        V[j, :] = True
        V[j, part] = False
    res = conj_search(V, target)
    assert res["found"] and res["min_k"] <= 3 and res["counts"][3] >= 1


def test_no_rule_when_pool_cannot_cover():
    target = np.zeros(32, bool)
    target[:14] = True
    V = np.ones((5, 32), bool)  # true everywhere: never false on a loss year
    assert not conj_search(V, target)["found"]


def test_keys_solver_yes_no():
    rng = np.random.default_rng(11)
    target = np.zeros(32, bool)
    target[:16] = True
    V = np.zeros((20, 32), bool)
    V[:5, :16] = True  # 5 statements true on wins only -> perfect keys rule exists
    assert keys_feasible(V, target) == "yes"
    V2 = np.ones((1, 32), bool)
    assert keys_feasible(V2, target) == "no"
    assert cp_model is not None and rng is not None


def test_n1_reproducible_from_seed():
    from src.nulls.n1 import run

    a = run("T1", 15, with_keys=False, seed=123)
    b = run("T1", 15, with_keys=False, seed=123)
    assert a.equals(b)


def test_fast_exists_matches_exact_counts():
    from src.nulls.search_core import conj_exists

    rng = np.random.default_rng(21)
    hits = 0
    ks = set()
    for _ in range(80):
        p = rng.choice([0.5, 0.65, 0.8, 0.9])
        V = rng.random((25, 32)) < p
        target = np.zeros(32, bool)
        target[rng.choice(32, 16, replace=False)] = True
        V[: rng.integers(5, 25), :][:, target] = True
        V[:, target] |= rng.random((25, 16)) < 0.97
        ex = conj_search(V, target)
        fa = conj_exists(V, target)
        assert fa["found"] == ex["found"] and fa["min_k"] == ex["min_k"]
        hits += ex["found"]
        ks.add(ex["min_k"])
    assert hits > 5 and hits < 80 and len(ks) >= 3  # exercises found, not-found, several k


def test_fast_exists_nested_limits():
    from src.nulls.search_core import conj_exists

    rng = np.random.default_rng(5)
    V = rng.random((80, 32)) < 0.85
    target = np.zeros(32, bool)
    target[rng.choice(32, 16, replace=False)] = True
    V[:, target] |= True
    nested = conj_exists(V, target, limits=(20, 50, 80))
    for lim, r in zip((20, 50, 80), nested, strict=True):
        assert r == conj_exists(V[:lim], target)
