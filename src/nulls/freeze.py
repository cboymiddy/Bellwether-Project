"""Write freeze.yaml: hashes of everything the real search depends on. Run once, then do not edit."""

from __future__ import annotations

import hashlib
import importlib.metadata as md
import json
import sys

import yaml

from src.config import ROOT, config_sha256
from src.literals import astro_family
from src.literals.core import OUT
from src.nulls import pools
from src.nulls.freeze_params import CAPS

CODE = ["src/config.py", "src/literals/core.py", "src/literals/astro_family.py", "src/nulls/pools.py",
        "src/nulls/search_core.py", "src/nulls/procedure.py", "src/nulls/freeze_params.py",
        "src/nulls/parallel.py", "src/nulls/whole.py", "src/nulls/n1.py", "src/nulls/freeze.py",
        "src/search/real.py"]
POOL_FILES = ["literals_main.yaml", "matrix_main.csv", "resolves_by_main.csv",
              "literals_era_indicator.yaml", "matrix_era_indicator.csv", "resolves_by_era_indicator.csv"]


def sha(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(null_counts: dict | None = None) -> dict:
    from src.nulls import procedure

    A, B = pools.pool_a(), pools.pool_b()
    grid = {"months": astro_family.MONTHS, "days": astro_family.DAYS,
            "sep_grid_deg": astro_family.SEP_GRID, "bodies": list(astro_family.BODIES),
            "instant": "00:00 UTC", "sector_width_deg": 30}
    freeze = {
        "config_sha256": config_sha256(),
        "pool_files": {n: sha(OUT / n) for n in POOL_FILES},
        "astro_files": {p.name: sha(p) for p in sorted(astro_family.OUT.glob("*.*"))},
        "ephemeris_sha256": astro_family.EPH_SHA,
        "astro_date_grid": grid,
        "astro_date_grid_sha256": hashlib.sha256(json.dumps(grid, sort_keys=True).encode()).hexdigest(),
        "pool_A": {"rule": "main pool restricted to F>=2", "distinct_vectors": len(A),
                   "vectors_sha256": pools.vectors_sha(A)},
        "pool_B": {"rule": "pool A + astro_geometry included literals (positives and complements)",
                   "distinct_vectors": len(B), "vectors_sha256": pools.vectors_sha(B)},
        "code_sha256": {c: sha(ROOT / c) for c in CODE},
        "cutoffs": {"k_max": 4, "keys_N_star": CAPS["n_star"], "keys_margin_star": CAPS["m_star"]},
        "solver": {"cp_sat_time_limit_s": procedure.KEYS_LIMIT, "cp_sat_workers": 1,
                   "keys_candidate_reduction": "exact Pareto dominance"},
        "ranking": "O in {A,B}; higher min F; higher mean F; fewer conditions; fewer tz_sensitive",
        "seeds": {"config_seed": yaml.safe_load((ROOT / "config.yaml").read_text())["seed"]},
        "null_plan": null_counts or {},
        "versions": {"python": sys.version.split()[0], **{p: md.version(p) for p in
                     ("numpy", "pandas", "ortools", "skyfield", "pyyaml")}},
    }
    blob = json.dumps(freeze, sort_keys=True, default=str).encode()
    freeze["freeze_sha256"] = hashlib.sha256(blob).hexdigest()
    return freeze


if __name__ == "__main__":
    plan = {"N1_per_target": int(sys.argv[1]) if len(sys.argv) > 1 else 0,
            "N1_party": int(sys.argv[2]) if len(sys.argv) > 2 else 0,
            "N2_block": int(sys.argv[3]) if len(sys.argv) > 3 else 0, "N2_exact": 63}
    fz = build(plan)
    (ROOT / "freeze.yaml").write_text(yaml.safe_dump(fz, sort_keys=False, width=100))
    print(fz["freeze_sha256"])
