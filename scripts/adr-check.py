#!/usr/bin/env python3
"""Check a just-written file against the project's accepted ADRs.

Reads a Claude Code PostToolUse payload on stdin, walks up from the touched
file to find the nearest `adr/` directory, and applies every `forbid` pattern
whose ADR governs that path.

WHY THIS EXISTS: an agent under ambiguity does not stall, it decides — and
decides differently each time. That is the measured cause of "a structural
change doesn't reach everywhere". An ADR writes the structure down; this makes
the writing enforceable instead of decorative.

WHY REGEX AND NOT A MODEL: this runs on every single write. The binding
constraint in this workspace is the usage quota, so the per-edit tier costs
zero model calls. The judgement-level half of an ADR lives in its `review`
key and is checked once per commit instead.

Only `status: accepted` ADRs are enforced. Only the fenced JSON block under
`## Enforcement` is parsed — the frontmatter is for people.

EXIT CODES: 1 warns, 2 blocks. Blocking since 2026-09-30 (see MODE_EXIT).
"""

from __future__ import annotations

import fnmatch
import json
import re
import sys
from pathlib import Path

MODE_EXIT = 2  # blocking since 2026-09-30. Two weeks of the first factory app showed a warning is read and
#   passed by: two test files crossed 500 lines under it. Exit 2 hands the finding back and the
#   agent fixes it before going on. Back to 1 only with a reason written here.
MAX_ADRS = 200

_STATUS = re.compile(r"^status:\s*(\S+)", re.MULTILINE)
_BLOCK = re.compile(r"##\s*Enforcement\s*\n+```json\s*\n(.*?)\n```", re.DOTALL)


def touched_file() -> Path | None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return None
    ti = payload.get("tool_input") or {}
    raw = ti.get("file_path") or ti.get("notebook_path")
    if not raw:
        return None
    p = Path(raw)
    return p if p.is_file() else None


def find_adr_dir(start: Path) -> Path | None:
    """Nearest ancestor holding an `adr/` directory — that ancestor is the project root."""
    for parent in start.resolve().parents:
        candidate = parent / "adr"
        if candidate.is_dir():
            return candidate
        if (parent / ".git").exists():
            return None  # reached the repo root without finding one
    return None


def load_rules(adr_dir: Path) -> list[tuple[str, dict]]:
    """(adr_name, enforcement_dict) for every accepted ADR that has a parseable block."""
    out: list[tuple[str, dict]] = []
    for f in sorted(adr_dir.glob("[0-9]*.md"))[:MAX_ADRS]:
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        status = _STATUS.search(text)
        if not status or status.group(1) != "accepted":
            continue
        block = _BLOCK.search(text)
        if not block:
            continue
        try:
            out.append((f.name, json.loads(block.group(1))))
        except json.JSONDecodeError as e:
            # A malformed ADR must be loud, not silently unenforced.
            print(f"ADR {f.name}: enforcement block is not valid JSON ({e}). "
                  f"It is being ignored, so its rule is NOT in force.", file=sys.stderr)
    return out


def _variants(glob: str) -> list[str]:
    """Every spelling of `glob` that should match, given fnmatch's flat `*`.

    fnmatch has no notion of `**`: its `*` already crosses `/`, but a literal
    `a/**/b.py` still demands the slash on both sides, so it fails to match
    `a/b.py` — zero intervening directories. Found by test: an ADR governing
    "app/**/*.py" silently enforced nothing on `app/pay.py`, which is most of
    an app. A rule that quietly matches nothing is worse than no rule.
    """
    out = {glob}
    if "/**/" in glob:
        out.add(glob.replace("/**/", "/"))
    if not glob.startswith(("*", "/")):
        out.add(f"*/{glob}")
    return list(out)


def matches(rel: str, globs: list[str]) -> bool:
    return any(
        fnmatch.fnmatch(rel, v) for g in globs for v in _variants(g)
    )


