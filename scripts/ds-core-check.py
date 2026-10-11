#!/usr/bin/env python3
"""Verify core.css obeys the rules that make a second brand a file swap.

Usage:  ds-core-check.py [core.css]

Five rules, each one a failure that has already shipped in this workspace:

1. NO HEX. A literal colour in core.css is invisible to every brand file, so it
   looks right under the brand it was written against and wrong under the next.

2. NO BRAND-PRIVATE REFERENCE. `var(--_pine)` outside a brand file is the whole
   multi-brand guarantee, expressed as one grep.

3. NO BRAND WORD, even in a class name. The prior art's layer names a brand
   colour 179 times against 113 naming a role — which is why it cannot be
   re-branded without a fork.

4. NO PHYSICAL DIRECTION. `margin-left` in an RTL application is how the other
   Jinja app in this workspace ended up with its sidebar pinned to the wrong
   side. Two constructs are exempt and must say so — see EXEMPT below.

5. EVERY SLOT EXISTS. `var(--ink-mutted)` renders nothing at all: no error, no
   warning, just uncoloured text nobody notices until a person sees the page.
   Every custom property core.css reads must be one it declares itself or one of
   the 31 slots in the contract.

Comments are stripped first — rule 4's own explanation contains the word
`margin-left`, and a checker that fails on its own documentation gets disabled.

Exit 0 when clean, 1 otherwise.
"""

from __future__ import annotations

import difflib
import re
import sys
from pathlib import Path

# The slot list has ONE authority — ds-brand-check.py — and is read from it at
# runtime by _contract_slots() below. A second hand-maintained copy of a list is
# precisely how the prior art came to document a colour as passing while it failed.

BRAND_WORDS = (
    "pine", "navy", "cream", "amber", "bronze", "sand", "charcoal", "brown", "brass", "stone",
    "slate", "forest", "graphite", "steel", "mist", "paper",
)

PHYSICAL = re.compile(
    r"\b(?:margin|padding|border|inset|scroll-margin|scroll-padding)-(?:left|right)\b"
    r"|(?<![\w-])(?:left|right)\s*:"
    r"|\btext-align\s*:\s*(?:left|right)\b"
    r"|\bfloat\s*:\s*(?:left|right)\b"
    r"|\bborder-(?:top|bottom)-(?:left|right)-radius\b"
)

# The two constructs that are allowed to be physical, and the marker each must
# carry. A rule with no escape hatch gets worked around invisibly; one with a
# named, counted hatch gets worked around visibly.
EXEMPT_MARKER = "ds-allow: physical"

HEX = re.compile(r"#[0-9a-fA-F]{3,8}\b")
# D4, restated here because core.css is exempt from the template linter — it is
# where colour legitimately lives. That exemption is what let a decor slot get
# painted as a breadcrumb separator at 3.36:1, found only by measuring the page.
DECOR_AS_TEXT = re.compile(r"(?<![-\w])color\s*:\s*var\(\s*--(?:accent|rule)\b")
PRIVATE_REF = re.compile(r"var\(\s*--_")
VAR_READ = re.compile(r"var\(\s*(--[a-z0-9-]+)")
VAR_DECL = re.compile(r"^\s*(--[a-z0-9-]+)\s*:", re.M)
COMMENT = re.compile(r"/\*.*?\*/", re.S)


def _contract_slots() -> frozenset[str]:
    """Read the slot names out of ds-brand-check.py, the authority on them."""
    src = (Path(__file__).resolve().parent / "ds-brand-check.py").read_text(encoding="utf-8")
    ns: dict = {}
    body = src.split("# ── The contract")[1].split("LIGHT_SURFACES")[0]
    exec("CONTRACT: dict = " + body.split("=", 1)[1].strip().rstrip(), {}, ns)  # noqa: S102
    return frozenset(f"--{s}" for group in ns["CONTRACT"].values() for s in group)


