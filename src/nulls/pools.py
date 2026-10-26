"""Tiered pools. Pool A = main pool restricted to F>=2; Pool B = A + astronomy family (tier 1b/2).

Both are returned as arrays of distinct 32-bit vectors (negations included). Astronomy rows are
stored positive-only on disk; their complements are added here.
"""

from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd
import yaml

from src.literals import astro_family
from src.literals.core import OUT


def pool_a_rows() -> np.ndarray:
    meta = pd.DataFrame(yaml.safe_load((OUT / "literals_main.yaml").read_text())).set_index("id")
    mat = pd.read_csv(OUT / "matrix_main.csv").set_index("id")
    keep = meta.index[meta.F >= 2]
    return mat.loc[keep].to_numpy(dtype=bool)


def astro_rows() -> np.ndarray:
    m = astro_family.load_matrix().to_numpy(dtype=bool)
    return np.concatenate([m, ~m])


def distinct(rows: np.ndarray) -> np.ndarray:
    return np.unique(rows, axis=0)


def pool_a() -> np.ndarray:
    return distinct(pool_a_rows())


def pool_b() -> np.ndarray:
    return distinct(np.concatenate([pool_a_rows(), astro_rows()]))


def vectors_sha(V: np.ndarray) -> str:
    return hashlib.sha256(np.packbits(V, axis=1).tobytes()).hexdigest()
