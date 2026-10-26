"""Phase 1 pool report. Reads only the literal pool; never touches outcomes (no search)."""

from __future__ import annotations

import collections

from src.config import ROOT, config_sha256
from src.literals.build import build
from src.literals.core import YEARS, Literal
from src.verify import pool_stats

MANUAL_EXCLUSIONS = [
    ("sports", "Heisman Trophy",
     ("Presented in December, after Election Day: every literal would be constant False. "
      "(Reason stated from general knowledge; not verified from a fetched source.)")),
    ("sports", "Belmont Stakes / Preakness winner literals",
     ("Belmont run date unsourced for 20 of 31 held election years (see triple_crown_gaps.md); "
      "completion before Election Day cannot be established from fetched data. Only the "
      "computed 'won the Triple Crown' literal is built, True only in a dated year.")),
    ("sports", "pre-1936 college-football champions", "Disputed; no official dataset cited (CLAUDE.md)."),
    ("other", "Academy Awards, Nobel categories",
     "Optional series (CLAUDE.md Section 4.4): not built in Phase 1."),
    ("markets", "Markets/macro series", "Off by Open Decision #4."),
]


CAVEATS = [
    "Weather: only NYC Central Park (USW00094728) is complete for the snow window; Central Park and "
    "Blue Hill (USC00190736) are complete for Jun-Aug TMAX. Chicago, Washington DC, Los Angeles, "
    "Boston Logan, Newark and Battery have no single complete station; nothing was spliced. "
    "Blue Hill misses the 1984 snow window by one day.",
    "Weather: single source (GHCN-D .dly), no second source yet; quality-flagged values treated as "
    "missing; 0.1 in tested as >= 2.5 mm (GHCN whole mm), a boundary sensitivity.",
    "Triple Crown: Belmont dates unsourced for 20 of 31 held years (1900, 1904, 1908, 1916, 1924, "
    "1928, 1936, 1940, 1944, 1952, 1956, 1960, 1964, 1968, 1972, 1976, 1980, 1988, 1992, 1996).",
    "Olympics: closing dates differ between Wikipedia and Olympedia for 1904, 1908, 1912, 1920; "
    "checked that no disagreement changes any before-Election-Day truth value (1904 and 1956 end "
    "after Election Day under every source; 1900 ends 28 Oct). 2020 Games are held=0 (held 2021).",
    "Masters 2020 final round 2020-11-15 (after Election Day), so all 2020 Masters literals are False.",
    "Single-source dates: Derby, Masters, Wimbledon (Wikipedia infoboxes); Wimbledon completed_date "
    "is the tournament end date, a proxy for the final. Indy dates checked against champcarstats "
    "except 1916, 1996, 2000, 2004.",
    "NFL second source is ESPN only (PFR and footballdb returned 403). NBA game dates are "
    "Wikipedia-only. NHL 1900-1916 has no independent non-Wikipedia source.",
    "MLB: 1900 and 1904 have no Series (sources: Wikipedia list, Baseball-Reference index); lineage "
    "mappings come from Wikipedia row labels, not an MLB-published page.",
    "FIFA men's World Cup: every edition year is 2 mod 4, so none falls in an election year; the "
    "'held' literal is constant False and excluded.",
    "Solar eclipses and the optional series (Academy Awards, Nobel) are not built.",
    "Everything above is what the sources say or what agents report; none of it is yet "
    "human_verified (Phase 4).",
]


NHL_NOTE = (
    "Parsed from the fetched challenge-games list (all opposed series in 1900, 1904, 1908, 1912): "
    "every year's series were all won by one club (1900 Montreal Shamrocks; 1904 Ottawa HC/Silver "
    "Seven; 1908 Montreal Wanderers; 1912 Quebec Bulldogs), so *winner* literals do not depend on "
    "which series is called the final. Losers, series length, and sweep do (1904 had four different "
    "opponents, 1908 four, 1900 two): the 7 quarantined literals (four `loser` literals: Brandon Wheat City, Edmonton HC, Halifax Crescents, "
    "Moncton Victorias; plus the 7-game, 6-game and sweep literals) stay quarantined "
    "(O=C). Net change from the first Gate-1 report (10 quarantined): the Shamrocks, Ottawa and Quebec winner "
    "literals were re-graded B, `sports_nhl_held` became constant True (dropped as a constant), and "
    "`Edmonton HC lost` became non-constant after the winner-date fix and was quarantined. Two corrections made while checking: (1) the fetched Ottawa Senators (original) page says "
    "the Ottawa Hockey Club was the Silver Seven 1903-07 and the Senators from 1908, so 'Ottawa Silver "
    "Seven' (1904) and 'Ottawa Senators' (1920) are now one franchise (it was wrongly split); (2) the "
    "winner's event date is now the latest series completed before Election Day, so the 1908 "
    "Wanderers (series ending 1908-03-14, and a Dec 30 series after Election Day) are no longer "
    "silently dropped as a constant. No remaining B-graded NHL literal names a club that appears in "
    "any 1900-1912 series other than those winner literals (src/verify/nhl_judgment_check.py). "
    "Caveat: literals that an alternative selection would create (e.g. 'Montreal Wanderers lost') "
    "are simply absent from the pool."
)


