---
name: run-phases
description: >
  Execute mode, unattended. Builds a specced project's phases back-to-back in one run — each
  phase in a fresh subagent, verified against its own success criteria AND the project's full
  regression suite, then committed — without stopping for approval between phases and without
  ever deploying. Halts loudly on a red test, a phase with no written success criteria, an
  ambiguity that would change direction, or the run's phase cap. Writes ONE report for the
  whole run, not one per phase. Invoke on "run phases", "run the next N phases", "run project
  X unattended".
---

# run-phases

The fourth mode, beside Design → Build-spec → Execute → Update. **Execute, minus the human
checkpoint between phases.**

**Before anything else, read the operating rules in the skill `factory-guide` (section *The operating rules*)** — they win over anything here.
One of them is load-bearing and is never relaxed by this skill: **never deploy without explicit
approval.**

## Why this exists

Normal Execute stops after every phase for the user's approval. That checkpoint catches wrong
direction, scope creep and bad design calls — but it also means the user sits idle between phases,
which on a 50-phase project is the single biggest drag on throughput.

This skill removes the *human* checkpoint and replaces it with **mechanical gates that fail
loudly**. The trade is explicit: the run goes unattended only as far as the gates can vouch
for it. The moment a gate can't, it stops — it does not guess and carry on.

## Preconditions — refuse to start unless all of these hold

Check these first, in order. A missing one is a **stop**, not something to improvise around.

1. **A spec exists.** `<project>/SPEC.md`. No spec → this project has never been
   through `design-task` / `build-spec`. Say so and stop.
2. **A phase register exists**, and it is the single place phase numbers are allocated
   (`PROGRESS.md`). Read it before choosing anything — never infer the next number from
   `_prompts/`, from `SPEC.md`'s `<phases>`, or from the newest report. Those three disagree
   routinely and it has already cost a full round trip.
3. **A verification command exists and is written down.** The project must state how its
   suites are run (e.g. `ARCHITECTURE.md §11`). No stated command → you cannot gate on green
   → stop and ask the user to establish one. Do **not** invent a test command.
4. **What the phase rests on is real.** Open the design section, brief or handover the phase
   cites and judge it: is there a prototype view for the screen, and do the numbers it asks for
   exist as stored data? A prompt that argues with its own source ("§X is stale, §Y wins") means
   the design was never fixed — stop and split that work out for a design round. A source the user
   does not recognise is not authoritative; say what it is and ask.
5. **The working tree is clean** and you know the branch. Dirty tree → stop and show
   `git status`; do not stash or discard anything.
6. **A factory app carries its marker.** If the project has `adr/` or `ARCHITECTURE.md` but no
   `.factory` file at its root, the scaffold only half-ran: every hook and the commit lock will
   stay silent on it, and nothing will say so. Stop and send it back to `build-spec` step 0.

## The run contract — agreed once, at launch

Before the first phase, state back to the user in three lines and get the user's go:

