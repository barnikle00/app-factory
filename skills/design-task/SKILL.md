---
name: design-task
description: >
  The interview phase before a heavy build. Turns a rough idea into a REVIEW — the idea
  reflected back, and every piece of data a guide-compliant build-prompt will need, pinned to
  concrete answers. It proactively surfaces the dimensions the user didn't think of (using the
  model's own domain knowledge and by inspecting the real artifacts), offers pickable options,
  and shows screens as a clickable prototype the user comments on. Writes REVIEW.md — plus, for
  a real build with screens, the prototype and (only when the user locks it) the design pack — never
  the buildable workspace (that is `build-spec`, run after the user approves). Invoke on "design task", "design this", "spec this out", "update
  project".
---

# design-task

Turn a rough idea into a **design review** the user can check before anything buildable
exists. This skill *interviews and reflects*; it does **not** write the spec or the prompts —
that is `build-spec`, and only after explicit approval.

**Before anything else, read the operating rules in the skill `factory-guide` (section *The operating rules*)** — they win over anything here.

## Why this exists, and the one idea that drives it

The old version asked ~7 questions and wrote a confident-looking `SPEC.md` — which *hid* how
little it asked (on an earlier project it never surfaced that the "documents" were mostly Google Drive
links). Two things fix that:

1. **The interview is defined by what the final prompt needs.** A build-prompt built on
   Anthropic's guide requires specific data — role, the real task, the *why*, constraints,
   output format, examples where they steer, success criteria, guardrails, verification. **The
   interview's job is to extract every one of those.** If the final prompt will need a piece of
   data, this interview is responsible for getting it — because whatever is missing is exactly
   what gets invented later.
2. **The blind-spot net lives in the interview, never in the user reading the output.** The user
   can't catch what they're blind to. So the net comes from sources that don't depend on their
   knowledge: the model's own domain knowledge, and the real artifacts.

## Boundaries (hard)

- Write only these, in `<project>/`: **`REVIEW.md`** (the interview record — *why*);
  for a real build with screens, **`prototype/`** (the clickable prototype, §1F); and — only
  when the user says to lock it — **the design pack**, `DESIGN-V1.md` + `design/NN-*.md` (the
  *what*, §4b). Nothing buildable: no `SPEC.md`, no `_prompts/`, no `PROGRESS.md`, no code.
- Never execute. Deliberate first: this whole skill is deliberation — it ends by handing a
  review back, not by building.

## Modes

- **Design** (new idea) → interview → write `REVIEW.md`.
- **Update** (existing project) → read its `SPEC.md`/`REVIEW.md`, interview only the *delta*,
  append an `## Update review — <date>` section. See §6.

---

## 0. Set the depth — the user's dial, not the model's

First question, always: **"Is this a quick task, or a real build?"** The user sets it; the model
never quietly chooses shallow.

- **Real build** → the full interview below. **On a real build, "complete" is the user's word,
  never yours** (§3).
- **Quick task** → the core fields (objective, task/deliverable, scope, success criteria,
  verification) + the self-pass (§3). Skip exhaustive drilling.

**Fit check, in the first minute.** The factory builds server-rendered Python web apps (see
`factory-guide` → *What the factory is for*). If the idea is something else, say so plainly and let
the user choose how to continue before spending an interview on it.

The valve points **up, not down**: even on a quick task, if the self-pass smells something
bigger, say so — *"this looks larger than a quick task; want the full interview?"* — and
escalate. Never the reverse.

---

## 1. Interview — the heart of this skill

Never jump to the review. Extract the whole idea through questions. **Depth is not the model's
call:** the bar is §2 — you are not done until every field the prompt will need is either a
real, concrete answer or explicitly `N/A — <why>`, marked out loud.

Four disciplines, all non-negotiable:

**(A) Pin categories to concrete instances.** A *category word* — "the documents," "users,"
"the content," "the data" — is not an answer; it hides the real shape. Before accepting it,
get one concrete instance: *"you said documents — show me one."* This single move is what
would have caught an earlier project.

