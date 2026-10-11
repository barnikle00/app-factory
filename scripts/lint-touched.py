#!/usr/bin/env python3
"""Format and lint exactly the file a session just wrote — nothing else.

Reads a Claude Code PostToolUse payload on stdin. Formats and auto-fixes the
touched file, then reports whatever ruff still objects to.

WHY ONLY THE TOUCHED FILE: `ruff format` would rewrite 219 of this workspace's
334 Python files in an older project alone. A one-shot reformat is a
219-file commit that destroys `git blame` on a live money-handling system and
changes no behaviour. Touch-scoped formatting converges on the same end state,
one real edit at a time, and every diff stays reviewable.

EXIT CODES: 1 warns (the message reaches the model, the edit stands).
2 blocks. Blocking since 2026-09-30 (see MODE_EXIT); a missing ruff still only warns.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from _project import is_factory_project
from _ruff import MISSING, find_ruff

MODE_EXIT = 2  # blocking since 2026-09-30. Two weeks of the first factory app showed a warning is read and
#   passed by: two test files crossed 500 lines under it. Exit 2 hands the finding back and the
#   agent fixes it before going on. Back to 1 only with a reason written here.
_ROOT = Path(__file__).resolve().parent.parent
CONFIG = _ROOT / "foundation" / "tooling" / "ruff.toml"
# One fixed cache outside the plugin (its folder is replaced on update) and outside the
# project, or ruff drops a .ruff_cache/ into whatever directory the session was standing in.
CACHE = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "app-factory" / "ruff"


def touched_file() -> Path | None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return None
    ti = payload.get("tool_input") or {}
    raw = ti.get("file_path") or ti.get("notebook_path")
    return Path(raw) if raw else None


def main() -> int:
    f = touched_file()
    if f is None or f.suffix != ".py" or not f.is_file():
        return 0
    # Existing projects are left exactly as they were. Measured on a copy of
    # an older project: one edit let this hook delete an import that looked
    # unused in its file but is re-imported elsewhere and loaded at startup — the
    # dashboard and the bot would not have started. It also rewrote 103 unrelated
    # lines of a settlement file. Neither is acceptable on code this hook did not
    # write, so it only acts inside a project the factory built.
    if not is_factory_project(f):
        return 0
    ruff = find_ruff()
    if not ruff:
        # Loud, never silent: a missing tool must not stop work, and must not pass as clean either.
        print(MISSING, file=sys.stderr)
        return 1

    cfg = ["--config", str(CONFIG), "--cache-dir", str(CACHE)]
    # Format and auto-fix silently — these are not findings, they are tidying.
    subprocess.run([ruff, "format", "--config", str(CONFIG), "--cache-dir", str(CACHE), str(f)],
                   capture_output=True, text=True)
    subprocess.run([ruff, "check", *cfg, "--fix", "--quiet", str(f)],
                   capture_output=True, text=True)

    # Whatever survives is a real finding the author has to see.
    result = subprocess.run([ruff, "check", *cfg, "--output-format=concise", str(f)],
                            capture_output=True, text=True)
    if result.returncode == 0:
        return 0

    print(
        f"ruff still objects to {f} after formatting and auto-fix:\n"
        f"{result.stdout.strip()}\n"
        f"Fix these before moving on. Config: {CONFIG}",
        file=sys.stderr,
    )
    return MODE_EXIT


if __name__ == "__main__":
    sys.exit(main())
