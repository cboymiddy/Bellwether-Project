"""Assemble reports/real_search/REPORT.md from the saved outputs. No interpretation."""

import hashlib
import json

import pandas as pd
import yaml

from src.config import ROOT

RS = ROOT / "reports" / "real_search"


def table(rows, header):
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def label_section(tag: str, title: str) -> list[str]:
    lab = json.loads((RS / f"labels_{tag}.json").read_text())
    out = [f"### {title}\n"]
    rows = []
    for t, r in lab.items():
        rows.append([t, r["n_true"], 32 - r["n_true"], r["label"], r.get("k") or "-",
                     r.get("n_candidates", "-"), r.get("n_minimal_perfect", "-"), r.get("n_pareto", "-"),
                     r.get("k_hist", "-"), r.get("perfect_subsets_by_k", "-")])
    out.append(table(rows, ["target", "true yrs", "false yrs", "label", "min k", "candidate vectors",
                            "minimal perfect rules", "pareto rules", "rules by k", "perfect k-subsets (incl. non-minimal)"]))
    for t, r in lab.items():
        f = RS / f"top50_{tag}_{t}.csv"
        if f.exists():
            df = pd.read_csv(f)
            out.append(f"\n**{t}: top 10 of 50 by the frozen ranking** "
                       f"(full frontier: `frontier_{tag}_{t}.csv`, {r['n_minimal_perfect']} rules)\n")
            out.append(table(df.head(10)[["rank", "k", "literals", "F", "O", "min_F", "mean_F",
                                          "tz_sensitive_flags", "n_tz_sensitive"]].values.tolist(),
                             ["rank", "k", "literals", "F", "O", "min F", "mean F", "tz flags", "# tz"]))
    return out


def main() -> None:
    fz = yaml.safe_load((ROOT / "freeze.yaml").read_text())
    n3 = json.loads((RS / "n3_summary.json").read_text())
    t = ["# Gate-2 real-search report (pre-declared runs; no interpretation)\n"]
    t.append(f"- freeze sha256 `{fz['freeze_sha256']}`; frozen real-search driver "
             f"`{fz['code_sha256']['src/search/real.py'][:16]}...` (unchanged); caps N*=4, m*=2")
    t.append(f"- outcomes.csv sha256 `{sha(ROOT / 'data/processed/outcomes.csv')}` (identical to Phase 0 commit d73cdb2)")
    t.append(f"- runner `src/search/gate2.py` sha256 `{sha(ROOT / 'src/search/gate2.py')[:16]}...` (committed before the run, "
             "commit 2f3166e; it is an unfrozen orchestrator over the frozen functions)")
    t.append("- run order: PRIMARY (Electoral College, T1-T3), SENSITIVITY (popular vote), N3; each exactly once; "
             "lock file present; no reruns, no pool/code/cutoff/ranking changes")
    t.append("- progress log: `reports/real_search/progress.log`\n")
    t.append("## Deviations and notes the pre-declaration did not anticipate\n")
    t.append("1. The frozen driver `run_real` writes only to `reports/real_search_results.json`, logs nothing, and keeps "
             "only the top 40 rules, so it could not meet the pre-declared outputs. I ran the same frozen functions "
             "(`evaluate`, `conjunction_report`, `keys_solution`, `literal_table`) from a new runner, passing an "
             "unbounded `top`, and wrote to `reports/real_search/`. The frozen driver was not run.")
    t.append("2. N3 null: 2,000 permutations per target (not 20,000). Finding the top-ranked rule exactly is expensive "
             "on the 21-year training data when tier 1b fires (up to about 1e6 covers per permutation); the run took "
             "about 3 h 20 min. N3 permutes each target's own full 32-year vector (counts fixed), fits on 1900-1980, "
             "scores 1984-2024.")
    t.append("3. N3 merges literals that are identical on the 21 training years; the representative literal is chosen by the "
             "frozen alias order (highest F, then O, then not tz_sensitive, then id), never by test performance, and "
             "its own 1984-2024 values are scored.")
    t.append("4. Ranking dependence of the nulls: the earlier N1, N1-party and N2 label distributions use only "
             "existence and minimal k (not the ranking function). The N3 null uses the frozen ranking to pick "
             "the top rule.")
    t.append("5. The popular-vote sensitivity has no null (the frozen nulls used the Electoral College counts "
             "18/15/17; popular-vote counts are 20/17/15). The CLAUDE.md second N3 split (1900-1990 / 1992-2024) was "
             "not pre-declared and was not run.\n")
    t.append("## 1. PRIMARY: Electoral College coding\n")
    t += label_section("primary_ec", "Labels and frontier summary")
    t.append("\n## 2. SENSITIVITY (labeled separately): popular-vote coding\n")
    t += label_section("sensitivity_popvote", "Labels and frontier summary")
    t.append("\n## 3. N3: fit 1900-1980 (21 elections), score 1984-2024 (11 elections)\n")
    rows = []
    for name, r in n3.items():
        real, null = r["real"], r["null"]
        nh = {int(k): v for k, v in null["top_correct_hist"].items()}
        n_fit = sum(nh.values())
        rc = real.get("top_correct")
        ge = sum(v for k, v in nh.items() if rc is not None and k >= rc)
        rows.append([name, real["label"], real.get("k") or "-", real.get("n_rules", "-"),
                     f"{rc}/{real.get('test_n')}" if rc is not None else "-",
                     real.get("test_correct_hist_all_rules", "-"), null["B"], null["labels"],
                     n_fit, f"{ge}/{n_fit} ({ge / n_fit:.4f})" if n_fit and rc is not None else "-",
                     f"{nh.get(11, 0)}/{n_fit}"])
    t.append(table(rows, ["target", "real label (train)", "min k", "# training-perfect rules",
                          "top-ranked rule, test correct", "test correct, all rules (hist)", "null perms",
                          "null label counts", "null perms with a conjunction", "null: top-rule test correct >= real top",
                          "null: top rule 11/11"]))
    for name, r in n3.items():
        nh = {int(k): v for k, v in r["null"]["top_correct_hist"].items()}
        t.append(f"\n**{name} null: top-ranked rule test-correct histogram (of 11):** {dict(sorted(nh.items()))}")
    t.append("\nOutputs: `labels_*.json`, `frontier_*_T*.csv` (every perfect rule), `top50_*_T*.csv`, "
             "`n3_rules_T*.csv` (every training-perfect rule with its test score), `n3_null_T*.csv`, `n3_summary.json`.")
    (RS / "REPORT.md").write_text("\n".join(t) + "\n")
    print("\n".join(t))


if __name__ == "__main__":
    main()
