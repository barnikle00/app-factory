---
name: build-spec
description: >
  The second half of the design flow. Turns an APPROVED design review (<project>/
  REVIEW.md, produced by design-task) into the buildable workspace — SPEC.md + phase build-
  prompts + PROGRESS.md — following Anthropic's prompt-engineering guide. Runs only after
  the user has approved the review. As a second security layer it re-verifies the review for
  prompt-completeness and domain-completeness, and may ask narrow completion questions — but it
  never runs the full interview and never executes. Invoke on "build the spec for X", "build
  spec X", "the review is approved".
---

# build-spec

Turn an **approved** `REVIEW.md` into a living project workspace a fresh session can build
from. This is step two; `design-task` is step one. The split is deliberate — the interview
phase physically cannot write the workspace, so a shallow interview can't slip straight into a
finished-looking spec.

**Before anything else, read the operating rules in the skill `factory-guide` (section *The operating rules*)** — they win over anything here.

## The gate — build-spec is the SECOND security layer

`design-task` is the first net. This is the second: before writing anything, **independently
re-verify the review on two axes**, then check approval. Only when all pass do you write.

**Basic checks:**
1. `<project>/REVIEW.md` **must exist**. No review → stop, tell the user to run
   `design-task` first. Never write a spec from a rough idea directly.
2. **The user must have approved.** "build the spec for X" is the go-ahead. Any doubt → ask
   "the review is approved — build it?" and wait.
3. **A factory app with a design pack** also needs `ARCHITECTURE.md`, `adr/` and `TRACE.md`, and
   both of these green:
   - `${CLAUDE_PLUGIN_ROOT}/scripts/trace-check.py <project> --stage architecture`
   - `${CLAUDE_PLUGIN_ROOT}/scripts/architecture-check.py <project>`
   Either red → stop and send it back to `design-architecture`. A spec transcribed from an
   architecture with a missing section, an unanswered principle or an off-list library carries
   those gaps into every phase prompt, where they become code.

**Axis 1 — prompt-completeness.** Walk the review's "## The prompt's inputs" against what a
guide-compliant build-prompt actually needs (§2): role, task, output format, the *why*,
constraints, examples where they steer, success criteria, guardrails, verification. For each:
**do I actually have this?** A blank, or a category word with no concrete instance behind it
("the documents"), does **not** count as having it.

**Axis 2 — domain-completeness.** Separately from prompt shape: given the domain the review
chose, is the project fully specified *for that kind of work*? Bring your own domain knowledge
— what does this kind of build always need that this review doesn't mention?

**On any gap (either axis): never fill it from imagination.** Either
- ask the user a **narrow** completion question to close it (build-spec may ask targeted
  questions — it does **not** run the full interview), or
- if the gap is substantial, **stop and send the review back to `design-task`.**

## Boundaries (hard)

- Write **only** inside `<project>/`: `SPEC.md`, `_prompts/NN-*.md`, `PROGRESS.md`,
  plus the scaffold in step 0 for an app.
- **Nothing may appear in `SPEC.md` that isn't in the locked design pack, the review or
  `ARCHITECTURE.md`** — this is transcription, not
  authoring. A missing input is a gap to close (above), never something to invent.
- Never execute the build.

---

## 0. Scaffold from the factory — a NEW app only

**Skip this whole section for an update to an existing project**, and for a one-off script, an
ops job, a panel upgrade, a campaign or a report. An existing project — anything without a
`.factory` file at its root — keeps its own design layer, its own conventions and its own tests,
and **nothing from the factory's foundation is copied into it.** The factory is for new projects
only, with no retrofit, and that matters for a measured reason: the factory's lint hook, run on a
copy of an older project, deleted an import another module depended on at startup.

**Skip for small work too.** Those get a spec and prompts and nothing else; making small work heavier is the
disease, not the cure.

For an app, the project starts from the factory's **starter kit** before the spec is written.
This is the only moment the foundation can arrive — a hook that enforces decisions a project never
received enforces nothing.

