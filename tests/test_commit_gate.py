"""commit-gate.py and verified.py — the lock before a commit, tested both ways.

Each refusal the lock exists for must happen, by name: an untested tree, a change after the tests,
a lint error, a migration that adds and drops. And each thing it must never do must not happen:
touch a project the factory did not build, stop a documentation-only commit, stop a migration that
only drops, or miss a commit written as `git -C <repo> commit` or `cd <repo> && git commit`.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))
from _ruff import find_ruff  # noqa: E402


def sh(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    r = tmp_path / "new-app"
    (r / "app").mkdir(parents=True)
    sh(tmp_path, "init", "-q", str(r))
    sh(r, "config", "user.email", "test@example.com")
    sh(r, "config", "user.name", "Test")
    (r / ".factory").write_text("factory project — test\n")
    (r / "app" / "main.py").write_text("VALUE = 1\n")
    (r / "README.md").write_text("# app\n")
    sh(r, "add", "-A")
    sh(r, "commit", "-q", "-m", "start")
    return r


def gate(repo: Path, command: str = "git commit -m change", cwd: Path | None = None) -> tuple[int, str]:
    payload = {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": str(cwd or repo)}
    p = subprocess.run([sys.executable, str(SCRIPTS / "commit-gate.py")], input=json.dumps(payload),
                       capture_output=True, text=True)
    return p.returncode, p.stderr


def verify(repo: Path, *command: str) -> int:
    return subprocess.run([sys.executable, str(SCRIPTS / "verified.py"), str(repo), "--",
                           *(command or (sys.executable, "-c", "pass"))], capture_output=True, text=True).returncode


def change(repo: Path, rel: str = "app/main.py", text: str = "VALUE = 2\n", stage: bool = True) -> None:
    (repo / rel).parent.mkdir(parents=True, exist_ok=True)
    (repo / rel).write_text(text)
    if stage:
        sh(repo, "add", "-A")


def test_an_untested_commit_is_refused(repo):
    change(repo)
    code, err = gate(repo)
    assert code == 2 and "not what the tests last passed on" in err and "verified.py" in err


def test_a_tested_commit_passes(repo):
    change(repo)
    assert verify(repo) == 0
    code, err = gate(repo)
    assert code == 0, err


def test_a_change_after_the_tests_is_refused(repo):
    change(repo)
    assert verify(repo) == 0
    change(repo, text="VALUE = 3\n")
    code, err = gate(repo)
    assert code == 2 and "something changed after the last passing test run" in err


def test_a_failing_verification_records_nothing(repo):
    change(repo)
    assert verify(repo, sys.executable, "-c", "raise SystemExit(1)") == 1
    assert gate(repo)[0] == 2


def test_a_project_the_factory_did_not_build_is_never_touched(repo):
    (repo / ".factory").unlink()
    change(repo)
    assert gate(repo)[0] == 0


def test_a_documentation_only_commit_needs_no_test_run(repo):
    change(repo, "README.md", "# app\n\nmore words\n")
    assert gate(repo)[0] == 0


def test_a_commit_is_found_however_it_is_written(repo, tmp_path):
    change(repo)
    elsewhere = tmp_path
    assert gate(repo, f"git -C {repo} commit -m x", cwd=elsewhere)[0] == 2
    assert gate(repo, f"cd {repo} && git commit -m x", cwd=elsewhere)[0] == 2
    assert gate(repo, f'/opt/homebrew/bin/git -c user.name=B -C {repo} commit -q -m "$(cat <<EOF\nx\nEOF\n)"', cwd=elsewhere)[0] == 2
    assert gate(repo, "git status", cwd=repo)[0] == 0


def test_commit_dash_a_is_judged_on_the_tracked_changes_it_will_record(repo):
    change(repo, stage=False)
    assert verify(repo) == 0
    code, err = gate(repo, "git commit -am 'change'")
    assert code == 0, err


def test_a_migration_that_adds_and_drops_is_refused(repo):
    change(repo, "alembic/versions/002_x.py",
           "def upgrade():\n    op.add_column('sale', sa.Column('seller_id', sa.BigInteger(), nullable=True))\n"
           "    op.drop_column('sale', 'old_seller')\n")
    assert verify(repo) == 0
    code, err = gate(repo)
    assert code == 2 and "ADR 0001" in err


def test_a_migration_that_only_drops_is_the_contract_step_and_passes(repo):
    change(repo, "alembic/versions/003_x.py", "def upgrade():\n    op.drop_column('sale', 'old_seller')\n")
    assert verify(repo) == 0
    code, err = gate(repo)
    assert "ADR 0001" not in err


@pytest.mark.skipif(find_ruff() is None, reason="ruff not installed")
def test_a_lint_error_in_a_committed_file_is_refused(repo):
    change(repo, "app/extra.py", "import os\n")
    assert verify(repo) == 0
    code, err = gate(repo)
    assert code == 2 and "ruff objects" in err and "F401" in err


# ── stand-ins ────────────────────────────────────────────────────────────────
# the first factory app's final check traced several defects to placeholders an early phase left for a
# later one — `SequencesOnly()`, `NoConditionsYet`, `SYSTEM_FOLDERS_NOW = 0` — which the later phase
# was marked done without replacing.

STANDIN = "def folder_use(detector):\n    return []  # STAND-IN(phase 12): the real folder-use query\n"


def test_a_stand_in_for_a_phase_still_open_may_be_committed(repo):
    (repo / "PROGRESS.md").write_text("- [x] 11 detectors\n- [ ] 12 folders\n")
    change(repo, "app/use.py", STANDIN)
    assert verify(repo) == 0
    code, err = gate(repo)
    assert code == 0, err


def test_marking_its_phase_done_while_the_stand_in_is_there_is_refused(repo):
    (repo / "PROGRESS.md").write_text("- [x] 11 detectors\n- [x] 12 folders\n")
    change(repo, "app/use.py", STANDIN)
    assert verify(repo) == 0
    code, err = gate(repo)
    assert code == 2 and "stand-in for phase 12" in err and "app/use.py:2" in err


def test_a_stand_in_that_names_no_phase_is_refused(repo):
    (repo / "PROGRESS.md").write_text("- [ ] 12 folders\n")
    change(repo, "app/use.py", "SYSTEM_FOLDERS_NOW = 0  # STAND-IN: counted later\n")
    assert verify(repo) == 0
    code, err = gate(repo)
    assert code == 2 and "names no phase" in err


def test_prose_about_stand_ins_is_not_one(repo):
    (repo / "PROGRESS.md").write_text("- [x] 12 folders\n")
    change(repo, "app/use.py", '"""Every STAND-IN marker names its phase; a stand-in is fine."""\n')
    assert verify(repo) == 0
    code, err = gate(repo)
    assert code == 0, err


def test_a_same_size_edit_right_after_a_commit_is_never_missed(tmp_path):
    """The lock copies git's index to compute a tree. A copy stamped «now» made git trust stale
    size-and-time data, so an edit of the same size inside the same tick as the commit was not
    seen: 12 of 600 trees came back as the old content, and a commit-lock test failed once in a full
    run. Measured over many quick edits, because the race only shows that way."""
    from _git import commit_tree_id, working_tree_id
    stale = 0
    for i in range(100):
        r = tmp_path / f"r{i}"
        (r / "app").mkdir(parents=True)
        sh(tmp_path, "init", "-q", str(r))
        sh(r, "config", "user.email", "t@example.com")
        sh(r, "config", "user.name", "T")
        (r / "app" / "main.py").write_text("VALUE = 1\n")
        sh(r, "add", "-A")
        sh(r, "commit", "-q", "-m", "x")
        (r / "app" / "main.py").write_text("VALUE = 2\n")
        head = sh(r, "rev-parse", "HEAD^{tree}").stdout.strip()
        stale += (working_tree_id(r) == head) + (commit_tree_id(r, True) == head)
    assert stale == 0, f"{stale} of 200 trees were the old content"
