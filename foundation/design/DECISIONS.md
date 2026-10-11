# DECISIONS — why the design system is shaped this way

Four artifacts, four jobs, and this is the third:

| Artifact | Job | Never |
|---|---|---|
| `.claude/skills/design-system/SKILL.md` | What to do, imperatively | Contains history |
| `REFERENCE.md` | What exists — signatures, tokens, slots, rules | Hand-written |
| **`DECISIONS.md`** (this file) | **Why, and what was rejected** | Tells you what to type |
| `<app>/DESIGN.md` | What *this one app* decided | Repeats any of the above |

The prior art collapsed all four into one `ARCHITECTURE.md` section that is ~90%
chronology, so an agent building screen #40 has to reverse-engineer the rules out
of a history. That is the failure this split exists to prevent.

---

## The finding that started it

The existing design layer was measured, not read:

| | |
|---|---|
| Colour references naming a **brand** colour vs a **role** | **179 vs 113** |
| Spacing declarations using a literal instead of the published scale | **154 of 203**, across 37 ad-hoc values |
| Classes defined | **216**, ~175 of them hand-typed with no macro emitting them |

It is not a bad stylesheet. It is an **unexportable** one — which is a different
and more useful finding, because it says the defect is structural rather than a
matter of care. The proof is the workspace's other Jinja application, which
re-learned every lesson from zero and failed differently: `#fff`, gradients,
Tahoma, a sidebar pinned to the physical **left** in an RTL app, and a secondary
grey at **4.43:1** painting every table header.

Nothing travelled between them, because nothing was *shaped* to travel.

---

## Why the brand contract is defined by contrast ratio, not by hue

`--ink-muted` is not "the brand's warm grey". It is "the tone that reaches 4.5:1
on all four light surfaces". Filling in a brand therefore **is** the accessibility
audit, performed once, at authoring time, by a checker rather than by a person
remembering.

This is not theoretical. Writing a real brand's file with its identity document's
own published grey failed immediately at **2.86:1**. That exact value shipped
unnoticed in two separate projects. The passing value is the same hue walked down
until green; the book's original survives as `--rule`, where it carries no text
and is correct.

**The corollary that matters:** a brand book is a starting point, not an answer.

---

## Why the second example brand was written before the first was relied on

A contract proved against one brand is not proved at all. The first brand's
assumptions hide inside the contract and surface only when a second arrives — by
which time the core stylesheet has grown around them.

The first real brand file was written deliberately against a brand the system was *not* built
for. The cost was a day. The alternative cost is a fork, which is what the
measured prior art is.

**The evidence it worked:** `/-/gallery` rendered under both brands produces
8,694 and 8,682 bytes — the difference is the brand's name in the page. Same
core.css, same macros, zero conditionals.

---

## Why seventeen macros instead of 216 classes

The rules an agent must not break are encoded in **signatures**, not in prose
beside them:

- `actions(primary=…, secondary=[…])` has one primary slot, so "at most one
  primary per block" is *unrepresentable* rather than reviewed.
- `table()` writes its own `.table-scroll`, so a phone cannot scroll the page
  body sideways — the most common RTL dashboard failure, and the one nobody
  catches on a laptop. Measured after: `scrollWidth == clientWidth == 375`.
- `select()` writes its own wrapper, because a `<select>` cannot carry the
  chevron and `background-position` has no logical form.
- `button()` validates `intent` against a closed set: raising in dev, rendering a
  visible marker in production. A misuse on one screen must not take a live
  dashboard down, and must not be invisible either.
- Every interactive element carries `data-tap`, so the 44px floor selects on an
  attribute instead of a hand-maintained list of class names that rots the first
  time a macro is added.

And the context argument: 216 class names is a vocabulary an agent must hold to
write one page. Seventeen signatures is not.

---

## Two rules the system's own components broke first

Both were found by looking, not by reasoning, and both are recorded because the
general lesson is larger than either bug.

1. **Three macros reached for `style=`** to set content-keyed widths — while the
   linter's D2 rejects `style=` outright. A rule the system's own components
   break is not a rule; it is an exception waiting to become the hole everything
   else goes through. Widths became classes.

2. **The select chevron pointed left.** It was built from `border-inline-end` +
   `border-block-end` rotated 45°, which is the logical form, correctly applied —
   and wrong, because a chevron is *rotational geometry*, not text direction. In
   RTL the logical form flipped the shape. It now uses the physical borders and
   carries the `ds-allow: physical` marker with the reason.

**The general lesson:** "use logical properties" is a rule about *direction of
reading*, and applying it to *shape* produces confidently-wrong output. Only
looking at the rendered page catches that class of error.

---

## What was rejected, and why

**Open Props.** ~2,000 properties optimised for giving a *designer* choices; our
consumer is an agent that must not be able to choose wrong. Its greys are neutral
where both brands forbid neutral, its spacing is not two-sizes-apart, its shadows
are neutral (a grey shadow on cream reads as dirt), and it offers nothing for RTL
or right-to-left type. What we would buy is ~40 lines of numbers, at the cost of a large
wrong vocabulary in every agent's context. **Trade-off accepted:** we hand-write
the easing curves and the fluid-type formula.

**Figma, and hand-written HTML mockups.** Both create a second source of truth
about a UI that also exists in code, which diverges by definition. Measured here:
ten of one project's twelve mockups were copied byte-identically into a second
project, tokens redeclared per file, 287 inline styles — and both are now wrong
about what ships. `/-/mockup/<name>` renders the real macros against fixture data
instead, so an approved mockup is a screen that is already 80% built.

**A full component-token layer (L3 per component).** It triples the vocabulary an
agent must hold and buys theming a two-brand system will never spend. Six
documented knobs instead.

**Porting `an older project`.** Its layer works and is defended by a
1,298-line verification suite that took seventy phases of real defects to write.
Two systems coexist — accepted. The mitigation is that `ds`'s names are a
mechanical rename of the old ones, so a later port is `sed` plus the linter. What
was harvested immediately was not its CSS but its **test's checks**.

---

## Why enforcement is split into two tiers

**Tier 1** (`ds-lint.py`, `PostToolUse`, per edit) carries only rules decidable
from one file's text with no judgement. That narrowness is the point: a blocking
hook that misfires teaches an agent to route around it, and an agent that has
learned to route around one hook has learned to route around all of them.

The first version of D6 proved this. It checked one line at a time, so a
`<button>` written across three lines was reported as missing an attribute that
was on the next line. It now reads the whole tag.

**Tier 2** (`verify_design.py`, per phase) takes everything computed, cross-file
or arguable — contrast measured in a real browser rather than read from source,
horizontal overflow at 375px, JavaScript-as-mechanism, and the escape-hatch count.

**The escape hatch is deliberate.** A rule with no hatch gets worked around
invisibly; one with a counted hatch gets worked around visibly. Tier 2 counts
them, so a rule being routed around shows up as a number instead of as a surprise.
