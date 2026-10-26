"""The real search. Runs EXACTLY ONCE, after Gate 2 approval, on the frozen pools and procedure.

Guards: needs --approved-gate-2, freeze.yaml must match the current files, and a lock file prevents a
second run. The enumeration/ranking functions below are also exercised on noise targets in tests.
Run: uv run python -m src.search.real --approved-gate-2
"""

from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd
import yaml
from ortools.sat.python import cp_model

from src.config import ROOT
from src.literals import astro_family
from src.literals.core import OUT
from src.nulls import pools
from src.nulls.freeze_params import CAPS
from src.nulls.procedure import evaluate
from src.nulls.search_core import K_MAX, conj_search, pareto_reduce

LOCK = ROOT / "reports" / "real_search.lock"


def literal_table() -> dict[bytes, list[dict]]:
    """vector bytes -> aliases [{id, F, O, tz, pool}] for pool A rows and the astronomy family."""
    meta = pd.DataFrame(yaml.safe_load((OUT / "literals_main.yaml").read_text())).set_index("id")
    mat = pd.read_csv(OUT / "matrix_main.csv").set_index("id")
    table: dict[bytes, list[dict]] = {}
    for lid in meta.index[meta.F >= 2]:
        r = meta.loc[lid]
        table.setdefault(mat.loc[lid].to_numpy(dtype=bool).tobytes(), []).append(
            {"id": lid, "F": int(r.F), "O": r.O, "tz": int("tz_sensitive" in (r["flags"] or [])), "pool": "A"})
    idx = pd.read_csv(astro_family.OUT / "index.csv")
    idx = idx[idx.included == 1].set_index("id")
    am = astro_family.load_matrix()
    for lid in am.index:
        v = am.loc[lid].to_numpy(dtype=bool)
        r = idx.loc[lid]
        for pre, vec in (("", v), ("NOT_", ~v)):
            table.setdefault(vec.tobytes(), []).append(
                {"id": pre + lid, "F": int(r.F), "O": r.O, "tz": int(r.tz_sensitive), "pool": "astro"})
    return table


def enumerate_minimal(masks: np.ndarray, n: int, k_max: int = K_MAX) -> list[tuple[int, ...]]:
    """All MINIMAL covers (size <= k_max) of the n-bit universe by distinct masks, as index tuples."""
    full = (1 << n) - 1
    masks = [int(m) for m in masks]
    by_bit = [[i for i, m in enumerate(masks) if m >> b & 1] for b in range(n)]
    found: set[frozenset] = set()

    def rec(chosen: tuple[int, ...], covered: int) -> None:
        if covered == full:
            found.add(frozenset(chosen))
            return
        if len(chosen) == k_max:
            return
        bit = min((b for b in range(n) if not covered >> b & 1), key=lambda b: len(by_bit[b]))
        for i in by_bit[bit]:
            if i not in chosen:
                rec(chosen + (i,), covered | masks[i])

    rec((), 0)

    def covers(s: frozenset) -> int:
        out = 0
        for i in s:
            out |= masks[i]
        return out

    return sorted((tuple(sorted(s)) for s in found if not any(
        covers(s - {i}) == full for i in s)), key=lambda t: (len(t), t))


def rank_key(cover_lits: list[dict]) -> tuple:
    """Lexicographic C5 ranking, best first: O in {A,B} (all true here), higher min F, higher mean F,
    fewer conditions, fewer tz_sensitive literals."""
    fs = [lit["F"] for lit in cover_lits]
    return (-min(fs), -sum(fs) / len(fs), len(cover_lits), sum(lit["tz"] for lit in cover_lits))


def best_alias(aliases: list[dict]) -> dict:
    return min(aliases, key=lambda a: (-a["F"], a["O"], a["tz"], a["id"]))


def pareto(rows: list[dict]) -> list[dict]:
    """Non-dominated rules over (min F up, mean F up, k down, tz down)."""
    def dom(a, b):
        ka, kb = a["key"], b["key"]
        return all(x <= y for x, y in zip(ka, kb, strict=True)) and ka != kb
    return [r for r in rows if not any(dom(o, r) for o in rows)]


