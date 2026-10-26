"""Search primitives shared by the null harness (and, later, the real search).

Conjunction stage (CLAUDE.md Section 5): keep vectors true in all target years P; a conjunction is
perfect iff the OR of their false-masks over the non-target years N covers N. Exact counts of
perfect k-subsets (k<=4, distinct vectors) come from a zeta/Moebius transform over the 2^|N| masks.
Keys stage: unit-weight "at least t of <=N_MAX statements" with perfect separation (CP-SAT).
"""

from __future__ import annotations

from math import factorial

import numpy as np
from ortools.sat.python import cp_model

K_MAX = 4
N_MAX = 13


def conj_search(V: np.ndarray, target: np.ndarray, k_max: int = K_MAX) -> dict:
    """V: (M, 32) bool distinct vectors; target: (32,) bool (True = predict WIN years)."""
    P = np.flatnonzero(target)
    N = np.flatnonzero(~target)
    n = len(N)
    cand = V[:, P].all(axis=1)
    masks = ((~V[cand][:, N]).astype(np.int64) << np.arange(n)).sum(axis=1)
    f = np.bincount(masks, minlength=1 << n).astype(np.int64)
    for b in range(n):  # zeta transform: f[S] = number of candidates with mask subset of S
        f = f.reshape(-1, 2, 1 << b)
        f[:, 1, :] += f[:, 0, :]
        f = f.reshape(-1)
    if n > 20:
        raise ValueError("conj_search supports at most 20 non-target years")
    if f.max() >= 40_000:
        raise ValueError("too many candidates for exact int64 binomials")
    pop = np.array([s.bit_count() for s in range(1 << n)])
    sign = np.where((n - pop) % 2 == 0, 1, -1).astype(np.int64)
    counts = {}
    for k in range(1, k_max + 1):
        ck = f.copy()
        if k > 1:
            ck = np.ones_like(f)
            for j in range(k):
                ck = ck * np.maximum(f - j, 0)
            ck //= factorial(k)
        counts[k] = int(sum((sign * ck).tolist()))  # exact Python-int sum
    ks = [k for k, c in counts.items() if c > 0]
    return {"n_candidates": int(cand.sum()), "found": bool(ks), "min_k": min(ks) if ks else 0,
            "counts": counts}


def keys_feasible(V: np.ndarray, target: np.ndarray, n_max: int = N_MAX,
                  time_limit: float = 20.0) -> str:
    """'yes' / 'no' / 'unknown': exists subset S (|S|<=n_max) and t with wins>=t>losses."""
    m = cp_model.CpModel()
    M = V.shape[0]
    x = [m.NewBoolVar(f"x{i}") for i in range(M)]
    t = m.NewIntVar(1, n_max, "t")
    m.Add(sum(x) <= n_max)
    for y in range(V.shape[1]):
        s = sum(x[i] for i in np.flatnonzero(V[:, y]))
        if target[y]:
            m.Add(s >= t)
        else:
            m.Add(s <= t - 1)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_workers = 1
    st = solver.Solve(m)
    return {cp_model.OPTIMAL: "yes", cp_model.FEASIBLE: "yes", cp_model.INFEASIBLE: "no"}.get(
        st, "unknown")


def _superset_transform(a: np.ndarray, n: int) -> np.ndarray:
    """For each S: aggregate (sum, or OR for bool) of a[T] over all T that are supersets of S."""
    a = a.copy()
    for b in range(n):
        a = a.reshape(-1, 2, 1 << b)
        if a.dtype == bool:
            a[:, 0, :] |= a[:, 1, :]
        else:
            a[:, 0, :] += a[:, 1, :]
        a = a.reshape(-1)
    return a


def conj_exists(V: np.ndarray, target: np.ndarray, k_max: int = K_MAX,
                limits: tuple[int, ...] | None = None) -> dict | list[dict]:
    """Fast existence + minimal k of a perfect conjunction (no counts).

    `limits` (sorted row counts) evaluates nested sub-pools V[:limit] sharing one candidate pass;
    returns a list of {found, min_k, n_candidates}, one per limit (else a single dict).
    Only maximal masks matter for cover existence, so dominated masks are dropped.
    """
    P, N = np.flatnonzero(target), np.flatnonzero(~target)
    n = len(N)
    if n > 20:
        raise ValueError("conj_exists supports at most 20 non-target years")
    cand = V[:, P].all(axis=1)
    idx = np.flatnonzero(cand)
    allmasks = ((~V[idx][:, N]).astype(np.int64) << np.arange(n)).sum(axis=1)
    full = (1 << n) - 1
    out = []
    for lim in limits or (len(V),):
        sel = allmasks[idx < lim]
        res = {"n_candidates": len(sel), "found": False, "min_k": 0}
        if len(sel):
            t1 = np.zeros(1 << n, dtype=np.int32)
            t1[sel] = 1
            cnt = _superset_transform(t1, n)
            mx = np.flatnonzero(t1)[cnt[np.flatnonzero(t1)] == 1]  # maximal masks
            if t1[full]:
                res.update(found=True, min_k=1)
            else:
                g1 = _superset_transform(t1.astype(bool), n)
                if g1[full ^ mx].any():
                    res.update(found=True, min_k=2)
                elif k_max >= 3:
                    t2 = np.zeros(1 << n, dtype=bool)
                    t2[(mx[:, None] | mx[None, :]).ravel()] = True
                    g2 = _superset_transform(t2, n)
                    if g2[full ^ mx].any():
                        res.update(found=True, min_k=3)
                    elif k_max >= 4 and g2[full ^ np.flatnonzero(t2)].any():
                        res.update(found=True, min_k=4)
        out.append(res)
    return out if limits else out[0]


def pareto_reduce(V: np.ndarray, target: np.ndarray) -> np.ndarray:
    """Drop keys candidates that can never help: u dominates v when u is true on every win v is true
    on and false on every loss v is false on (win sums never fall, loss sums never rise). Exact for
    unit-weight keys rules; identical (wins, losses) projections keep one representative."""
    P, N = np.flatnonzero(target), np.flatnonzero(~target)
    W = (V[:, P].astype(np.int64) << np.arange(len(P))).sum(axis=1)
    L = (V[:, N].astype(np.int64) << np.arange(len(N))).sum(axis=1)
    key = np.stack([W, L], axis=1)
    _, first = np.unique(key, axis=0, return_index=True)
    W, L, V = W[first], L[first], V[first]
    keep = np.ones(len(V), dtype=bool)
    step = 400
    for s in range(0, len(V), step):
        wv, lv = W[s:s + step][None, :], L[s:s + step][None, :]
        dom = ((W[:, None] & wv) == wv) & ((L[:, None] & lv) == L[:, None])
        dom[np.arange(s, min(s + step, len(V))), np.arange(min(step, len(V) - s))] = False
        keep[s:s + step] = ~dom.any(axis=0)
    return V[keep]
