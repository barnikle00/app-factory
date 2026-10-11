#!/usr/bin/env python3
"""The lock before a commit — factory projects only.

A PreToolUse hook on Bash. When the command is a `git commit` inside a project the factory built
(a `.factory` file at its root), it refuses the commit — exit 2, with the reason handed back to the
agent — when any of these is true:

  1. What is being committed is not what the tests last passed on. The verification command must
     have passed on exactly this tree, run through verified.py, which records the tree it tested.
     Change one line after the tests and the commit is refused until they run again.
  2. ruff reports a problem in a Python file being committed.
  3. A migration being committed both adds a shape and removes one. ADR 0001 is expand, migrate,
     contract — never in one migration. One edited line cannot show that, so it is checked here,
     where the whole file is known. A migration that only drops is the legitimate contract step
     and passes.
  4. A stand-in outlived its phase: code marked `STAND-IN(phase NN)` while PROGRESS.md says phase
     NN is done, or a stand-in that names no phase at all (_standins.py). Checked on every commit
     that touches code or the register — the moment a phase is claimed done.

A commit that touches no code (documentation, reports, the design pack) needs no test run.
Outside a factory project this hook does nothing.

WHY IT BLOCKED FROM THE START, while the edit hooks warned until 2026-09-30: every refusal here is mechanical —
an untested tree, a lint error, an add and a drop in one file — so there is no noise to watch for
first. The owner asked for the lock on 2026-09-15, before any project had reached it.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _git import commit_tree_id, git, git_dir, has_head, toplevel  # noqa: E402
from _project import is_factory_project  # noqa: E402
from _ruff import MISSING, find_ruff  # noqa: E402
from _standins import problems as standin_problems  # noqa: E402

MODE_EXIT = 2
STAMP = "factory-verified"
CONFIG = Path(__file__).resolve().parent.parent / "foundation" / "tooling" / "ruff.toml"
CODE_SUFFIXES = {".py", ".html", ".jinja", ".jinja2", ".j2", ".css", ".js", ".mjs", ".ts", ".sql",
                 ".toml", ".cfg", ".ini", ".yml", ".yaml", ".json"}

GIT_COMMIT = re.compile(r"(?:^|[\s;&|(])(?:\S*/)?git((?:\s+(?:-C\s+\S+|-c\s+\S+|--[\w-]+(?:=\S+)?))*)\s+commit\b")
CD = re.compile(r"(?:^|[;&]\s*)cd\s+(\S+)\s*&&")
MIGRATION = re.compile(r"(?:^|/)(?:alembic|migrations)/versions/[^/]+\.py$")
ADDS = re.compile(r"\bop\.(?:add_column|create_table|create_index|create_foreign_key|create_unique_constraint)\s*\(")
DROPS = re.compile(r"\bop\.(?:drop_column|drop_table|drop_constraint|drop_index)\s*\(")


def target(command: str, cwd: str | None) -> tuple[Path, bool] | None:
    """(the directory the commit runs in, whether it commits all tracked changes with -a)."""
    m = GIT_COMMIT.search(command)
    if not m:
        return None
    base = Path(cwd or os.getcwd())
    cds = [c.group(1).strip("'\"") for c in CD.finditer(command[: m.start() + 1])]
    if cds:
        base = (base / os.path.expanduser(cds[-1])).resolve()
    dash_c = re.search(r"-C\s+(\S+)", m.group(1) or "")
    if dash_c:
        base = (base / os.path.expanduser(dash_c.group(1).strip("'\""))).resolve()
    head = re.split(r"\s-m\b|\s--message\b|\s-F\b|\s--file\b|[\"'$\n;&|]", command[m.end():], maxsplit=1)[0]
    all_tracked = bool(re.search(r"(?:^|\s)(?:--all|-[A-Za-z]*a[A-Za-z]*)(?=\s|$)", head))
    return base, all_tracked


def changed_files(repo: Path, all_tracked: bool) -> list[str]:
    if not has_head(repo):
        out = git(repo, "ls-files").stdout
    elif all_tracked:
        out = git(repo, "diff", "--name-only", "HEAD").stdout
    else:
        out = git(repo, "diff", "--cached", "--name-only").stdout
    return [n for n in out.splitlines() if n.strip()]


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    if payload.get("tool_name") not in (None, "Bash"):
        return 0
    found = target((payload.get("tool_input") or {}).get("command") or "", payload.get("cwd"))
    if not found or not found[0].is_dir():
        return 0
    where, all_tracked = found
    repo = toplevel(where)
    if repo is None or not is_factory_project(repo):
        return 0
    files = changed_files(repo, all_tracked)
    if not files:
        return 0

    problems: list[str] = []

    if any(Path(f).suffix.lower() in CODE_SUFFIXES for f in files):
        stamp_file = git_dir(repo) / STAMP
        stamp = json.loads(stamp_file.read_text(encoding="utf-8")) if stamp_file.is_file() else None
        if not stamp or stamp.get("tree") != commit_tree_id(repo, all_tracked):
            why = ("the tests have never been recorded as passing here" if not stamp else
                   "something changed after the last passing test run, or not everything that was "
                   "tested is staged")
            pending = git(repo, "status", "--porcelain").stdout.splitlines()[:8]
            problems.append(
                "What you are committing is not what the tests last passed on — " + why + ".\n"
                f"    Run: {Path(__file__).resolve().parent / 'verified.py'} {repo} -- <the project's verification command>\n"
                "    then commit straight away, changing nothing in between."
                + ("\n    Working tree right now:\n      " + "\n      ".join(pending) if pending else ""))

    python = [f for f in files if f.endswith(".py") and (repo / f).is_file()]
    if python:
        ruff = find_ruff()
        if not ruff:
            problems.append(MISSING)
        else:
            r = subprocess.run([ruff, "check", "--config", str(CONFIG), "--no-cache",
                                "--output-format=concise", *python], cwd=repo, capture_output=True, text=True)
            if r.returncode != 0:
                problems.append("ruff objects to files in this commit:\n    "
                                + "\n    ".join((r.stdout or r.stderr).strip().splitlines()[:20]))

    for f in files:
        if MIGRATION.search(f) and (repo / f).is_file():
            text = (repo / f).read_text(encoding="utf-8", errors="replace")
            if ADDS.search(text) and DROPS.search(text):
                problems.append(
                    f"{f} both adds a shape and removes one. ADR 0001: expand, migrate, then contract — "
                    f"keep the add here and move the drop into its own later migration, after the code "
                    f"has stopped reading the old shape.")

    if any(Path(f).suffix.lower() in CODE_SUFFIXES or Path(f).name == "PROGRESS.md" for f in files):
        problems.extend(standin_problems(repo))

    if not problems:
        return 0
    print("Commit refused — this is a factory project, and the commit lock found:\n\n- "
          + "\n\n- ".join(problems), file=sys.stderr)
    return MODE_EXIT


if __name__ == "__main__":
    sys.exit(main())
