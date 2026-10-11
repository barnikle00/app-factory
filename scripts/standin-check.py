#!/usr/bin/env python3
"""List the stand-ins a project is carrying, and fail on any that outlived its phase.

    standin-check.py <project>

The commit lock enforces the same rule on every commit; this prints the whole list, so a run can
say how many placeholders are still waiting and for which phase. Rule and reasons: _standins.py.
Exit 0 when every stand-in names a phase that is still open, 1 otherwise.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _standins  # noqa: E402


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: standin-check.py <project>", file=sys.stderr)
        return 2
    project = Path(argv[1]).expanduser().resolve()
    found = _standins.scan(project)
    print(f"STAND-INS — {project.name}: {len(found)}")
    for rel, n, phase, what in found:
        print(f"  phase {phase if phase is not None else '?':>3}  {rel}:{n}  {what}")
    bad = _standins.problems(project)
    for p in bad:
        print(f"  FAIL  {p}")
    print("\nFAILED" if bad else "\nOK — every stand-in waits for a phase that is still open")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
