import json

import pandas as pd
import pytest
from src.config import ROOT
from src.site import export as ex
from tests.privacy import private_strings

RS = ROOT / "reports" / "real_search"


@pytest.fixture(scope="module")
def out(tmp_path_factory):
    d = tmp_path_factory.mktemp("site_data")
    ex.export(d)
    return d


def load(out, name):
    return json.loads((out / name).read_text())


def test_hash_gate_refuses_on_freeze_mismatch(monkeypatch):
    monkeypatch.setattr(ex, "freeze_build", lambda plan: {"freeze_sha256": "0" * 64})
    with pytest.raises(SystemExit, match="freeze.yaml does not match"):
        ex.verify_inputs()


def test_hash_gate_refuses_on_outcomes_mismatch(monkeypatch):
    monkeypatch.setattr(ex, "OUTCOMES_SHA", "0" * 64)
    with pytest.raises(SystemExit, match="outcomes.csv differs"):
        ex.verify_inputs()


def test_schema_and_32_of_32(out):
    r = load(out, "rule.json")
    assert {"literals", "sentence", "years", "selection", "popvote", "verification_status"} <= set(r)
    assert len(r["literals"]) == 4 and len(r["years"]) == 32 and r["correct_ec"] == 32
    o = pd.read_csv(ROOT / "data/processed/outcomes.csv").set_index("year")
    for row in r["years"]:
        assert len(row["cells"]) == 4
        assert row["incumbent_party_won"] == bool(o.loc[row["year"], "incumbent_party_won"])
        assert row["prediction"] == all(c["literal_value"] for c in row["cells"]) == row["incumbent_party_won"]


def test_table_values_equal_verification_sheet(out):
    r = load(out, "rule.json")
    sheet = pd.read_csv(RS / "verification_sheet.csv")
    for row in r["years"]:
        for c in row["cells"]:
            s = sheet[(sheet.literal == c["literal"]) & (sheet.year == row["year"])].iloc[0]
            assert c["literal_value"] == bool(s.literal_value)
            if c["kind"] == "astro":
                assert abs(c["measured_deg"] - float(s.value)) < 1e-9 and abs(c["margin_deg"] - float(s.margin)) < 1e-9


def test_tie_and_cushion_counts_are_derived_and_match_regression_values(out):
    sel = load(out, "rule.json")["selection"]
    f = pd.read_csv(RS / "frontier_primary_ec_T1.csv")
    top = f.sort_values("rank").iloc[0]
    tied = f[(f.min_F == top.min_F) & (f.mean_F == top.mean_F) & (f.k == top.k) & (f.n_tz_sensitive == top.n_tz_sensitive)]
    assert sel["tied_top_key_rules"] == len(tied) == 22 and sel["featured_in_tied_set"] and 8 in set(tied["rank"])
    assert sel["tied_with_no_moon_literal"] == 15
    assert sel["tied_sharing_best_cushion"] == 12 and abs(sel["featured_cushion_hours"] - 19.33) < 0.01
    assert sel["featured_rank"] == 8 and sel["chosen_after_seeing_results"] is True and sel["chosen_by"] == "Carson Middleton"


def test_popular_vote_exhibit(out):
    r, fr = load(out, "rule.json"), load(out, "frontier.json")
    assert r["popvote"] == {"correct": 30, "wrong_years": [2000, 2016]}
    t = fr["targets"]
    assert (t["T1"]["ec"]["label"], t["T2"]["ec"]["label"], t["T3"]["ec"]["label"]) == ("conjB", "none", "conjB")
    assert [t[k]["popvote"]["n_minimal_perfect"] for k in ("T1", "T2", "T3")] == [150, 199, 3]
    assert [t[k]["rules_perfect_under_both_codings"] for k in ("T1", "T2", "T3")] == [0, 0, 0]


def test_wording_era_names_and_defunct_flags(out):
    text = "".join((out / n).read_text() for n in ("rule.json", "frontier.json", "meta.json", "nulls.json"))
    assert "angular separation" not in text and not [b for b in private_strings() if b.lower() in text.lower()]
    r = load(out, "rule.json")
    row = next(x for x in r["years"] if x["year"] == 1988)
    assert row["cells"][2]["winner_at_time"] == "Washington Redskins"
    assert not any(x["defunct_entity"] for x in r["literals"])
    fr = load(out, "frontier.json")["frontier"]["ec_T1"]
    assert fr["n_rules"] == 446 and fr["defunct_rules"] == {"count": 3, "ranks": [1, 23, 24]}
    assert next(x for x in fr["tied_top_key"] if x["rank"] == 1)["defunct_entity"] is True


def test_nulls_numbers(out):
    n = load(out, "nulls.json")
    for t in ("T1", "T2", "T3"):
        b = n["n1"][t]
        assert b["B"] == 100_000 and sum(b[k]["count"] for k in ("conjA", "conjB", "keys", "none", "unknown")) == b["B"]
        assert b["keys"]["count"] == 0 and b["unknown"]["count"] == 0
        p = [x["P"] for x in n["power"][t]]
        assert p == sorted(p) and p[0] < 0.001 and p[-1] > 0.999
    assert abs(n["n1"]["T2"]["none"]["rate"] - 0.02323) < 1e-9
    assert 0.070 < n["party"]["rejected_fraction"] < 0.072


def test_export_is_deterministic(out, tmp_path):
    ex.export(tmp_path)
    for name in ("meta.json", "rule.json", "frontier.json", "nulls.json", "n3.json"):
        assert (tmp_path / name).read_bytes() == (out / name).read_bytes()