def conjunction_report(V: np.ndarray, target: np.ndarray, table: dict, top: int = 40) -> dict:
    P, N = np.flatnonzero(target), np.flatnonzero(~target)
    n = len(N)
    cand = np.flatnonzero(V[:, P].all(axis=1))
    masks = ((~V[cand][:, N]).astype(np.int64) << np.arange(n)).sum(axis=1)
    covers = enumerate_minimal(masks, n)
    rows = []
    for c in covers:
        lits = [best_alias(table[V[cand[i]].tobytes()]) for i in c]
        rows.append({"k": len(c), "literals": [lit["id"] for lit in lits],
                     "aliases": [[a["id"] for a in table[V[cand[i]].tobytes()]] for i in c],
                     "key": rank_key(lits)})
    rows.sort(key=lambda r: (r["key"], r["literals"]))
    exact = conj_search(V, target)
    return {"n_candidates": len(cand), "n_minimal_perfect": len(rows),
            "perfect_subsets_by_k": exact["counts"], "top": rows[:top], "pareto": pareto(rows)[:top]}


def keys_solution(VB: np.ndarray, target: np.ndarray, n_star: int, m_star: int) -> dict | None:
    R = pareto_reduce(VB, target)
    md = cp_model.CpModel()
    x = [md.NewBoolVar(f"x{i}") for i in range(len(R))]
    a = md.NewIntVar(1, n_star, "a")
    mg = md.NewIntVar(m_star, n_star, "m")
    md.Add(sum(x) <= n_star)
    for y in range(32):
        s = sum(x[i] for i in np.flatnonzero(R[:, y]))
        md.Add(s >= a) if target[y] else md.Add(s <= a - mg)
    md.Minimize(1000 * sum(x) - mg)  # smallest N first, then largest margin
    so = cp_model.CpSolver()
    so.parameters.max_time_in_seconds = 120
    so.parameters.num_workers = 1
    if so.Solve(md) not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None
    sel = [i for i in range(len(R)) if so.Value(x[i])]
    table = literal_table()
    return {"N": len(sel), "threshold": so.Value(a), "margin": so.Value(mg),
            "statements": [best_alias(table[R[i].tobytes()])["id"] for i in sel]}


def run_real() -> dict:
    from src.nulls.freeze import build as freeze_build

    fz = yaml.safe_load((ROOT / "freeze.yaml").read_text())
    now = freeze_build(fz["null_plan"])
    if now["freeze_sha256"] != fz["freeze_sha256"]:
        raise SystemExit("freeze.yaml does not match current files: refusing to run")
    if LOCK.exists():
        raise SystemExit("real search already run (lock present): refusing to run again")
    LOCK.write_text("started\n")
    o = pd.read_csv(ROOT / "data" / "processed" / "outcomes.csv")
    targets = {"T1": o.incumbent_party_won.to_numpy(bool), "T2": (o.ec_winner_party == "D").to_numpy(bool),
               "T3": (o.ec_winner_party == "R").to_numpy(bool)}
    VA, VB, table = pools.pool_a(), pools.pool_b(), literal_table()
    out = {"freeze_sha256": fz["freeze_sha256"], "caps": CAPS,
           "search_size": {"pool_A_distinct": len(VA), "pool_B_distinct": len(VB),
                           "pool_B_raw_literals_incl_negations": int(sum(len(v) for v in table.values()))}}
    for name, t in targets.items():
        label = evaluate(t, VA, VB, CAPS["n_star"], CAPS["m_star"])
        rec = {"label": label[0], "k": label[1]}
        if label[0] == "conjA":
            rec["conjunctions"] = conjunction_report(VA, t, table)
        elif label[0] == "conjB":
            rec["conjunctions"] = conjunction_report(VB, t, table)
        elif label[0] == "keys":
            rec["keys"] = keys_solution(VB, t, CAPS["n_star"], CAPS["m_star"])
        out[name] = rec
    (ROOT / "reports" / "real_search_results.json").write_text(json.dumps(out, indent=2, default=str))
    return out


if __name__ == "__main__":
    if "--approved-gate-2" not in sys.argv:
        raise SystemExit("refusing to run: Gate 2 approval flag missing")
    res = run_real()
    print({k: (v["label"], v["k"]) for k, v in res.items() if k.startswith("T")})