def strip_comments(text: str) -> list[tuple[int, str]]:
    """Blank out comments but keep line numbers intact."""
    blanked = COMMENT.sub(lambda m: "\n" * m.group(0).count("\n"), text)
    return list(enumerate(blanked.splitlines(), start=1))


def check(path: Path) -> list[str]:
    raw = path.read_text(encoding="utf-8")
    lines = strip_comments(raw)
    problems: list[str] = []

    for n, line in lines:
        for m in HEX.finditer(line):
            problems.append(f"{n}: hex literal {m.group(0)} — every colour must be a "
                            f"contract slot, or it cannot follow the brand")
        if PRIVATE_REF.search(line):
            problems.append(f"{n}: reads a brand-private primitive (--_…). Those live "
                            f"only in brand-*.css; use the contract slot instead")
        for w in BRAND_WORDS:
            if re.search(rf"(?<![a-z]){w}(?![a-z])", line, re.I):
                problems.append(f"{n}: names the brand ('{w}'). core.css must be "
                                f"brand-blind — this is the line that forces a fork")
        # The marker is accepted anywhere in the six lines above as well as on the
        # line itself. Requiring it on the same line forces the justification to be
        # a trailing fragment, and the whole value of an escape hatch is that the
        # reason is readable — the chevron's reason takes five lines to state.
        _raw = raw.splitlines()
        _window = "\n".join(_raw[max(0, n - 7):n])
        if DECOR_AS_TEXT.search(line):
            problems.append(f"{n}: paints a decor slot as text. --accent and --rule "
                            f"are structurally incapable of carrying a glyph — both "
                            f"identity documents forbid it and the brand check keeps "
                            f"them below 4.5:1 on purpose. Use --ink-muted or "
                            f"--ink-accent")
        if PHYSICAL.search(line) and EXEMPT_MARKER not in _window:
            problems.append(f"{n}: physical direction — {PHYSICAL.search(line).group(0)!r}. "
                            f"Use the logical form (margin-inline-start, inset-inline-end, "
                            f"text-align: start). If it is genuinely one of the exempt "
                            f"constructs, mark the line /* {EXEMPT_MARKER} — why */")

    declared = set(VAR_DECL.findall(raw))
    contract = _contract_slots()
    known = declared | contract
    seen: set[str] = set()
    for n, line in lines:
        for name in VAR_READ.findall(line):
            if name not in known and name not in seen:
                seen.add(name)
                # difflib, not a prefix match: the failing name is almost always a
                # typo of a real slot, and the whole value of this check is naming
                # the right one. A prefix match on --ink- suggests --ink-accent for
                # --ink-mutted, which sends the reader to the wrong slot.
                near = difflib.get_close_matches(name, known, n=1, cutoff=0.75)
                hint = f" Did you mean {near[0]}?" if near else ""
                problems.append(f"{n}: reads {name}, which nothing declares. It will "
                                f"render as nothing at all — no error, no warning.{hint}")

    unused = contract - set(VAR_READ.findall(raw))
    if unused:
        problems.append(
            f"note: {len(unused)} contract slot(s) are never used by core.css: "
            f"{', '.join(sorted(unused))}. Every brand is required to fill them, so a "
            f"slot nothing reads is a tax on every future brand — use it or retire it."
        )
    return problems


def main(argv: list[str]) -> int:
    here = Path(__file__).resolve().parent.parent / "foundation" / "design"
    files = [Path(a) for a in argv[1:]] or [here / "core.css"]
    failed = False
    for f in files:
        if not f.is_file():
            print(f"FAIL {f}: not found", file=sys.stderr)
            failed = True
            continue
        problems = check(f)
        hard = [p for p in problems if not p.startswith("note:")]
        if hard:
            failed = True
        if problems:
            print(f"{'FAIL' if hard else 'PASS (with notes)'} {f.name}",
                  file=sys.stderr if hard else sys.stdout)
            for p in problems:
                print(f"  - {p}", file=sys.stderr if hard else sys.stdout)
        else:
            print(f"PASS {f.name}: no hex, no brand word, no physical direction, "
                  f"every slot declared")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