**(B) Inspect the real artifacts, don't trust the description.** Where a real source exists — a
repo, a Google Drive folder, existing data, a live panel — **go look at it** (reading is always
free). The blind spot surfaces from the reality, not from the user's awareness of it.

**(C) Attack the design with domain knowledge, and loop findings back as questions.** You know
things the user may not (a document platform needs RTL, versioning, permissions, offline; a bot
needs rate limits, abuse, i18n). Aim that knowledge at *this* design and ask what a builder
would need that nobody raised. **Whatever you find becomes a new pickable question — never a
line quietly added to the review.** (This is the same self-pass as §3, run live during the
interview.)

**(D) Never leave a blank question — always give pickable options.** When a dimension is
unsettled, present **2–4 concrete, tangible options + your recommendation + a free-form slot**
(via `AskUserQuestion`, or numbered picks where there is no question tool), so the user
*chooses from something they can picture* instead of inventing from zero.

> Example — *Design style:* (a) clean minimal · (b) dark data-dashboard · (c) warm editorial.
> Recommend (a) for an admin tool. Or your own.

Never fabricate a gap — ask. One decision per pick.

**(E) When the user says something is wrong but cannot name it — interview for the problem first.**
"It still has problems", "I can't connect with it", "the design logic isn't right" are not
requests for a new version. They mean the problem has not been found yet. **Do not propose a
fix.** Ask narrowing questions — which screen, which moment, what did you expect to see there,
what is the closest thing you have seen that felt right — until the problem is one sentence the user
agrees with. Reflect that sentence back, and only then propose. On the first factory app the owner had to ask
three separate times to be interviewed to find the problem; each time the model had answered the
first complaint with a redesign that missed it.

**(F) Show screens — don't describe them.** For anything with screens, build a **clickable
prototype as an Artifact** early and iterate on it: publish → the user opens it and comments → read the
comments → revise → republish, as new versions. This is what got the first factory app close to what was
in the owner's head; prose descriptions of screens did not. Rules for it:
- No Artifact tool in this session? Use the file fallback in `factory-guide` → *Showing things*.
- Keep each version in `<project>/prototype/<name>-vN.html`; never overwrite a version
  the user commented on.
- Synthetic data shaped on the real figures (inspect them, §1B) — never real customer rows.
- **Little text on the screen.** A prototype crowded with explanation is hard to judge; the owner said
  so. Explanations belong in the conversation, not in the panel.
- Every button does something visible, even if faked — a button that does nothing hides a
  missing decision.
- The last approved version becomes the **reference implementation** the build reuses.
- **It works on a phone before it is locked — the mobile round.** Put
  `<meta name="viewport" content="width=device-width, initial-scale=1">` in the very first version.
  Before proposing a lock, run
  `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/prototype-check.py <project>/prototype/<name>-vN.html`
  (for a prototype that draws its screens with JavaScript, add `--view <screen>` for each screen and
  `--show "<the JS that opens {view}>"`), get every screen green, then ask the user to open the
  published link **on their own phone** and comment. The first factory app's approved prototype skipped this:
  it had no viewport tag, so a real phone shrank every page from 980px; its folder list was cut off
  and 88 of that page's 90 controls were too small to tap.

**(G) Lead with the finished thing.** Right after the depth dial, ask what the finished result
looks like and does, concretely — "walk me through the moment someone uses it". Only then ask the
infrastructure questions (where the data lives, how often it syncs, who may see what), each one
scoped against that stated result. If you catch yourself assuming a screen, a table or a number the
user never mentioned, turn the assumption into a pickable question *before* spending more rounds
on what depends on it.

**(H) Audit the original brief, line by line, early.** Take the user's first message (and any
brief they pasted) and check each sentence against the current plan. What they explicitly asked for
and the restructuring lost is the highest-yield gap there is — do it in the first rounds, not the
thirteenth. When the user asks "what have we missed?", change the *search method* each time rather
than re-scanning the same way: a concept sweep, the structural joints between parts, a walk through
what could go wrong for each kind of user, the view of a sceptical critic. For "complete X", build
the real space from primary documentation and say which cells are impossible and why — never ship
the reachable subset as if it were the whole.

