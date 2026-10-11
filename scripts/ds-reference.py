#!/usr/bin/env python3
"""Generate REFERENCE.md from the system itself.

NEVER HAND-WRITE THE REFERENCE. That is not a style preference — it is the exact
mechanism by which a failing colour came to be documented as passing in this
workspace: the correction lived in one project's stylesheet header, the reference
said something else, and nothing could reach either. A reference that is derived
cannot disagree with what it describes.

So this reads the macro signatures out of ds.html, the token declarations out of
core.css, the slots out of the contract, and the rule list out of ds-lint.py, and
writes them into one file an agent can load instead of four.

Usage:  ds-reference.py [> foundation/design/REFERENCE.md]
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

DESIGN = Path(__file__).resolve().parent.parent / "foundation" / "design"
SCRIPTS = Path(__file__).resolve().parent

MACRO = re.compile(r"\{%\s*macro\s+([a-z_]+)\((.*?)\)\s*-?%\}", re.S)
SECTION = re.compile(r"/\*\s*═+\s*(.*?)\s*═+\s*\*/|/\* ── (.*?) ─+ \*/")
DECL = re.compile(r"^\s*(--[a-z0-9-]+)\s*:\s*([^;]+);(?:\s*/\*(.*?)\*/)?", re.M)
RULE = re.compile(r'\("(D\d+)",\s*"(\w+)",.*?\n?\s*"(.*?)"\),\n', re.S)


def macros() -> list[tuple[str, str]]:
    src = (DESIGN / "templates" / "ds.html").read_text(encoding="utf-8")
    out = []
    for m in MACRO.finditer(src):
        args = " ".join(m.group(2).split())
        # The comment block immediately above the macro is its one-line purpose.
        before = src[:m.start()].rstrip().rsplit("{#-", 1)
        note = ""
        if len(before) == 2:
            note = " ".join(before[1].split("-#}")[0].split())
            # The banner is "── 7. table — why it exists ──────". Everything up to
            # and including the first em-dash is decoration; the trailing box-drawing
            # run is decoration too. What is left is the one line worth publishing.
            note = re.sub(r"^─+\s*\d+\.\s*[a-z_]+\s*(?:—\s*)?", "", note)
            note = re.sub(r"\s*─+\s*$", "", note).strip()
        out.append((f"{m.group(1)}({args})", note))
    return out


def tokens() -> dict[str, list[tuple[str, str, str]]]:
    src = (DESIGN / "core.css").read_text(encoding="utf-8")
    groups: dict[str, list] = {}
    current = "scales"
    for line in src.splitlines():
        head = SECTION.search(line)
        if head:
            current = (head.group(1) or head.group(2) or current).strip()
            continue
        d = DECL.match(line)
        if d:
            groups.setdefault(current, []).append(
                (d.group(1), d.group(2).strip(), (d.group(3) or "").strip()))
    return groups


def contract_slots() -> dict[str, tuple[str, ...]]:
    src = (SCRIPTS / "ds-brand-check.py").read_text(encoding="utf-8")
    ns: dict = {}
    body = src.split("# ── The contract")[1].split("LIGHT_SURFACES")[0]
    exec("CONTRACT: dict = " + body.split("=", 1)[1].strip(), {}, ns)  # noqa: S102
    return ns["CONTRACT"]


def lint_rules() -> list[tuple[str, str]]:
    src = (SCRIPTS / "ds-lint.py").read_text(encoding="utf-8")
    block = src.split("RULES:", 1)[1].split("ALLOW =", 1)[0]
    out, seen = [], set()
    for rid, msg in re.findall(r'\("(D\d+)",\s*"\w+",.*?\),\n\s*"(.*?)"\),', block, re.S):
        first = " ".join(msg.split()).split(".")[0]
        if rid not in seen:
            seen.add(rid)
            out.append((rid, first))
    return out


def main() -> int:
    lines = [
        "# REFERENCE — generated, do not edit",
        "",
        "Regenerate with `scripts/ds-reference.py > foundation/design/REFERENCE.md`.",
        "",
        "Hand-editing this file is how a colour came to be documented as passing "
        "while it failed. Everything below is read out of the system itself: the "
        "macro signatures from `templates/ds.html`, the tokens from `core.css`, "
        "the slots from `ds-brand-check.py`, the rules from `ds-lint.py`.",
        "",
        "## The seventeen macros",
        "",
        "```jinja",
        '{% import "ds.html" as ds %}',
        "```",
        "",
    ]
    for sig, note in macros():
        lines.append(f"- `ds.{sig}`")
        if note:
            lines.append(f"  - {note[:400]}")
    lines += ["", "## The brand contract — every brand fills all of these", ""]
    for group, slots in contract_slots().items():
        lines.append(f"- **{group}** — " + ", ".join(f"`--{s}`" for s in slots))
    lines += ["", "## Tokens declared by core.css", ""]
    for group, decls in tokens().items():
        if not decls:
            continue
        lines.append(f"### {group}")
        lines.append("")
        lines.append("| token | value | note |")
        lines.append("|---|---|---|")
        for name, value, note in decls:
            v = value if len(value) < 60 else value[:57] + "…"
            lines.append(f"| `{name}` | `{v}` | {note} |")
        lines.append("")
    lines += ["## The rules the linter enforces", "",
              "Each has an escape hatch: `{# ds-allow: D<n> — why #}` on the line "
              "above, or the same in a CSS comment. Hatches are counted, not hidden.",
              ""]
    for rid, msg in lint_rules():
        lines.append(f"- **{rid}** — {msg}")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