- **Which phases** — the range, taken from the register (e.g. "41, 42, 43 — the next three
  open phases that have written success criteria").
- **The cap** — how many phases this run may complete. **Default 5.** When the cap is
  reached the run stops and reports, even if more phases are ready.
- **The budget** — **ask how much headroom the user has** (usage limit, or a wall-clock stop
  time). They can see their usage; you cannot. Take their answer as the real cap and lower the
  phase cap to match it. If they don't know, default to 2 phases, not 5.
- **The follow-ups** — ask once which follow-up work the run may take on by itself. Offer this
  bundle: detail decisions settled by your recommendation (written into the report), one fix phase
  per review finding, an obvious dependency install. Then work to the cap; stop early only on a real
  gate (red test, deploy/push, a real account, a direction-changing ambiguity) — a run that ends
  early with a to-do list defeats the point of running unattended.
- **The gates** — repeat that a red test stops the run, and that nothing will be deployed,
  pushed, or run against production.

That is the only approval in the run. After it, do not ask between phases.

## Surviving a limit — the run must be killable at any moment

Hitting a limit mid-run is normal, not exceptional. **You cannot see how much budget is left,
so never claim you are pacing against it.** Design for the interruption instead: every
mechanism below exists so that being killed costs one phase at most, never a broken tree and
never a lost thread.

**Know which limit you are up against — they pull in opposite directions.** the usual
one is the **usage quota** ("limit reached, come back at HH:MM"), not the context window. That
matters, because per-phase subagents *help* the context window and *cost more* against the
quota: a cold subagent pays full price for every file it opens, while a single long session
would have had them cached. The trade is deliberate — flat, resumable, non-degrading phases in
exchange for a somewhat higher total — but it means **the brief in step 2 is the real budget
control**, not an optimisation to skip when in a hurry. A sloppy brief is the single most
expensive thing in this skill.

- **The subagent is what dies, not you.** Each phase burns its context inside its own subagent.
  When that context fills, the subagent ends and the orchestrator — still small — survives to
  record the state and report. Keeping the orchestrator lean is not a nicety; it is what makes
  a run reportable after a failure.
- **Resuming after a quota reset must be nearly free.** The user will come back hours later. The
  restart reads `STATE.md`, `git log`, and the register — and re-runs the verification command.
  It does **not** re-read the codebase to "get oriented". If resuming costs a quarter of the
  fresh budget, the run never catches up.
- **A commit is the only safe point.** Between commits, assume everything is disposable. Never
  start a phase whose work cannot be committed as a unit.
- **Write `STATE.md` BEFORE starting each phase**, not after: which phases are done and at
  which commits, which phase is about to start, and the exact verification command. Written
  after the fact, it is exactly the file that is missing when you need it.
- **An oversized phase is a spec problem — say so instead of pushing through.** If a phase
  cannot plausibly be built and verified inside one subagent, stop and tell the user it needs
  splitting. A phase that repeatedly dies half-built is the single most expensive failure mode
  here, because every attempt pays the full setup cost and leaves nothing.
- **A subagent that feels its own context running out must stop, hand back what it has, and say
  so** — never rush to a finish it cannot verify. An unverified "done" is worse than an honest
  stop, because the register then lies and the next phase builds on it.
- **Stopping early is a success, not a failure.** Ending cleanly at phase 3 of 5 with three
  green commits and an accurate `STATE.md` is a good run. Being killed at phase 4 with a dirty
  tree and a stale register is the outcome all of this exists to prevent.

## The per-phase loop

For each phase, in register order:

**1 — Select.** Take the lowest-numbered open phase that has **written success criteria**.
A phase whose criteria are missing, vague, or a category word with no concrete instance
behind it is **not runnable** — stop the run there and ask. This gate is the whole defence
against building the wrong thing unsupervised, and it is not negotiable.

**2 — Write the brief, then delegate to a fresh subagent.** Each phase runs in its own
subagent with a clean context, so the orchestrator never accumulates the phase's file reads,
diffs and test output.

**The brief is where the run's cost is decided.** A subagent starts cold: every file it opens
is paid for in full. "Read `ARCHITECTURE.md` and work it out" makes it read forty files to find
four. So the orchestrator's job before spawning is to do the cheap narrowing itself and hand
over a closed brief. Quote the two or three traps that actually apply — do not send it to go
read the trap chapter.

Brief every phase agent with exactly these ten fields, in this order:

```
1  PHASE          <number> — <one-line goal, from the register>
2  TASK           <the _prompts/ file verbatim if one exists; otherwise the register row
                   expanded into a concrete statement of what to build>
3  CRITERIA       <the success criteria, numbered, verbatim — these are what gets checked>
4  START FILES    <explicit paths, each with a one-line why. Search beyond them only if they
                   prove insufficient — and report it if you did (field 10).>
5  TRAPS &        <the 2-3 chokepoints/known traps that apply here, quoted inline, PLUS —
   DECISIONS      only if the project has a `.factory` file — every ADR governing the files
                  in START FILES, number and one line each,
                  quoted, never "read adr/". Close with: "These are recorded decisions. If
                  one is wrong for this phase, STOP and say so — do not work around it.">
6  VERIFY         <the project's verification command, verbatim. If this phase touches a
                  template or a stylesheet IN A FACTORY PROJECT, add
                  `${CLAUDE_PLUGIN_ROOT}/scripts/verify_design.py --project
                  <project> --url <a page this phase changed>` — it measures contrast and
                  375px overflow in a real browser, which no amount of reading the source can.
                  If it adds or changes a button, also `${CLAUDE_PLUGIN_ROOT}/scripts/press-check.py <project>
                  --base-url <local dev app> --param …` — every button of its screens pressed in
                  a real browser, each `ok`.>
7  MIGRATION      <the next free migration number, or "none expected">
8  LIMITS         no deploy, no push, nothing against production; stay inside this phase's
                  scope; never renumber or touch another phase. Anything left in place of what a
                  later phase builds is marked `STAND-IN(phase NN): <what replaces it>` in a
                  comment — an unmarked placeholder is a defect, and the commit lock refuses a
                  commit once phase NN is done and the stand-in is still there
9  BUDGET         don't re-read what is quoted above; don't explore outside START FILES
                  without saying so; if the phase turns out to need much more than this,
                  STOP and report — do not expand the task to fit
10 RETURN         the result block below, filled in — nothing else
```

**Existing projects are briefed exactly as before.** No `.factory` file at the project root —
a pre-factory project, and every project built before the factory — means
no ADR lines, no design-system line and no `verify_design.py`. Those projects have their own
design layer and their own verification suites; pointing a subagent at macros the project does
not have is an instruction to break its pages.

**In a factory project, a phase that builds a screen gets one more line in field 2:** *"Screens are built with the
`design-system` skill — call macros from `ds.html`. Do not write CSS, a bare `<table>`, a bare
`<button>`, or a colour in a template."* That is the whole instruction; the skill carries the
rest, and the linter catches what the skill does not.

Quoting the ADRs inline costs a few lines per brief and is the only version that works. A
subagent starts cold: "the decisions live in `adr/`" makes it either read six files or read
none, and it reliably reads none.

**The result block.** The subagent must return exactly this, so the orchestrator can decide
mechanically without re-reading the code:

```
STATUS:        complete | partial | blocked
CRITERIA:      1. <criterion> — met | not met | not checked — <how it was checked>
               2. …
CHANGED:       <file paths, one per line>
MIGRATION:     <number applied, or none>
TESTS:         <command run> → <N passed / M failed> — <names of any failing suite>
COMMIT:        <hash + subject, or "not committed" and why>
ARCHITECTURE:  updated (§…) | not needed | NOT DONE
TRACE:         <each trace id this phase owns: done — verified by <test> | not done — why>, or none
ASSUMPTIONS:   <any call made under ambiguity, or none>
LEFTOVER:      <anything unfinished, or none>
EXTRA READS:   <files opened beyond START FILES, or none>
```

Two fields exist for reasons that are not obvious:

- **`ASSUMPTIONS`** is how stop-condition 4 is actually enforced. A phase agent that quietly
  decided something is invisible unless it is required to name it.
- **`EXTRA READS`** is the run's cost feedback. If phases keep opening files the brief didn't
  list, the briefs are too thin — widen `START FILES` next time. If it is consistently `none`,
  the briefs can be tightened further. This is the one lever that actually reduces quota burn
  over time, so do not drop the field because it looks like bookkeeping.

**2b — When a phase comes back unfinished.** `partial` is the dangerous result, not `blocked`
and not a red test: something got built, some tests are green, and it *looks* like success. A
partial phase recorded as done is the worst outcome this skill can produce, because the next
phase is then built on it and the damage only surfaces much later.

Three rules, and they are not interchangeable:

- **`partial` → exactly one retry, then stop.** Never two. Most genuine misses are finished on
  the second attempt; a third is a spec problem wearing a build problem's clothes.
- **`blocked` → no retry at all.** Blocked means information is missing. A second agent with
  the same missing information will block in the same place and cost a full phase to learn
  nothing. Stop and ask.
- **Never finish it yourself in the orchestrator.** It is tempting and it is how the
  orchestrator's context and the run's remaining budget both get destroyed. The orchestrator
  delegates, checks, and records — it does not build.

**The retry brief is a different brief.** Do not re-send the original — a fresh agent given the
same brief tends to redo the parts that already worked. Send a narrowed one:

- only the criteria that came back **not met** or **not checked**
- what the first attempt already changed (`CHANGED`), stated as *already done, do not redo*
- its `ASSUMPTIONS` and `LEFTOVER` verbatim — that is where the real obstacle usually is
- everything else (traps, verify command, limits, budget, return block) as before

The uncommitted work from attempt one **stays in the working tree** and the retry continues
from it. Never discard it, and never commit a phase that is still partial — a commit is the
claim that the phase is done.

**A retry counts against the run's cap.** It costs a full phase of budget, so a cap of 5 means
five *attempts*, not five phases plus five hidden retries. If the cap is reached by retries,
the run stops there like any other cap hit and says so.

If the retry also returns `partial` or `blocked`: stop the run, show the user the criteria
table in plain language — which parts work, which don't, what the agent thinks is in the way —
and leave the tree uncommitted for the user to look at.

**3 — Verify — and never claim a pass you did not see.**
- the phase's own `success_criteria`, each one checked explicitly
- **then the project's full regression suite**, every time, after every phase
- capture the raw output. "Tests pass" without the output is not a verification.
- **In a factory project, run the suite through the recorder:**
  `${CLAUDE_PLUGIN_ROOT}/scripts/verified.py <repo> -- <verification command>`. The commit lock refuses a commit
  whose content is not exactly what the tests last passed on, so stage everything the run tested and
  commit straight after it, changing nothing in between.
- **red = stop the whole run.** Do not start the next phase. Do not "fix it later". Report
  which suite failed, with its output.
- **In a factory project, then the size:** `${CLAUDE_PLUGIN_ROOT}/scripts/budget-check.py <project>`. Over the
  code budget = stop the run (condition 7). Do not trim code to squeeze under it inside the phase:
  the choice between simplifying and raising the number is the user's.

**3b — Review against the design, by someone who did not write it — factory projects with a
`TRACE.md`.** Green tests prove the code agrees with its own tests, and the builder wrote both, so a
misreading of the design passes both. the first factory app went eighteen phases like that and its final
check found about 45 places where the code did not do what the design says — a pause button that
did not pause, a detector replacement that silently broke every folder using it.

So before the commit, spawn a **fresh reviewer subagent** — never the builder, never the
orchestrator — and give it only: this phase's trace rows with their design text quoted and their §,
the prototype functions those rows name, and the files in `CHANGED`. It reads, it never edits, and
returns exactly:

    PHASE:       <number>
    MISMATCHES:  §<id> — design: "<quoted>" — code: "<quoted>" — <file:line>   (or none)
    STAND-INS:   <code that fakes, hardcodes or skips a design item with no STAND-IN marker — file:line>  (or none)
    UNSURE:      §<id> — <what the code could not settle>                    (or none)

A mismatch quotes **both** sides; "looks different" is not one. Any mismatch or unmarked stand-in
makes the phase `partial`: one retry (2b) whose criteria are those lines, verbatim; a second
`partial` stops the run. `UNSURE` lines go into the run report for the user and do not block. The
review costs one small subagent per phase — it sees one phase's rows and changed files, not the
project — and it is the cheapest place this drift will ever be caught.

**3c — Audit the phase for half-done work, before the commit.** Green gates cannot see work that
only *reads* as finished. The reviewer in 3b (or, with no `TRACE.md`, a fresh subagent given the
same checklist) checks, and reports as `MISMATCHES`:
- stubs the suite cannot see: a literal `0`, `[]` or `None` passed where a real value belongs, and a
  docstring or comment describing behaviour the code does not implement;
- every row the phase marks `done` is **reachable by a user** — a dialog with no button that opens
  it is not built;
- caller-controlled inputs (query parameters, posted form fields) cannot crash a route
  (`.index()`, `int()`, a dict lookup on raw input);
- no read path can write — a button the design calls a report must not fall through to the branch
  that commits;
- dead exports (constants and helpers nothing references): wire, test or delete;
- the real SQL ran against a real database (`realdb_url`), because fakes prove the logic and never
  the queries.

**4 — Keep the map true, in the same commit.** If the change touches anything the project's
maintenance rules list (schema, chokepoint, trap, job, role/gate, test procedure…), update
that document **in the commit that makes the change** — not afterwards. Append the dated
revision line the project's convention asks for.

**5 — Commit.** One commit per phase, message naming the phase number and what it did.
**Never `git push`.** Local history only.

**6 — Record.** Update the register row to done + the commit hash, and refresh `STATE.md`
so a dead session can resume. Then next phase, fresh context.

## The eight stop conditions

Stop the run, report where it stopped and why, and leave the tree committed and green:

1. **A test went red** — the phase's own criteria or any regression suite.
2. **A phase came back unfinished twice**, or came back `blocked` (see 2b — `blocked` gets no
   retry at all).
3. **The next phase has no written success criteria.**
4. **An ambiguity that would change direction.** If resolving it either way produces a
   materially different build, stop and ask. If it is only a detail, decide it, and write the
   assumption into the run report — do not silently absorb it.
5. **The phase cap was reached** — counting retries as attempts.
6. **The work reached a deploy, a push, a production migration, or anything outward-facing.**
   Halt there and ask — mid-run is exactly when this rule matters most.
7. **The app crossed its code budget** (`budget-check.py`) — show the user where the lines are
   (its output lists the largest parts) and ask: simplify, or raise the number with a dated revision.
8. **The phase marked `real run` in the register is committed.** Stop, and put the real run to
   the user in plain words: what will be started where, which real systems it reads, that it
   writes nothing, and how it is undone. On the user's go the app runs **read-only** against them; every
   defect it finds becomes one fix phase, built and green before any later phase starts. This is
   where the first factory app found eight defects in a day — after its last phase instead of its sixth.

The only one of these that leaves an uncommitted tree is 2 — a twice-unfinished phase, kept for
the user to look at.

## Never, in this mode

- deploy, restart a live service, or make anything publicly reachable
- `git push`, publish, or release
- run a migration or a script against production data
- write into the project's `reports/` folder more than the one run report
- invent a phase, a success criterion, or a test command
- reuse a phase number, or allocate one anywhere but the register
- report a success that was not verified with output in hand

## The design trace — when the project has a `TRACE.md`

The trace is how "nothing from the design is lost" is proven rather than hoped for.

- **Brief.** Field 3 (CRITERIA) carries the phase's trace rows verbatim, with the quoted design
  text `build-spec` put in the phase prompt. Field 4 (START FILES) adds the design sections
  (file + §) and the prototype functions those rows name — quoted where short, so the subagent
  does not go hunting through the whole design.
- **Record.** When a phase comes back complete, set each row it built to `done` with its
  `verified by`, in the **same commit** as the code. A row is never `done` without the test that
  proves it.
- **Never bend the design to fit the code.** If the subagent reports that a row cannot be built as
  designed, or that it built it differently, the phase is `blocked`: stop the run and put the
  conflict to the user. Changing the design or the trace to match the code is drift wearing a
  green tick.
- **After the last build phase.** When the register has no open build phases left, run the
  `final-check` skill before the run's report, and put its verdict at the top of the report.

## Reporting — one report per run

At the end, write **one** `<project>/reports/YYYY-MM-DD run — phases N–M.md`, with a short block
per phase inside it: what was built, the criteria met, the commit, and what is left.

**Not one report per phase.** A five-phase run producing five reports buries the one thing a
reader needs — the current truth and the durable decisions. The per-phase detail already lives in
`PROGRESS.md` and in git.

The report also carries a **"How it works / design & logic"** section for the run as a whole: what
the phases together changed about the system, and any assumption made under stop-condition 4.

## Resuming a dead run

Assume every run may end without warning. On resume, **establish the real state from evidence,
never from the register alone** — the register is written by the run, so a run that died before
updating it is exactly the case where it lies.

1. Read `STATE.md` — which phase was about to start.
2. `git log` and `git status` — which phases actually committed, and whether the tree is dirty.
3. **Re-run the verification command.** This, not the register, is what tells you the code is
   really green.
4. If a phase is half-built (dirty tree, no commit): show the user the diff and ask whether to
   finish it or discard it. **Never discard uncommitted work on your own**, and never assume it
   was finished.
5. Restart from the first phase that is not both committed and green.

## Speaking to the user during a run

Assume the user may not be a programmer: jargon does not inform, it slows them down. Every
between-phase line and the final report follow the plain-language rule in `factory-guide`:
**the plain sentence first, the evidence second, the technical detail only if they ask.** "Phase 42 is done and nothing else broke" is the report; the suite names and the
migration number belong underneath it, not in front of it.

## Not in scope (deliberately, for now)

**Parallel phases.** Running several phases at once is a separate, later capability, and it is
not free: a project with sequential migration numbers has a global serializer (two parallel
phases both take the next migration number and collide), and most phases genuinely depend on
the one before. When it is built it will need a conflict analysis (file overlap + migration
need) producing waves, each wave on its own git worktree, merged and fully re-tested between
waves. Do not improvise it inside this skill.