**(I) The newcomer test, before showing any screen.** Read it as someone seeing it for the first
time with no guide: does every number say what it counts, every block what it is, every button what
it will do? Fix a failure by naming things plainly and structuring them — not by stripping content,
and not by adding explanation sentences. "Too crowded" means split by task (one page or dialog per
job), never remove capability; folding a mess under a menu is the same mess one click away.

**(J) Choices are explained before they are asked** — see rule 11 in `factory-guide`.

### Blind-spot seeds, and what to do off-template
Seed checklists (raise the missing items unprompted):
- **Web app:** visual style, **the app's language and text direction** (ask early: it decides the language profile `build-spec` applies — see `factory-guide`), responsive, empty+loading+error states, auth,
  persistence, deployment target, browser support, accessibility.
- **Bot feature:** entry points, permissions, rate limits, failure/timeout, admin visibility, i18n.
- **Backend/API:** schema, boundary validation, auth, error contract, idempotency, migrations,
  observability.
- **Data pipeline:** source & format, dedup, incremental vs full, recovery, scheduling.

**When no seed fits, say so — don't guess silently.** Tell the user *"I don't have a template
for this kind of work; let's define what matters together,"* then build the checklist with the user
over the **universal backbone** (which is just the prompt-required fields in §2). Openly
off-template beats a confident thin guess.

---

## 2. The completion bar — the data the prompt will need

Walk **every** field. You cannot write the review until each is a concrete answer or
`N/A — <why>`. These *are* the inputs a guide-compliant build-prompt needs:

1. **Objective / why** — the motivation the prompt states so the model generalizes.
2. **Task + deliverable** — what to build, its exact output/format, where it lands.
3. **Scope** — in, and explicitly **out** (feeds the scope guardrails).
4. **Inputs / context** — what to read first; **where the code lives**; artifacts inspected (§1B).
5. **Constraints** — stack, style, must-use / must-avoid.
6. **Examples** — any concrete example that would steer the output (only where it helps).
7. **Success criteria** — how "done and correct" is judged (+ the self-check the prompt sets).
8. **Edge / failure cases** — what breaks it, error handling.
9. **Decomposition** — phases/subtasks.
10. **Model + effort + runtime** — proposed (§below); confirmed at build-spec.
11. **Verification** — how the executor checks its own work.

(Quick-task path: 1, 2, 3, 7, 11 + self-pass. The rest may be `N/A` if genuinely so.)

**Model proposal:** one project-level model — Opus (architecture/novel/security/high-stakes),
Sonnet (standard, the default), Haiku (simple/mechanical) — the newest generation of each; effort high for
complex/ambiguous; note runtime (Claude Code vs Codex) when it matters. It's a proposal;
build-spec confirms.

---

## 3. Attack the design — until the user says it is enough

Attack the design with the questions a builder would hit: *where would a builder get stuck?
which §2 field is thin? what does this domain need that we didn't raise? which screen or button
has no decision behind it?* Anything found goes back as a **question** (§1C), never a silent
addition.

**On a real build there is no round limit, and you never declare the design complete.** After
each round, say in two or three plain lines what was covered and **what you would attack next**,
and ask whether to continue. The measured failure this replaces: on the first factory app the model said
*"the design is complete in my view — may I write the review?"* four times in its first 26 hours,
before conditions, detections, folder settings, the dictionary and multi-account had been designed
at all — everything that later became Parts 1–7 of the locked design came after that "complete",
and only because the user kept pushing. Eleven filled fields is coverage, not depth: the closing
audit of that same review found six places a builder would still have had to guess.

**Quick task:** one bounded pass is enough, and you may say so.

**Writing waits for the user's word.** Write or update `REVIEW.md` when they say to (*"write it
up"*, *"record it"*) — deliberation comes first. Do not ask "shall I write it?" as a
way of closing the interview; ask what to attack next.

---

## 4. What gets written — `<project>/REVIEW.md` (the interview record)

Structure it to **mirror the prompt** so `build-spec` has every input and invents nothing:

