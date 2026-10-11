"""factory-brief.py — said at session start, or not said at all.

The factory must not make other work heavier. This brief appears only when a project under the
session's directory actually carries the marker, and it names those projects so a session cannot
apply the rules to the wrong one.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "factory-brief.py"


def run(cwd: Path) -> tuple[int, str]:
    p = subprocess.run([sys.executable, str(SCRIPT)], input=json.dumps({"cwd": str(cwd)}),
                       capture_output=True, text=True)
    return p.returncode, p.stdout


def test_it_says_nothing_when_no_project_is_under_the_factory(tmp_path):
    (tmp_path / "some-bot").mkdir()
    code, out = run(tmp_path)
    assert code == 0 and out.strip() == ""


def test_it_names_the_factory_projects_and_the_gates(tmp_path):
    (tmp_path / "new-app").mkdir()
    (tmp_path / "new-app" / ".factory").write_text("x\n")
    (tmp_path / "old-bot").mkdir()
    code, out = run(tmp_path)
    assert code == 0
    context = json.loads(out)["hookSpecificOutput"]["additionalContext"]
    assert "new-app" in context and "old-bot" not in context
    assert "verified.py" in context and "final-check" in context
    assert len(context.splitlines()) <= 14, "a session-start brief must stay small"


def test_it_works_from_inside_the_project_too(tmp_path):
    (tmp_path / ".factory").write_text("x\n")
    code, out = run(tmp_path)
    assert code == 0 and tmp_path.name in json.loads(out)["hookSpecificOutput"]["additionalContext"]
