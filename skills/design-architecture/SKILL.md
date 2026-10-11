---
name: design-architecture
description: >
  The bridge between an approved design and a buildable spec. Turns the locked design pack
  (DESIGN-V1.md + design/, else REVIEW.md) into TRACE.md — every design item traced to where it
  will be built — plus ARCHITECTURE.md and the founding Architecture Decision
  Records — the handful of things that must stay true as the code grows, each written so a
  machine can check it. Runs only after the user approves the review, and only for the app
  lane. It decides structure; it never writes code and never writes the spec. Invoke on
  "design the architecture", "architecture for X", "write the ADRs".
---

# design-architecture

Step 2 of the app lane: `design-task` → **`design-architecture`** → `build-spec` →
`run-phases`.

**Before anything else, read the operating rules in the skill `factory-guide` (section *The operating rules*)** — they win over anything here.

## Why this stage exists

Every complaint that survived the speed problem traces to its absence. A coding agent under
ambiguity does not stall — it decides, plausibly, and differently the next time. Across the 34
projects this factory grew out of, only **one** had an `ARCHITECTURE.md`, and the projects without
one re-implement the same job in incompatible ways: a date converter four times, one a
self-described "line-for-line hand-port" of another; spreadsheet writers five times; auth helpers
three times in identically-named files at identical paths.

A `SPEC.md` says **what to build**. An ADR says **what must not drift**. Only the second one
survives phase 40.

## When it runs — and when it must not

**Runs** for the app lane: something with a schema, screens and phases.

**Does not run** for the course lane, or for ad-hoc/ops work — a panel upgrade, a campaign, a
one-off script. Forcing an ADR onto a twenty-line script is how a factory starts making small
work heavier, which is the disease, not the cure. If you are unsure which lane you are in,
ask; do not default to ceremony.

**Gate, both parts:**
1. `REVIEW.md` must exist and the user must have approved it. No review → stop and send the user to
   `design-task`. Never derive an architecture from a rough idea.
2. If the design names a reference prototype, **the mobile round must be green**:
   `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/prototype-check.py <the prototype> [--view … --show …]`.
   Red → send it back to `design-task`, do not start here. The look is about to be carried whole
   into the project's design layer (§ Frontend source); carrying a broken phone layout with it
   turns one prototype revision into a phase.

## The input — the locked design wins over the interview

If `DESIGN-V1.md` exists, **the design pack is the input**: `DESIGN-V1.md`, every
`design/NN-*.md`, and the prototype it names as the reference implementation. `REVIEW.md` is read
for *why* a decision was taken and what was rejected — never as the list of what to build. It is
an interview record in time order; decisions in it were changed in later sittings, and an early
one read as live is exactly how a build drifts from what the user approved.

Precedence, highest first: **design pack → prototype → review.** Where two disagree, the higher
one wins and the disagreement is written into `ARCHITECTURE.md` — never resolved silently.

The review's list of questions left for this stage is a to-do list, not background. Every item on
it is answered in `ARCHITECTURE.md` or an ADR before the go, or put back to the user as a question.

## What it produces

Three things in `<project>/`, and nothing else:

1. **`ARCHITECTURE.md`** — the map. Sections, in this order, each allowed to be one line at
   this stage: data model, the flows that create or change the core row, what counts as money
   and which date axes exist, roles and gates, scheduled work, **chokepoints**, **known
   traps**, **how the suites are run** — the exact command, which `run-phases` refuses to start
   without and the commit lock records through `verified.py` — the **frontend source** (when the
   design names a prototype), the **stack**, the **operating principles**, the **budgets**, the
   **real runs**, and a dated revisions log.
2. **`adr/NNNN-*.md`** — the founding decisions. Format, and *why* it is shaped that way, in
   `${CLAUDE_PLUGIN_ROOT}/foundation/adr/README.md`; skeleton in `TEMPLATE.md`. Copy `TEMPLATE.md`, do not
   improvise the shape — the enforcement block is parsed by a hook.
3. **`TRACE.md`** — *whenever a design pack exists* — one row per numbered design section, per
   dialog and per prototype button, saying where each will be built. This is the file that makes
   "nothing from the design gets lost" checkable instead of hoped for.

**Do not write `SPEC.md`, `_prompts/`, `PROGRESS.md`, or any code.** Same split as
design-task → build-spec, for the same reason: a stage that could produce the next stage's
output will, and badly.