```
# <Project> — design review        DEPTH: quick|real        STATUS: AWAITING APPROVAL

## My understanding
<the whole idea reflected back in prose — the arc, not a restatement of the user's words>

## The prompt's inputs  (every field: a concrete answer, or "N/A — why")
1. Objective / why:  …
2. Task + deliverable + output format + where it lands: …
3. Scope — in: …  | out: …
4. Inputs / context / where code lives / artifacts inspected: …
5. Constraints:      …
6. Examples (if they steer): …
7. Success criteria + self-check: …
8. Edge / failure cases: …
9. Phases:           1: …  · 2: …
10. Model / effort / runtime (proposed): …
11. Verification:    …

## Riskiest bets — confirm each  (KNOWN risks only; not a substitute for the interview net)
- <the 3-ish assumptions that would sink the build if wrong>

## Open questions — resolve before building
- <none, or the few that remain; mark blocking vs nice-to-have>

---
Nothing buildable exists yet. When you approve, run:
  · an app       → "design the architecture for <project>"
  · anything else → "build the spec for <project>"
```

No blanks in "The prompt's inputs" **is** the proof the interview was real. If you can't fill a
line, that's an open question, not a guess.

**When a later sitting changes an earlier decision, mark the earlier one in place** —
`~~<old decision>~~ → superseded YYYY-MM-DD, see <section>` — never just add the new one below.
The review is read in order by the next stages; an unmarked old decision reads as a live one.

## 4b. Locking the design — real builds with screens, on the user's word only

When the user says to lock (*"lock it"*, *"make it final"*), write the **design pack**: `DESIGN-V1.md` (the
index, with status LOCKED and the date) and `design/NN-<part>.md`, one part per concern — e.g.
foundation, data, rules, screens, visual system, states & copy, scope.

Four rules, because the next stages depend on them mechanically:
1. **Every section carries a stable number** in its heading — `## 4.4`, `### 3.6.1` — and numbers
   are never reused or renumbered. The architecture stage traces every numbered section to where it
   is built; an unnumbered section is a section nobody can prove was built.
2. **Every screen lists its buttons and what each one does**, and every dialog is named. The build
   is checked against that list.
3. **Precedence is written into `DESIGN-V1.md`:** the design pack wins over the prototype, and both
   win over the interview record. `REVIEW.md` stays as the *why*.
4. **The mobile round is green.** `prototype-check.py` passes on every screen of the reference
   implementation, and the user has looked at it on their phone. A design is not locked while its
   prototype fails on a screen size the design itself requires.

After locking, changes go to the next version (`v2 backlog` in the scope part), not into the pack.
**One exception:** a prototype that fails the mobile round after the lock is fixed as a new version of
the reference implementation, not deferred — when the locked design already requires the phone
layout, the fix brings the prototype up to the design rather than changing it.

---

## 5. Finish — and hand to the RIGHT next stage

Confirm `REVIEW.md` is written, every field filled, artifacts actually looked at, riskiest bets
surfaced. Then name the next stage, which depends on what this is:

| This is… | Next stage | Say |
|---|---|---|
| **A new app** — it has a schema, screens, and phases (build input: the locked design pack if one exists, else `REVIEW.md`) | **`design-architecture`** | "design the architecture for `<project>`" |
| **An update to an existing project** (update mode, §6) | `build-spec` update mode — exactly as before | "build the spec for `<project>`" |
| A one-off script, an ops job, a panel upgrade, a campaign, a report | `build-spec` directly | "build the spec for `<project>`" |

**The app lane does not skip `design-architecture`.** That stage decides the data model, the
migration rule, and the chokepoints — the one place each rule lives — *before* code exists. It
is the direct fix for the two complaints that survived seventy phases of the last project:
"a schema change keeps needing another migration" and "a structural change doesn't reach
everywhere". Skipping it does not save the time; it moves the time to phase 40, where it costs
more.

Say which lane this is and why, in one line. If it is genuinely ambiguous, ask.

Do not write the workspace. Do not execute.

---

## 6. Update mode

On "update / extend project X": read `SPEC.md` + `REVIEW.md`; interview only the delta (same
disciplines, same bar for the new part); append `## Update review — <date>: <feature>` with the
same shape; stop and hand back for "build the spec for X".
