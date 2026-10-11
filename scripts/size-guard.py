#!/usr/bin/env python3
"""Stop a source file from CROSSING 500 lines. Never punish one already over.

The root CLAUDE.md rule "keep files under 500 lines" is currently broken 356
times across the workspace, the worst at 10,054 lines. A guard that simply
refused every oversized file would make those 356 files unrepairable — a
one-line bug fix in a 1,700-line module would be blocked — so the guard would
be switched off within a day.

So it fires only on the transition: the file was at or under the limit before
this edit and is over it now. The baseline comes from git (HEAD), which is the
only honest "before" available in a PostToolUse hook, since the write already
happened. A file outside a git repo, or newly added, is checked against 0.

EXIT CODES: 1 warns, 2 blocks. Blocking since 2026-09-30 (see MODE_EXIT).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from _project import is_factory_project

LIMIT = 500
MODE_EXIT = 2  # blocking since 2026-09-30. Two weeks of the first factory app showed a warning is read and
#   passed by: two test files crossed 500 lines under it. Exit 2 hands the finding back and the
#   agent fixes it before going on. Back to 1 only with a reason written here.
SOURCE_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".dart"}


def touched_file() -> Path | None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return None
    ti = payload.get("tool_input") or {}
    raw = ti.get("file_path") or ti.get("notebook_path")
    return Path(raw) if raw else None


def lines_at_head(f: Path) -> int:
    """Line count of this file as of HEAD; 0 if untracked or not in a repo."""
    try:
        root = subprocess.run(
            ["git", "-C", str(f.parent), "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        rel = f.resolve().relative_to(Path(root).resolve())
        blob = subprocess.run(
            ["git", "-C", root, "show", f"HEAD:{rel}"],
            capture_output=True, text=True,
        )
        if blob.returncode != 0:
            return 0  # untracked: this edit created it
        return len(blob.stdout.splitlines())
    except Exception:
        return 0


def main() -> int:
    f = touched_file()
    if f is None or f.suffix not in SOURCE_SUFFIXES or not f.is_file():
        return 0
    if not is_factory_project(f):
        return 0   # an existing project behaves exactly as it did before the factory

    try:
        after = len(f.read_text(encoding="utf-8", errors="replace").splitlines())
    except OSError:
        return 0

    if after <= LIMIT:
        return 0

    before = lines_at_head(f)
    if before > LIMIT:
        return 0  # already over before this edit — repairing it must stay possible

    print(
        f"{f} just crossed {LIMIT} lines ({before} → {after}).\n"
        f"Split it now, while the seam is obvious: move the newest coherent piece "
        f"into its own module and import it. This workspace already has 356 files "
        f"over the limit; each one became unsplittable by passing this exact moment "
        f"without anyone noticing.",
        file=sys.stderr,
    )
    return MODE_EXIT


if __name__ == "__main__":
    sys.exit(main())
