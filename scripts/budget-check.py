#!/usr/bin/env python3
"""Is the app still inside the size its architecture promised?

    budget-check.py <project>

Counts the app's own code — under `app/`, without tests, comments, docstrings, blank lines,
vendored or minified files — and compares it with `## Budgets → Code` in ARCHITECTURE.md. Prints
where the lines are, largest part first, so "too big" arrives with "and this is where".

WHY. the first factory app's architecture said "simple" and meant it; nothing counted. Its prototype was
2,900 lines and the build reached 27,500 lines of code before the owner's "far too big and complicated"
was the first measurement anyone made. run-phases runs this after every phase: crossing the budget
stops the run and puts the choice to the user — simplify, or raise the number knowingly.

Exit 0 inside the budget, 1 over it or when the architecture states no code budget.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _budgets  # noqa: E402


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: budget-check.py <project>", file=sys.stderr)
        return 2
    project = Path(argv[1]).expanduser().resolve()
    budget = _budgets.read(project).get("code_lines")
    total, parts = _budgets.count(project)
    print(f"CODE SIZE — {project.name}: {total:,} lines of code"
          + (f" · budget {budget:,} ({100 * total // budget}%)" if budget else ""))
    for name, n in sorted(parts.items(), key=lambda kv: -kv[1])[:8]:
        print(f"  {n:>7,}  {name}")
    if not budget:
        print("\nFAIL  ARCHITECTURE.md → ## Budgets states no code budget "
              "(a line like «**Code** — 12,000 lines: …»)")
        return 1
    if total > budget:
        print(f"\nOVER BUDGET by {total - budget:,} lines. Stop and ask the user: simplify what is "
              f"listed above, or raise the budget in ARCHITECTURE.md with a dated revision saying why.")
        return 1
    print("\nOK — inside the budget")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
