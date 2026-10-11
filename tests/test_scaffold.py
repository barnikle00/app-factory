"""build-spec step 0, exactly as the skill prints it, run on a clean copy of the plugin.

The skill carries a bash block that lays down a new app. Nobody runs that block except a new
project, so it can rot unseen — and did: the "generic design system" branch overwrote the kit's
base template and never installed itself, and no real app had taken that branch yet. This test
extracts the block from `skills/build-spec/SKILL.md`, runs it for each way a project can start, and
then runs the project's own verification command.

Slow (a virtualenv and a PostgreSQL container), so it needs uv and a running Docker.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from test_skeleton import needs_tools

ROOT = Path(__file__).resolve().parent.parent
SKILL = (ROOT / "skills" / "build-spec" / "SKILL.md").read_text(encoding="utf-8")
BLOCK = re.search(r"```bash\n(P=<project>.*?)```", SKILL, re.S).group(1)


def scaffold(tmp_path: Path, *, profile: str, prototype: bool) -> Path:
    plugin = tmp_path / "plugin"        # a clean copy, as a stranger's machine would hold it
    shutil.copytree(ROOT, plugin, ignore=shutil.ignore_patterns(
        "__pycache__", ".pytest_cache", ".cache", ".venv", ".git"))
    project = tmp_path / "newapp"
    project.mkdir()
    if prototype:                        # a design that names its own prototype skips step 3
        (project / "DESIGN-V1.md").write_text("Reference implementation: `prototype/v1.html`\n")
    script = BLOCK.replace("P=<project>", f"P={project}", 1).replace("NAME=<project>", "NAME=newapp", 1)
    (tmp_path / "step0.sh").write_text(script)
    env = {**os.environ, "CLAUDE_PLUGIN_ROOT": str(plugin), "PROFILE": profile}
    r = subprocess.run(["bash", "-e", str(tmp_path / "step0.sh")], capture_output=True, text=True,
                       env=env, timeout=900)
    assert r.returncode == 0, (r.stdout[-3000:], r.stderr[-3000:])
    return project


@needs_tools
@pytest.mark.parametrize("profile,prototype", [
    ("", False), ("persian", False), ("", True), ("persian", True)],
    ids=["neutral+design-system", "persian+design-system", "neutral+own-prototype", "persian+own-prototype"])
def test_step_zero_lays_down_an_app_whose_own_verification_passes(tmp_path, profile, prototype):
    project = scaffold(tmp_path, profile=profile, prototype=prototype)
    assert (project / ".factory").is_file() and (project / "adr" / "0001-schema-changes-are-expand-contract.md").is_file()
    assert (project / "app" / "ds.py").is_file() is (not prototype)
    assert "factory-app" not in "".join(
        p.read_text(encoding="utf-8") for p in project.rglob("*.py") if ".venv" not in p.parts)
    # the script's last line ran pytest, ruff and pyrefly under `bash -e`, so reaching here means all passed
