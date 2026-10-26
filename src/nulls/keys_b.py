"""Keys null on the tier-1b pool: minimal N for a perfect unit-weight rule at each margin m=1..4.

P(a rule with N <= n and margin >= m exists) = P(min_N_m <= n), so these four distributions give
both the minimal-N and the maximum-margin-at-each-N distributions. Exact (Pareto reduction + CP-SAT).
Run: uv run python -m src.nulls.keys_b T1 [B]
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd
from ortools.sat.python import cp_model

from src.config import ROOT, load_config
from src.nulls.n1 import TARGET_COUNTS
from src.nulls.parallel import run_chunks
from src.nulls.pools import pool_b
from src.nulls.search_core import pareto_reduce

MARGINS = (1, 2, 3, 4)
N_FREE = 60
LIMIT = 120.0


def _init() -> dict:
    return {"V": pool_b()}


def min_n(V: np.ndarray, target: np.ndarray, m: int, limit: float = LIMIT) -> int | None:
    md = cp_model.CpModel()
    x = [md.NewBoolVar(f"x{i}") for i in range(len(V))]
    a = md.NewIntVar(1, N_FREE, "a")
    for y in range(V.shape[1]):
        s = sum(x[i] for i in np.flatnonzero(V[:, y]))
        md.Add(s >= a) if target[y] else md.Add(s <= a - m)
    md.Minimize(sum(x))
    so = cp_model.CpSolver()
    so.parameters.max_time_in_seconds = limit
    so.parameters.num_workers = 1
    st = so.Solve(md)
    return int(so.ObjectiveValue()) if st == cp_model.OPTIMAL else None


def _job(rng, n, state, params):
    out = []
    for _ in range(n):
        t = np.zeros(32, dtype=bool)
        t[rng.choice(32, TARGET_COUNTS[params["target"]], replace=False)] = True
        R = pareto_reduce(state["V"], t)
        out.append({f"minN_m{m}": min_n(R, t, m) for m in MARGINS} | {"reduced": len(R)})
    return out


def summarize(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for n in range(2, 16):
        r = {"N_cap": n}
        for m in MARGINS:
            r[f"P(m>={m})"] = float((df[f"minN_m{m}"].notna() & (df[f"minN_m{m}"] <= n)).mean())
        rows.append(r)
    return pd.DataFrame(rows)


if __name__ == "__main__":
    tgt = sys.argv[1]
    B = int(sys.argv[2]) if len(sys.argv) > 2 else 1500
    recs = run_chunks(_job, B, 25, load_config()["seed"] + 200 + ord(tgt[1]), {"target": tgt}, _init)
    df = pd.DataFrame(recs)
    df.to_csv(ROOT / "reports" / f"keys_B_{tgt}.csv", index=False)
    print(tgt, "unsolved:", {c: int(df[c].isna().sum()) for c in df if c.startswith("minN")})
    for m in MARGINS:
        print(f"minN_m{m}:", df[f"minN_m{m}"].value_counts().sort_index().to_dict())
    print(summarize(df).round(4).to_string(index=False))
