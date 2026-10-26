"""Full Horizons comparison for the three astronomy literals of T1 EC rank 8 (all 32 years).

Settings are exactly those in reports/real_search/HORIZONS_CONVENTION.md. Read-only: the pool,
ranking and hashes are untouched. Raw responses are saved with sha256.
Run: uv run python -m src.verify.horizons_rank8
"""

import datetime as dt
import hashlib
import re
import subprocess

import numpy as np
import pandas as pd

from src.config import ROOT
from src.literals import astro_family as af

OUT = ROOT / "reports" / "real_search" / "horizons_rank8"
LITERALS = {  # literal (as used in the rule) -> (month, day, body a, body b, threshold, negated)
    "astro_geo_1021_sep_mercury_venus_ge020": (10, 21, "Mercury", "Venus", 20, False),
    "NOT_astro_geo_0121_sep_mars_jupiter_ge160": (1, 21, "Mars", "Jupiter", 160, True),
    "NOT_astro_geo_0701_sep_mercury_pluto_ge160": (7, 1, "Mercury", "Pluto", 160, True),
}
CODE = {"Mercury": "1", "Venus": "2", "Mars": "4", "Jupiter": "5", "Pluto": "9"}  # barycentres
TOL_DEG = 0.001


def jd(y: int, m: int, d: int) -> float:
    return dt.date(y, m, d).toordinal() + 1721424.5


def fetch(body: str, m: int, d: int) -> list[float]:
    tlist = " ".join(f"{jd(y, m, d):.1f}" for y in af.YEARS).replace(" ", "%20")
    url = (f"https://ssd.jpl.nasa.gov/api/horizons.api?format=text&COMMAND=%27{CODE[body]}%27&OBJ_DATA=%27NO%27"
           f"&MAKE_EPHEM=%27YES%27&EPHEM_TYPE=%27OBSERVER%27&CENTER=%27500@399%27&TLIST=%27{tlist}%27"
           "&TLIST_TYPE=%27JD%27&TIME_TYPE=%27UT%27&QUANTITIES=%2731%27&ANG_FORMAT=%27DEG%27"
           "&CSV_FORMAT=%27YES%27&REF_SYSTEM=%27ICRF%27")
    txt = subprocess.run(["curl", "-sL", "-m", "120", url], check=False, capture_output=True, text=True).stdout
    f = OUT / f"hz_{CODE[body]}_{m:02d}{d:02d}.txt"
    f.write_text(txt)
    block = re.search(r"\$\$SOE\s*(.*?)\s*\$\$EOE", txt, re.DOTALL)
    if not block:
        raise RuntimeError(f"Horizons returned no ephemeris for {body} {m}/{d}: {txt[:300]}")
    lons = []
    for line in block.group(1).splitlines():
        parts = [p.strip() for p in line.split(",")]
        lons.append(float(parts[3]))
    if len(lons) != len(af.YEARS):
        raise RuntimeError(f"{body} {m}/{d}: {len(lons)} rows, expected {len(af.YEARS)}")
    return lons


def folded(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    d = np.abs(a - b) % 360
    return np.where(d > 180, 360 - d, d)


def main() -> None:
    rows, manifest = [], ["file,sha256"]
    cache: dict[tuple, list[float]] = {}
    for lit, (m, d, a, b, c, neg) in LITERALS.items():
        sky = af.longitudes((m, d))
        for body in (a, b):
            if (body, m, d) not in cache:
                cache[(body, m, d)] = fetch(body, m, d)
        ha, hb = np.array(cache[(a, m, d)]), np.array(cache[(b, m, d)])
        sd, hd = folded(sky[a], sky[b]), folded(ha, hb)
        for i, y in enumerate(af.YEARS):
            ts_, th_ = (sd[i] >= c) != neg, (hd[i] >= c) != neg
            rows.append({"literal": lit, "year": y, f"skyfield_lon_{a}": round(float(sky[a][i]), 7),
                         f"skyfield_lon_{b}": round(float(sky[b][i]), 7),
                         f"horizons_lon_{a}": ha[i], f"horizons_lon_{b}": hb[i],
                         "skyfield_diff_deg": round(float(sd[i]), 7), "horizons_diff_deg": round(float(hd[i]), 7),
                         "gap_deg": round(float(abs(sd[i] - hd[i])), 7), "threshold": c,
                         "skyfield_literal": bool(ts_), "horizons_literal": bool(th_),
                         "truth_differs": bool(ts_ != th_)})
    df = pd.DataFrame(rows)
    # per-literal frames share column names only partly; keep a tidy long version too
    keep = ["literal", "year", "skyfield_diff_deg", "horizons_diff_deg", "gap_deg", "threshold",
            "skyfield_literal", "horizons_literal", "truth_differs"]
    df[keep].to_csv(OUT / "horizons_rank8_comparison.csv", index=False)
    for p in sorted(OUT.glob("hz_*.txt")):
        manifest.append(f"{p.name},{hashlib.sha256(p.read_bytes()).hexdigest()}")
    (OUT / "MANIFEST.csv").write_text("\n".join(manifest) + "\n")
    for lit, g in df.groupby("literal"):
        i = g.gap_deg.idxmax()
        print(f"{lit}: max gap {g.gap_deg.max():.7f} deg in {int(g.loc[i, 'year'])}; "
              f"years with gap > {TOL_DEG}: {g[g.gap_deg > TOL_DEG].year.tolist()}; "
              f"truth differs in years: {g[g.truth_differs].year.tolist()}")
    print("overall max gap:", df.gap_deg.max())


if __name__ == "__main__":
    main()
