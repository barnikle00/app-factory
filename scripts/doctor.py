#!/usr/bin/env python3
"""Check this machine has what the factory's gates need, and say how to get what is missing.

    python3 scripts/doctor.py

Nothing here installs anything. A missing tool is reported with the command that fixes it, and a
check that cannot run is never reported as a pass.
"""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _ruff import find_ruff  # noqa: E402


def docker_running() -> bool:
    if shutil.which("docker") is None:
        return False
    return subprocess.run(["docker", "info"], capture_output=True).returncode == 0


# (name, ok, why it matters, how to fix, required for every project?)
CHECKS = [
    ("Python 3.11 or newer", sys.version_info >= (3, 11),
     "every gate script runs on it", "install Python 3.11+ (https://www.python.org/downloads/)", True),
    ("git", shutil.which("git") is not None,
     "the commit lock and the phase commits", "install git", True),
    ("ruff", find_ruff() is not None,
     "formats and lints every file a session writes in a factory project",
     "uv tool install ruff   (or: pipx install ruff)", True),
    ("uv", shutil.which("uv") is not None,
     "builds a new app's virtual environment from the starter kit",
     "curl -LsSf https://astral.sh/uv/install.sh | sh", False),
    ("Docker (running)", docker_running(),
     "a throwaway PostgreSQL for the tests that touch data (ADR: tested on the real thing)",
     "install and start Docker Desktop or the Docker engine", False),
    ("playwright", importlib.util.find_spec("playwright") is not None,
     "presses every button and measures contrast and phone layout in a real browser",
     "python3 -m pip install playwright && python3 -m playwright install chromium", False),
]


def main() -> int:
    missing_required = False
    for name, ok, why, fix, required in CHECKS:
        print(f"  {'OK     ' if ok else 'MISSING'}  {name}")
        if not ok:
            print(f"           needed for: {why}\n           fix: {fix}")
            missing_required |= required
    print()
    if missing_required:
        print("Something every factory project needs is missing — see above.")
        return 1
    print("The always-on gates can run. Anything marked MISSING above only limits the checks that use it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
