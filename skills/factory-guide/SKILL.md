---
name: factory-guide
description: >
  The map and the operating rules of the app factory. Read this first when the user wants to build
  an app with the factory, asks how the process works, asks which step comes next, says "start
  project X" or "continue project X", or when a factory skill refers to "the factory's operating
  rules". Explains the lane (design → architecture → spec → build → final check), what each skill
  does, where each file lives, which rules never bend (no deploy without a go, no building while the
  design is still being decided), and how to run a supervised phase.
---

# The app factory — the map and the rules

The factory is a **process**, not a template. An idea goes through six gates, each one a separate
skill that writes only its own artifact, so a shallow step cannot slip into a finished-looking
build. Machines check what machines can check; the user decides everything else.

## The lane

```
 idea ──► design-task ──► design-architecture ──► build-spec ──► build ──► final-check ──► (deploy: only on the user's go)
          REVIEW.md       ARCHITECTURE.md          SPEC.md        phases    verdict page
          prototype/      adr/  TRACE.md           _prompts/      STATE.md
          DESIGN-V1.md                             PROGRESS.md    reports/
```

| Step | Skill | Say | Writes | Stops for |
|---|---|---|---|---|
| 1 Interview | `design-task` | "design this", "spec this out" | `REVIEW.md`, `prototype/`, then (on lock) `DESIGN-V1.md` + `design/` | the user locking the design |
| 2 Architecture | `design-architecture` | "design the architecture" | `ARCHITECTURE.md`, `adr/`, `TRACE.md` | the user's go on the shape |
| 3 Spec | `build-spec` | "build the spec for X" | the scaffold + `.factory`, `SPEC.md`, `_prompts/`, `PROGRESS.md` | — (it never builds) |
| 4 Build | supervised, or `run-phases` | "start project X" / "run phases" | code, tests, `STATE.md`, one report | each phase (supervised) or a red gate (unattended) |
| 5 Final check | `final-check` | "final check" | a fix phase, the verdict page | the user reading the verdict |
| — Screens | `design-system` | (used while writing templates) | templates, CSS | — |

**Updates to a project the factory built** go through the same lane: `design-task` interviews only
the new part and appends an `## Update review`, then `build-spec` appends a dated revision. **Small
work** (a script, an ops job, a report) skips architecture and the scaffold: `design-task` quick
mode, then `build-spec`.

## What the factory is for — and not for

It builds **server-rendered web apps in Python** (FastAPI, PostgreSQL, Jinja templates, a small
amount of JavaScript): panels, dashboards, internal tools, bots with an admin side. The starter kit,
the stack list, the decision records and the hooks assume that. It runs on **macOS or Linux**
(bash, rsync, git, Python 3.11+; Docker for the real-database tests).

For anything else — a mobile app, a static site, a game, a CLI, an app in another language — the
design half still works (`design-task`, `design-architecture` for the decisions and the trace,
`build-spec`), but there is no starter kit and the Python gates do not apply. **Say so in the first
minute of `design-task`**, plainly, and let the user choose: continue without the scaffold, or use
something else. Never force a non-Python idea through the Python kit.

## Which projects the factory applies to

Only a project with a **`.factory` file at its root** — written by `build-spec` when it scaffolds a
new app. Every hook checks for it and does nothing without it. An existing project is never touched:
no starter kit, no ADRs, no design system copied in. Bringing one under the factory is a separate
decision the user makes, never a side effect.

## What runs by itself (the hooks)

