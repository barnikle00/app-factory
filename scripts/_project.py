"""Is this file inside a project the factory built?

    from _project import is_factory_project
    if not is_factory_project(path):
        return 0          # an existing project: behave exactly as before

THE RULE THIS ENFORCES: the factory's rules apply only to projects the factory
created. The owner decided that explicitly — new projects only, existing code is
not retrofitted — and until this file existed nothing in the system could tell a
new project from an old one.

That gap was not theoretical. Measured on a copy of an older project: a
one-line edit to app/sales/scenarios.py let the lint hook delete an import that
looked unused there but is re-imported by app/help.py, which the web app and the
bot both load at startup. One line in, a dashboard that does not start out.

The marker is a file named `.factory` at the project root, written by build-spec
when it scaffolds a new app. No marker, no factory rules. Adding one to an
existing project is a deliberate retrofit decision, never a side effect.
"""

from __future__ import annotations

from pathlib import Path

MARKER = ".factory"


def factory_root(path: Path) -> Path | None:
    """The nearest ancestor holding `.factory`, or None."""
    p = Path(path).expanduser().resolve()
    for parent in (p, *p.parents) if p.is_dir() else p.parents:
        if (parent / MARKER).is_file():
            return parent
    return None


def is_factory_project(path: Path) -> bool:
    return factory_root(path) is not None
