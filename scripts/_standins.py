"""Stand-ins: code a phase leaves in place of something a later phase must build.

A stand-in is fine — phases are built in order, and phase 9 may need an answer that phase 12 will
compute. What is not fine is a stand-in nobody comes back for. the first factory app's final check found
several, each the root of a defect a person would meet: `SequencesOnly()` answering «no folder uses
this detector» long after folders existed, `NoConditionsYet` leaving every «where used» empty,
`SYSTEM_FOLDERS_NOW = 0` printing zero system folders. Each was the right placeholder when written;
each was marked done by a later phase that never replaced it.

So a stand-in carries its phase, in a comment, in any language:

    # STAND-IN(phase 12): the real folder-use query replaces this
    {# STAND-IN(phase 15): the version history table #}

and the commit lock refuses a commit while a stand-in names a phase the register says is done.
"""

from __future__ import annotations

import re
from pathlib import Path

# Upper case, followed by «(» or «:» — so prose that merely mentions a stand-in is not one.
MARK = re.compile(r"STAND-IN(?:\(\s*phase\s*0*(\d+)\s*\)\s*:?|\s*:|\()\s*(.*)")
DONE = re.compile(r"^\s*-\s*\[[xX]\]\s*0*(\d+)\b", re.M)
ANY = re.compile(r"^\s*-\s*\[[ xX]\]\s*0*(\d+)\b", re.M)
SKIP = {".git", ".venv", "venv", "node_modules", "__pycache__", "tests", "test", "prototype", "design"}
SUFFIXES = {".py", ".html", ".jinja", ".j2", ".js", ".css", ".sql", ".toml", ".yml", ".yaml"}


def scan(project: Path) -> list[tuple[str, int, int | None, str]]:
    """Every stand-in marker: (file, line, phase or None, what replaces it)."""
    out = []
    for f in sorted(project.rglob("*")):
        rel = f.relative_to(project)
        if not f.is_file() or f.suffix not in SUFFIXES or any(p in SKIP for p in rel.parts[:-1]):
            continue
        for n, line in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            m = MARK.search(line)
            if m:
                what = re.sub(r"\s*(#}|-->|\*/)\s*$", "", m.group(2)).strip()
                out.append((str(rel), n, int(m.group(1)) if m.group(1) else None, what))
    return out


def problems(project: Path) -> list[str]:
    progress = project / "PROGRESS.md"
    text = progress.read_text(encoding="utf-8") if progress.is_file() else ""
    done = {int(n) for n in DONE.findall(text)}
    known = {int(n) for n in ANY.findall(text)}
    out = []
    for rel, n, phase, what in scan(project):
        where = f"{rel}:{n}"
        if phase is None:
            out.append(f"{where} is a stand-in that names no phase — write STAND-IN(phase NN): "
                       f"<what replaces it>, so somebody comes back for it")
        elif phase in done:
            out.append(f"{where} is a stand-in for phase {phase}, and PROGRESS.md says phase {phase} is "
                       f"done — build what it stands in for ({what or 'unstated'}), or reopen the phase")
        elif known and phase not in known:
            out.append(f"{where} is a stand-in for phase {phase}, which PROGRESS.md does not have")
    return out
