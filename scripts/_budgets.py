"""The two numbers an architecture promises: how long a click may take, and how big the code may grow.

the owner's words for the first factory app: "slow and heavy" and "far too big and complicated". Both were
written into its architecture as wishes — "simple", "light" — and nothing measured either, so the
app reached 27,500 lines of code and a folder editor that waited on the server for every chip
before anyone noticed. A wish no tool reads is a document; a number a tool reads is a gate.

    ## Budgets
    - **Click** — 800 ms: from pressing a button to the page settling, measured locally.
    - **Code** — 12,000 lines: the app's own code, without tests, comments or blank lines.

Read by architecture-check (both must be there), budget-check (code) and press-check (click).
"""

from __future__ import annotations

import io
import re
import tokenize
from pathlib import Path

_HEADING = re.compile(r"^#{2,4}\s+(.*)$", re.M)
_CLICK = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*(ms|milliseconds?|s|sec|seconds?)\b", re.I)
_CODE = re.compile(r"(\d[\d,]*)\s*(?:lines?)\b", re.I)

# Not the app's own code: tests, other people's code, and generated migrations. Everything else under
# app/ counts — dev-only mockup fixtures included, because they are shipped, read and maintained.
SKIP_DIRS = {"tests", "test", "alembic", "migrations", "vendor", "node_modules", ".venv", "venv",
             "__pycache__", ".git"}
SOURCE = {".py", ".html", ".jinja", ".j2", ".js", ".css"}


def section(text: str) -> str | None:
    marks = list(_HEADING.finditer(text))
    for i, m in enumerate(marks):
        if "budget" in m.group(1).lower():
            end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
            return text[m.end():end]
    return None


def read(project: Path) -> dict[str, int]:
    """{'click_ms': …, 'code_lines': …} — whichever the architecture states; empty if none."""
    doc = project / "ARCHITECTURE.md"
    body = section(doc.read_text(encoding="utf-8")) if doc.is_file() else None
    out: dict[str, int] = {}
    for line in (body or "").splitlines():
        low = line.lower()
        if "click" in low and "click_ms" not in out and (m := _CLICK.search(line)):
            value = float(m.group(1).replace(",", ""))
            out["click_ms"] = int(value if m.group(2).lower().startswith("m") else value * 1000)
        elif "code" in low and "code_lines" not in out and (m := _CODE.search(line)):
            out["code_lines"] = int(m.group(1).replace(",", ""))
    return out


def _python_code_lines(src: str) -> int:
    """Lines that carry code: not blank, not a comment, not a docstring."""
    lines = src.splitlines()
    doc: set[int] = set()
    prev = tokenize.NEWLINE
    try:
        for tok in tokenize.generate_tokens(io.StringIO(src).readline):
            starts = prev in (tokenize.NEWLINE, tokenize.NL, tokenize.INDENT, tokenize.DEDENT,
                              tokenize.ENCODING)
            if tok.type == tokenize.COMMENT or (tok.type == tokenize.STRING and starts):
                doc.update(range(tok.start[0], tok.end[0] + 1))
            if tok.type not in (tokenize.COMMENT, tokenize.NL):
                prev = tok.type
    except (tokenize.TokenError, IndentationError, SyntaxError):
        pass
    return sum(1 for n, ln in enumerate(lines, 1) if ln.strip() and n not in doc)


def count(project: Path) -> tuple[int, dict[str, int]]:
    """(total code lines, {top folder: lines}). Counts `app/` when it exists, else the project."""
    root = project / "app" if (project / "app").is_dir() else project
    total, parts = 0, {}
    for f in sorted(root.rglob("*")):
        rel = f.relative_to(root)
        if (not f.is_file() or f.suffix not in SOURCE or ".min." in f.name
                or any(p in SKIP_DIRS or p.startswith(".") for p in rel.parts[:-1])):
            continue
        text = f.read_text(encoding="utf-8", errors="replace")
        n = _python_code_lines(text) if f.suffix == ".py" else sum(1 for ln in text.splitlines() if ln.strip())
        total += n
        key = rel.parts[0] if len(rel.parts) > 1 else "(top level)"
        parts[key] = parts.get(key, 0) + n
    return total, parts
