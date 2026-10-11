#!/usr/bin/env python3
"""Tell every session which projects are under the factory, and what that means.

A SessionStart hook. Five hooks in this workspace are deterministic — they run whether or not a
session remembers them. Every other check runs only because a skill says so, and a skill is
guidance: the model reads its description and decides. This closes the gap a little, at a cost of
about a dozen lines per session: it states, before any work begins, which projects carry the
factory's guarantees and what must be green in them.

Silent when no project under the current directory is a factory project — the ad-hoc and course
lanes must never be made heavier by this.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

BRIEF = """Factory projects here: {projects}. In those projects only:
- Commits are locked: the verification command must have passed on exactly the tree being
  committed, recorded by `{root}/scripts/verified.py <repo> -- <command>`; lint must be clean;
  one migration may not both add and drop; no `STAND-IN(phase NN)` may outlive phase NN.
- Edits are checked, and refused, as they are written: format and lint, a file crossing 500 lines, the project's
  own ADRs, the design linter.
- A new app starts from `{root}/foundation/skeleton`. Before a spec: `trace-check.py --stage
  architecture` and `architecture-check.py` green; outside writes go through app/core/outside.py.
- Data tests use a real throwaway PostgreSQL (`realdb_url`). After each phase `budget-check.py`;
  over budget, or the phase marked "real run" done, stops the run for the user.
- Before a deploy: `final-check` — trace, suites, every button pressed (`press-check.py`, local
  only), budgets, health, and the verdict page the user reads. The rules and the build loop: skill `factory-guide`.
Nothing above applies to any other project in the workspace. The scripts live in `{root}/scripts`."""


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        payload = {}
    root = Path(payload.get("cwd") or ".").expanduser()
    if not root.is_dir():
        return 0
    found = sorted({p.parent.name for p in root.glob("*/.factory")} | {p.parent.name for p in root.glob(".factory")})
    if not found:
        return 0
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": BRIEF.format(projects=", ".join(found), root=ROOT),
    }}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
