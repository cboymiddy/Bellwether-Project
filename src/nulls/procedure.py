"""The tiered procedure, evaluated on one target vector. Used identically for nulls and (once) real data.

Tier 1a: perfect conjunction (k<=4) on pool A (main pool, F>=2).
Tier 1b: same on pool B (A + astronomy family), only if 1a found nothing.
Tier 2 : perfect unit-weight keys rule on pool B with N <= N_STAR and margin >= M_STAR, only if
         neither conjunction tier fired.
Label order (best first): conjA < conjB < keys < none; ties broken by smaller k.
"""

from __future__ import annotations

import numpy as np
from ortools.sat.python import cp_model

from src.nulls.search_core import conj_exists, pareto_reduce

RANK = {"conjA": 0, "conjB": 1, "keys": 2, "none": 3}
KEYS_LIMIT = 120.0


def keys_exists(VB: np.ndarray, t: np.ndarray, n_star: int, m_star: int) -> bool | None:
    """True/False if solved; None if the solver hit its time limit (reported, never silently False)."""
    R = pareto_reduce(VB, t)
    md = cp_model.CpModel()
    x = [md.NewBoolVar(f"x{i}") for i in range(len(R))]
    a = md.NewIntVar(1, n_star, "a")
    md.Add(sum(x) <= n_star)
    for y in range(R.shape[1]):
        s = sum(x[i] for i in np.flatnonzero(R[:, y]))
        md.Add(s >= a) if t[y] else md.Add(s <= a - m_star)
    so = cp_model.CpSolver()
    so.parameters.max_time_in_seconds = KEYS_LIMIT
    so.parameters.num_workers = 1
    st = so.Solve(md)
    if st in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return True
    return False if st == cp_model.INFEASIBLE else None


def evaluate(t: np.ndarray, VA: np.ndarray, VB: np.ndarray, n_star: int, m_star: int) -> tuple[str, int]:
    a = conj_exists(VA, t)
    if a["found"]:
        return "conjA", a["min_k"]
    b = conj_exists(VB, t)
    if b["found"]:
        return "conjB", b["min_k"]
    k = keys_exists(VB, t, n_star, m_star)
    if k is None:
        return "unknown", 0
    return ("keys", 0) if k else ("none", 0)


def better(l1: tuple[str, int], l2: tuple[str, int]) -> tuple[str, int]:
    """The better of two labels (unknown ranks worst but is surfaced)."""
    r = {**RANK, "unknown": 4}
    return min(l1, l2, key=lambda x: (r[x[0]], x[1] if x[1] else 99))


def party_targets(w: np.ndarray, w_prev: int = 0) -> dict[str, np.ndarray]:
    """w: array of 32 winner parties (1=D, 0=R) for 1900..2024; w_prev = party of the 1896 winner.
    T1 = incumbent-party win (winner equals previous winner), T2 = D wins, T3 = R wins."""
    prev = np.concatenate([[w_prev], w[:-1]])
    return {"T1": w == prev, "T2": w == 1, "T3": w == 0}
