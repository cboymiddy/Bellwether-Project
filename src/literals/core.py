"""Literal records, the pool, constant/era-indicator classification, and serialization.

A literal is a Boolean predicate defined for every election year. Positives are registered by
the family modules; the pool adds each literal's negation automatically (CLAUDE.md C4).
"""

from __future__ import annotations

import datetime as dt
import hashlib
from dataclasses import asdict, dataclass, field

import numpy as np
import pandas as pd
import yaml

from src.config import ROOT, config_sha256, election_day, election_years

YEARS = election_years()
OUT = ROOT / "data" / "processed" / "literals"
CITES = {"F": (1, 2, 3), "O": ("A", "B", "C")}


def cutoff(year: int) -> dt.date:
    """Latest date an observation may carry and still resolve before Election Day."""
    return election_day(year) - dt.timedelta(days=1)


def era_indicator_rule(v: np.ndarray, min_run: int = 3) -> bool:
    """Frozen rule: at most two value changes across the 32 elections and every run >= min_run."""
    change = np.flatnonzero(v[1:] != v[:-1])
    if len(change) == 0 or len(change) > 2:
        return False
    edges = np.concatenate(([0], change + 1, [len(v)]))
    return int(np.diff(edges).min()) >= min_run


@dataclass
class Literal:
    id: str
    statement: str
    category: str  # calendar | astronomy | sports | weather
    family: str  # e.g. easter, mlb_world_series
    definition: str
    source_url: str
    dataset_citation: str
    retrieval_date: str
    F: int
    O: str
    values: list[bool]
    resolves_by: list[dt.date]
    polarity: str = "pos"
    base_id: str | None = None
    status: str = "auto"
    era_indicator: bool = False
    flags: list[str] = field(default_factory=list)
    equiv_class: int | None = None

    def __post_init__(self) -> None:
        assert len(self.values) == len(YEARS) == len(self.resolves_by), self.id
        assert self.F in CITES["F"] and self.O in CITES["O"], self.id
        for y, r in zip(YEARS, self.resolves_by, strict=True):
            assert r < election_day(y), f"{self.id} {y}: resolves_by {r} not before Election Day"

    @property
    def vec(self) -> np.ndarray:
        return np.array(self.values, dtype=bool)

    def negation(self) -> Literal:
        return Literal(
            id=f"NOT_{self.id}", statement=f"NOT: {self.statement}", category=self.category,
            family=self.family, definition=f"Negation of {self.id}. {self.definition}",
            source_url=self.source_url, dataset_citation=self.dataset_citation,
            retrieval_date=self.retrieval_date, F=self.F, O=self.O,
            values=[not x for x in self.values], resolves_by=list(self.resolves_by),
            polarity="neg", base_id=self.id, status=self.status, flags=list(self.flags),
        )


class Pool:
    def __init__(self) -> None:
        self.positives: list[Literal] = []
        self.exclusions: list[dict] = []  # {id, family, reason}
        self.quarantined: list[Literal] = []  # O=C: forbidden unless Carson approves the literal

    def add(self, lit: Literal) -> None:
        assert all(p.id != lit.id for p in self.positives[-50:]), f"duplicate id {lit.id}"
        self.positives.append(lit)

    def exclude(self, family: str, what: str, reason: str) -> None:
        self.exclusions.append({"family": family, "what": what, "reason": reason})

    def finalize(self) -> tuple[list[Literal], list[Literal]]:
        """Return (main_pool, era_indicators), both with negations. Constants are excluded."""
        ids = [p.id for p in self.positives]
        assert len(ids) == len(set(ids)), "duplicate literal ids"
        keep: list[Literal] = []
        for p in self.positives:
            v = p.vec
            if p.O == "C":
                p.status = "quarantined"
                self.quarantined.append(p)
                continue
            if v.all() or not v.any():
                self.exclusions.append({
                    "family": p.family, "what": p.id,
                    "reason": f"constant across all 32 years ({'True' if v.all() else 'False'})",
                })
                continue
            p.era_indicator = era_indicator_rule(v)
            keep += [p, p.negation()]
        for lit in keep:
            lit.era_indicator = era_indicator_rule(lit.vec)
        classes: dict[bytes, int] = {}
        for lit in keep:
            lit.equiv_class = classes.setdefault(lit.vec.tobytes(), len(classes))
        main = [lit for lit in keep if not lit.era_indicator]
        era = [lit for lit in keep if lit.era_indicator]
        return main, era


def write_pool(main: list[Literal], era: list[Literal]) -> dict[str, str]:
    """Write literals.yaml, matrix.csv, resolves_by.csv for each of main/era; return file hashes."""
    OUT.mkdir(parents=True, exist_ok=True)
    hashes: dict[str, str] = {}
    for name, lits in (("main", main), ("era_indicator", era)):
        recs = []
        for lit in lits:
            d = asdict(lit)
            d.pop("values")
            d["resolves_by"] = max(lit.resolves_by).isoformat()
            recs.append(d)
        (OUT / f"literals_{name}.yaml").write_text(yaml.safe_dump(recs, sort_keys=False, width=100))
        m = pd.DataFrame([lit.vec.astype(int) for lit in lits], columns=YEARS)
        m.insert(0, "id", [lit.id for lit in lits])
        m.to_csv(OUT / f"matrix_{name}.csv", index=False)
        r = pd.DataFrame([[x.isoformat() for x in lit.resolves_by] for lit in lits], columns=YEARS)
        r.insert(0, "id", [lit.id for lit in lits])
        r.to_csv(OUT / f"resolves_by_{name}.csv", index=False)
    for p in sorted(OUT.glob("*.*")):
        hashes[p.name] = hashlib.sha256(p.read_bytes()).hexdigest()
    return hashes


def pool_sha256(hashes: dict[str, str]) -> str:
    h = hashlib.sha256()
    for k in sorted(hashes):
        h.update(f"{k}:{hashes[k]}\n".encode())
    h.update(f"config.yaml:{config_sha256()}\n".encode())
    return h.hexdigest()
