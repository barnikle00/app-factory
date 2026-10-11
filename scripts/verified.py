#!/usr/bin/env python3
"""Run a factory project's verification command, and remember exactly what it passed on.

    scripts/verified.py <project> -- <verification command ...>

The commit lock (commit-gate.py) refuses a commit in a factory project unless what is being
committed is exactly what the tests last passed on. This is what records that: the command runs in
the project, and only when it exits 0 is the id of the working tree — everything `git add -A` would
stage, test artefacts included — written to .git/factory-verified. Change one line afterwards and
the id no longer matches.

Commit everything you tested. To commit only part of it, stash the rest before running the tests.
"""

from __future__ import annotations

import datetime as _dt
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _git import git_dir, toplevel, working_tree_id  # noqa: E402

STAMP = "factory-verified"


def main(argv: list[str]) -> int:
    if "--" not in argv or argv.index("--") != 2 or len(argv) < 4:
        print("usage: verified.py <project> -- <verification command ...>", file=sys.stderr)
        return 2
    project = Path(argv[1]).expanduser().resolve()
    command = argv[3:]
    repo = toplevel(project)
    if repo is None:
        print(f"{project} is not inside a git repository", file=sys.stderr)
        return 2
    print(f"verifying {repo.name}: {' '.join(command)}", flush=True)
    result = subprocess.run(command, cwd=project)
    if result.returncode != 0:
        print(f"\nNOT VERIFIED — the command exited {result.returncode}. Nothing recorded; a commit of "
              f"this work will be refused until it passes.", file=sys.stderr)
        return result.returncode
    tree = working_tree_id(repo)
    (git_dir(repo) / STAMP).write_text(json.dumps({
        "tree": tree, "command": command,
        "at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
    }), encoding="utf-8")
    print(f"\nVERIFIED — tree {tree[:12]} recorded. Commit it as it is; any further change needs another run.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