## The trace — nothing from the design is lost

The requirement: the build comes out exactly as designed — backend, logic, and what every
button is wired to — with nothing forgotten. Prose cannot guarantee that; a table a script checks
can.

1. **Start it mechanically, never by hand**, as a draft in your session scratchpad:
   `${CLAUDE_PLUGIN_ROOT}/scripts/trace-check.py <project> --skeleton > <scratchpad>/TRACE.md`
   One row per numbered design section (`S-`), per dialog (`D-`), per labelled button in the
   reference prototype (`B-`). Hand-listing is how an item gets missed; on the first factory app the
   skeleton is 75 sections, 10 dialogs and 76 button labels.
2. **Fill `built in` for every row** — the table, endpoint, job, template or chokepoint that will
   carry it. For a screen, add `route: /path` and the prototype function that renders it
   (`← prototype viewFolders`). For every `B-` and `D-` row, cite the screen section it sits on
   (`§4.2`) and say what it does: the endpoint it calls and what changes.
3. **Rows are never dropped.** A section genuinely not built in this version is `out-of-v1`, with
   its reason. A section this architecture cannot build as designed is a `deviation` — say what
   would change and why — and it goes to the user before the go. Adding, removing or
   reinterpreting a design item without a row is drift, and drift is what this stage exists to
   prevent.
4. **It must be green before you reflect:**
   `${CLAUDE_PLUGIN_ROOT}/scripts/trace-check.py <project> --stage architecture --trace <scratchpad>/TRACE.md`.
   Only deviations awaiting the user's answer may remain. On the user's go, write it to `<project>/TRACE.md`.

`phase`, `verified by` and `status` stay as they are here — `build-spec` fills the phase, the
build fills the rest.

## Frontend source — the prototype is built once, not twice

When the design names a reference implementation, the approved prototype is the UI already built
once. Redrawing it is slower, and it is the surest way to lose what the user approved. Write
`## Frontend source` in `ARCHITECTURE.md`, deciding four things with the user:

1. **The look is the prototype's, carried whole.** Its stylesheet becomes the project's own design
   layer — its tokens in light and dark, its type and spacing, and the components the visual-system
   part of the design names — split into files the templates share. The factory's generic design
   system is **not** used beside it: one look with two sources of truth is how a screen drifts.
   On the first factory app the owner compared the factory system, Tabler and the app's own prototype
   on the same screen and chose the prototype; neither generic base was usable as it stood. What the
   factory contributes instead is its checks — contrast in both themes, the mobile round
   (`prototype-check.py`), right-to-left, no colour outside the tokens — and the look-neutral
   libraries in `${CLAUDE_PLUGIN_ROOT}/foundation/stack.md`. If the prototype has not passed the mobile round,
   send it back to `design-task` before going further.
2. **The markup.** Each screen and dialog is ported from the prototype function or block that
   renders it into server-rendered templates, keeping structure, classes and wording. Its TRACE
   row names that function, so the builder copies instead of redesigning.
3. **The behaviour.** Prototype JavaScript that decides something — validation, allocation,
   matching, counting — is **reference logic, not code**. List each such function; map it to the
   backend function that reproduces it and a test that feeds both the same inputs. Name what the
   prototype only faked — live counts, queues, Telegram itself — so the fake is never shipped.
4. **Where a founding ADR pushes back** — "JavaScript is enhancement, never mechanism" against a
   live editor; "Latin digits in number columns" against "native-script digits everywhere" — decide each
   with the user and record it as a superseding ADR for this project. The prototype never wins
   silently, and an ADR never erases an approved screen silently.

## Stack — pick, do not invent

`${CLAUDE_PLUGIN_ROOT}/foundation/stack.md` holds one checked pick per job — web, database, migrations,
settings, background jobs, retries, logs, metrics, dates, tests. Write `## Stack` in
`ARCHITECTURE.md` by choosing from it, one line per job this project actually has. A library that
is not on the list needs one line saying why the listed pick does not fit; a phase never adds one on
its own. None of these decide the look — that is the prototype's.

## Operating principles — answered in writing, each tied to a check

The requirement, as the owner of the first factory app put it: simple code and a light app, no trouble under pressure, room
to grow, a database that has thought about its future, cheap future changes, measurable health,
nothing hardcoded. Write `## Operating principles` in `ARCHITECTURE.md` — one concrete answer per
line, never a promise:

