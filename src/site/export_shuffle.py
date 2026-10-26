"""Data for the shuffle demo: packed pool, ids, real targets, and Python goldens for the TS parity tests.

pool.bin  : uint32 LE count N, then N uint32 vectors (bit i = election year index i, 1900..2024), then N bytes
            (1 if the vector is also in pool A). Vectors are the distinct pool-B rows in np.unique order.
pool_meta : representative literal id per vector (frozen alias order) and glosses for non-astronomy ids.
goldens   : null shuffles regenerated from the published N1 seeds (so labels can be checked against the
            published CSV), plus the three real histories; each with the Python conjunction result.
Run: uv run python -m src.site.export_shuffle
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from src.config import ROOT, election_years, load_config
from src.literals import astro_family as af
from src.nulls.n1 import TARGET_COUNTS
from src.nulls.pools import pool_a, pool_b
from src.nulls.search_core import conj_exists
from src.search.real import best_alias, literal_table
from src.site.export import gloss

YEARS = election_years()
PUB = ROOT / "site" / "public" / "data"
DATA = ROOT / "site" / "src" / "data"
FIX = ROOT / "site" / "tests" / "fixtures"
REP = ROOT / "reports"
N_PER_TARGET = {"conjA": 12, "none": 12, "conjB": 76}


def pack(rows: np.ndarray) -> np.ndarray:
    """(N,32) bool -> uint32, bit i = year index i."""
    return (rows.astype(np.uint64) << np.arange(32, dtype=np.uint64)).sum(axis=1).astype(np.uint32)


def real_targets() -> dict[str, np.ndarray]:
    o = pd.read_csv(ROOT / "data" / "processed" / "outcomes.csv")
    return {"T1": o.incumbent_party_won.to_numpy(bool), "T2": (o.ec_winner_party == "D").to_numpy(bool),
            "T3": (o.ec_winner_party == "R").to_numpy(bool)}


def regen_targets(target: str, indices: set[int]) -> dict[int, np.ndarray]:
    """Re-draw the exact N1 permutations (chunk i of 500 uses SeedSequence(entropy).spawn(200)[i])."""
    entropy = load_config()["seed"] + 300 + ord(target[1])
    seqs = np.random.SeedSequence(entropy).spawn(200)
    out: dict[int, np.ndarray] = {}
    for c in sorted({j // 500 for j in indices}):
        rng = np.random.default_rng(seqs[c])
        for off in range(500):
            t = np.zeros(32, dtype=bool)
            t[rng.choice(32, TARGET_COUNTS[target], replace=False)] = True
            if c * 500 + off in indices:
                out[c * 500 + off] = t
    return out


def python_result(t: np.ndarray, VA: np.ndarray, VB: np.ndarray) -> dict:
    a, b = conj_exists(VA, t), conj_exists(VB, t)
    label = "conjA" if a["found"] else "conjB" if b["found"] else "none"
    return {"label": label, "min_k": a["min_k"] if a["found"] else b["min_k"] if b["found"] else 0,
            "candidates_A": a["n_candidates"], "candidates_B": b["n_candidates"]}


def build_goldens(VA: np.ndarray, VB: np.ndarray) -> list[dict]:
    cases = []
    for name, t in real_targets().items():
        r = python_result(t, VA, VB)
        cases.append({"id": f"real:{name}", "source": "real", "target": int(pack(t[None, :])[0]), "n_true": int(t.sum()),
                      "python_label": r["label"], **{k: r[k] for k in ("min_k", "candidates_A", "candidates_B")}})
    for tgt in ("T1", "T2", "T3"):
        csv = pd.read_csv(REP / f"whole_n1_{tgt}.csv")
        pick: dict[str, list[int]] = {}
        for lab, n in N_PER_TARGET.items():
            pick[lab] = [int(i) for i in csv.index[csv.label == lab][:n]]
        wanted = {j for js in pick.values() for j in js}
        drawn = regen_targets(tgt, wanted)
        for lab, js in pick.items():
            for j in js:
                t = drawn[j]
                r = python_result(t, VA, VB)
                if r["label"] != lab:
                    raise SystemExit(f"{tgt}#{j}: regenerated target gives {r['label']}, published CSV says {lab}")
                cases.append({"id": f"null:{tgt}#{j}", "source": f"null_{tgt}", "target": int(pack(t[None, :])[0]),
                              "n_true": int(t.sum()), "python_label": lab,
                              **{k: r[k] for k in ("min_k", "candidates_A", "candidates_B")}})
    return cases


def export_shuffle(pub: Path = PUB, data: Path = DATA, fix: Path = FIX) -> dict:
    VB, VA = pool_b(), pool_a()
    table = literal_table()
    ids = [best_alias(table[v.tobytes()])["id"] for v in VB]
    in_a = {v.tobytes() for v in VA}
    flags = np.array([v.tobytes() in in_a for v in VB], dtype=np.uint8)
    vecs = pack(VB)
    pub.mkdir(parents=True, exist_ok=True)
    with (pub / "pool.bin").open("wb") as f:
        f.write(np.array([len(VB)], dtype="<u4").tobytes())
        f.write(vecs.astype("<u4").tobytes())
        f.write(flags.tobytes())
    idx = pd.read_csv(af.OUT / "index.csv").set_index("id")
    labels = pd.read_csv(ROOT / "display" / "literal_labels.csv").set_index("id")
    glosses = {i: gloss(i, idx, labels) for i in ids if "astro_geo_" not in i}
    (pub / "pool_meta.json").write_text(json.dumps({"n": len(VB), "ids": ids, "gloss": glosses, "years": YEARS},
                                                   separators=(",", ":"), ensure_ascii=False))
    real = {k: {"bits": [int(x) for x in t], "target": int(pack(t[None, :])[0]), "n_true": int(t.sum())}
            for k, t in real_targets().items()}
    labels_ec = json.loads((REP / "real_search" / "labels_primary_ec.json").read_text())
    data.mkdir(parents=True, exist_ok=True)
    (data / "shuffle.json").write_text(json.dumps(
        {"years": YEARS, "real": real, "real_labels": {k: v["label"] for k, v in labels_ec.items()}},
        indent=1, sort_keys=True) + "\n")
    goldens = build_goldens(VA, VB)
    fix.mkdir(parents=True, exist_ok=True)
    (fix / "goldens.json").write_text(json.dumps(goldens, separators=(",", ":")) + "\n")
    return {"n_vectors": len(VB), "n_in_A": int(flags.sum()), "goldens": len(goldens),
            "pool_bin_bytes": (pub / "pool.bin").stat().st_size, "meta_bytes": (pub / "pool_meta.json").stat().st_size}


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    print(export_shuffle() if out is None else export_shuffle(out / "pub", out / "data", out / "fix"))
