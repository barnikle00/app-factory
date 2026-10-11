# app-factory

A Claude Code plugin that turns "build me an app" into a **gated process** instead of one long,
drifting conversation.

An idea goes through six steps. Each step is its own skill and writes only its own artifact, so a
shallow step cannot slip into a finished-looking build — and the things a machine can check (lint,
file size, architecture decisions, tests on exactly the tree being committed, every button pressed
in a real browser) are checked by hooks and scripts, not by remembering.

```
idea ─► design-task ─► design-architecture ─► build-spec ─► build phases ─► final-check ─► you deploy
        interview,      decisions that are     scaffold +     supervised, or   proves the build
        prototype,      enforced, and a        spec + one     unattended       matches the locked
        locked design   trace of every         prompt per     behind gates     design, item by item
                        design item            phase
```

## Install

```text
/plugin marketplace add barnikle00/app-factory
/plugin install app-factory@app-factory
```

Then, once per machine, ask Claude to *run the factory doctor* (it runs `scripts/doctor.py`) to check
what the gates need.

It needs Python 3.11+ and git, and reports how to install the rest: `ruff` (lint on every write),
`uv` and Docker (the starter kit builds its environment and tests on a real throwaway PostgreSQL),
and `playwright` (pressing buttons and measuring layout in a real browser).

## Use

Start in an empty folder and say:

| Say | Skill | You get |
|---|---|---|
| "design this: …" | `design-task` | an interview that pins every vague word to an example, a clickable prototype you comment on, then a locked design |
| "design the architecture" | `design-architecture` | `ARCHITECTURE.md`, ten founding decisions (ADRs) with machine-checkable rules, and `TRACE.md` mapping every design item to where it will be built |
| "build the spec" | `build-spec` | the scaffolded app (settings, database, sign-in, health, jobs, guarded outside writes, a green test suite) and a phased spec |
| "start project X" / "run phases" | supervised build / `run-phases` | one phase at a time with your approval, or several in a row behind mechanical gates |
| "final check" | `final-check` | a verdict page you can read: every design promise, green or red |

`factory-guide` is the map; ask "how does the factory work?" any time.

## The rules that never bend

- **Nothing is built while the design is still being decided**, and nothing is deployed without an
  explicit go from you.
- **The factory only touches projects it built** (a `.factory` file at the root). Every hook is
  silent anywhere else.
- **A check that could not run is never a pass.**
- **Plain language first**: one sentence on what is true and what you must decide, then evidence.

## What is inside

| | |
|---|---|
| `skills/` | `factory-guide`, `design-task`, `design-architecture`, `build-spec`, `run-phases`, `final-check`, `design-system` |
| `hooks/hooks.json` | session brief, commit lock, and the edit-time checks (format+lint, 500-line limit, ADR rules, design linter) |
| `scripts/` | the gate scripts the skills and hooks call (`trace-check`, `architecture-check`, `press-check`, `budget-check`, `verified`, `doctor`, …) |
| `foundation/skeleton/` | the starter kit every new app begins from — FastAPI, PostgreSQL, sign-in, health, jobs, the outside-write guard |
| `foundation/adr/` | the ten founding decisions and the format that makes them enforceable |
| `foundation/design/` | a small design system: 17 Jinja macros, a 31-slot brand contract with a contrast checker, two example brands |
| `foundation/stack.md` | one checked library pick per job |
| `foundation/profiles/` | language overlays — today `persian` (right-to-left pages, Jalali dates, Persian digits) |
| `tests/` | the factory's own test suite |

## Language

The starter kit and design system are English, left-to-right and Gregorian by default; the display
time zone is a setting. A **profile** overlays another language without touching the core — see
`foundation/profiles/persian/README.md` for the model, and add your own the same way.

## Develop

```bash
python3 -m venv .venv && .venv/bin/pip install pytest hypothesis jinja2 ruff playwright httpx
.venv/bin/python -m pytest tests -q
```

`tests/test_skeleton.py` builds the starter kit in a fresh environment (with and without a profile)
and runs its whole suite on a real PostgreSQL — it needs `uv` and a running Docker, and skips
itself without them.

## Licence

MIT.
