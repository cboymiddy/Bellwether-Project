"""Pool structure statistics (no outcomes): support histogram, complement folding, family x F."""

import numpy as np
import pandas as pd
import yaml

from src.literals.core import OUT

BUCKETS = [(1, 1), (2, 2), (3, 4), (5, 8), (9, 12), (13, 16)]


def load() -> tuple[pd.DataFrame, pd.DataFrame]:
    meta = pd.DataFrame(yaml.safe_load((OUT / "literals_main.yaml").read_text()))
    mat = pd.read_csv(OUT / "matrix_main.csv").set_index("id")
    return meta.set_index("id"), mat


def main() -> str:
    meta, mat = load()
    v = mat.to_numpy(dtype=bool)
    sup = v.sum(axis=1)
    keys = [r.tobytes() for r in v]
    fold = [min(r.tobytes(), (~r).tobytes()) for r in v]
    out = []
    out.append(f"main-pool literals (with negations): {len(v)}")
    out.append(f"distinct vectors: {len(set(keys))}; distinct up to complement: {len(set(fold))}")
    fam = meta.loc[mat.index, "family"].to_numpy()
    cat = meta.loc[mat.index, "category"].to_numpy()
    rows = []
    for f in sorted(set(fam)):
        idx = np.flatnonzero(fam == f)
        folded = {fold[i] for i in idx}
        seen = {}
        for i in idx:
            seen.setdefault(fold[i], min(int(sup[i]), 32 - int(sup[i])))
        mins = np.array(list(seen.values()))
        row = [f, cat[idx[0]], len(idx), len({keys[i] for i in idx}), len(folded)]
        for lo, hi in BUCKETS:
            row.append(int(((mins >= lo) & (mins <= hi)).sum()))
        rows.append(row)
    cols = ["family", "category", "literals", "distinct", "distinct/compl"] + [
        f"min-support {lo}" if lo == hi else f"{lo}-{hi}" for lo, hi in BUCKETS]
    df = pd.DataFrame(rows, columns=cols)
    out.append("\nMinimum-support (min(#True, 32-#True)) histogram of distinct-up-to-complement "
               "vectors, by family (a vector shared by two families counts in each):\n")
    out.append(df.to_string(index=False))
    seen_all = {}
    for i in range(len(v)):
        seen_all.setdefault(fold[i], min(int(sup[i]), 32 - int(sup[i])))
    mins = np.array(list(seen_all.values()))
    tot = ["ALL (unique)", "-", len(v), len(set(keys)), len(seen_all)] + [
        int(((mins >= lo) & (mins <= hi)).sum()) for lo, hi in BUCKETS]
    out.append("\nTOTAL: " + "  ".join(f"{c}={x}" for c, x in zip(cols, tot, strict=True)))
    out.append("\nFull support histogram of distinct main-pool vectors (all polarities, #True):")
    hist = pd.Series(sup[[keys.index(k) for k in dict.fromkeys(keys)]]).value_counts().sort_index()
    out.append(" ".join(f"{k}:{c}" for k, c in hist.items()))
    # family x F (positives)
    pos = meta[meta.polarity == "pos"]
    ft = pd.crosstab(pos.family, pos.F)
    ft.columns = [f"F={c}" for c in ft.columns]
    ft["total"] = ft.sum(axis=1)
    out.append("\nFamily x F-grade (positive main-pool literals):\n")
    out.append(ft.to_string())
    out.append("\nColumn totals: " + ", ".join(f"{c}={int(ft[c].sum())}" for c in ft.columns))
    text = "\n".join(out)
    print(text)
    return text


if __name__ == "__main__":
    main()
