"""N1 exchangeable null on the FROZEN pool: random permutations of each target's own vector.

Only the true/false COUNT of each target is used (from outcomes.csv aggregates); no real outcome
vector is ever scored against the pool here. Records, per permutation: perfect conjunction (k<=4)
found?, min k, exact counts of perfect k-subsets, and perfect keys feasibility (N<=13).
Run: uv run python -m src.nulls.n1 T1 [B]
"""

from __future__ import annotations

import hashlib
import sys

import numpy as np
import pandas as pd

from src.config import ROOT, load_config
from src.literals.core import OUT
from src.nulls.search_core import conj_search, keys_feasible

TARGET_COUNTS = {"T1": 18, "T2": 15, "T3": 17}  # number of True years (counts from outcomes.csv)
SEED_INDEX = {"T1": 0, "T2": 1, "T3": 2}


def pool_files_sha() -> str:
    h = hashlib.sha256()
    for p in sorted(OUT.glob("*.*")):
        h.update(f"{p.name}:{hashlib.sha256(p.read_bytes()).hexdigest()}\n".encode())
    return h.hexdigest()


def load_pool() -> np.ndarray:
    m = pd.read_csv(OUT / "matrix_main.csv").set_index("id")
    return np.unique(m.to_numpy(dtype=bool), axis=0)


def run(target: str, B: int, with_keys: bool = True, seed: int | None = None) -> pd.DataFrame:
    V = load_pool()
    base = load_config()["seed"] if seed is None else seed
    rng = np.random.default_rng(np.random.SeedSequence(base).spawn(3)[SEED_INDEX[target]])
    n_true = TARGET_COUNTS[target]
    rows = []
    for b in range(B):
        t = np.zeros(32, dtype=bool)
        t[rng.choice(32, n_true, replace=False)] = True
        c = conj_search(V, t)
        row = {"perm": b, "n_cand": c["n_candidates"], "conj_found": int(c["found"]),
               "min_k": c["min_k"], **{f"n_k{k}": c["counts"][k] for k in (1, 2, 3, 4)}}
        if with_keys:
            row["keys"] = keys_feasible(V, t)
        rows.append(row)
    return pd.DataFrame(rows)


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def summarize(df: pd.DataFrame) -> dict:
    n = len(df)
    s = {"B": n, "P_conj": df.conj_found.mean(), "CI_conj": wilson(int(df.conj_found.sum()), n)}
    s["min_k_hist"] = df[df.conj_found == 1].min_k.value_counts().sort_index().to_dict()
    s["mean_n_perfect_when_found"] = float(
        df[df.conj_found == 1][["n_k1", "n_k2", "n_k3", "n_k4"]].sum(axis=1).mean()
    ) if df.conj_found.any() else 0.0
    s["median_candidates"] = float(df.n_cand.median())
    if "keys" in df.columns:
        yes = int((df["keys"] == "yes").sum())
        s.update({"P_keys": yes / n, "CI_keys": wilson(yes, n),
                  "keys_no": int((df["keys"] == "no").sum()), "keys_unknown": int((df["keys"] == "unknown").sum())})
        nc = df[df.conj_found == 0]
        s["P_keys_given_no_conj"] = float((nc["keys"] == "yes").mean()) if len(nc) else float("nan")
        s["P_two_stage_any"] = float(((df.conj_found == 1) | (df["keys"] == "yes")).mean())
    return s


if __name__ == "__main__":
    tgt = sys.argv[1]
    B = int(sys.argv[2]) if len(sys.argv) > 2 else 10_000
    out = run(tgt, B)
    out.to_csv(ROOT / "reports" / f"n1_{tgt}.csv", index=False)
    print(tgt, summarize(out), "pool_files_sha", pool_files_sha())
