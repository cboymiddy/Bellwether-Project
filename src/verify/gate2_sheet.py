"""verification_sheet.csv for T1 EC frontier ranks 2-4: every literal used, every election year."""

import pandas as pd

from src.config import ROOT, election_day
from src.literals.astro_family import EPH_SHA, YEARS
from src.verify.gate2_margins import RS, astro_series, ranks, strip

SKY = (f"Skyfield 1.55 + JPL DE421 (sha256 {EPH_SHA[:12]}...), computed by src/literals/astro_family.py; "
       "see reports/real_search/HORIZONS_CONVENTION.md")
HOR = "JPL Horizons API, settings in HORIZONS_CONVENTION.md (not yet queried)"


def main() -> None:
    top = pd.read_csv(RS / "top50_primary_ec_T1.csv")
    used = ranks(top, 2, 4)
    mlb = pd.read_csv(ROOT / "data/processed/events/mlb_world_series.csv").set_index("year")
    rows = []
    for lit, rk in used.items():
        base, neg = strip(lit)
        rr = ",".join(map(str, sorted(set(rk))))
        if base.startswith("astro_geo_"):
            s = astro_series(base)
            qty = ("ecliptic-longitude difference folded to [0,180] deg" if s["kind"] == "sep"
                   else "ecliptic longitude deg")
            for i, y in enumerate(YEARS):
                truth = bool(s["truth"][i]) != neg
                rows.append({"literal": lit, "year": y,
                             "instant_utc": f"{y}-{s['md'][0]:02d}-{s['md'][1]:02d}T00:00:00Z",
                             "quantity": qty, "value": round(float(s["value"][i]), 6),
                             "threshold": s["threshold"], "margin": round(float(s["margin"][i]), 6),
                             "literal_value": truth, "rule_ranks": rr, "source": SKY,
                             "second_source": HOR, "checked": ""})
        else:
            col = "loser_franchise" if "_loser_" in base else "winner_franchise"
            for y in YEARS:
                r = mlb.loc[y]
                held = int(r["held"]) == 1
                val = r[col] if held else "no World Series held"
                urls = [u.strip() for u in str(r["source_url"]).split(";")]
                truth = False
                target = base.split("franchise_")[-1]
                if held and election_day(y) and pd.to_datetime(r["completed_date"]).date() < election_day(y):
                    truth = str(r[col]).lower().replace(" ", "_").replace(".", "_") == target
                rows.append({"literal": lit, "year": y, "instant_utc": r["completed_date"] if held else "",
                             "quantity": f"MLB World Series {col.split('_')[0]} (event table)", "value": val,
                             "threshold": "n/a", "margin": "n/a", "literal_value": truth != neg,
                             "rule_ranks": rr, "source": "; ".join(urls[:2]),
                             "second_source": urls[2] if len(urls) > 2 else "", "checked": ""})
    df = pd.DataFrame(rows)
    df.to_csv(RS / "verification_sheet.csv", index=False)
    print(len(df), "rows;", df.literal.nunique(), "literals;", sorted(df.rule_ranks.unique()))
    print(df.groupby("literal").literal_value.agg(["sum", "count"]))


if __name__ == "__main__":
    main()
