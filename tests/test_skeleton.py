"""The starter kit passes its own verification command, exactly as a new project will run it.

the first factory app spent three phases building what every panel needs; the kit is that work done once.
A kit that arrives broken would cost every new app its first phase, so the factory proves it here:
a fresh environment from the kit's own pins, its whole suite — including the real-database tests —
then ruff and pyrefly.

Slow (a virtualenv and a PostgreSQL container), so it runs only when uv and Docker are present.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

FOUNDATION = Path(__file__).resolve().parent.parent / "foundation"
KIT = FOUNDATION / "skeleton"

needs_tools = pytest.mark.skipif(
    shutil.which("uv") is None
    or shutil.which("docker") is None
    or subprocess.run(["docker", "info"], capture_output=True).returncode != 0,
    reason="uv and a running Docker are needed to build and test the kit",
)


def sh(cwd: Path, *cmd: str, timeout: int = 600) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)


def scaffold(tmp_path: Path, profile: str | None) -> Path:
    """The starter kit as build-spec step 0 lays it down, with a language profile overlaid if asked."""
    project = tmp_path / "new-app"
    shutil.copytree(KIT, project, ignore=shutil.ignore_patterns(".venv", "__pycache__", ".*_cache"))
    shutil.copy(FOUNDATION / "tooling" / "realdb.py", project / "tests" / "realdb.py")
    if profile:
        overlay = FOUNDATION / "profiles" / profile
        shutil.copytree(overlay, project, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("README.md", "requirements.add.txt", "adr"))
        extra = overlay / "requirements.add.txt"
        if extra.is_file():
            with (project / "requirements.txt").open("a", encoding="utf-8") as f:
                f.write(extra.read_text(encoding="utf-8"))
    return project


def verify(project: Path) -> None:
    assert sh(project, "uv", "venv", "-q", "-p", "3.11", ".venv").returncode == 0
    install = sh(project, "uv", "pip", "install", "-q", "-p", ".venv/bin/python",
                 "-r", "requirements-dev.txt")
    assert install.returncode == 0, install.stderr[-2000:]
    for cmd in ((".venv/bin/python", "-m", "pytest", "-q"),
                (".venv/bin/ruff", "check", "."),
                (".venv/bin/ruff", "format", "--check", "."),
                (".venv/bin/pyrefly", "check")):
        r = sh(project, *cmd)
        assert r.returncode == 0, f"{' '.join(cmd)}\n{r.stdout[-3000:]}\n{r.stderr[-2000:]}"


@needs_tools
@pytest.mark.parametrize("profile", [None, "persian"], ids=["neutral", "persian-profile"])
def test_the_kit_passes_its_own_verification_command(tmp_path, profile):
    verify(scaffold(tmp_path, profile))


def test_the_kit_stays_small():
    """The kit is the floor every app starts from, so its size is every app's size before its first
    screen. the first factory app's equivalent was built across three phases; this must stay a fraction."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
    import _budgets
    total, _ = _budgets.count(KIT)
    assert total < 1200, f"the starter kit has grown to {total} lines of code"