def n1_section() -> str:
    import pandas as pd

    from src.nulls.n1 import pool_files_sha, summarize

    lines = ["\n## N1 on the frozen pool, before any real search\n",
             f"pool files sha256: `{pool_files_sha()}`\n"]
    rows = []
    for t in ("T1", "T2", "T3"):
        f = ROOT / "reports" / f"n1_{t}.csv"
        if not f.exists():
            continue
        s = summarize(pd.read_csv(f))
        rows.append([t, s["B"], f"{s['P_conj']:.4f}", f"[{s['CI_conj'][0]:.4f}, {s['CI_conj'][1]:.4f}]",
                     s["min_k_hist"], f"{s['P_keys']:.4f}", s["keys_no"], s["keys_unknown"],
                     f"{s['median_candidates']:.0f}"])
    lines.append(_table(rows, ["target", "perms", "P(perfect conj k<=4)", "95% CI", "min-k hist",
                               "P(perfect keys N<=13)", "keys infeasible", "keys unknown",
                               "median candidates"]))
    return "\n".join(lines)


def _true_years(lit: Literal) -> str:
    ys = [y for y, v in zip(YEARS, lit.values, strict=True) if v]
    return ", ".join(map(str, ys)) if len(ys) <= 6 else f"{len(ys)} years ({ys[0]}-{ys[-1]})"


def _table(rows: list[list], header: list[str]) -> str:
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def make_report() -> str:
    r = build(("computed", "sports", "weather"))
    pool, main, era = r["pool"], r["main"], r["era"]
    allp = main + era
    pos = [lit for lit in allp if lit.polarity == "pos"]

    def distinct(lits):
        return len({lit.vec.tobytes() for lit in lits})

    lines = ["# Phase 1 pool report (no search run)\n"]
    lines.append(f"- config.yaml sha256: `{config_sha256()}`")
    lines.append(f"- **pool + config hash: `{r['sha']}`**")
    lines.append("- pool files: " + ", ".join(f"`{k}`" for k in sorted(r["hashes"])))
    lines.append("")
    lines.append("## Counts by category (main pool; era indicators excluded)\n")
    rows = []
    for cat in ["calendar", "astronomy", "sports", "weather"]:
        m = [lit for lit in main if lit.category == cat]
        e = [lit for lit in era if lit.category == cat]
        mp = [lit for lit in m if lit.polarity == "pos"]
        rows.append([cat, len(mp), len(m), distinct(m), len(e)])
    tot_m = main
    rows.append(["**total**", sum(1 for lit in main if lit.polarity == "pos"), len(tot_m),
                 distinct(tot_m), len(era)])
    lines.append(_table(rows, ["category", "positive literals", "with negations", "distinct vectors",
                               "era-indicator literals (excluded)"]))
    lines.append("\nRaw literal count vs distinct 32-bit vectors is the honest search-size input "
                 "(CLAUDE.md Section 5). Distinct vectors are counted over all polarities in the main pool.\n")
    lines.append("## Counts by family (positives)\n")
    fam = collections.Counter(lit.family for lit in pos if lit in main or lit.base_id is None)
    lines.append(_table(sorted([[k, v] for k, v in fam.items()]), ["family", "positive literals"]))
    lines.append("\n## Quality grades (positives in main pool)\n")
    mp = [lit for lit in main if lit.polarity == "pos"]
    fo = collections.Counter((lit.F, lit.O) for lit in mp)
    lines.append(_table(sorted([[f"F={k[0]}", f"O={k[1]}", v] for k, v in fo.items()]),
                        ["familiarity", "objectivity", "count"]))
    flagged = sorted(lit.id for lit in mp if lit.flags)
    tz = [i for i in flagged if any("tz_sensitive" in lit.flags for lit in mp if lit.id == i)]
    lines.append(f"\nFlagged literals (positives): {len(flagged)}; timezone-sensitive (graded O=B): {len(tz)}.")
    lines.append("\n## Era-indicator literals (reported separately; excluded from the main pool)\n")
    lines.append("Frozen rule: at most two value changes across the 32 elections and every run at "
                 "least 3 elections long. Negations of these are also era indicators.\n")
    lines.append(_table(
        [[lit.id, lit.family, _true_years(lit)] for lit in era if lit.polarity == "pos"
         or lit.base_id not in {x.id for x in era}],
        ["literal", "family", "true in"]))
    lines.append("\n## Exclusions with reasons\n")
    cons = [e for e in pool.exclusions if e["reason"].startswith("constant")]
    other = [e for e in pool.exclusions if not e["reason"].startswith("constant")]
    ex = [[e["family"], e["what"], e["reason"]] for e in other]
    ex += [[a, b, c] for a, b, c in MANUAL_EXCLUSIONS]
    lines.append(_table(ex, ["family", "what", "reason"]))
    lines.append(f"\nConstant literals dropped ({len(cons)}): " + "; ".join(
        f"`{e['what']}` ({e['reason'].split('(')[1].rstrip(')')})" for e in cons))
    lines.append("\n## Quarantined (O=C, judgment-dependent; forbidden unless Carson approves)\n")
    lines.append(_table([[q.id, q.statement, _true_years(q)] for q in pool.quarantined],
                        ["literal", "statement", "true in"]))
    lines.append("\nCause: Stanley Cup 1900-1912 challenge era. Several challenge series occurred "
                 "per calendar year; the table uses the last opposed series (agent judgment), and "
                 "the 1908 final series ended 1908-12-30, after Election Day. Any literal whose value "
                 "depends on which series counts is graded C.")
    lines.append("\n## Pool structure (no outcomes used)\n")
    lines.append("```\n" + pool_stats.main() + "\n```")
    lines.append("\n## NHL 1900-1912 judgment check\n")
    lines.append(NHL_NOTE)
    lines.append("\n## Chicago threaded record check (report only)\n")
    lines.append((ROOT / "data" / "raw" / "chicago_thread_check" / "NOTES.md").read_text())
    lines.append(n1_section())
    lines.append("\n## Coverage failures and data caveats\n")
    lines += [f"- {c}" for c in CAVEATS]
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    text = make_report()
    (ROOT / "reports" / "phase1_pool_report.md").write_text(text)
    print(text)
