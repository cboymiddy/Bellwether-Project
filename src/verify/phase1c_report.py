"""Assemble reports/phase1c_report.md (noise-only whole-procedure results). No real outcomes."""

import pandas as pd
import yaml

from src.config import ROOT
from src.nulls.count_dist import summarize as count_summary
from src.nulls.keys_b import summarize as keys_summary
from src.nulls.n1 import wilson

R = ROOT / "reports"


def table(rows, header):
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def label_rows(df: pd.DataFrame, col: str) -> list:
    n = len(df)
    row = []
    for k in ("conjA", "conjB", "keys", "none", "unknown"):
        c = int((df[col] == k).sum())
        lo, hi = wilson(c, n)
        row.append(f"{c} ({c / n:.4f}) [{lo:.4f}, {hi:.4f}]")
    return row


def main() -> None:
    fz = yaml.safe_load((ROOT / "freeze.yaml").read_text())
    fam = yaml.safe_load((ROOT / "data/processed/literals/astro/family.yaml").read_text())
    idx = pd.read_csv(ROOT / "data/processed/literals/astro/index.csv")
    inc = idx[idx.included == 1]
    text = ["# Phase 1c report (noise only; no real outcome was scored; the real search has NOT been run)\n"]
    text.append(f"- **freeze sha256: `{fz['freeze_sha256']}`**  (config `{fz['config_sha256'][:16]}...`, "
                f"astro grid `{fz['astro_date_grid_sha256'][:16]}...`)")
    text.append(f"- pool A: {fz['pool_A']['distinct_vectors']} distinct vectors (`{fz['pool_A']['vectors_sha256'][:16]}...`); "
                f"pool B: {fz['pool_B']['distinct_vectors']} distinct vectors (`{fz['pool_B']['vectors_sha256'][:16]}...`)")
    text.append(f"- cutoffs: k<=4; tier 2 N*={fz['cutoffs']['keys_N_star']}, m*={fz['cutoffs']['keys_margin_star']}; "
                f"null plan {fz['null_plan']}\n")
    text.append("## 1. Astronomy family (built)\n")
    text.append(table([[k, v] for k, v in fam["counts"].items()] + [
        ["tz_sensitive among included positives", int(inc.tz_sensitive.sum())],
        ["distinct vectors among included positives (matrix.csv)", len(set(map(tuple, pd.read_csv(ROOT / 'data/processed/literals/astro/matrix.csv').iloc[:, 1:].to_numpy())))],
        ["DE421 sha256", fz["ephemeris_sha256"][:16] + "..."],
    ], ["quantity", "value"]))
    text.append("\nTests (all pass): date grid frozen; every instant's date precedes Election Day in all 32 years; DE421 "
                "evaluates all instants including US Eastern/Pacific local midnights and 2028-10-26 and rejects 2060; "
                "Sun's longitude is 0 within 0.01 degrees at the March equinox (1900, 1960, 2024), confirming the "
                "of-date convention; built files match the index.\n")
    text.append("## 2. Number of perfect conjunctions per noise permutation (pool B, 20,000 perms/target)\n")
    rows = []
    for t in ("T1", "T2", "T3"):
        s = count_summary(pd.read_csv(R / f"countdist_B_{t}.csv"))
        rows.append([t, f"{s['P_found']:.4f}", f"{s['mean_all']:.0f}", f"{s['mean_given_found']:.0f}",
                     f"{s['median_given_found']:.0f}", f"{s['p90_given_found']:.0f}", s["max"],
                     f"{s['median_at_min_k_given_found']:.0f}", s["min_k_hist"]])
    text.append(table(rows, ["target", "P(>=1)", "mean (all)", "mean | >=1", "median | >=1", "p90 | >=1",
                             "max", "median count at min k | >=1", "min-k histogram"]))
    text.append("\nCounts are exact numbers of perfect k-subsets (k<=4) of distinct vectors. Typical noise permutation "
                "yields hundreds of perfect conjunctions, so a real hit will not be a unique rule: the output must be "
                "ranked and shown as a frontier.\n")
    text.append("## 3. Keys null on pool B (1,500 perms/target, exact)\n")
    for t in ("T1", "T2", "T3"):
        df = pd.read_csv(R / f"keys_B_{t}.csv")
        text.append(f"**{t}** minimal N by required margin m:")
        text.append(table([[f"m>={m}", str(df[f"minN_m{m}"].value_counts().sort_index().to_dict())] for m in (1, 2, 3, 4)],
                          ["margin", "distribution of minimal N"]))
        text.append("")
        text.append(table([[int(r[0])] + [f"{x:.4f}" for x in r[1:]] for r in keys_summary(df).iloc[:11].values.tolist()],
                          ["N cap", "P(m>=1)", "P(m>=2)", "P(m>=3)", "P(m>=4)"]))
        text.append("")
    text.append("**Proposed and frozen caps: N* = 4, m* = 2.** Noise rate P(keys rule with N<=4, margin>=2): "
                "T1 0.0007 (1/1500), T2 0/1500, T3 0/1500 (rule-of-three upper bound about 0.002). Alternatives with a similar "
                "noise rate are N<=6/m>=3 (T1 0.0013) and N<=8/m>=4 (T1 0.0007); the 288-vector-pool figure of ~3% "
                "(N<=5, m=1) no longer applies because the expanded pool makes N<=5, m=1 certain.\n")
    text.append("## 4. Whole-procedure nulls (frozen; labels: conjA, conjB, keys, none)\n")
    hdr = ["null", "perms", "conjA", "conjB", "keys", "none", "unknown"]
    rows = []
    for t in ("T1", "T2", "T3"):
        df = pd.read_csv(R / f"whole_n1_{t}.csv")
        rows.append([f"N1 {t}", len(df)] + label_rows(df, "label"))
    party = pd.read_csv(R / "whole_party.csv")
    rows.append(["N1-party, best of T1-T3", len(party)] + label_rows(party, "best_label"))
    for t in ("T1", "T2", "T3"):
        rows.append([f"N1-party, {t}", len(party)] + label_rows(party, f"{t}_label"))
    ex = pd.read_csv(R / "whole_n2_exact.csv")
    rows.append(["N2 exact (63 shifts/reversals), best", len(ex)] + label_rows(ex, "best_label"))
    blk = pd.read_csv(R / "whole_n2_block.csv")
    rows.append(["N2 block perms, best", len(blk)] + label_rows(blk, "best_label"))
    text.append(table(rows, hdr))
    rej = int(party.rejected_before.sum())
    text.append(f"\nN1-party rejected {rej} winner sequences (T1 with fewer than 12 true years; fraction "
                f"{rej / (rej + len(party)):.3f}) to stay within exact-counting limits; the real T1 has 18 true years.")
    text.append("\nk of the conjunction tiers (N1, per target):")
    for t in ("T1", "T2", "T3"):
        df = pd.read_csv(R / f"whole_n1_{t}.csv")
        text.append(f"- {t}: " + ", ".join(f"{lab} k={k}: {c}" for (lab, k), c in
                                          df[df.label.isin(['conjA', 'conjB'])].groupby(['label', 'k']).size().items()))
    text.append("")
    (R / "phase1c_report.md").write_text("\n".join(text))
    print("\n".join(text))


if __name__ == "__main__":
    main()
