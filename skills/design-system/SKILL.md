---
name: design-system
description: Build or change a screen, template, or stylesheet in a project that has a .factory file at its root (a new app scaffolded by build-spec). Never in an existing project that predates the factory, and never in a project whose locked design names its own prototype as the reference implementation — both keep their own design layer. Use when writing HTML/Jinja templates, CSS, a dashboard or panel UI, a mockup, or when a screen needs a table, form, button, status, empty state, modal or navigation. Also use when adding a brand, checking contrast, or when the design linter (D1–D9) reports a finding.
---

# The design system

**First, check the project root for a `.factory` file. If there is none, stop using this skill.**
The project predates the factory — follow its own templates, its own stylesheet and its own
verification suite, and do not bring `ds.html`, `core.css` or any rule below into it. That is a
decision already taken (new projects only), not a gap to fill.

**Second, check `DESIGN-V1.md`. If it names a prototype as the reference implementation, stop using
this skill too.** That project's look is its own prototype, carried into its own design layer
(`ARCHITECTURE.md → Frontend source`). On the first factory app the owner compared this system,
Tabler and the app's own prototype side by side on the same screen and chose the prototype; neither
generic base was usable as it stood. This system remains for factory apps that have no prototype.

**You do not write CSS. You call macros.** Seventeen of them cover every screen
this factory builds. If you are reaching for a `<div>` with a class you invented,
stop — either a macro exists, or this is the rare case that needs a new one, and
that is a decision, not an edit.

Read `${CLAUDE_PLUGIN_ROOT}/foundation/design/REFERENCE.md` for the signatures. It is
generated from the system, so it cannot be out of date.

## Before the first screen

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/ds-brand-check.py          # every brand fills 31 slots, all contrast obligations met
${CLAUDE_PLUGIN_ROOT}/scripts/ds-core-check.py           # core.css has no hex, no brand word, no physical direction
python3 -m pytest ${CLAUDE_PLUGIN_ROOT}/tests/ -q
```

Copy into the project: `core.css`, `ds.js`, the brand file(s), `ds.py`,
`ds_dev.py`, and `templates/ds.html` + `base.html`. Then:

```python
from ds import install
env = install(env, brand="slate", app_name="…", dev=settings.dev)
```

Set `dev=True` in development. It turns a wrong macro call into a raised
exception instead of a quiet marker, and turns a typo'd template variable into an
error instead of an empty string.

## Writing a screen

1. `{% extends "base.html" %}{% import "ds.html" as ds %}` — always both.
2. Build from macros. Never write `<table>`, `<button>`, `<input>`, or `style=`.
3. Every list gets an empty state. `ds.table()` takes `empty_title` and
   `empty_hint`; write real sentences, not "No data".
4. Money goes through `ds.amount()`. Dates go through `ds.datestamp()`. Both
   isolate direction — this is the only place left-to-right is correct.
5. Status goes through `ds.pill()`, messages through `ds.alert()`. The intent
   sets are closed: `ok / warn / danger` (+ `neutral` for pills).
6. Form actions go through `ds.actions(primary=…, secondary=[…])`. One primary.

## Colour

The only colour vocabulary is the 31 contract slots. There is no hex anywhere
outside a `brand-*.css` file, and no `--_private` primitive outside one either.

- text → `--ink`, `--ink-muted`, `--ink-accent`, `--ink-on-inverse`
- surfaces → `--surface-page / -raised / -card / -sunken / -inverse`
- the one action colour → `--action`, `--action-ink`, `--action-hover`
- state → `--ok / --warn / --danger`, each with a `-tint`
- **decor → `--rule`, `--accent`, `--accent-tint`. These never carry text.**
  If you want a tinted word, the slot is `--ink-accent`.

## Direction

Logical properties only: `margin-inline-start`, `inset-inline-end`,
`padding-block`, `text-align: start`. `margin-left` does not exist in this
system. Two exemptions exist, both marked in the source: the numeric islands
(`.amount`, `.datestamp`) and the select chevron's rotational geometry.

## Showing it to the user before building it

The mockup **is** the system — there is no separate design file, because a
second copy of a UI diverges by definition.

1. Write `app/design/mockups/<name>.html` extending `base.html`, using real
   macros against fixture data.
2. `ds_dev.mount(app, env, design_dir=…, brands=[…])` in dev only.
3. Send the user `/-/mockup/<name>`. They open it on their phone and see real text in their
   language, the real direction (left-to-right or right-to-left), the real brand at 375px.
4. On approval, POST `/-/mockup/<name>/approve` — it writes a dated
   `app/design/approved/<name>.md`.
5. Promote: swap the fixture for the real query. Nothing visual changes, because
   nothing visual was a fixture.

`/-/gallery` shows every macro. `/-/brands` shows the gallery under each brand
side by side — that page *is* the proof the contract is brand-independent.

**The honest limit:** this can only show what the system already knows how to
build. For a brand-new app whose component set is not yet decided, that is not
enough, and the answer is a one-time visual exploration *before* the macros are
fixed — not a per-screen mockup habit.

## Adding a brand

Copy an existing `brand-*.css`, fill all 31 slots, run `ds-brand-check.py`.

**The ink slots are defined by the ratio they must reach, not by the hue the
brand book names.** Expect to darken. One real brand's published warm grey reached
2.86:1 on its own cream page — the check refuses it, and it is right to: that
exact value shipped in two projects, in the second one painting every table
header. Walk the hue down until green. The book's original usually survives as
`--rule`, where it carries no text and is correct.

## When the linter fires

`ds-lint.py` reports D1–D9 on the file you just touched. Each message names the
construct to use instead. Fix the cause — do not reach for the hatch first.

The hatch exists and is legitimate:

```jinja
{# ds-allow: D2 — the embed sizes itself and ignores CSS #}
```

It is **counted**, not hidden. A rule with no hatch gets worked around
invisibly; one with a counted hatch gets worked around visibly.

## Adding a macro

A new macro is a change to the shared vocabulary of every future screen, so it
is a decision and not an edit:

1. Can two existing macros compose it? Then do that.
2. If not, say what rule its signature makes unrepresentable. A macro that only
   saves typing is a class, and this system has enough classes.
3. Write it, add its test to `${CLAUDE_PLUGIN_ROOT}/tests/test_ds.py` — the test checks the
   guarantee, not that it renders — and regenerate the reference:
   `${CLAUDE_PLUGIN_ROOT}/scripts/ds-reference.py > ${CLAUDE_PLUGIN_ROOT}/foundation/design/REFERENCE.md`.
4. The count in `test_the_macro_set_is_exactly_seventeen…` will fail. Updating
   that number is the moment to justify the addition, which is the point of it.

## What not to do

- Do not port a pre-factory project's design layer. It works and is defended
  by its own verification suite; two systems coexist deliberately.
- Do not add a CSS framework, a build step, or a component-token layer.
- Do not hand-write `REFERENCE.md`. Generate it.
- Do not make `ds.js` load-bearing. Delete it and every page must still work.