- **Simple** — no layer, abstraction or library without two real callers or a written reason; files
  stay under 500 lines (hook).
- **Under pressure** — every outside call has a time limit (`0008`); every list is bounded (`0004`);
  slow work runs in the queue, not inside a request; the pool sizes are named.
- **Growth** — web processes keep no state; state lives in the database. The scale ADR gives today's
  real volumes and the first thing that breaks, with its number.
- **Database future** — schema changes are expand → migrate → contract (`0001`). For every table that
  only grows, decide now: time partitions, a BRIN index, and what happens to old rows.
- **Cheap change** — each rule has one home (the chokepoint table below).
- **Health** — `/health`, `/health/ready`, and every job's last success (`0009`).
- **Nothing hardcoded** — every address, limit, timeout and interval is a setting with its unit in its
  name (`0007`).
- **Measurable** — the few numbers that show the app works (request time, queue length, job
  failures), exported without per-person labels.

An answer that no hook, test or final check can verify is written as an open question for the user,
not as a principle.

## Budgets — two numbers, not two adjectives

the first factory app's principles said "simple" and meant it. Nothing measured it, and the build reached
27,500 lines of code against a 2,900-line prototype, with a folder editor that waited on the
server for every chip — the owner's words: "slow and heavy", "it became far too big and complicated".
A word no tool reads is a wish. Write `## Budgets` with exactly two lines, each a number and the reason for it:

    - **Click** — 800 ms: from pressing a button to the page settling, measured locally.
    - **Code** — 12,000 lines: the app's own code, without tests, comments or blank lines.

- **Click** is measured by `press-check.py` on every traced button of a local copy. The distance
  to the server comes on top, so pick the number knowing where the users are; say which screen is
  the heavy one and why it still fits.
- **Code** is counted by `budget-check.py` after every phase. Estimate it from the design, not from
  a wish: screens × what a screen of this kind cost the last project, plus the backend pieces the
  chokepoint table names. State the estimate's arithmetic in the line.

Crossing either stops the run and puts the choice to the user: simplify, or raise the number with a
dated revision saying why. A budget raised knowingly is fine; a budget nobody noticed passing is
the failure this exists to end.

## Real runs — where the build meets reality, early

The first factory app met a real database and a real account after its last phase, and found eight
defects in a day that 2,682 tests on fakes had passed — a race that silently lost data, a query
that only failed on the real database, a button that could never be pressed, deployment settings
nobody passed. Write `## Real runs` saying two things:

1. **Which tests use a real database.** Every test of the data layer and the chokepoints takes
   `realdb_url` — a throwaway PostgreSQL started per test run (`${CLAUDE_PLUGIN_ROOT}/foundation/tooling/
   realdb.py`, copied in by build-spec). Fakes stay for outside services a test cannot own
   (Telegram, a model API); they do not stand in for our own database.
2. **What the real-run phase will touch.** The outside systems this app reaches — a database, an
   account, a source, the server it deploys to — and what a **read-only** run against them must
   show. build-spec marks the first phase that reaches them as the real run; the build pauses
   there for the user's go and a read-only run, before the phases after it are built.

## The chokepoint table is the most valuable thing here

A chokepoint is the **one** place a rule is expressed, so changing it changes the system
everywhere at once. "A structural change doesn't get applied everywhere" is not a discipline
problem — it is what happens when a rule has no single home and gets re-implemented at each
call site.

Name them **before** the code exists. At minimum, decide where these live:

- the only construction of the core row
- the only writer of money, and the one definition of what counts as money
- the one isolation rule — what a given viewer may see
- the one place a role or gate is enforced, which the permission matrix also reads
- the one place the system hands text to an external service
- the one writer to each outside system — its guard (ADR 0010): the switch, the hourly ceiling,
  the repeat limit. one app's reconciler wrote the same folder into a customer's own account
  70,565 times in five days before anyone noticed

Each gets a line in `## Chokepoints` and, where it is checkable, an ADR.

## Ten ADRs are already decided — copy them, do not re-derive them

`${CLAUDE_PLUGIN_ROOT}/foundation/adr/` holds **0001–0010**, the decisions this factory has already
paid for. Copy all ten into `<project>/adr/` before writing anything of your own, and number the
project's own from **0100**. A locale profile (for example `persian`) may add ADRs of its own
in `foundation/profiles/<name>/adr/`; copy those too when the project uses the profile.

