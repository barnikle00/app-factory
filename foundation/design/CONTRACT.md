# The brand contract

A **closed set of 31 slots** that every brand file must fill, and the only public colour
vocabulary in the system. `core.css` and every template reference these names and nothing else.

**The authority is `scripts/ds-brand-check.py`, not this file.** The slot list and the
contrast obligations live there as data, because a hand-maintained second copy of a list is how
the prior art ended up documenting a colour as passing while it failed — the correction lived in
one project's stylesheet header where nothing could reach it. This document explains the shape;
the script decides.

Run it:

```bash
scripts/ds-brand-check.py
```

## The four layers

| Layer | Lives in | Rule |
|---|---|---|
| **L0** brand primitives — `--_pine`, `--_navy` | `brand-*.css` only | `var(--_` appearing anywhere else is an error. This one grep is the whole multi-brand guarantee |
| **L1** the contract — the 31 slots | `brand-*.css` only | Every brand fills every slot. Nothing else is a public colour name |
| **L2** core scales — spacing, radius, type, elevation, and every component rule | `core.css` | **Zero hex values.** Zero `--_` references. Zero brand words |
| **L3** six documented knobs | `core.css` | Not a full component-token layer — that triples the vocabulary an agent must hold and buys theming a two-brand system will never spend |

## The groups

- **surfaces** (5) — page, raised, card, sunken, inverse
- **ink** (4) — ink, muted, on-inverse, accent
- **action** (3) — action, its ink, its hover
- **intent** (6) — warn, danger, ok, each with a tint
- **decor** (3) — rule, accent, accent-tint. **Never text**, structurally: the linter rejects
  `color: var(--accent)` and the brand check fails if one becomes readable enough to tempt
- **chrome** (4) — bar, its ink, glass, glass edge
- **type** (5) — display face, body face, latin face, the size below which display becomes
  texture, and the body line-height floor. These are facts about the *typeface*, which is why
  they sit in the brand layer and not in core
- **depth** (1) — `--shadow-rgb`, from which core composes `--shadow-1..3`. Warm, because a grey
  shadow on a cream page reads as dirt

## The idea that makes this work

**The ink slots are defined by the ratio they must achieve, not by the hue the brand book
names.** So filling in a brand *is* the accessibility audit, done once, at authoring time — and
the human's job is "darken it until `ds-brand-check` is green."

This is not theoretical. Writing a real brand's file with its identity document's own warm grey
produced an immediate failure at **2.86:1** against the cream page. That exact value shipped
unnoticed in two separate projects, in the second one painting every table header. The passing
value is the same hue walked down until it clears all four surfaces; the book's original
survives as `--rule`, where it carries no text and is correct.

## Order of work

**Write the second brand first.** The first example brand was authored before the second
deliberately: a contract proved against one brand is not proved at all — the first brand's
assumptions hide inside it and surface only when a second arrives, by which time core has grown
around them. The measured prior art is exactly that failure: 179 of its colour references name a
brand colour against 113 naming a role, so it cannot be re-branded without a fork.