```bash
P=<project>          # an empty folder, or one holding only the design pack
NAME=<project>

# 0. The marker. Every factory hook and skill checks for this file, and does nothing in a
#    project that lacks it. Write it first, so the hooks are on for every file that follows.
mkdir -p $P && printf 'factory project — scaffolded %s from the app-factory plugin\n' "$(date +%F)" > $P/.factory

# 1. The starter kit: settings, database, sign-in, health, jobs, the outside-write guard, the
#    container, and a green test suite — what the first factory app spent its first three phases on.
rsync -a --exclude README.md --exclude .venv --exclude __pycache__ ${CLAUDE_PLUGIN_ROOT}/foundation/skeleton/ $P/
grep -rl factory-app $P --include='*.toml' --include='*.yml' --include='*.py' | xargs perl -pi -e "s/factory-app/$NAME/g"
cp ${CLAUDE_PLUGIN_ROOT}/foundation/tooling/realdb.py $P/tests/realdb.py

# 1b. A language profile — only when the design says the app is in that language (today:
#     persian; leave PROFILE empty for English / left-to-right). It replaces the pages, the text
#     helpers and the sample tests, and adds its own dependency lines. Read its README first.
#     --checksum matters: in a fresh clone every file has the same timestamp, and rsync's default
#     size-and-time shortcut would skip an overlay file whose size happens to equal the kit's.
PROFILE=${PROFILE:-}
if [ -n "$PROFILE" ]; then
  rsync -a --checksum --exclude README.md --exclude requirements.add.txt --exclude adr \
        ${CLAUDE_PLUGIN_ROOT}/foundation/profiles/$PROFILE/ $P/
  cat ${CLAUDE_PLUGIN_ROOT}/foundation/profiles/$PROFILE/requirements.add.txt >> $P/requirements.txt
fi

# 2. The founding decisions (0001–0010). The project numbers its own from 0100.
mkdir -p $P/adr && cp ${CLAUDE_PLUGIN_ROOT}/foundation/adr/0*.md ${CLAUDE_PLUGIN_ROOT}/foundation/adr/TEMPLATE.md $P/adr/

# 3. The generic design system (its example brands are `slate` and `forest`; the project writes its
#    own brand file) — ONLY when the design names no prototype of its own. A project
#    whose DESIGN-V1.md names a reference prototype carries that look into its own design layer
#    (ARCHITECTURE.md → Frontend source). On the first factory app the owner compared the generic
#    base with the app's own prototype on the same screen and chose the prototype.
if ! grep -q 'prototype/' $P/DESIGN-V1.md 2>/dev/null; then
  mkdir -p $P/app/web/static/ds
  cp ${CLAUDE_PLUGIN_ROOT}/foundation/design/core.css ${CLAUDE_PLUGIN_ROOT}/foundation/design/brand-*.css \
     ${CLAUDE_PLUGIN_ROOT}/foundation/design/ds.js ${CLAUDE_PLUGIN_ROOT}/foundation/design/fonts.css $P/app/web/static/ds/
  cp ${CLAUDE_PLUGIN_ROOT}/foundation/design/ds.py ${CLAUDE_PLUGIN_ROOT}/foundation/design/ds_dev.py $P/app/
  cp ${CLAUDE_PLUGIN_ROOT}/foundation/design/templates/*.html $P/app/web/templates/
fi

# 4. Prove it arrived: its own suite, on a real database, before a line of the app is written.
cd $P && uv venv -q -p 3.11 .venv && uv pip install -q -p .venv/bin/python -r requirements-dev.txt \
  && .venv/bin/python -m pytest -q && .venv/bin/ruff check . && .venv/bin/pyrefly check
```

**The phases start from the kit, they do not rebuild it.** Do not spec settings, the engine, sign-in,
roles, health, the jobs loop or the outside-write guard as phases — they exist and are tested. A
phase *extends* them: a new settings class, a new role, a job on the schedule, a guarded target.
Every write to an outside system goes through `app/core/outside.py` (ADR 0010); its switch starts off.
The verification command in `SPEC.md` is the kit's:
`.venv/bin/python -m pytest -q && .venv/bin/ruff check . && .venv/bin/pyrefly check`.

Then write **one** project ADR, `0100`, naming what this app assumes about scale — row counts,
concurrent users, and the one thing that would break first. An honest small number is worth
more than an aspirational large one, and it is the number every later "does this scale?"
argument gets measured against.

If `design-architecture` already wrote ADRs for this project, **do not rewrite them** — check
they are present and continue.

---

## 1. Write `SPEC.md` from the review

**When a design pack exists, transcribe from it:** `DESIGN-V1.md` + `design/` for *what*,
`ARCHITECTURE.md` + `adr/` for *how*, `REVIEW.md` only for *why*. Where they disagree, the design
pack wins — it says so itself — and the interview record never overrides a locked decision.