| | |
|---|---|
| `0001` | A schema change is expand → migrate → contract |
| `0002` | Money is an integer count of the currency's smallest unit, never float |
| `0003` | Stored instants are UTC; the display time zone is a setting |
| `0004` | Lists are bounded at the query, from the first version |
| `0005` | JavaScript is enhancement, never mechanism |
| `0006` | User input is normalised at the boundary — digits of any script, one spelling |
| `0007` | Every address, limit, timeout and interval is a typed setting |
| `0008` | Every outside call has a time limit, every retry stops |
| `0009` | Every app reports its own health — alive, ready, each job's last success |
| `0010` | Every write to an outside system goes through one guard — off by default, capped, stopped when it repeats |

Each carries a tested enforcement block, so copying them turns the hook on. **If one of them is
genuinely wrong for this project, supersede it with a new ADR that says why** — do not edit or
delete it. That argument is exactly the conversation worth having at this stage.

## The project's own ADRs — the questions the ten cannot answer

Not a checklist to fill mechanically. These are the decisions that are cheap now and cost
weeks at phase 40. Write an ADR for each one the project actually has:

- **Roles and what each may do**, expressed as data the gate reads, not as scattered `if`s.
- **What scale is assumed.** Row counts, concurrent users, and the one thing that would break
  first. An honest small number is worth more than an aspirational large one.
- **What is deliberately not built**, and what would have to change for it to be.

**Interview only for what the design pack and the review do not answer, and ask narrowly.** This stage is not a
second `design-task`; a full re-interview here means the review was too thin and should go
back rather than be patched.

## Making a decision enforceable

Every ADR carries an `## Enforcement` block. Two tiers, and the split is deliberate:

- **`forbid`** — regexes matching what a violation looks like in a diff. Checked on **every
  write** by `${CLAUDE_PLUGIN_ROOT}/scripts/adr-check.py`, at **zero model cost**.
- **`review`** — prose for what regex cannot see, judged **once per commit**.

The expensive tier is not per-edit on purpose: the binding constraint here is the usage quota,
and a per-commit check catches the same violation before it can reach anyone.

**Prefer a false negative to a false positive.** A rule that misfires teaches an agent to route
around the checker, which is strictly worse than the rule not existing. If a pattern would fire
in tests or fixtures, scope it with `where` or move it to `review`.

Write each `message` as the **repair** — name the correct construct. "Amounts are integer minor
units; use Integer or BigInteger" beats "float not allowed".

## Check the document before showing it

    ${CLAUDE_PLUGIN_ROOT}/scripts/architecture-check.py <project>

Green before you reflect. It reads `ARCHITECTURE.md` itself — the one artifact nothing used to
read — and fails on a missing section, a verification command nobody can run, an operating
principle answered with a placeholder instead of a decision, a library that is not in
`stack.md` and does not say why, missing founding ADRs or none of the project's own, and any
question the review left here that the document never quotes and answers, budgets without both
numbers, and real runs that do not say which tests use `realdb`.

Write each library name in backticks, exactly as `stack.md` writes it; that is how both files are
read. A library off the list is allowed — say `off-list:` and the reason on the same line.

## Reflect, then get the go

Before writing anything: state back, in plain language, the shape you are proposing — the core
row, the chokepoints, each founding decision in one sentence with its cost, the trace in one
line (how many design items, how many deviations — and each deviation in plain words), and the
frontend-source decisions. **Assume the user is
not a programmer**: architecture reads well, jargon badly. Verdict first, evidence
second, implementation vocabulary only if they ask.

Write only on an explicit go. A decision the user has not actually agreed to is worse than no ADR,
because the hook will then enforce it against them.

## Never, in this stage

- write code, a spec, phase prompts, or a phase register
- invent a decision the design pack or the review does not support and the user has not confirmed
- drop, merge or reinterpret a design item without a `deviation` row the user has seen
- write an ADR with neither `forbid` nor `review` — that is a note, and notes rot
- renumber or delete an ADR; a decision that stops being true is **superseded**, never erased
- put a rule in prose and call it settled. The prior art published a spacing scale in its own
  architecture document and then broke it in 154 of its own 203 spacing declarations, because
  nothing checked. Prose is not enforcement.