In a factory project only: every file a session writes is formatted and linted, refused if it
crosses 500 lines, checked against the project's ADRs (`forbid` rules) and the design-system linter.
A `git commit` is refused unless the verification command last passed on exactly the tree being
committed (`scripts/verified.py <repo> -- <command>`), lint is clean, no migration both adds and
drops, and no `STAND-IN(phase NN)` outlives phase NN. At session start, a short brief names the
factory projects and these gates. Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/doctor.py` once on a
new machine: it lists what is missing (ruff, uv, Docker, playwright) and how to install it.

## Finding the plugin's own files

Skills name scripts as `${CLAUDE_PLUGIN_ROOT}/scripts/…` and starter files as
`${CLAUDE_PLUGIN_ROOT}/foundation/…`. Claude Code fills that variable in. If you ever see it
literally, unexpanded, in a command you are about to run, do not guess a path: find the folder that
holds `.claude-plugin/plugin.json` with `"name": "app-factory"` (search under `~/.claude/plugins`, or
the directory given to `--plugin-dir`), and use that folder in its place.

## The operating rules

These win over anything inside a skill. **Every factory skill starts by reading this section.**

1. **Deliberate first; act only on an explicit go.** While something is still being worked out — a
   design, a plan, which approach — keep proposing, reflecting and asking, but do not implement it.
   Reading, searching and thinking are always free. Changing things waits for the user to approve
   that specific work in words. One answer to a sub-question is not approval of the whole. Once a
   plan is agreed, executing it is fine; the gate is *are we still deciding, or has it been decided?*
2. **Never deploy without an explicit go.** Not to a server, not to a public address, not to a
   registry, not to real users, not against production data. Build it, test it, get it ready, then
   stop and say plainly what will change, where, what it could affect, and how to roll back. Silence
   or an approval of something else is not a go. This holds mid-run: reaching a deploy stops
   `run-phases`.
3. **Verdict first, in plain language.** Assume the user is not a programmer. Lead with one sentence
   — what is true, what it means for them, what (if anything) they must decide — then the evidence
   in a few lines, then technical detail only if asked. Explain in terms of what the system does,
   not how it is implemented.
4. **Never fabricate.** If you do not know, say so or ask. This covers your own limits: do not imply
   you can see the user's usage budget, a service's internal state, or whether a background job
   really ran. Say what you cannot see and design around it.
5. **Give pushback, not validation.** Name flaws and simpler alternatives; do not agree reflexively.
6. **Keep it simple.** The minimal solution that works. A rule that cannot be checked is a wish.
7. **Confirm before anything consequential or irreversible** — deleting, sending, spending,
   publishing. Reading never needs confirmation.
8. **Report outcomes faithfully.** A failed test, a skipped check or an unverified claim is reported
   as exactly that. A check that could not run is never counted as a pass.
9. **Never commit or expose secrets.**
10. **Speak the user's language.** Reply in the language the user writes in. Ask once which language
    the written artifacts (`REVIEW.md`, the design pack, reports) should be in, and keep to it.
11. **Explain a choice before asking for it.** Before any pick, say in plain words what each option
    *is*, with an everyday analogy, what it costs, and the one fact that decides between them; state
    which you would pick and why. Keep option labels plain too. Do not put implementation questions
    to the user at all — choose, say "this one is technical, I chose X because Y", and record it.
    A question the user says they do not understand usually has a wrong premise: back up and
    explain what the thing is.
12. **Match the effort to the ask.** A status question gets a plain answer in chat, verdict first. A
    document, a page or a prototype is made when asked for or when it is a deliverable for someone
    else — not as packaging for an answer.
13. **Green is not proof.** A passing suite, clean lint and `done` trace rows can all coexist with
    half-finished work. Before calling a phase done, audit it (see `run-phases`, step 3c); before
    building from a document — a design section, a brief, a handover — open it and judge whether it
    is real: a prompt that argues with its own design section means that screen was never designed,
    and a source the user does not recognise is not authoritative.

## Supervised build ("start project X", "continue project X")

Read `<project>/SPEC.md` and `PROGRESS.md` (and `STATE.md` if it exists). Work **one phase**: build
it from its `_prompts/NN-*.md`, run the project's verification command, check the phase's success
criteria, update `PROGRESS.md` and `STATE.md`, report in plain language — then **stop** and wait for
the user's approval before the next phase. A phase finishing is a checkpoint, not a green light.
When the phases ahead are well specified and the user wants less supervision, `run-phases` does the
same with mechanical gates instead of a human stop.

Keep `STATE.md` current at checkpoints (which phase, which commit, what is next) so a fresh session
can resume from evidence: `git log`, `git status`, and the verification command — not from memory.

## The project folder

```
<project>/
  .factory            marker: this project is under the factory
  REVIEW.md           the interview record (why)
  DESIGN-V1.md        the locked design index   ─┐ the design pack (what);
  design/NN-*.md      one numbered part per concern ┘ wins over the prototype and the review
  prototype/          clickable prototype versions (the approved one is the reference implementation)
  ARCHITECTURE.md     the map: chokepoints, traps, stack, principles, budgets, real runs
  adr/NNNN-*.md       decisions, each with an enforceable block (founding 0001–0010; yours from 0100)
  TRACE.md            every design section, dialog and button → where it is built → the test
  SPEC.md  _prompts/  the buildable spec and one prompt per phase
  PROGRESS.md         the phase register (the only place phase numbers are allocated)
  STATE.md            where a resumed session picks up
  reports/            one report per run
```

## Showing things: prototypes and the verdict page

The skills say "publish as an Artifact" when the Claude Code session has an Artifact tool. If it
has none, do the same with files: write the prototype (or the verdict page) as a single
self-contained HTML file in the project (`prototype/<name>-vN.html`, `reports/verdict.html`), tell
the user its path, and offer to serve it for a phone check with
`python3 -m http.server 8000 --directory <folder>` (the user opens `http://<this-machine's-address>:8000/…`
on the same network). Comments come back in chat; keep each version as a new file. Never skip the
visual step because the tool is missing — a person judges a screen by seeing it, not by reading a
description.

## Language profiles

The starter kit and the design system are language-neutral (English, left-to-right, Gregorian
dates, a display time zone that is a setting). A **profile** in `foundation/profiles/<name>/` is a
small overlay for an app in another language. Today there is one: `persian` (Persian pages,
right-to-left, Jalali dates, Persian digits for display). `design-task` asks the app's language and
direction early; `build-spec` step 0 applies the profile. See the profile's `README.md`.
