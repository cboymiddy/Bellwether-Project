"""Power curve: P(perfect conjunction, k<=4 | noise) as the pool grows with synthetic noise families.

Each synthetic series is iid Uniform(0,1) over the 32 election years and contributes "series >= c"
and "series <= c" literals on the frozen grid c = 0.1, 0.2, ..., 0.9 (18 literals/series, 9 distinct
vectors up to complement). Pools are nested (first M series), and every permutation is evaluated on
all M levels (common random numbers). Targets use only true counts, as in n1.py.
Run: uv run python -m src.nulls.power T1 [B] [M list, comma-separated]
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from src.config import ROOT, load_config
from src.nulls.n1 import SEED_INDEX, TARGET_COUNTS, load_pool, wilson
from src.nulls.search_core import conj_exists

GRID = np.round(np.arange(1, 10) / 10, 1)  # frozen threshold levels
LITS_PER_SERIES = 2 * len(GRID)
SYNTH_STREAM = 3  # SeedSequence child index reserved for the synthetic series


def synthetic_rows(n_series: int, seed: int | None = None) -> np.ndarray:
    base = load_config()["seed"] if seed is None else seed
    rng = np.random.default_rng(np.random.SeedSequence(base).spawn(4)[SYNTH_STREAM])
    x = rng.random((n_series, 32))
    ge = x[:, None, :] >= GRID[None, :, None]  # (S, 9, 32)
    le = x[:, None, :] <= GRID[None, :, None]
    return np.concatenate([ge, le], axis=1).reshape(-1, 32)  # series-major, 18 rows each


def run(target: str, B: int, Ms: list[int], seed: int | None = None) -> pd.DataFrame:
    base_rows = load_pool()
    syn = synthetic_rows(max(Ms), seed)
    V = np.concatenate([base_rows, syn])
    limits = tuple(len(base_rows) + LITS_PER_SERIES * m for m in Ms)
    base = load_config()["seed"] if seed is None else seed
    rng = np.random.default_rng(np.random.SeedSequence(base).spawn(4)[SEED_INDEX[target]])
    n_true = TARGET_COUNTS[target]
    rows = []
    for b in range(B):
        t = np.zeros(32, dtype=bool)
        t[rng.choice(32, n_true, replace=False)] = True
        res = conj_exists(V, t, limits=limits)
        rec = {"perm": b}
        for m, r in zip(Ms, res, strict=True):
            rec[f"found_M{m}"] = int(r["found"])
            rec[f"mink_M{m}"] = r["min_k"]
        rows.append(rec)
    return pd.DataFrame(rows)


def curve(df: pd.DataFrame, Ms: list[int]) -> pd.DataFrame:
    out = []
    for m in Ms:
        k = int(df[f"found_M{m}"].sum())
        lo, hi = wilson(k, len(df))
        out.append({"M": m, "found": k, "B": len(df), "P": k / len(df), "lo": lo, "hi": hi})
    return pd.DataFrame(out)


if __name__ == "__main__":
    tgt = sys.argv[1]
    B = int(sys.argv[2]) if len(sys.argv) > 2 else 20_000
    Ms = [int(x) for x in sys.argv[3].split(",")] if len(sys.argv) > 3 else [0, 100, 300, 1000, 3000]
    df = run(tgt, B, Ms)
    df.to_csv(ROOT / "reports" / f"power_{tgt}.csv", index=False)
    print(tgt, "\n", curve(df, Ms).to_string(index=False))
