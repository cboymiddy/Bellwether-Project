"""Site exporter: frozen artifacts -> versioned JSON for the Astro site. Computes no new science.

Refuses to run unless freeze.yaml still matches the current files and outcomes.csv has the Phase 0
hash. Everything on the rule card is re-derived from the frozen files (outcomes, event tables,
verification sheet, Horizons comparison, frontier) and cross-checked (32/32, tie and cushion counts).
Run: uv run python -m src.site.export [out_dir]
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from src.config import ROOT, config_sha256, election_day, election_years
from src.literals import astro_family as af
from src.nulls.count_dist import summarize as count_summary
from src.nulls.freeze import build as freeze_build
from src.nulls.keys_b import summarize as keys_summary
from src.nulls.n1 import wilson
from src.nulls.power import curve as power_curve
from src.search.gate2 import OUTCOMES_SHA
from src.verify.gate2_margins import astro_series, hours_equivalent, strip

RS = ROOT / "reports" / "real_search"
REP = ROOT / "reports"
DEFAULT_OUT = ROOT / "site" / "src" / "data"
YEARS = election_years()
FEATURED_RANK = 8
LABELS = ("conjA", "conjB", "keys", "none", "unknown")
# Literals that name an entity with no current counterpart (CLAUDE.md C2.3). Flagged, never hidden.
DEFUNCT = re.compile(
    r"sports_nhl_(winner|loser)_franchise_(quebec_bulldogs|montreal_shamrocks|montreal_wanderers|"
    r"ottawa_senators|calgary_tigers|montreal_maroons|portland_rosebuds|seattle_metropolitans)$"
    r"|sports_nba_(winner|loser)_franchise_baltimore_bullets|sports_olympics_host_country_(soviet_union|west_germany)$"
)


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def verify_inputs() -> dict:
    """Hash gate: raise unless the frozen state is intact. Returns the hashes to embed."""
    fz = yaml.safe_load((ROOT / "freeze.yaml").read_text())
    if freeze_build(fz["null_plan"])["freeze_sha256"] != fz["freeze_sha256"]:
        raise SystemExit("freeze.yaml does not match current files: refusing to export")
    if sha(ROOT / "data/processed/outcomes.csv") != OUTCOMES_SHA:
        raise SystemExit("outcomes.csv differs from Phase 0: refusing to export")
    if not (RS / "LOCK").exists() or "all pre-declared runs complete" not in (RS / "progress.log").read_text():
        raise SystemExit("Gate-2 run is not complete: refusing to export")
    return {"freeze_sha256": fz["freeze_sha256"], "config_sha256": config_sha256(),
            "outcomes_sha256": OUTCOMES_SHA, "astro_grid_sha256": fz["astro_date_grid_sha256"],
            "ephemeris_sha256": fz["ephemeris_sha256"],
            "pool_A_vectors_sha256": fz["pool_A"]["vectors_sha256"],
            "pool_B_vectors_sha256": fz["pool_B"]["vectors_sha256"],
            "inputs": {f: sha(RS / f) for f in ("frontier_primary_ec_T1.csv", "verification_sheet.csv",
                                                "labels_primary_ec.json", "n3_summary.json")}}


def dump(obj, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, sort_keys=True, ensure_ascii=False) + "\n")


def clean(v):
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return None if np.isnan(v) else float(v)
    if isinstance(v, (np.bool_,)):
        return bool(v)
    return v


# ------------------------------------------------------------------------------ frontier + rule
def tied_set(f: pd.DataFrame) -> pd.DataFrame:
    top = f.sort_values("rank").iloc[0]
    return f[(f.min_F == top.min_F) & (f.mean_F == top.mean_F) & (f.k == top.k)
             & (f.n_tz_sensitive == top.n_tz_sensitive)]


def cushions(tied: pd.DataFrame) -> pd.DataFrame:
    """Minimum cushion per tied rule: degrees and hours of clock error, from the astronomy literals."""
    cache: dict[str, tuple[float, float]] = {}

    def lit(b: str) -> tuple[float, float]:
        if b not in cache:
            s = astro_series(b)
            i = int(np.argmin(np.abs(s["margin"])))
            m = float(abs(s["margin"][i]))
            cache[b] = (m, hours_equivalent(b, YEARS[i], m))
        return cache[b]

    rows = []
    for _, r in tied.iterrows():
        ls = [strip(x.strip())[0] for x in r.literals.split(" & ")]
        a = [lit(b) for b in ls if b.startswith("astro_geo_")]
        rows.append({"rank": int(r["rank"]), "min_deg": min(x[0] for x in a), "min_hours": min(x[1] for x in a),
                     "has_moon": "moon" in r.literals})
    return pd.DataFrame(rows)


def gloss(lit_id: str, idx: pd.DataFrame, labels: pd.DataFrame) -> str:
    base, neg = strip(lit_id)
    if base in idx.index:
        r = idx.loc[base]
        when = f"{af.MON[int(r.month) - 1]} {int(r.day)}"
        if r.kind == "sep":
            text = (f"{r.body_a} and {r.body_b} are at least {int(r.param)}° apart in ecliptic longitude "
                    f"on {when} (00:00 UTC)")
        else:
            text = f"{r.body_a}'s ecliptic longitude is in [{int(r.param)}°, {int(r.param) + 30}°) on {when}"
    else:
        text = str(labels.loc[base, "display_statement"])
        if base.startswith("sports_nfl_sb_"):
            text = text.replace(" in the election year", " played earlier that year")
        text = text.replace(" in the election year", " that election year").replace("the election year", "that year")
        if base.startswith("sports_") and not text.startswith(("The ", "A ", "An ")):
            text = "the " + text
    return f"NOT: {text}" if neg else text


def rule_sentence(lits: list[str], g: dict[str, str]) -> str:
    pos = [g[x] for x in lits if not x.startswith("NOT_")]
    neg = [g[x][5:] for x in lits if x.startswith("NOT_")]
    s = "The party holding the White House on Election Day wins"
    if pos:
        s += " if " + " and ".join(pos)
    if neg:
        s += ", unless " + (", ".join(neg[:-1]) + ", or " + neg[-1] if len(neg) > 1 else neg[0])
    return s + "."


def build_verification(hz: pd.DataFrame, sheet: pd.DataFrame) -> dict:
    """Second-source results for the featured rule (all already computed; summarised here)."""
    chk = pd.read_csv(RS / "outcomes_second_source_check.csv")
    human = pd.read_csv(RS / "human_checks.csv")
    games = sheet[sheet.checked.str.contains("ESPN")]
    return {"horizons_comparisons": len(hz), "horizons_max_gap_deg": float(hz.gap_deg.max()),
            "horizons_tolerance_deg": 0.001, "horizons_truth_differs": int(hz.truth_differs.sum()),
            "espn_games_agree": int(games.checked.str.startswith("auto-OK").sum()), "espn_games_total": len(games),
            "outcomes_second_source_years_agree": int(chk.all_agree.sum()), "outcomes_second_source_years": len(chk),
            "human_checks": [{"literal": r.literal, "year": int(r.year), "checked_by": r.checked_by, "checked_on": r.checked_on,
                              "source_url": r.source_url, "note": r.note} for r in human.itertuples()],
            "outcomes_second_source": "Wikipedia list of presidents and list of elections in which the winner lost "
                                      "the popular vote (Phase 0 used the National Archives and UCSB)"}


def build_rule(hashes: dict) -> tuple[dict, dict]:
    top = pd.read_csv(RS / "top50_primary_ec_T1.csv")
    frontier = pd.read_csv(RS / "frontier_primary_ec_T1.csv")
    row = top[top["rank"] == FEATURED_RANK].iloc[0]
    lits = [x.strip() for x in row.literals.split(" & ")]
    idx = pd.read_csv(af.OUT / "index.csv").set_index("id")
    labels = pd.read_csv(ROOT / "display" / "literal_labels.csv").set_index("id")
    glosses = {x: gloss(x, idx, labels) for x in lits}
    out = pd.read_csv(ROOT / "data/processed/outcomes.csv").set_index("year")
    sheet = pd.read_csv(RS / "verification_sheet.csv")
    hz = pd.read_csv(RS / "horizons_rank8" / "horizons_rank8_comparison.csv")
    nfl = pd.read_csv(ROOT / "data/processed/events/nfl_super_bowl.csv").set_index("year")

    rows = []
    for y in YEARS:
        cells = []
        for lit in lits:
            s = sheet[(sheet.literal == lit) & (sheet.year == y)].iloc[0]
            base = strip(lit)[0]
            cell = {"literal": lit, "literal_value": bool(s.literal_value), "checked": s.checked}
            if base.startswith("astro_geo_"):
                m = float(s.margin)
                h = hz[(hz.literal == lit) & (hz.year == y)].iloc[0]
                cell |= {"kind": "astro", "measured_deg": float(s.value), "threshold_deg": float(s.threshold),
                         "margin_deg": m, "margin_hours": round(hours_equivalent(base, y, abs(m)), 2),
                         "instant_utc": s.date_or_instant, "horizons_deg": float(h.horizons_diff_deg),
                         "horizons_gap_deg": float(h.gap_deg)}
            else:
                held = int(nfl.loc[y, "held"]) == 1
                cell |= {"kind": "event", "held": held}
                if held:
                    r = nfl.loc[y]
                    cell |= {"game": str(r.game_number), "date": r.completed_date, "score": r.score,
                             "winner_at_time": r.winner_name_at_time, "loser_at_time": r.loser_name_at_time,
                             "espn_detail": s.second_source_value}
            cells.append(cell)
        pred = all(c["literal_value"] for c in cells)
        actual = bool(out.loc[y, "incumbent_party_won"])
        rows.append({"year": y, "election_day": election_day(y).isoformat(),
                     "incumbent_party": out.loc[y, "incumbent_party"], "incumbent_party_won": actual,
                     "incumbent_party_won_popvote": bool(out.loc[y, "incumbent_party_won_popvote"]),
                     "prediction": pred, "correct": pred == actual, "cells": cells})
    n_ok = sum(r["correct"] for r in rows)
    if n_ok != 32:
        raise SystemExit(f"featured rule is {n_ok}/32 on the exported table: refusing to export")
    pv_wrong = [r["year"] for r in rows if r["prediction"] != r["incumbent_party_won_popvote"]]

    tied = tied_set(frontier)
    cu = cushions(tied)
    r8 = cu[cu["rank"] == FEATURED_RANK].iloc[0]
    best = cu.min_hours.max()
    quebec = frontier[frontier.literals.str.contains("quebec_bulldogs")]
    status = {"astro_auto_ok": int((sheet.checked.str.startswith("auto-OK") & sheet.literal.str.startswith(
        ("astro", "NOT_astro"))).sum()), "event_auto_ok": int((sheet.checked.str.startswith("auto-OK") & ~sheet.literal.str.contains(
            "astro")).sum()), "human_checked": int(sheet.human_checked.notna().sum()), "rows": len(sheet),
              "automated_only": len(sheet) - int(sheet.human_checked.notna().sum())}
    selection = {"rule_label": f"T1 (incumbent party wins), Electoral College coding, frontier rank {FEATURED_RANK}",
                 "featured_rank": FEATURED_RANK,
                 "chosen_by": "Carson Middleton", "chosen_after_seeing_results": True,
                 "reason": "no Moon literal and the largest minimum timing cushion in the tied set",
                 "tied_top_key_rules": len(tied), "tied_with_no_moon_literal": int((~cu.has_moon).sum()),
                 "tied_sharing_best_cushion": int((np.isclose(cu.min_hours, best)).sum()),
                 "featured_cushion_hours": round(float(r8.min_hours), 2),
                 "featured_cushion_deg": round(float(r8.min_deg), 4),
                 "featured_in_tied_set": bool(FEATURED_RANK in set(tied["rank"])),
                 "featured_on_pareto": bool(int(frontier[frontier["rank"] == FEATURED_RANK].pareto.iloc[0]))}
    rule = {"literals": [{"id": x, "gloss": glosses[x], "F": int(row_f), "O": o, "tz_sensitive": bool(int(tz)),
                          "defunct_entity": bool(DEFUNCT.match(strip(x)[0])),
                          "rows": int((sheet.literal == x).sum()),
                          "human_checked_rows": int(sheet[sheet.literal == x].human_checked.notna().sum())}
                         for x, row_f, o, tz in zip(lits, row.F.split(","), row.O.split(","),
                                                    row.tz_sensitive_flags.split(","), strict=True)],
            "sentence": rule_sentence(lits, glosses), "years": rows, "correct_ec": n_ok,
            "popvote": {"correct": 32 - len(pv_wrong), "wrong_years": pv_wrong},
            "selection": selection, "verification_status": status,
            "verification": build_verification(hz, sheet)}
    tied_rows = []
    tied_glosses: dict[str, str] = {}
    for _, r in tied.sort_values("rank").iterrows():
        ls = [x.strip() for x in r.literals.split(" & ")]
        for x in ls:
            tied_glosses[x] = gloss(x, idx, labels)
        tied_rows.append({"rank": int(r["rank"]), "literals": ls,
                          "defunct_entity": any(DEFUNCT.match(strip(x)[0]) for x in ls), "pareto": bool(int(r.pareto)),
                          "has_moon": "moon" in r.literals})
    front = {"ec_T1": {"n_rules": len(frontier), "k_hist": {str(k): int(v) for k, v in frontier.k.value_counts().items()},
                       "n_tz_sensitive_rules": int((frontier.n_tz_sensitive > 0).sum()),
                       "n_pareto": int(frontier.pareto.sum()),
                       "defunct_rules": {"count": len(quebec), "ranks": [int(x) for x in quebec["rank"]]},
                       "tied_top_key": tied_rows, "tied_glosses": tied_glosses}}
    return rule, front


def build_frontier_and_pv(front: dict, rule: dict) -> dict:
    labels_ec = json.loads((RS / "labels_primary_ec.json").read_text())
    labels_pv = json.loads((RS / "labels_sensitivity_popvote.json").read_text())

    def lit_sets(fn: str) -> set:
        p = RS / fn
        if not p.exists():
            return set()
        return {frozenset(x.strip() for x in s.split(" & ")) for s in pd.read_csv(p).literals}

    targets = {}
    for t in ("T1", "T2", "T3"):
        ec, pv = labels_ec[t], labels_pv[t]
        ec_set = lit_sets(f"frontier_primary_ec_{t}.csv")
        pv_set = lit_sets(f"frontier_sensitivity_popvote_{t}.csv")
        keys5 = ("label", "k", "n_true", "n_minimal_perfect", "n_pareto")
        targets[t] = {"ec": {k: clean(ec.get(k)) for k in keys5} | {"perfect_subsets": sum((ec.get("perfect_subsets_by_k") or {}).values())},
                      "popvote": {k: clean(pv.get(k)) for k in keys5} | {"perfect_subsets": sum((pv.get("perfect_subsets_by_k") or {}).values())},
                      "rules_perfect_under_both_codings": len(ec_set & pv_set)}
    t3_front = pd.read_csv(RS / "frontier_primary_ec_T3.csv")
    front["ec_T3"] = {"n_rules": len(t3_front), "defunct_rules": {"count": int(
        sum(any(DEFUNCT.match(strip(x.strip())[0]) for x in s.split(" & ")) for s in t3_front.literals))}}
    return {"targets": targets, "frontier": front,
            "featured_rule_popvote": rule["popvote"]}


# ------------------------------------------------------------------------------------- nulls
def build_nulls() -> dict:
    out = {"n1": {}, "party": {}, "n2": {}, "counts": {}, "power": {}, "keys_poolB": {}}

    def label_block(df: pd.DataFrame, col: str) -> dict:
        n = len(df)
        blk = {"B": n}
        for k in LABELS:
            c = int((df[col] == k).sum())
            lo, hi = wilson(c, n)
            blk[k] = {"count": c, "rate": c / n, "ci_lo": float(lo), "ci_hi": float(hi)}
        return blk

    for t in ("T1", "T2", "T3"):
        d = pd.read_csv(REP / f"whole_n1_{t}.csv")
        out["n1"][t] = label_block(d, "label")
        out["n1"][t]["k_hist"] = {f"{lab}_k{int(k)}": int(c) for (lab, k), c in
                                  d[d.label.isin(["conjA", "conjB"])].groupby(["label", "k"]).size().items()}
    party = pd.read_csv(REP / "whole_party.csv")
    out["party"] = {"best": label_block(party, "best_label"), **{t: label_block(party, f"{t}_label") for t in ("T1", "T2", "T3")},
                    "rejected_sequences": int(party.rejected_before.sum()),
                    "rejected_fraction": float(party.rejected_before.sum() / (party.rejected_before.sum() + len(party)))}
    out["n2"] = {"exact": label_block(pd.read_csv(REP / "whole_n2_exact.csv"), "best_label"),
                 "block": label_block(pd.read_csv(REP / "whole_n2_block.csv"), "best_label")}
    bins = [0, 1, 10, 100, 1000, 10_000, 100_000, 1_000_000, float("inf")]
    names = ["0", "1-9", "10-99", "100-999", "1k-9.9k", "10k-99k", "100k-999k", "1M+"]
    for t in ("T1", "T2", "T3"):
        d = pd.read_csv(REP / f"countdist_B_{t}.csv")
        tot = d[["n_k1", "n_k2", "n_k3", "n_k4"]].sum(axis=1)
        h = pd.cut(tot, bins=bins, right=False, labels=names).value_counts().reindex(names)
        s = count_summary(d)
        out["counts"][t] = {"summary": {k: clean(v) for k, v in s.items() if k != "min_k_hist"},
                            "min_k_hist": {str(k): int(v) for k, v in s["min_k_hist"].items()},
                            "histogram": {n: int(v) for n, v in h.items()}}
    ms = [0, 50, 100, 150, 200, 250, 300, 400, 500, 700, 1000, 3000]
    for t in ("T1", "T2", "T3"):
        c = power_curve(pd.read_csv(REP / f"power_{t}.csv"), ms)
        out["power"][t] = [{k: clean(v) for k, v in r.items()} for r in c.to_dict("records")]
    for t in ("T1", "T2", "T3"):
        d = pd.read_csv(REP / f"keys_B_{t}.csv")
        s = keys_summary(d)
        out["keys_poolB"][t] = [{k: clean(v) for k, v in r.items()} for r in s.to_dict("records")]
    return out


CONSTANT_NAMES = {
    "T1": {"no": "the incumbent party always loses", "yes": "the incumbent party always wins"},
    "T2": {"no": "always Republican", "yes": "always Democratic"},
    "T3": {"no": "always Democratic", "yes": "always Republican"},
}


def literal_vector(lit_id: str, main: pd.DataFrame, astro: pd.DataFrame) -> np.ndarray:
    """32-year truth vector of a literal as used (polarity included), from the frozen matrices."""
    if lit_id in main.index:
        return main.loc[lit_id].to_numpy(dtype=bool)
    base, neg = strip(lit_id)
    v = astro.loc[base].to_numpy(dtype=bool)
    return ~v if neg else v


def build_n3() -> dict:
    """N3 exhibit data: fit on 1900-1980 (21 elections), score on 1984-2024 (11 elections)."""
    summ = json.loads((RS / "n3_summary.json").read_text())
    labels_ec = json.loads((RS / "labels_primary_ec.json").read_text())
    o = pd.read_csv(ROOT / "data/processed/outcomes.csv").set_index("year")
    actual = {"T1": (o.incumbent_party_won == 1).to_numpy(), "T2": (o.ec_winner_party == "D").to_numpy(),
              "T3": (o.ec_winner_party == "R").to_numpy()}
    main = pd.read_csv(ROOT / "data/processed/literals/matrix_main.csv").set_index("id")
    astro = af.load_matrix()
    idx = pd.read_csv(af.OUT / "index.csv").set_index("id")
    labels = pd.read_csv(ROOT / "display" / "literal_labels.csv").set_index("id")
    train = [i for i, y in enumerate(YEARS) if y <= 1980]
    test = [i for i, y in enumerate(YEARS) if y >= 1984]
    out: dict = {"train_years": [YEARS[i] for i in train], "test_years": [YEARS[i] for i in test], "targets": {}}
    for t in ("T1", "T2", "T3"):
        real = summ[t]["real"]
        ids = real["top_ids"]
        vecs = [literal_vector(x, main, astro) for x in ids]
        says = np.logical_and.reduce(vecs)
        a = actual[t]
        if not (says[train] == a[train]).all():
            raise SystemExit(f"{t}: top rule does not fit the training years")
        correct = int((says[test] == a[test]).sum())
        if correct != real["top_correct"]:
            raise SystemExit(f"{t}: recomputed test score {correct} != summary {real['top_correct']}")
        nd = pd.read_csv(RS / f"n3_null_{t}.csv")
        hist = real["test_correct_hist_all_rules"]
        if sum(hist.values()) != real["n_rules"]:
            raise SystemExit(f"{t}: rule histogram does not add up to the rule count")
        glosses = [gloss(x, idx, labels) for x in ids]
        lab32 = labels_ec[t]
        names = CONSTANT_NAMES[t]
        n_no, n_yes = int((~a[test]).sum()), int(a[test].sum())
        best_which = "no" if n_no >= n_yes else "yes"
        rf = RS / f"n3_rules_{t}.csv"
        rules = pd.read_csv(rf if rf.exists() else rf.with_name(rf.name + ".gz")).head(20)  # the public copy is gzipped
        top20 = []
        for _, rr in rules.iterrows():
            rids = [x.strip() for x in rr.literals.split(" & ")]
            top20.append({"rank": int(rr["rank"]), "k": int(rr.k), "ids": rids, "glosses": [gloss(x, idx, labels) for x in rids],
                          "defunct": [bool(DEFUNCT.match(strip(x)[0])) for x in rids], "test_correct": int(rr.test_correct)})
        if top20[0]["ids"] != ids or top20[0]["test_correct"] != correct:
            raise SystemExit(f"{t}: first row of the rule list is not the top-ranked rule")
        out["targets"][t] = {
            "real_label_21yr": real["label"], "min_k_21yr": real["k"], "n_rules_21yr": real["n_rules"],
            "label_32yr": lab32["label"], "min_k_32yr": lab32.get("k"), "n_rules_32yr": lab32.get("n_minimal_perfect"),
            "top_rule": {"ids": ids, "glosses": glosses, "defunct": [bool(DEFUNCT.match(strip(x)[0])) for x in ids], "k": real["top_k"], "test_correct": correct, "test_n": len(test),
                         "fits_all_21_training_years": True,
                         "rows": [{"year": YEARS[i], "actual": bool(a[i]), "rule_says": bool(says[i]),
                                   "correct": bool(says[i] == a[i]), "baseline_correct": not bool(a[i]),
                                   "always_yes_correct": bool(a[i])} for i in test]},
            "top20": top20,
            "baseline": {"always_loss_correct": n_no, "always_win_correct": n_yes,
                         "test_true_years": n_yes, "test_n": len(test),
                         "name_no": names["no"], "name_yes": names["yes"],
                         "best_constant_correct": max(n_no, n_yes), "best_constant_name": names[best_which]},
            "all_rules_hist": {k: int(v) for k, v in hist.items()},
            "null": {"B": len(nd), "labels": {k: int(v) for k, v in nd.label.value_counts().items()},
                     "top_correct_hist": {str(k): int(v) for k, v in nd.top_correct.value_counts().sort_index().items()},
                     "ge_real": int((nd.top_correct >= correct).sum()), "ge_baseline": int((nd.top_correct >= max(n_no, n_yes)).sum()),
                     "perfect_11_of_11": int((nd.top_correct == 11).sum())},
        }
    return out


def build_search_size() -> dict:
    fz = yaml.safe_load((ROOT / "freeze.yaml").read_text())
    main = pd.DataFrame(yaml.safe_load((ROOT / "data/processed/literals/literals_main.yaml").read_text()))
    pos = main[main.polarity == "pos"]
    fam = yaml.safe_load((af.OUT / "family.yaml").read_text())
    era = yaml.safe_load((ROOT / "data/processed/literals/literals_era_indicator.yaml").read_text())
    report = (REP / "phase1_pool_report.md").read_text()
    quarantined = report.split("## Quarantined")[1].split("\n## ")[0]
    cuts = {"main_era_indicator_positives": sum(1 for r in era if r["polarity"] == "pos"),
            "main_quarantined_O_C": len(re.findall(r"^\| sports_", quarantined, re.MULTILINE)),
            "main_constant_dropped": int(re.search(r"Constant literals dropped \((\d+)\)", report).group(1))}
    return {"pool_cuts": cuts, "pool_A_distinct_vectors": fz["pool_A"]["distinct_vectors"], "pool_B_distinct_vectors": fz["pool_B"]["distinct_vectors"],
            "main_pool_positives": len(pos), "main_pool_positives_F_ge_2": int((pos.F >= 2).sum()),
            "main_pool_by_category": {k: int(v) for k, v in pos.category.value_counts().items()},
            "astro": fam["counts"], "cutoffs": fz["cutoffs"], "null_plan": fz["null_plan"]}


def git_provenance() -> list[dict]:
    out = subprocess.run(["git", "log", "--format=%h|%s", "-n", "12"], cwd=ROOT, capture_output=True, text=True,
                         check=False).stdout.strip().splitlines()
    return [dict(zip(("id", "subject"), x.split("|", 1), strict=True)) for x in out]


def export(out_dir: Path = DEFAULT_OUT) -> dict:
    hashes = verify_inputs()
    rule, front = build_rule(hashes)
    pv = build_frontier_and_pv(front, rule)
    meta = {"hashes": hashes, "provenance_local_commits": git_provenance(), "search_size": build_search_size(),
            "built_utc_date": dt.date.today().isoformat(), "freeze_note": "freeze hash covers config, pools, astronomy "
            "grid, search code, cutoffs and seeds"}
    nulls = build_nulls()
    p = nulls["party"]["best"]
    meta["headline"] = {"p_perfect_rule_under_noise": {t: round(1 - nulls["n1"][t]["none"]["rate"], 5) for t in ("T1", "T2", "T3")},
                        "p_perfect_rule_best_of_three_targets": round(1 - p["none"]["rate"], 5),
                        "tier_1a_rate_under_noise": {t: round(nulls["n1"][t]["conjA"]["rate"], 5) for t in ("T1", "T2", "T3")},
                        "permutations": nulls["n1"]["T1"]["B"]}
    dump(meta, out_dir / "meta.json")
    dump(rule, out_dir / "rule.json")
    dump(pv, out_dir / "frontier.json")
    dump(nulls, out_dir / "nulls.json")
    dump(build_n3(), out_dir / "n3.json")
    from src.site.export_2028 import build_2028

    idx = pd.read_csv(af.OUT / "index.csv").set_index("id")
    labels = pd.read_csv(ROOT / "display" / "literal_labels.csv").set_index("id")
    dump(build_2028(rule, lambda x: gloss(x, idx, labels)), out_dir / "2028.json")
    return {"meta": meta, "rule": rule, "frontier": pv}


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUT
    res = export(target)
    sel = res["rule"]["selection"]
    print("exported to", target)
    print("rule:", res["rule"]["sentence"])
    print("EC 32/32; popular vote:", res["rule"]["popvote"], "| selection:", {k: sel[k] for k in (
        "tied_top_key_rules", "tied_with_no_moon_literal", "tied_sharing_best_cushion", "featured_cushion_hours")})
