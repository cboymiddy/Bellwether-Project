// Shapes of the JSON written by src/site/export.py (the only source of numbers on the site).
export interface Literal { id: string; gloss: string; F: number; O: string; tz_sensitive: boolean; defunct_entity: boolean; rows: number; human_checked_rows: number }
export interface AstroCell {
  kind: 'astro'; literal: string; literal_value: boolean; checked: string; measured_deg: number; threshold_deg: number;
  margin_deg: number; margin_hours: number; instant_utc: string; horizons_deg: number; horizons_gap_deg: number;
}
export interface EventCell {
  kind: 'event'; literal: string; literal_value: boolean; checked: string; held: boolean; game?: string; date?: string;
  score?: string; winner_at_time?: string; loser_at_time?: string; espn_detail?: string;
}
export type Cell = AstroCell | EventCell;
export interface YearRow {
  year: number; election_day: string; incumbent_party: string; incumbent_party_won: boolean;
  incumbent_party_won_popvote: boolean; prediction: boolean; correct: boolean; cells: Cell[];
}
export interface Selection {
  rule_label: string; chosen_by: string; chosen_after_seeing_results: boolean; reason: string;
  tied_top_key_rules: number; tied_with_no_moon_literal: number; tied_sharing_best_cushion: number;
  featured_rank: number; featured_cushion_hours: number; featured_cushion_deg: number; featured_in_tied_set: boolean; featured_on_pareto: boolean;
}
export interface Verification {
  horizons_comparisons: number; horizons_max_gap_deg: number; horizons_tolerance_deg: number; horizons_truth_differs: number;
  espn_games_agree: number; espn_games_total: number; outcomes_second_source_years_agree: number;
  outcomes_second_source_years: number; outcomes_second_source: string;
  human_checks: { literal: string; year: number; checked_by: string; checked_on: string; source_url: string; note: string }[];
}
export interface Rule {
  literals: Literal[]; sentence: string; years: YearRow[]; correct_ec: number;
  popvote: { correct: number; wrong_years: number[] }; selection: Selection;
  verification_status: { astro_auto_ok: number; event_auto_ok: number; human_checked: number; rows: number; automated_only: number };
  verification: Verification;
}
export interface TiedRule { rank: number; literals: string[]; defunct_entity: boolean; pareto: boolean; has_moon: boolean }
export interface Frontier {
  frontier: { ec_T1: { n_rules: number; n_pareto: number; k_hist: Record<string, number>;
    defunct_rules: { count: number; ranks: number[] }; tied_top_key: TiedRule[]; tied_glosses: Record<string, string> };
    ec_T3: { n_rules: number } };
  targets: Record<string, { ec: { label: string; n_minimal_perfect: number | null };
    popvote: { label: string; n_minimal_perfect: number | null }; rules_perfect_under_both_codings: number }>;
}
export interface Meta {
  search_size: { pool_A_distinct_vectors: number; pool_B_distinct_vectors: number };
  hashes: { freeze_sha256: string; outcomes_sha256: string; config_sha256: string };
  built_utc_date: string; provenance_local_commits: { id: string; subject: string }[];
  headline: { p_perfect_rule_under_noise: Record<string, number>; p_perfect_rule_best_of_three_targets: number;
    tier_1a_rate_under_noise: Record<string, number>; permutations: number };
}
