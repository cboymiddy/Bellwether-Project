"""Strings that must never appear in published files: derived at run time so the tests don't contain them.

Sources: the OS account name and home directory, the local git email, and an optional untracked
`.private_strings` file (one string per line, gitignored) for anything else, such as a GitHub handle.
"""

from __future__ import annotations

import getpass
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def private_strings() -> list[str]:
    out = {"/Use" + "rs/", str(Path.home()), getpass.getuser()}
    try:
        email = subprocess.run(["git", "config", "user.email"], capture_output=True, text=True, cwd=ROOT, check=False).stdout.strip()
    except OSError:
        email = ""
    if email:
        out |= {email, email.split("@")[0]}
    extra = ROOT / ".private_strings"
    if extra.exists():
        out |= {ln.strip() for ln in extra.read_text().splitlines() if ln.strip()}
    return sorted(s for s in out if len(s) >= 4)
