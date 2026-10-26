import numpy as np
import pytest
from src.literals import astro_family as af
from src.site.export_2028 import YEAR, eval_sky, next_super_bowl, roman, state, unroman, verdict
from src.verify.gate2_margins import astro_series


def test_election_day_2028_and_super_bowl_number():
    from src.config import election_day

    assert election_day(YEAR).isoformat() == "2028-11-07"
    assert next_super_bowl() == "LXII"
    assert unroman("LVIII") == 58 and roman(62) == "LXII"


@pytest.mark.parametrize("base", [
    "astro_geo_1021_sep_mercury_venus_ge020", "astro_geo_0121_sep_mars_jupiter_ge160", "astro_geo_0701_sep_mercury_pluto_ge160",
    "astro_geo_0906_sep_sun_moon_ge140", "astro_geo_0101_mars_lon030"])
def test_2028_code_reproduces_stored_pool_for_all_32_years(base):
    s = astro_series(base)
    for i, y in enumerate(af.YEARS):
        e = eval_sky(base, y)
        assert e["base_truth"] == bool(s["truth"][i])
        assert np.isclose(e["margin_deg"], float(s["margin"][i]), atol=1e-6)


def test_negation_and_verdict_rules():
    b = "astro_geo_1021_sep_mercury_venus_ge020"
    assert eval_sky(b)["value"] != eval_sky("NOT_" + b)["value"]
    assert state("NOT_sports_nfl_sb_winner_franchise_pittsburgh_steelers") == "pending"
    assert verdict(["true", "pending"]) == "pending" and verdict(["false", "pending"]) == "no_win"
    assert verdict(["true", "true"]) == "win"


def test_exported_2028_is_consistent():
    import json

    from src.config import ROOT

    d = json.loads((ROOT / "site/src/data/2028.json").read_text())
    t, w = d["tally"], d["tally"]["wordings"]
    assert d["election_day"] == "2028-11-07" and sum(t["counts"].values()) == t["n_others"] == t["n_rules"] - 1
    assert w["total"] == w["no_win"] + w["win"] + w["pending"]
    cells = d["featured"]["cells"]
    sky_ok = all(c["state"] == "true" for c in cells if c["kind"] == "sky")
    assert d["featured"]["sky_conditions_hold"] == sky_ok
    if not sky_ok:  # a failed sky fact settles the answer whatever the game does
        assert all(not b["prediction_hold_party_wins"] for b in d["featured"]["branches"])


def test_wording_sensitive_rules_listed():
    import json

    from src.config import ROOT

    t = json.loads((ROOT / "site/src/data/2028.json").read_text())["tally"]
    assert len(t["wording_sensitive"]) == t["alias_changes_verdict"] == 31
    for r in t["wording_sensitive"]:
        assert len(r["reachable"]) > 1 and r["wordings"]["total"] == sum(r["wordings"][k] for k in ("no_win", "win", "pending"))
