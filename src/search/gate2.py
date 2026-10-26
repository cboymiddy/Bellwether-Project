"""Gate-2 runner: PRIMARY (EC), SENSITIVITY (popular vote), and N3 (fit 1900-1980, score 1984-2024).

A thin orchestrator over the FROZEN functions in src/search/real.py and src/nulls/*; it changes no
pool, cutoff, ranking, or procedure code. Differences from the frozen driver `run_real`, forced by the
pre-declared outputs: results go to reports/real_search/ (not reports/real_search_results.json), every
perfect rule is saved (conjunction_report is called with an unbounded `top`), and progress is logged.
Run: uv run python -m src.search.gate2 --approved-gate-2
Dry run on noise only: uv run python -m src.search.gate2 --dry-noise
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import multiprocessing as mp
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from src.config import ROOT, load_config
from src.nulls import parallel, pools
from src.nulls.freeze import build as freeze_build
from src.nulls.freeze_params import CAPS
from src.nulls.procedure import evaluate
from src.search.real import (
    best_alias,
    conjunction_report,
    enumerate_minimal,
    keys_solution,
    literal_table,
    rank_key,
)

TRAIN = 21  # elections 1900..1980; test = 1984..2024 (11 elections)
OUTCOMES_SHA = "788dac38a7e61bbfbbd581f6ba0210ff5a1d96d6d49322bd8a4bf22ddb197868"  # Phase 0 / d73cdb2
EC_COUNTS = {"T1": 18, "T2": 15, "T3": 17}
N3_NULL_PERMS = 2_000  # exact top-rule search is heavy when tier 1b fires (up to ~1e6 covers); see report
N3_CHUNK = 20


class Log:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)

    def __call__(self, msg: str) -> None:
        line = f"{dt.datetime.now().isoformat(timespec='seconds')} {msg}"
        with self.path.open("a") as f:
            f.write(line + "\n")
        print(line, flush=True)


def targets_from(o: pd.DataFrame, coding: str) -> dict[str, np.ndarray]:
    if coding == "ec":
        return {"T1": o.incumbent_party_won.to_numpy(bool), "T2": (o.ec_winner_party == "D").to_numpy(bool),
                "T3": (o.ec_winner_party == "R").to_numpy(bool)}
    return {"T1": o.incumbent_party_won_popvote.to_numpy(bool),
            "T2": (o.pv_winner_party == "D").to_numpy(bool), "T3": (o.pv_winner_party == "R").to_numpy(bool)}


def alias_by_id(table: dict) -> dict[str, dict]:
    return {a["id"]: a for aliases in table.values() for a in aliases}


def rule_records(rows: list[dict], by_id: dict) -> pd.DataFrame:
    pareto_keys = set()
    recs = []
    for rank, r in enumerate(rows, 1):
        lits = [by_id[i] for i in r["literals"]]
        recs.append({"rank": rank, "k": r["k"], "literals": " & ".join(r["literals"]),
                     "F": ",".join(str(x["F"]) for x in lits), "O": ",".join(x["O"] for x in lits),
                     "min_F": min(x["F"] for x in lits), "mean_F": round(sum(x["F"] for x in lits) / len(lits), 4),
                     "tz_sensitive_flags": ",".join(str(x["tz"]) for x in lits),
                     "n_tz_sensitive": sum(x["tz"] for x in lits),
                     "aliases": " | ".join("/".join(a) for a in r["aliases"])})
        pareto_keys.add(rank)
    return pd.DataFrame(recs)


def run_primary(targets: dict, tag: str, outdir: Path, log: Log, VA, VB, table, by_id) -> dict:
    out = {}
    for name, t in targets.items():
        log(f"[{tag}] {name}: {int(t.sum())} true / {int((~t).sum())} false; evaluating frozen procedure")
        label, k = evaluate(t, VA, VB, CAPS["n_star"], CAPS["m_star"])
        rec = {"label": label, "k": k, "n_true": int(t.sum())}
        if label in ("conjA", "conjB"):
            V = VA if label == "conjA" else VB
            log(f"[{tag}] {name}: label {label} k={k}; enumerating ALL minimal perfect conjunctions")
            rep = conjunction_report(V, t, table, top=10**9)
            rows = rep["top"]
            df = rule_records(rows, by_id)
            pk = {tuple(r["literals"]) for r in rep["pareto"]}
            df["pareto"] = [int(tuple(r["literals"]) in pk) for r in rows]
            df.to_csv(outdir / f"frontier_{tag}_{name}.csv", index=False)
            df.head(50).to_csv(outdir / f"top50_{tag}_{name}.csv", index=False)
            rec |= {"n_candidates": rep["n_candidates"], "n_minimal_perfect": rep["n_minimal_perfect"],
                    "perfect_subsets_by_k": rep["perfect_subsets_by_k"],
                    "n_pareto": int(df.pareto.sum()), "tier_pool_distinct_vectors": len(V),
                    "k_hist": {int(a): int(b) for a, b in df.k.value_counts().sort_index().items()}}
            log(f"[{tag}] {name}: {rep['n_minimal_perfect']} minimal perfect rules saved "
                f"(pareto {rec['n_pareto']}); top: {df.literals.iloc[0] if len(df) else None}")
        elif label == "keys":
            rec["keys"] = keys_solution(VB, t, CAPS["n_star"], CAPS["m_star"])
            log(f"[{tag}] {name}: keys rule {rec['keys']}")
        else:
            log(f"[{tag}] {name}: label {label}")
        out[name] = rec
    (outdir / f"labels_{tag}.json").write_text(json.dumps(out, indent=2, default=str))
    return out


# ------------------------------------------------------------------------------------------- N3
def train_state() -> dict:
    VA, VB, table = pools.pool_a(), pools.pool_b(), literal_table()
    rep: dict[bytes, dict] = {}
    merged: dict[bytes, list] = {}
    for key, aliases in table.items():
        for a in aliases:
            merged.setdefault(key[:TRAIN], []).append({**a, "vec": np.frombuffer(key, dtype=bool)})
    for k, aliases in merged.items():
        rep[k] = best_alias(aliases)
    return {"VA": np.unique(VA[:, :TRAIN], axis=0), "VB": np.unique(VB[:, :TRAIN], axis=0), "rep": rep}


def _covers(V: np.ndarray, t_tr: np.ndarray, rep: dict, f_min: int | None):
    P, N = np.flatnonzero(t_tr), np.flatnonzero(~t_tr)
    n = len(N)
    cand = np.flatnonzero(V[:, P].all(axis=1))
    if f_min is not None:
        cand = np.array([i for i in cand if rep[V[i].tobytes()]["F"] >= f_min], dtype=int)
    if len(cand) == 0:
        return cand, []
    masks = ((~V[cand][:, N]).astype(np.int64) << np.arange(n)).sum(axis=1)
    return cand, enumerate_minimal(masks, n)


def _rows(V, cand, covers, rep):
    rows = []
    for c in covers:
        lits = [rep[V[cand[i]].tobytes()] for i in c]
        rows.append({"k": len(c), "lits": lits, "key": rank_key(lits), "ids": [x["id"] for x in lits]})
    rows.sort(key=lambda r: (r["key"], r["ids"]))
    return rows


def top_rule(V: np.ndarray, t_tr: np.ndarray, rep: dict) -> dict | None:
    """Top-ranked rule under the frozen ranking: the max-min-F level is searched first (exactly
    equivalent to enumerating everything and sorting, because min F is the first sort key)."""
    for f in (3, 2, 1):
        cand, covers = _covers(V, t_tr, rep, f)
        if covers:
            return _rows(V, cand, covers, rep)[0]
    return None


def score_rule(lits: list[dict], t_full: np.ndarray) -> tuple[int, int]:
    pred = np.logical_and.reduce([x["vec"][TRAIN:] for x in lits])
    truth = t_full[TRAIN:]
    return int((pred == truth).sum()), len(truth)


def n3_fit(t_full: np.ndarray, st: dict, full: bool = False) -> dict:
    t = t_full[:TRAIN]
    if t.all() or not t.any():
        return {"label": "degenerate"}
    label, k = evaluate(t, st["VA"], st["VB"], CAPS["n_star"], CAPS["m_star"])
    out = {"label": label, "k": k}
    if label in ("conjA", "conjB"):
        V = st["VA"] if label == "conjA" else st["VB"]
        if full:
            cand, covers = _covers(V, t, st["rep"], None)
            rows = _rows(V, cand, covers, st["rep"])
            out["n_rules"] = len(rows)
            out["rows"] = rows
            top = rows[0]
        else:
            top = top_rule(V, t, st["rep"])
        c, n = score_rule(top["lits"], t_full)
        out |= {"top_ids": top["ids"], "top_k": top["k"], "top_correct": c, "test_n": n}
    elif label == "keys":
        sol = keys_solution(st["VB"], t, CAPS["n_star"], CAPS["m_star"])
        out["keys"] = sol
    return out


def run_chunks_logged(fn, total, chunk, entropy, params, initializer, log: Log, label: str, workers=10):
    """Same seeding as parallel.run_chunks (chunk i <- SeedSequence(entropy).spawn(n)[i]) plus progress logs."""
    sizes = [chunk] * (total // chunk) + ([total % chunk] if total % chunk else [])
    jobs = [(fn, i, n, entropy, len(sizes), params) for i, n in enumerate(sizes)]
    done, results = 0, []
    with mp.get_context("fork").Pool(workers, initializer=parallel._init, initargs=(initializer, ())) as pool:
        for idx, recs in pool.imap_unordered(parallel._run, jobs, chunksize=1):
            results.append((idx, recs))
            done += len(recs)
            log(f"[{label}] {done}/{total} null permutations done")
    results.sort(key=lambda r: r[0])
    return [rec for _, recs in results for rec in recs]


def _n3_null_job(rng, n, st, p):
    out = []
    for _ in range(n):
        t = np.zeros(32, dtype=bool)
        t[rng.choice(32, EC_COUNTS[p["target"]], replace=False)] = True
        r = n3_fit(t, st)
        out.append({"label": r["label"], "top_k": r.get("top_k", 0), "top_correct": r.get("top_correct", -1)})
    return out


def run_n3(targets: dict, outdir: Path, log: Log, n_null: int) -> dict:
    st = train_state()
    res = {}
    for name, t in targets.items():
        log(f"[N3] {name}: real fit on 1900-1980 ({TRAIN} elections), score 1984-2024")
        r = n3_fit(t, st, full=True)
        rec = {k: v for k, v in r.items() if k not in ("rows",)}
        if "rows" in r:
            recs = []
            for rank, row in enumerate(r["rows"], 1):
                c, n = score_rule(row["lits"], t)
                recs.append({"rank": rank, "k": row["k"], "literals": " & ".join(row["ids"]),
                             "min_F": row["key"][0] * -1, "test_correct": c, "test_n": n})
            df = pd.DataFrame(recs)
            df.to_csv(outdir / f"n3_rules_{name}.csv", index=False)
            rec["test_correct_hist_all_rules"] = {int(a): int(b) for a, b in
                                                 df.test_correct.value_counts().sort_index().items()}
        res[name] = {"real": rec}
        log(f"[N3] {name}: real label {r['label']}, rules {r.get('n_rules')}, top "
            f"{r.get('top_correct')}/{r.get('test_n')}; running null ({n_null} perms)")
        recs = run_chunks_logged(_n3_null_job, n_null, N3_CHUNK, load_config()["seed"] + 700 + ord(name[1]),
                                 {"target": name}, train_state_init, log, f"N3 null {name}")
        df = pd.DataFrame(recs)
        df.to_csv(outdir / f"n3_null_{name}.csv", index=False)
        res[name]["null"] = {"B": len(df), "labels": df.label.value_counts().to_dict(),
                             "top_correct_hist": {int(a): int(b) for a, b in
                                                  df[df.top_correct >= 0].top_correct.value_counts().sort_index().items()}}
        log(f"[N3] {name}: null done {res[name]['null']['labels']}")
    (outdir / "n3_summary.json").write_text(json.dumps(res, indent=2, default=str))
    return res


def train_state_init() -> dict:
    return train_state()


def verify_and_lock(outdir: Path, real: bool, resume: bool = False) -> None:
    fz = yaml.safe_load((ROOT / "freeze.yaml").read_text())
    if freeze_build(fz["null_plan"])["freeze_sha256"] != fz["freeze_sha256"]:
        raise SystemExit("freeze mismatch: refusing to run")
    if real:
        got = hashlib.sha256((ROOT / "data/processed/outcomes.csv").read_bytes()).hexdigest()
        if got != OUTCOMES_SHA:
            raise SystemExit("outcomes.csv differs from Phase 0: refusing to run")
        lock = outdir / "LOCK"
        outdir.mkdir(parents=True, exist_ok=True)
        if lock.exists():
            if not resume:
                raise SystemExit("already run (lock present): refusing to run again (use --resume to finish "
                                 "stages that have no DONE marker; completed stages are never rerun)")
            return
        lock.write_text(f"started {dt.datetime.now().isoformat()}\nfreeze {fz['freeze_sha256']}\n")


def main(real: bool, resume: bool = False) -> None:
    outdir = ROOT / "reports" / ("real_search" if real else "real_search_dryrun")
    outdir.mkdir(parents=True, exist_ok=True)
    verify_and_lock(outdir, real, resume)
    log = Log(outdir / "progress.log")
    log(f"mode={'REAL' if real else 'DRY-NOISE'} freeze verified; caps {CAPS}")
    o = pd.read_csv(ROOT / "data" / "processed" / "outcomes.csv")
    if not real:
        rng = np.random.default_rng(12345)
        o = o.copy()
        for c in ("incumbent_party_won", "incumbent_party_won_popvote"):
            o[c] = rng.permutation(o[c].to_numpy())
        for c in ("ec_winner_party", "pv_winner_party"):
            o[c] = rng.permutation(o[c].to_numpy())
    VA, VB, table = pools.pool_a(), pools.pool_b(), literal_table()
    by_id = alias_by_id(table)
    ec = targets_from(o, "ec")
    log(f"EC targets true counts: { {k: int(v.sum()) for k, v in ec.items()} }")
    pv = targets_from(o, "pv")
    log(f"PV targets true counts: { {k: int(v.sum()) for k, v in pv.items()} }")

    def stage(name, fn):
        marker = outdir / f"DONE_{name}"
        if marker.exists():
            log(f"stage {name} already complete: not rerun")
            return
        fn()
        marker.write_text("done\n")

    stage("primary_ec", lambda: run_primary(ec, "primary_ec", outdir, log, VA, VB, table, by_id))
    stage("sensitivity_popvote", lambda: run_primary(pv, "sensitivity_popvote", outdir, log, VA, VB, table, by_id))
    stage("n3", lambda: run_n3(ec, outdir, log, N3_NULL_PERMS if real else 20))
    log("all pre-declared runs complete")


if __name__ == "__main__":
    if "--approved-gate-2" in sys.argv:
        main(real=True, resume="--resume" in sys.argv)
    elif "--dry-noise" in sys.argv:
        main(real=False)
    else:
        raise SystemExit("pass --approved-gate-2 (real) or --dry-noise (noise-only dry run)")
