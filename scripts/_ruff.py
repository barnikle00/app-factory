"""Find ruff the same way in every hook, and never go quiet when it is missing.

A hook process does not get an interactive shell's PATH. ruff is installed with `uv tool install`
into ~/.local/bin, and a plain PATH does not contain that directory — checked 2026-09-15:
`command -v ruff` finds it in a terminal and not on /usr/bin:/bin:/opt/homebrew/bin. lint-touched.py
used to return 0 when `shutil.which("ruff")` came back empty, so in any environment without
~/.local/bin the lint hook would have done nothing at all, and nobody would have known.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

CANDIDATES = (
    Path.home() / ".local" / "bin" / "ruff",
    Path("/opt/homebrew/bin/ruff"),
    Path("/usr/local/bin/ruff"),
    Path.home() / ".local" / "share" / "uv" / "tools" / "ruff" / "bin" / "ruff",
)

MISSING = ("ruff was not found — not on PATH, and not in ~/.local/bin, /opt/homebrew/bin, "
           "/usr/local/bin or the uv tool directory. Nothing was linted, and that is not a pass. "
           "Install it with: uv tool install ruff")


def find_ruff() -> str | None:
    """FACTORY_RUFF, when set, is the only place looked — so a test can prove the missing case."""
    override = os.environ.get("FACTORY_RUFF")
    if override is not None:
        return override if Path(override).is_file() else None
    found = shutil.which("ruff")
    if found:
        return found
    for candidate in CANDIDATES:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None
