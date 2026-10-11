#!/usr/bin/env python3
"""Verify a brand file against the design system's contract.

Usage:  ds-brand-check.py [brand-file.css ...]      (default: every brand-*.css)

Checks two things, and they are the whole reason the contract exists:

1. COMPLETENESS — every slot in the contract is filled. A missing slot is a
   blank page region at runtime, discovered by a person, in production.

2. CONTRAST — the ink slots are defined by the RATIO they must achieve, not by
   the hue their brand book happens to name. So filling in a brand IS the
   accessibility audit, done once, at authoring time.

   This is the fix for a measured failure: one brand's own published secondary
   grey fails AA against its own surfaces, and shipped that way in two separate
   projects — in the second one painting every table header at 4.43:1, because
   the correction lived in the first project's stylesheet header where nothing
   could reach it.

Exit 0 when every brand passes, 1 otherwise.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# ── The contract: the closed set of slots every brand must fill ──────────────
CONTRACT: dict[str, tuple[str, ...]] = {
    "surfaces": ("surface-page", "surface-raised", "surface-card",
                 "surface-sunken", "surface-inverse"),
    "ink":      ("ink", "ink-muted", "ink-on-inverse", "ink-accent"),
    "action":   ("action", "action-ink", "action-hover"),
    "intent":   ("warn", "warn-tint", "danger", "danger-tint", "ok", "ok-tint"),
    "decor":    ("rule", "accent", "accent-tint"),
    "chrome":   ("chrome", "chrome-ink", "glass", "glass-edge"),
    "type":     ("font-display", "font-body", "font-latin", "display-min", "lh-text"),
    "depth":    ("shadow-rgb",),
}
ALL_SLOTS = tuple(s for group in CONTRACT.values() for s in group)

LIGHT_SURFACES = ("surface-page", "surface-raised", "surface-card", "surface-sunken")

# (foreground slot, background slots, required ratio, why)
OBLIGATIONS: tuple[tuple[str, tuple[str, ...], float, str], ...] = (
    ("ink",            LIGHT_SURFACES,      7.0, "body text, on every light surface"),
    ("ink-muted",      LIGHT_SURFACES,      4.5, "secondary text — the slot brands get wrong"),
    ("ink-accent",     LIGHT_SURFACES,      4.5, "the one tinted text tone"),
    ("ink-on-inverse", ("surface-inverse",), 7.0, "text on the dark surface"),
    ("action-ink",     ("action",),          4.5, "the label inside a primary button"),
    ("chrome-ink",     ("chrome",),          4.5, "text in the app bar"),
    # An intent colour is always eventually used as text on its own tint —
    # a status pill, a validation message. Checking it here costs nothing and
    # is the difference between "the red one" being readable and merely visible.
    ("warn",           ("warn-tint",),       4.5, "warning text on its own tint"),
    ("danger",         ("danger-tint",),     4.5, "danger text on its own tint"),
    ("ok",             ("ok-tint",),         4.5, "success text on its own tint"),
)

# These carry no text, ever. The linter also rejects `color: var(--accent)`.
DECOR_ONLY = ("rule", "accent", "accent-tint")

_DECL = re.compile(r"--([a-z0-9-]+)\s*:\s*([^;]+);")
_HEX = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


def _channel(c: float) -> float:
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def luminance(hex_colour: str) -> float:
    h = hex_colour.lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)


def ratio(a: str, b: str) -> float:
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def parse(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    return {m.group(1): m.group(2).strip() for m in _DECL.finditer(text)}


def check(path: Path) -> list[str]:
    slots = parse(path)
    problems: list[str] = []

    missing = [s for s in ALL_SLOTS if s not in slots]
    if missing:
        problems.append(
            f"missing {len(missing)} contract slot(s): {', '.join('--' + m for m in missing)}"
        )

    private = [s for s in slots if s.startswith("_")]
    extra = [s for s in slots if s not in ALL_SLOTS and not s.startswith("_")]
    if extra:
        problems.append(
            f"declares {len(extra)} slot(s) outside the contract without a leading "
            f"underscore: {', '.join('--' + e for e in extra)}. A brand-private "
            f"primitive is named --_name so the linter can keep it out of core.css."
        )

    for fg, bgs, need, why in OBLIGATIONS:
        fg_val = slots.get(fg)
        if not fg_val or not _HEX.match(fg_val):
            continue  # missing is already reported; non-hex is not comparable
        for bg in bgs:
            bg_val = slots.get(bg)
            if not bg_val or not _HEX.match(bg_val):
                continue
            got = ratio(fg_val, bg_val)
            if got + 1e-9 < need:
                problems.append(
                    f"--{fg} ({fg_val}) on --{bg} ({bg_val}) is {got:.2f}:1, "
                    f"needs {need}:1 — {why}. Darken --{fg} until it passes; "
                    f"the brand book's own value is a starting point, not the answer."
                )

    for slot in DECOR_ONLY:
        val = slots.get(slot)
        if val and _HEX.match(val):
            worst = max(ratio(val, slots[s]) for s in LIGHT_SURFACES
                        if slots.get(s) and _HEX.match(slots[s]))
            if worst >= 4.5:
                problems.append(
                    f"--{slot} ({val}) reaches {worst:.2f}:1 — it is readable enough to "
                    f"tempt someone into using it as text, which both identity documents "
                    f"forbid. Keep decor visibly non-textual, or promote it to --ink-accent."
                )

    if private:
        print(f"  {path.name}: {len(private)} brand-private primitive(s) — fine, "
              f"they stay in this file")
    return problems


def main(argv: list[str]) -> int:
    here = Path(__file__).resolve().parent.parent / "foundation" / "design"
    files = [Path(a) for a in argv[1:]] or sorted(here.glob("brand-*.css"))
    if not files:
        print(f"no brand files found in {here}", file=sys.stderr)
        return 1

    failed = False
    for f in files:
        if not f.is_file():
            print(f"FAIL {f}: not found", file=sys.stderr)
            failed = True
            continue
        problems = check(f)
        if problems:
            failed = True
            print(f"FAIL {f.name}", file=sys.stderr)
            for p in problems:
                print(f"  - {p}", file=sys.stderr)
        else:
            print(f"PASS {f.name}: {len(ALL_SLOTS)} slots filled, "
                  f"{len(OBLIGATIONS)} contrast obligations met")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