The review already holds the answers; transcribe them into the durable spec — don't
re-interview, don't invent anything the review doesn't contain. If something needed is missing
from the review, that's a gap in the review → go back, don't guess.

```
---
project: <name>
created: YYYY-MM-DD
updated: YYYY-MM-DD
---

# <Project> — Spec

<objective> the why + one-line goal </objective>
<scope> in: … | out: … </scope>
<code_location> in-folder | <repo/VPS path> </code_location>
<constraints> stack, style, must-use / must-avoid </constraints>
<requirements> the pinned dimensions — incl. the blind-spot answers </requirements>
<success_criteria> how we know it's done/correct </success_criteria>
<model> claude-… · effort: … · runtime: … — one-line why (project-level; set once at launch,
  runs all phases) </model>
<phases> 1: … · 2: … (each maps to a _prompts/ file) </phases>

## Revisions
- YYYY-MM-DD — initial spec, from approved REVIEW.md.
```

---

## 2. Write the phase prompts — follow Anthropic's guide

Reference: `https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices`.
One `_prompts/NN-<phase>.md` per phase in the review. Each **references `SPEC.md`** (the
executor reads the file — don't re-paste it) and applies the **relevant subset** of the rubric
for that phase — not all of it; a kitchen-sink prompt wastes tokens and dilutes focus:

- **Clear role** up front; **clear and direct** (specific deliverable, format, constraints;
  numbered steps when order matters).
- **Context/motivation** — state the *why*; the model generalizes from it.
- **Tell it what TO do**, not what not to do.
- **XML tags** to separate instructions / context / inputs / examples. Examples only where
  they steer output (0–5, in `<example>` tags).
- **Success criteria + a self-check step** ("before finishing, verify against …").
- **Scope guardrails** ("don't improvise / don't get lost"):
  - Only make changes directly required; no extra abstractions, no unrequested features,
    validate only at boundaries.
  - "Pick an approach and commit; don't revisit unless new info contradicts it."
  - **"Act only within this scope. If you hit an ambiguity that would change direction, stop
    and ask — do not guess."**
- **The decisions this phase must respect — factory projects only** (a `.factory` file at the
  root; otherwise omit this bullet and the next one entirely). Every phase prompt names
  the ADRs that govern what it touches, by number and in one line each, and says:
  *"These are recorded decisions. If one is wrong for this phase, stop and say so — do not work
  around it."* A decision nothing cites is a document, and the measured failure of this
  workspace is documents nothing reads. (A hook checks the obvious violations at zero cost, but
  it only sees what a regex can see.)
- **The UI, if the phase has one — factory projects only.** Follow `ARCHITECTURE.md → Frontend
  source`. Where it says a screen is ported from the prototype, the prompt says: *"Port the markup
  of <prototype function> into the template, keeping structure, classes and wording. Do not
  redesign it."* Otherwise: *"Screens are built with the `design-system` skill. Call macros from
  `ds.html`; do not write CSS, a bare `<table>` or `<button>`, or a colour in a template."* For
  anything the user has not seen yet, require a `/-/mockup/<name>` before the real query is wired
  — approval is cheap before the logic exists and expensive after.
- **The design items this phase builds — mandatory whenever `TRACE.md` exists.** Assign
  **every** trace row to exactly one phase (fill its `phase` column). Give each phase prompt: its
  rows by id; for each, the design text it must match **quoted** from `design/NN-*.md` with its §
  (never "read the design"); the buttons on its screens and what each one calls; the prototype
  function whose markup it ports; and the reference-logic functions its backend must reproduce,
  each with the test that proves it. **The phase's success criteria are its rows** — "S-4.4 built
  in <…>, verified by <test>". A phase whose rows cannot be built and verified inside one subagent
  is split: an oversized phase is how an item gets skipped under pressure.
- **Tested on the real thing — factory apps.** A phase that writes data-layer or chokepoint code
  has a criterion that its tests take `realdb_url` (a real, throwaway PostgreSQL) — never a fake of
  our own database. A phase that adds or changes a screen has a criterion that
  `${CLAUDE_PLUGIN_ROOT}/scripts/press-check.py <project> --base-url <local dev> --param …` presses its buttons
  and every one comes back `ok`: a test that asks the server whether a form would be accepted does
  not prove the page can send it. The first factory app shipped both failures. A button that lives in a tab, a dialog or
  a later step gets its own `route:` in its trace row — the address that shows it.
- **Stand-ins — factory apps.** When a phase needs something a later phase builds, the prompt
  names it and says: *"Leave a stand-in marked `STAND-IN(phase NN): <what replaces it>`."* And the
  later phase's prompt lists the stand-ins it must replace, by file, as success criteria.
  `standin-check.py` lists them; the commit lock refuses to let one outlive its phase.
- **Libraries — factory apps.** Name the libraries the phase may use, from `ARCHITECTURE.md →
  Stack` (itself chosen from `${CLAUDE_PLUGIN_ROOT}/foundation/stack.md`). A library outside that list is not
  added inside a phase: it is a stop-and-ask.
- **Confirm-before-risky-actions** for anything destructive or outward-facing.
- **Deploy / go-live guardrail — mandatory on any phase that touches it.** If a phase deploys,
  exposes publicly (DNS, public domain, open ports, nginx vhost, TLS), publishes/releases,
  enables real users, migrates production data, or touches a live revenue-facing service, the
  prompt **must** carry: *"Build and test it fully, then STOP and get the user's explicit
  approval before deploying or going live — do not deploy on your own, even to finish the
  phase. State what will change, what it could affect, and how to roll back, then wait."*
  (The deploy rule in `factory-guide`: *always get approval first*.)
- **Terse.** No fluff. Dial back `CRITICAL`/`MUST` (current models over-trigger). No prefill.
- **Multi-window builds:** instruct state tracking (`PROGRESS.md`, `tests.json`, git) and
  incremental progress.

Match the prompt's own style to the desired output (terse prompt → terse output). No per-phase
model tag — the model is project-level in `SPEC.md`; every phase runs under the one session
model.

---

## 3. Write `PROGRESS.md`

```
# <Project> — progress
- [ ] 01 <phase>  — not started
- [ ] 02 <phase>  — not started — real run: read-only against <the systems ARCHITECTURE.md → Real runs names>
- [ ] 03 <phase>  — not started
Notes: <freeform; last session, next step>
```
Execute mode reads this to resume and updates it at checkpoints.

**Mark one phase `real run` — as early as the design allows.** It is the first phase after which
the app can reach a real system: its own database on the server, a real account, a real source.
`run-phases` stops after it, and with the user's go the app is run **read-only** against those
systems; what the run finds becomes a fix phase before any later phase is built.
`trace-check --stage spec` fails when no phase carries the mark. Put the phases that make a real run
possible (deploy files, settings, the read path) first; the screens built on top come after it.
the first factory app met reality after its eighteenth phase and found eight defects in one day — each one
cheaper to find at phase six.

---

## 4. Update mode (an approved delta review)

**Step 0 never runs in update mode.** Check the project root: no `.factory` file means an
existing project, and the update is specced exactly as it was before the factory existed — no
ADRs copied in, no design system, no factory lines in the phase prompts. If the user wants an
existing project brought under the factory, that is its own decision, asked as such.

If `REVIEW.md` has an unapplied `## Update review — <date>` section:
1. **Append** a dated entry to `SPEC.md`'s `## Revisions` and adjust the current-truth body to
   stay accurate — never overwrite the original.
2. Emit a new `_prompts/NN-<phase>.md` delta referencing the updated `SPEC.md`.
3. Add the new phase to `PROGRESS.md`.
4. **Grow the trace with the version.** A later design adds sections, dialogs and buttons, and
   they need rows or the "nothing is lost" guarantee quietly covers v1 only:
   `${CLAUDE_PLUGIN_ROOT}/scripts/trace-check.py <project> --new-rows` prints a row for every design
   item that has none yet — append them, fill in `built in` and the new phase, and leave
   `trace-check … --stage spec` green. The skeleton refuses to overwrite a trace in progress, so
   this is the only way a second version extends it.

---

## 5. Finish

Confirm the workspace is written — and for an app, that step 0 actually landed: the kit's suite is
green, `adr/` holds every founding decision plus the project's own, and the design system is in
`app/web/static/ds/` (skipped when the design names its own prototype). A scaffold that half-arrived is worse than none, because the hooks then pass
silently on a project that never received the decisions.

When `TRACE.md` exists, `${CLAUDE_PLUGIN_ROOT}/scripts/trace-check.py <project> --stage spec` must be green: every row
has a phase, every phase exists in `PROGRESS.md`, and one phase is marked `real run`. A row with no phase is a design item nobody
is going to build.

Tell the user: open a fresh session in the project's folder and say either **"start project `<name>`"** for a
single supervised phase, or **"run phases for `<name>`"** to let it build several back to back
under the run cap. Do not execute here.