def code_lines(path: Path, lines: list[str]) -> list[str]:
    """The same lines with comments and docstrings blanked out — line numbers unchanged.

    Found on the first real project: ADR 0017 forbids `log.info(..., text=...)`, and it fired on
    app/core/logging.py, whose module docstring *explains that rule*. A checker that flags the file
    documenting a decision is the misfire class these rules are written to avoid. String literals
    that are not docstrings stay: ADR 0007's rule against an address in code has to see them.
    """
    if path.suffix != ".py":
        return lines
    import io
    import tokenize
    try:
        toks = list(tokenize.generate_tokens(io.StringIO("\n".join(lines) + "\n").readline))
    except (tokenize.TokenError, SyntaxError, IndentationError, ValueError):
        return lines
    out, prev = list(lines), tokenize.NEWLINE
    for tok in toks:
        starts_statement = prev in (tokenize.NEWLINE, tokenize.NL, tokenize.INDENT,
                                    tokenize.DEDENT, tokenize.ENCODING)
        if tok.type == tokenize.COMMENT or (tok.type == tokenize.STRING and starts_statement):
            (sr, sc), (er, ec) = tok.start, tok.end
            for row in range(sr, min(er, len(out)) + 1):
                i = row - 1
                if 0 <= i < len(out):
                    a = sc if row == sr else 0
                    b = ec if row == er else len(out[i])
                    out[i] = out[i][:a] + " " * max(0, b - a) + out[i][b:]
        if tok.type not in (tokenize.NL, tokenize.COMMENT):
            prev = tok.type
    return out


def statements(path: Path, scan: list[str]) -> list[tuple[int, str]]:
    """(first line number, text) per statement — a call written over several lines is one.

    Found on the first real project: ADR 0008's rule «an httpx client with no timeout» fired on
    `httpx.AsyncClient(` whose `timeout=` sat two lines further down. A rule judged one physical
    line at a time cannot see an argument on the next one, and a guard that misfires on correct
    code is a guard the agent learns to route around — which is why none could block until this
    was fixed. Non-Python files stay line by line.
    """
    if path.suffix != ".py":
        return list(enumerate(scan, 1))
    import io
    import tokenize
    try:
        toks = list(tokenize.generate_tokens(io.StringIO("\n".join(scan) + "\n").readline))
    except (tokenize.TokenError, SyntaxError, IndentationError, ValueError):
        return list(enumerate(scan, 1))
    out: list[tuple[int, str]] = []
    first: int | None = None
    for tok in toks:
        if tok.type in (tokenize.INDENT, tokenize.DEDENT, tokenize.NL, tokenize.COMMENT,
                        tokenize.ENCODING, tokenize.ENDMARKER):
            continue
        if first is None:
            first = tok.start[0]
        if tok.type == tokenize.NEWLINE:
            last = tok.start[0]
            rows = scan[first - 1 : last]
            out.append((first, " ".join([rows[0].rstrip()] + [r.strip() for r in rows[1:]])))
            first = None
    return out


def main() -> int:
    f = touched_file()
    if f is None:
        return 0
    adr_dir = find_adr_dir(f)
    if adr_dir is None:
        return 0  # project has no ADRs yet — nothing to enforce
    root = adr_dir.parent
    try:
        rel = str(f.resolve().relative_to(root))
    except ValueError:
        return 0

    try:
        lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return 0

    scan = code_lines(f, lines)
    units = statements(f, scan)
    findings: list[str] = []
    for name, rules in load_rules(adr_dir):
        if not matches(rel, rules.get("governs") or []):
            continue
        for rule in rules.get("forbid") or []:
            pattern, message = rule.get("pattern"), rule.get("message", "")
            if not pattern:
                continue
            where = rule.get("where")
            if where and not matches(rel, [where]):
                continue
            # `except`: globs where the pattern is legitimate — the settings module is the one
            # place allowed to read the environment. Without it such a rule could only be written
            # as a false positive, and a rule that cries wolf gets routed around.
            excluded = rule.get("except") or []
            if excluded and matches(rel, excluded):
                continue
            try:
                rx = re.compile(pattern)
            except re.error as e:
                print(f"ADR {name}: bad regex {pattern!r} ({e}) — rule NOT in force.",
                      file=sys.stderr)
                continue
            for i, line in units:
                if rx.search(line):
                    findings.append(f"  {rel}:{i} — {message}  [{name}]")
                    break  # one hit per rule is enough to make the point

    if not findings:
        return 0

    print("This change contradicts a recorded architecture decision:\n"
          + "\n".join(findings)
          + f"\n\nThe decisions live in {adr_dir}. If the decision is now wrong, supersede it "
            f"with a new ADR — do not work around it silently.", file=sys.stderr)
    return MODE_EXIT


if __name__ == "__main__":
    sys.exit(main())
