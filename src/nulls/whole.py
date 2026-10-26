"""Whole-procedure nulls: N1 (per-target permutation), N1-party, N2 (structured). Noise only.

N1       permute each target's own vector (true count fixed), run the tiered procedure.
N1-party permute the D/R winner sequence (15 D / 17 R, 1896 winner fixed), derive T1,T2,T3 jointly,
         run the procedure on all three, record the best label across targets.
N2       circular shifts (1..31) and reversal+shift (0..31) of the real winner sequence, evaluated
         exactly once each (63 sequences), plus random block permutations (blocks of 4 years kept in
         order, blocks shuffled, random circular shift); the unshifted real sequence is never scored.
Run: uv run python -m src.nulls.whole <mode> <B> [n_star m_star]
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from src.config import ROOT, load_config
from src.nulls.freeze_params import CAPS
from src.nulls.n1 import TARGET_COUNTS
from src.nulls.parallel import run_chunks, run_items
from src.nulls.pools import pool_a, pool_b
from src.nulls.procedure import better, evaluate, party_targets

N_D, W_PREV = 15, 0  # D wins (count), and the party of the 1896 winner (R=0): constants only


def _init() -> dict:
    return {"VA": pool_a(), "VB": pool_b()}


def _label(t, st, caps):
    return evaluate(t, st["VA"], st["VB"], caps["n_star"], caps["m_star"])


def _n1(rng, n, st, p):
    out = []
    for _ in range(n):
        t = np.zeros(32, dtype=bool)
        t[rng.choice(32, TARGET_COUNTS[p["target"]], replace=False)] = True
        lab = _label(t, st, p["caps"])
        out.append({"label": lab[0], "k": lab[1]})
    return out


def _party_record(w, st, caps):
    labs = {k: _label(t, st, caps) for k, t in party_targets(w, W_PREV).items()}
    best = labs["T1"]
    for k in ("T2", "T3"):
        best = better(best, labs[k])
    rec = {f"{k}_label": v[0] for k, v in labs.items()} | {f"{k}_k": v[1] for k, v in labs.items()}
    return rec | {"best_label": best[0], "best_k": best[1]}


T1_MIN = 12  # exact conjunction counting needs <= 20 non-target years, i.e. at least 12 True years


def _usable(w: np.ndarray) -> bool:
    return int(party_targets(w, W_PREV)["T1"].sum()) >= T1_MIN


def _party(rng, n, st, p):
    """Rejects (and counts) winner sequences whose derived T1 has fewer than T1_MIN true years."""
    base = np.array([1] * N_D + [0] * (32 - N_D))
    out, rejected = [], 0
    while len(out) < n:
        w = rng.permutation(base)
        if not _usable(w):
            rejected += 1
            continue
        out.append(_party_record(w, st, p["caps"]) | {"rejected_before": rejected})
        rejected = 0
    return out


def n2_exact_sequences(w: np.ndarray) -> list[tuple[str, np.ndarray]]:
    seqs = []
    for s in range(1, 32):
        seqs.append((f"shift{s}", np.roll(w, s)))
    for s in range(32):
        seqs.append((f"rev_shift{s}", np.roll(w[::-1], s)))
    return [(name, q) for name, q in seqs if not np.array_equal(q, w) and _usable(q)]


def _n2_exact(item, st, p):
    name, q = item
    return {"name": name} | _party_record(np.array(q), st, p["caps"])


def _n2_block(rng, n, st, p):
    w = np.array(p["w"])
    out = []
    while len(out) < n:
        q = w.reshape(8, 4)[rng.permutation(8)].reshape(-1)
        q = np.roll(q, int(rng.integers(0, 32)))
        if np.array_equal(q, w) or not _usable(q):
            continue
        out.append(_party_record(q, st, p["caps"]))
    return out


def real_party_sequence() -> list[int]:
    """Real D/R winner sequence; used ONLY to build N2 transforms, never scored against a pool."""
    o = pd.read_csv(ROOT / "data" / "processed" / "outcomes.csv")
    return [int(x == "D") for x in o.ec_winner_party]


def summarize(df: pd.DataFrame, col: str = "label") -> dict:
    vc = df[col].value_counts()
    n = len(df)
    return {"B": n, **{k: int(vc.get(k, 0)) for k in ("conjA", "conjB", "keys", "none", "unknown")},
            **{f"P_{k}": float(vc.get(k, 0) / n) for k in ("conjA", "conjB", "keys", "none")}}


if __name__ == "__main__":
    mode = sys.argv[1]
    B = int(sys.argv[2])
    caps = {"n_star": int(sys.argv[3]), "m_star": int(sys.argv[4])} if len(sys.argv) > 4 else CAPS
    seed = load_config()["seed"]
    if mode in ("n1_T1", "n1_T2", "n1_T3"):
        recs = run_chunks(_n1, B, 500, seed + 300 + ord(mode[-1]), {"target": mode[-2:], "caps": caps}, _init)
        df = pd.DataFrame(recs)
        print(mode, caps, summarize(df))
    elif mode == "party":
        recs = run_chunks(_party, B, 250, seed + 400, {"caps": caps}, _init)
        df = pd.DataFrame(recs)
        print(mode, caps, "best:", summarize(df, "best_label"))
        for k in ("T1", "T2", "T3"):
            print(" ", k, summarize(df, f"{k}_label"))
    elif mode == "n2_exact":
        w = np.array(real_party_sequence())
        items = [(nm, q.tolist()) for nm, q in n2_exact_sequences(w)]
        df = pd.DataFrame(run_items(_n2_exact, items, {"caps": caps}, _init))
        print(mode, caps, len(df), "sequences; best:", summarize(df, "best_label"))
    elif mode == "n2_block":
        w = real_party_sequence()
        recs = run_chunks(_n2_block, B, 250, seed + 600, {"w": w, "caps": caps}, _init)
        df = pd.DataFrame(recs)
        print(mode, caps, "best:", summarize(df, "best_label"))
    else:
        raise SystemExit(f"unknown mode {mode}")
    df.to_csv(ROOT / "reports" / f"whole_{mode}.csv", index=False)
