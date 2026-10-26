"""Build the Phase 1 literal pool. No search is run here."""

from __future__ import annotations

import sys

from src.literals.computed import add_computed
from src.literals.core import Pool, pool_sha256, write_pool


def build(families: tuple[str, ...] = ("computed", "sports", "weather")) -> dict:
    pool = Pool()
    if "computed" in families:
        add_computed(pool)
    if "sports" in families:
        from src.literals.sports import add_sports
        add_sports(pool)
    if "weather" in families:
        from src.literals.weather import add_weather
        add_weather(pool)
    main, era = pool.finalize()
    hashes = write_pool(main, era)
    return {"pool": pool, "main": main, "era": era, "hashes": hashes, "sha": pool_sha256(hashes)}


if __name__ == "__main__":
    fams = tuple(sys.argv[1:]) or ("computed", "sports", "weather")
    r = build(fams)
    print(len(r["main"]), "main literals,", len(r["era"]), "era indicators,", r["sha"])
