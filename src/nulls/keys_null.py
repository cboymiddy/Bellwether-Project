"""Keys null: minimal N of a perfect unit-weight keys rule and max margin at each N (noise only).

Keys rule: subset S of pool statements, predict WIN iff #true >= a. Perfect iff every win has
count >= a and every loss has count <= a - m with margin m >= 1. N = |S|. No cap on N beyond
N_FREE. Targets use only true counts (permuted vectors), as in n1.py.
Run: uv run python -m src.nulls.keys_null T1 [B] [M]
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd
from ortools.sat.python import cp_model

from src.config import ROOT, load_config
from src.nulls.n1 import SEED_INDEX, TARGET_COUNTS, load_pool
from src.nulls.power import synthetic_rows

N_FREE = 40
N_LIST = list(range(1, 14))


def _model(V: np.ndarray, target: np.ndarray):
    m = cp_model.CpModel()
    x = [m.NewBoolVar(f"x{i}") for i in range(V.shape[0])]
    a = m.NewIntVar(1, N_FREE, "a")
    sums = [sum(x[i] for i in np.flatnonzero(V[:, y])) for y in range(V.shape[1])]
    return m, x, a, sums


def solve_min_n(V: np.ndarray, target: np.ndarray, limit: float = 30.0) -> int | None:
    m, x, a, sums = _model(V, target)
    for y, s in enumerate(sums):
        m.Add(s >= a) if target[y] else m.Add(s <= a - 1)
    m.Minimize(sum(x))
    sol = cp_model.CpSolver()
    sol.parameters.max_time_in_seconds = limit
    sol.parameters.num_workers = 1
    st = sol.Solve(m)
    return int(sol.ObjectiveValue()) if st == cp_model.OPTIMAL else None


def solve_max_margin(V: np.ndarray, target: np.ndarray, n_cap: int, limit: float = 30.0):
    m, x, a, sums = _model(V, target)
    mg = m.NewIntVar(1, N_FREE, "m")
    m.Add(sum(x) <= n_cap)
    for y, s in enumerate(sums):
        m.Add(s >= a) if target[y] else m.Add(s <= a - mg)
    m.Maximize(mg)
    sol = cp_model.CpSolver()
    sol.parameters.max_time_in_seconds = limit
    sol.parameters.num_workers = 1
    st = sol.Solve(m)
    return int(sol.ObjectiveValue()) if st == cp_model.OPTIMAL else None


def run(target: str, B: int, M: int = 0, seed: int | None = None) -> pd.DataFrame:
    V = load_pool()
    if M:
        V = np.concatenate([V, synthetic_rows(M, seed)])
    base = load_config()["seed"] if seed is None else seed
    rng = np.random.default_rng(np.random.SeedSequence(base).spawn(4)[SEED_INDEX[target]])
    rows = []
    for b in range(B):
        t = np.zeros(32, dtype=bool)
        t[rng.choice(32, TARGET_COUNTS[target], replace=False)] = True
        rec = {"perm": b, "min_N": solve_min_n(V, t)}
        for n in N_LIST + [N_FREE]:
            rec[f"margin_N{n}"] = solve_max_margin(V, t, n) if (
                rec["min_N"] is not None and n >= rec["min_N"]) else None
        rows.append(rec)
    return pd.DataFrame(rows)


def summarize(df: pd.DataFrame) -> pd.DataFrame:
    out = []
    for n in N_LIST + [N_FREE]:
        col = df[f"margin_N{n}"]
        ok = col.notna()
        out.append({"N_cap": n if n != N_FREE else f"free({N_FREE})", "P_feasible": ok.mean(),
                    "margin_median": col.median(), "margin_max": col.max(),
                    "margin_mean": col.mean()})
    return pd.DataFrame(out)


if __name__ == "__main__":
    tgt, B = sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 1000
    M = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    df = run(tgt, B, M)
    df.to_csv(ROOT / "reports" / f"keys_null_{tgt}_M{M}.csv", index=False)
    print(tgt, "M", M, "min_N dist:", df.min_N.value_counts().sort_index().to_dict())
    print(summarize(df).to_string(index=False))