def test_verification_block_and_headline(out):
    v = load(out, "rule.json")["verification"]
    assert v["horizons_comparisons"] == 96 and v["horizons_truth_differs"] == 0
    assert v["horizons_max_gap_deg"] < v["horizons_tolerance_deg"]
    assert v["espn_games_agree"] == v["espn_games_total"] == 15
    assert v["outcomes_second_source_years_agree"] == v["outcomes_second_source_years"] == 32
    h = load(out, "meta.json")["headline"]
    t = h["p_perfect_rule_under_noise"]
    assert h["permutations"] == 100_000 and 0.975 < t["T3"] < t["T1"] < 0.982
    assert h["p_perfect_rule_best_of_three_targets"] > 0.999


def test_tied_rules_have_glosses_for_every_literal(out):
    fr = load(out, "frontier.json")["frontier"]["ec_T1"]
    for row in fr["tied_top_key"]:
        for lit in row["literals"]:
            assert fr["tied_glosses"][lit]


def test_pool_cuts_and_perfect_subset_counts(out):
    m = load(out, "meta.json")["search_size"]
    assert m["pool_cuts"] == {"main_era_indicator_positives": 10, "main_quarantined_O_C": 7, "main_constant_dropped": 15}
    assert m["astro"]["positives_built"] == 28800 and m["astro"]["included_positives"] == 21476
    t = load(out, "frontier.json")["targets"]
    assert t["T1"]["ec"]["perfect_subsets"] == 446 and t["T3"]["ec"]["perfect_subsets"] == 126 and t["T2"]["ec"]["perfect_subsets"] == 0


def test_n3_numbers(out):
    n = load(out, "n3.json")
    assert n["train_years"][0] == 1900 and n["train_years"][-1] == 1980 and len(n["train_years"]) == 21
    assert n["test_years"][0] == 1984 and n["test_years"][-1] == 2024 and len(n["test_years"]) == 11
    t = n["targets"]
    assert [t[k]["top_rule"]["test_correct"] for k in ("T1", "T2", "T3")] == [6, 6, 5]
    assert [t[k]["baseline"]["always_loss_correct"] for k in ("T1", "T2", "T3")] == [6, 6, 5]
    assert [t[k]["baseline"]["always_win_correct"] for k in ("T1", "T2", "T3")] == [5, 5, 6]
    assert [t[k]["baseline"]["best_constant_correct"] for k in ("T1", "T2", "T3")] == [6, 6, 6]
    assert t["T3"]["baseline"]["best_constant_name"] == "always Republican"
    assert t["T3"]["top_rule"]["test_correct"] < t["T3"]["baseline"]["best_constant_correct"]
    for k in ("T1", "T2", "T3"):
        assert len(t[k]["top20"]) == 20 and t[k]["top20"][0]["ids"] == t[k]["top_rule"]["ids"]
        assert all(r["glosses"] and len(r["ids"]) == len(r["defunct"]) for r in t[k]["top20"])
    assert [t[k]["n_rules_21yr"] for k in ("T1", "T2", "T3")] == [7969, 70379, 36800]
    assert [t[k]["min_k_21yr"] for k in ("T1", "T2", "T3")] == [2, 3, 3]
    assert [t[k]["null"]["ge_real"] for k in ("T1", "T2", "T3")] == [996, 911, 1442]
    for k in ("T1", "T2", "T3"):
        assert t[k]["null"]["B"] == 2000 and sum(t[k]["null"]["top_correct_hist"].values()) == 2000
        assert sum(t[k]["all_rules_hist"].values()) == t[k]["n_rules_21yr"]
        rows = t[k]["top_rule"]["rows"]
        assert len(rows) == 11 and sum(r["correct"] for r in rows) == t[k]["top_rule"]["test_correct"]
        assert sum(r["baseline_correct"] for r in rows) == t[k]["baseline"]["always_loss_correct"]
    assert (t["T1"]["label_32yr"], t["T2"]["label_32yr"], t["T3"]["label_32yr"]) == ("conjB", "none", "conjB")


def test_n3_flags_defunct_club_in_t1_top_rule(out):
    t = load(out, "n3.json")["targets"]
    assert t["T1"]["top_rule"]["defunct"] == [False, True, False, False]
    assert not any(t["T2"]["top_rule"]["defunct"]) and not any(t["T3"]["top_rule"]["defunct"])


def test_human_check_recorded_for_exactly_two_rows(out):
    r = load(out, "rule.json")
    st = r["verification_status"]
    assert (st["human_checked"], st["rows"], st["automated_only"]) == (2, 128, 126)
    per = {x["id"]: x["human_checked_rows"] for x in r["literals"]}
    assert per == {"astro_geo_1021_sep_mercury_venus_ge020": 0, "NOT_astro_geo_0121_sep_mars_jupiter_ge160": 0,
                   "NOT_sports_nfl_sb_winner_franchise_pittsburgh_steelers": 2, "NOT_astro_geo_0701_sep_mercury_pluto_ge160": 0}
    hc = r["verification"]["human_checks"]
    assert [(h["year"], h["checked_by"], h["checked_on"]) for h in hc] == [(1976, "Carson Middleton", "2026-10-25"), (1980, "Carson Middleton", "2026-10-25")]
    assert all(h["source_url"] == "https://www.espn.com/nfl/superbowl/history/winners" for h in hc)
    # only the Steelers 1976/1980 rows are marked in the sheet itself
    import pandas as pd
    sheet = pd.read_csv(RS / "verification_sheet.csv")
    marked = sheet[sheet.human_checked.notna()]
    assert list(zip(marked.literal, marked.year)) == [("NOT_sports_nfl_sb_winner_franchise_pittsburgh_steelers", 1976),
                                                      ("NOT_sports_nfl_sb_winner_franchise_pittsburgh_steelers", 1980)]
