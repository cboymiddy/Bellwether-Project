"""Config loading, hashing, and computed election dates."""

import datetime as dt
import hashlib
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.yaml"


def load_config(path: Path = CONFIG_PATH) -> dict:
    return yaml.safe_load(path.read_text())


def config_sha256(path: Path = CONFIG_PATH) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def election_day(year: int) -> dt.date:
    """First Tuesday after the first Monday in November."""
    d = dt.date(year, 11, 1)
    first_monday = d + dt.timedelta(days=(0 - d.weekday()) % 7)
    return first_monday + dt.timedelta(days=1)


def election_years(cfg: dict | None = None) -> list[int]:
    e = (cfg or load_config())["elections"]
    return list(range(e["start"], e["end"] + 1, e["step"]))
