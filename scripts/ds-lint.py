#!/usr/bin/env python3
"""Tier 1 of the design system's enforcement: textual, single-file, per-edit.

Usage:  ds-lint.py <file> [...]        — or as a PostToolUse hook, reading the
                                         tool payload on stdin.

TIER 1 IS DELIBERATELY NARROW. It only carries rules that can be decided from one
file's text with no judgement at all, because a blocking hook that misfires
teaches an agent to route around it — and an agent that has learned to route
around one hook has learned to route around all of them. Everything computed,
cross-file, or arguable belongs to Tier 2 (verify_design.py), which runs per
phase and is allowed to be slow and to think.

Every rule has a numbered escape hatch:  {# ds-allow: D2 — why #}  on the line
above, or `/* ds-allow: D2 — why */` in CSS. A rule with no hatch gets worked
around invisibly; one with a counted hatch gets worked around visibly, and
verify_design.py counts them.

Exit: MODE_EXIT on findings (1 = warn, 2 = block), 0 when clean.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from _project import is_factory_project

MODE_EXIT = 2  # blocking since 2026-09-30. Two weeks of the first factory app showed a warning is read and
#   passed by: two test files crossed 500 lines under it. Exit 2 hands the finding back and the
#   agent fixes it before going on. Back to 1 only with a reason written here.

# The design system's own files ARE the exception to most of these rules — they
# are where the colours and the component rules legitimately live.
SYSTEM_FILES = {"core.css", "ds.html", "base.html", "ds.js"}
SYSTEM_DIR_MARKER = "foundation/design"

TEMPLATE_SUFFIXES = {".html", ".jinja", ".jinja2", ".j2"}
STYLE_SUFFIXES = {".css"}

# (id, applies-to, pattern, message)
RULES: tuple[tuple[str, str, re.Pattern[str], str], ...] = (
    ("D1", "both", re.compile(r"#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?\b(?![\"']?\s*[;,)]?\s*/\*\s*ds)"),
     "a colour literal. Every colour is a contract slot — var(--ink), var(--action), "
     "var(--danger). A hex here cannot follow the brand, which is the whole point"),

    ("D1", "both", re.compile(r"\b(?:rgb|hsl)a?\s*\(\s*\d"),
     "a colour literal. Use a contract slot; if you need transparency, the system "
     "composes it from --shadow-rgb or --glass"),

    ("D2", "template", re.compile(r"\sstyle\s*=\s*[\"']"),
     "an inline style. Every visual decision lives in core.css. Content-keyed "
     "widths are classes: width=\"amount\" on the macro, not a CSS declaration"),

    ("D3", "both", re.compile(r"\b(?:margin|padding|border|inset)-(?:left|right)\b"
                              r"|\btext-align\s*:\s*(?:left|right)\b"
                              r"|\bfloat\s*:\s*(?:left|right)\b"),
     "a physical direction in an RTL application. Use the logical form — "
     "margin-inline-start, inset-inline-end, text-align: start"),

    ("D4", "both", re.compile(r"(?<![-\w])color\s*:\s*var\(\s*--(?:accent|rule)\b"),
     "decor used as text. --accent and --rule are structurally incapable of "
     "carrying text: both identity documents forbid it, and the brand check fails "
     "any brand whose accent grows readable enough to tempt. Use --ink-accent"),

    ("D5", "template", re.compile(r"<table\b"),
     "a hand-written <table>. Use ds.table(), which writes its own scroll "
     "container — without it a phone scrolls the page body sideways, which is the "
     "most common RTL dashboard failure and the one nobody catches on a laptop"),

    ("D6", "tag", re.compile(r"<(?:button|input)\b"),
     "an interactive element with no data-tap. The 44px touch floor selects on "
     "that attribute. Use ds.button() / ds.field() rather than adding it by hand"),

    ("D7", "template", re.compile(r"user-scalable\s*=\s*no|maximum-scale\s*=\s*1"),
     "zoom disabled. On a Persian dashboard that is an accessibility failure, not "
     "a design decision. base.html already sets the correct viewport"),

    ("D8", "both", re.compile(r"linear-gradient|radial-gradient"),
     "a gradient. Neither identity document has one, and the other Jinja app in "
     "this workspace acquired three by drift"),

    ("D9", "both", re.compile(r"font-family\s*:(?![^;]*var\(--font-)"),
     "a typeface named outside the brand layer. The face is a brand fact: use "
     "var(--font-body), var(--font-display) or var(--font-latin)"),
)

ALLOW = re.compile(r"ds-allow:\s*(D\d+)")


def _skip(path: Path) -> bool:
    return path.name in SYSTEM_FILES or SYSTEM_DIR_MARKER in path.as_posix()


def _applies(scope: str, path: Path) -> bool:
    if scope == "both":
        return True
    if scope in ("template", "tag"):
        return path.suffix.lower() in TEMPLATE_SUFFIXES
    return path.suffix.lower() in STYLE_SUFFIXES


_HIDDEN = re.compile(r"type\s*=\s*[\"']hidden")


def _tag_text(lines: list[str], start: int) -> str:
    """The whole opening tag from `start`, however many lines it spans.

    Reading one line at a time is what makes an attribute-presence rule lie: the
    attribute is frequently on the next line. Capped at 12 lines so a file with an
    unclosed tag cannot turn this into a whole-file scan."""
    chunk = []
    for line in lines[start - 1:start + 11]:
        chunk.append(line)
        if ">" in line:
            break
    return " ".join(chunk)


def check(path: Path) -> list[str]:
    if _skip(path) or path.suffix.lower() not in (TEMPLATE_SUFFIXES | STYLE_SUFFIXES):
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    out: list[str] = []
    for n, line in enumerate(lines, start=1):
        # An escape hatch on this line or the one above it.
        context = line + ("\n" + lines[n - 2] if n >= 2 else "")
        allowed = set(ALLOW.findall(context))
        for rid, scope, pattern, message in RULES:
            if rid in allowed or not _applies(scope, path):
                continue
            m = pattern.search(line)
            if m and scope == "tag":
                tag = _tag_text(lines, n)
                if "data-tap" in tag or _HIDDEN.search(tag):
                    continue
            if m:
                out.append(f"{path}:{n}: [{rid}] {m.group(0).strip()!r} — {message}")
                break   # one finding per line: a cascade is noise, not information
    return out


def _paths_from_hook_payload() -> list[Path]:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return []
    ti = data.get("tool_input") or {}
    raw = ti.get("file_path") or ti.get("notebook_path")
    return [Path(raw)] if raw else []


def main(argv: list[str]) -> int:
    # --any checks a file outside a factory project, by hand, on purpose. As a
    # hook it never does: an existing project has no ds.html, so "use ds.table()"
    # is not a repair instruction there — it is an instruction to break the page.
    force = "--any" in argv
    args = [a for a in argv[1:] if a != "--any"]
    paths = [Path(a) for a in args] or _paths_from_hook_payload()
    if not force:
        paths = [p for p in paths if is_factory_project(p)]
    findings: list[str] = []
    for p in paths:
        if p.is_file():
            findings.extend(check(p))
    if not findings:
        return 0
    print("design-system findings (Tier 1):", file=sys.stderr)
    for f in findings:
        print(f"  {f}", file=sys.stderr)
    print("\n  Each has an escape hatch if it is genuinely right: put "
          "{# ds-allow: D<n> — why #} (or /* ds-allow: D<n> — why */) on the line "
          "above. It is counted, not hidden.", file=sys.stderr)
    return MODE_EXIT


if __name__ == "__main__":
    sys.exit(main(sys.argv))
