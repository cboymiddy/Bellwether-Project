"""Distribution of the NUMBER of perfect conjunctions per permutation on a pool (noise only).

Counts are exact numbers of perfect k-subsets (k<=4) of distinct vectors (zeta/Moebius transform).
Run: uv run python -m src.nulls.count_dist T1 [B] [pool: A|B]
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from src.config import ROOT, load_config
from src.nulls.n1 import TARGET_COUNTS
from src.nulls.parallel import run_chunks
from src.nulls.pools import pool_a, pool_b
from src.nulls.search_core import conj_search


def _init(which: str) -> dict:
    return {"V": pool_b() if which == "B" else pool_a()}


def _job(rng, n, state, params):
    out = []
    for _ in range(n):
        t = np.zeros(32, dtype=bool)
        t[rng.choice(32, TARGET_COUNTS[params["target"]], replace=False)] = True
        c = conj_search(state["V"], t)
        out.append({"found": int(c["found"]), "min_k": c["min_k"],
                    **{f"n_k{k}": c["counts"][k] for k in (1, 2, 3, 4)}})
    return out


def summarize(df: pd.DataFrame) -> dict:
    tot = df[["n_k1", "n_k2", "n_k3", "n_k4"]].sum(axis=1)
    hit = tot[tot > 0]
    atmin = df.apply(lambda r: r[f"n_k{int(r.min_k)}"] if r.min_k else 0, axis=1)
    return {"B": len(df), "P_found": float((tot > 0).mean()), "mean_all": float(tot.mean()),
            "mean_given_found": float(hit.mean()) if len(hit) else 0.0,
            "median_given_found": float(hit.median()) if len(hit) else 0.0,
            "p90_given_found": float(hit.quantile(0.9)) if len(hit) else 0.0,
            "max": int(tot.max()), "median_at_min_k_given_found": float(atmin[tot > 0].median())
            if len(hit) else 0.0, "min_k_hist": df[df.min_k > 0].min_k.value_counts().sort_index().to_dict()}


if __name__ == "__main__":
    tgt = sys.argv[1]
    B = int(sys.argv[2]) if len(sys.argv) > 2 else 20_000
    which = sys.argv[3] if len(sys.argv) > 3 else "B"
    recs = run_chunks(_job, B, 500, load_config()["seed"] + 100 + ord(tgt[1]), {"target": tgt}, _init, (which,))
    df = pd.DataFrame(recs)
    df.to_csv(ROOT / "reports" / f"countdist_{which}_{tgt}.csv", index=False)
    print(tgt, "pool", which, summarize(df))
