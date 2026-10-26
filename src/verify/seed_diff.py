"""Diff the CLAUDE.md seed outcome table against the source-derived data/processed/outcomes.csv."""

import io
import re

import pandas as pd

from src.config import ROOT


def seed_table() -> pd.DataFrame:
    text = (ROOT / "CLAUDE.md").read_text()
    block = re.search(r"```csv\n(year,incumbent_party,incumbent_party_won\n.*?)```", text, re.DOTALL)
    return pd.read_csv(io.StringIO(block.group(1)))


def main() -> None:
    seed = seed_table()
    ver = pd.read_csv(ROOT / "data" / "processed" / "outcomes.csv")
    m = seed.merge(ver, on="year", suffixes=("_seed", "_verified"))
    bad = m[
        (m.incumbent_party_seed != m.incumbent_party_verified)
        | (m.incumbent_party_won_seed != m.incumbent_party_won_verified)
    ]
    lines = [f"rows compared: {len(m)}", f"discrepancies: {len(bad)}"]
    lines += [bad.to_string(index=False)] if len(bad) else []
    report = "\n".join(lines) + "\n"
    (ROOT / "reports" / "outcomes_seed_diff.txt").write_text(report)
    print(report)


if __name__ == "__main__":
    main()
