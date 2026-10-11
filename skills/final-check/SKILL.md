---
name: final-check
description: >
  The last gate before anything is deployed. Proves a finished build matches its locked design
  item by item — every design section, screen, dialog and button traced to the code that builds
  it and a test that passes — runs every suite, presses every button in a real browser, holds
  the app to its click and code budgets, then reads each design part against the code for
  mismatches. Mismatches become one fix phase built through the normal gates. Ends with a page
  the user can read — every promise, green or red. Never deploys. Invoke on "final check", "check the
  build against the design"; run-phases runs it by itself when no build phases are left.
---

# final-check

Governed by the factory's operating rules (skill `factory-guide`) — they win. Never deploy.

## Why this exists

The requirement the factory exists for: the build comes out **exactly as designed** — the
backend, the logic, and what every button in the panel is wired to — with nothing lost or
forgotten, and a final check that fixes what it finds.

Per-phase gates prove each phase did what its prompt said. They cannot prove that the prompts,
taken together, covered the design. That is this skill's job, and nothing earlier does it.

## Preconditions — stop if one fails

1. A locked design pack (`DESIGN-V1.md` + `design/`) and a `TRACE.md` exist. No trace → say so
   and stop; there is nothing to prove the build against, and this skill never invents one.
2. The phase register has no open build phases — or the user asked for the check explicitly.
3. The working tree is clean, and the verification command is written down (same rule as
   `run-phases`).

## Four passes, cheapest first

**1 — The trace.** Zero model cost.

    ${CLAUDE_PLUGIN_ROOT}/scripts/trace-check.py <project> --stage final

Every row `done` with a test that exists, every deviation approved, no design section, dialog or
prototype button without a row. Then `${CLAUDE_PLUGIN_ROOT}/scripts/standin-check.py <project>` — no
placeholder may outlive the phase that was meant to replace it.

**2 — Every suite.** The project's full verification command, run through
`${CLAUDE_PLUGIN_ROOT}/scripts/verified.py <repo> -- <command>` so the fix phase can commit. Keep the raw output.

**3 — The screens, pressed.** Start the app in dev with fixture data — **locally, never the live
panel** (press-check refuses any other address) — then:

    ${CLAUDE_PLUGIN_ROOT}/scripts/press-check.py <project> --base-url http://localhost:<port> [--cookie "…"] \
        --param id=… --out <scratch>/press
    ${CLAUDE_PLUGIN_ROOT}/scripts/verify_design.py --project <project> --url <each screen route> [--cookie "…"]

Every traced button is found on its screen, **pressed**, and must do something — change the page,
the address, or send a request — without a server or script error, inside the click budget.
`dead`, `disabled`, `error`, `missing`, `slow` and `skipped` all fail; `needs-input` is listed on
the page as not proven. Pass a `--param` for every `{id}` a route needs — a skipped screen is a
screen nobody checked. A button that lives in a tab, a dialog or a later step is `missing` from its
screen's first view: give its own `B-` row the route that shows it (`route: /x/{id}?tab=cap`) —
that is a trace correction, not a code change — and seed the fixture so the state exists. Every page must also pass contrast and fit 375px. **A page that could not be
reached is SKIPPED and reported as skipped — never counted as passing.**

Then the size: `${CLAUDE_PLUGIN_ROOT}/scripts/budget-check.py <project>` — over the code budget is a failed item. And
the real database: `grep -rl realdb_url tests/` must list the data-layer and chokepoint tests
ARCHITECTURE.md → Real runs names; a data suite on fakes alone is a failed item.

Then the app's own health. `GET /health` answers fast and touches no dependency; `GET
/health/ready` checks the database and every backing service and names the one that failed. A
missing or lying health endpoint is a failed item, exactly like a missing button.

**4 — Design against code, one part at a time.** Before starting, tell the user the cost in one
line: *N design parts = N subagents, one after another.* The user may skip it or pick parts.

One subagent per `design/NN-*.md`, in order, **never in parallel**. Each receives only: that part,
the TRACE rows citing it, and the files in their `built in` column. It returns exactly:

    PART:        <file>
    MISMATCHES:  §<id> — design: "<quoted>" — code: "<quoted>" — <file:line>   (one per line, or none)
    UNSURE:      §<id> — <what the code could not settle>                     (or none)
    EXTRA READS: <files read beyond the given ones, or none>

A mismatch quotes **both** sides. "Looks different" is not a mismatch.

## Fixing what it finds

1. Every failed row, failed suite, missing button and mismatch becomes one line in **one fix
   phase** added to the register (`NN-final-fix`). Its success criteria are the design text each
   line must match, quoted.
2. Build it through the normal `run-phases` loop — fresh subagent, criteria, full regression,
   commit, TRACE rows updated in the same commit.
3. Re-run passes 1–3, and pass 4 only for the parts that had mismatches.
4. **One fix round only.** Anything still wrong after it is either a contradiction in the design
   or bigger than a fix phase — both need the user. Stop and report.

**Never make the check pass by changing the design or the trace to match the code.** If the code
is right and the design is wrong, that is a `deviation`: put it to the user, and record
`approved YYYY-MM-DD` only once the user agrees.

## The page the user reads — last, after the fix round

    ${CLAUDE_PLUGIN_ROOT}/scripts/verdict-page.py <project> --press <scratch>/press --out <scratch>/verdict.html   # add --lang fa for a Persian-profile app

One row per design promise, green or red; every button's pressed result; whether the suite passed
on exactly this code; the slowest click and the code size against their budgets; the screens as
served; and, in its own words, what it does not prove. **Publish it as an Artifact and give him the
link** — after nineteen green phases on the first factory app the owner's words were "I still
am not sure it actually works", because everything that proved the build was written for a
programmer. The page is built only from what the checks found; never edit it by hand to soften a
red row.

## Report — one, in the project's `reports/` folder

The verdict page's link first. Then plain language, verdict first: *the build matches the locked design* — or *it does not, in N
places*. Then per pass: what was checked, the raw numbers, what was skipped and why. Then what the
fix phase changed, and what is left for the user to decide. Nothing is deployed; say what a deploy
would now involve and wait for the user's go.

**When the build matches, add harvest candidates.** Name the components of this project's design
layer that proved themselves across several screens — for example the dense row, the stat
cell, the picker, the pill, the dialog — and propose them as additions to the factory's own
components, so the next project's prototype starts from proven work instead of a blank page or a
generic kit. Proposed only; nothing is copied without the user's go.

## Never

- deploy, push to production, or switch anything live — this skill ends at a report
- mark a row `done` without the test that proves it
- count a skipped check as a pass
- press buttons on a live panel — only on a local copy with fixture data
- run pass 4 in parallel, or give one subagent the whole design
- edit the design pack or a TRACE row's design text to make a mismatch disappear
