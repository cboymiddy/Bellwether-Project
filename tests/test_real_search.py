import itertools

import numpy as np
from src.search.real import enumerate_minimal, pareto, rank_key


def brute_minimal(masks, n, k_max=4):
    full = (1 << n) - 1
    out = []
    for k in range(1, k_max + 1):
        for c in itertools.combinations(range(len(masks)), k):
            cov = 0
            for i in c:
                cov |= masks[i]
            if cov == full and not any(
                    _cov([masks[j] for j in c if j != i]) == full for i in c):
                out.append(c)
    return out


def _cov(ms):
    c = 0
    for m in ms:
        c |= m
    return c


def test_enumerate_minimal_matches_brute_force():
    rng = np.random.default_rng(2)
    found_any = 0
    for _ in range(40):
        n = int(rng.integers(5, 9))
        masks = [int(x) for x in rng.integers(1, 1 << n, size=int(rng.integers(5, 12)))]
        masks = sorted(set(masks))
        got = enumerate_minimal(np.array(masks), n)
        exp = brute_minimal(masks, n)
        assert sorted(got) == sorted(exp)
        found_any += bool(exp)
    assert found_any > 10


def test_rank_key_orders_by_min_f_then_mean_then_k_then_tz():
    a = [{"F": 3, "tz": 0}, {"F": 3, "tz": 1}]
    b = [{"F": 3, "tz": 0}, {"F": 3, "tz": 0}]
    c = [{"F": 2, "tz": 0}, {"F": 3, "tz": 0}]
    assert rank_key(b) < rank_key(a) < rank_key(c)


def test_pareto_keeps_nondominated():
    rows = [{"key": (-3, -3.0, 2, 0)}, {"key": (-3, -3.0, 2, 1)}, {"key": (-2, -3.0, 1, 0)}]
    assert {tuple(r["key"]) for r in pareto(rows)} == {(-3, -3.0, 2, 0), (-2, -3.0, 1, 0)}
