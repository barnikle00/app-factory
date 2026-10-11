# Architecture Decision Records — the format, and why it is shaped this way

An ADR records a decision that must **stay true** as the code grows. A `SPEC.md` says what to
build; an ADR says what must not drift.

This is the artifact the whole app lane is missing. A coding agent under ambiguity does not
stall — it decides, plausibly, and differently each time. That is the measured cause of
"a structural change doesn't get applied everywhere": nothing wrote the structure down in a
form anything could check.

## What makes these different from ordinary ADRs

A human ADR explains *why*. One in this factory must also state **what a violation looks
like in a diff**, because an unenforced rule decays — the prior art proves it: one project
published a spacing scale in its own architecture document and then broke it in 154 of its
own 203 spacing declarations, with nothing checking.

So every ADR carries an `## Enforcement` block, and that block is executable.

## The file

`<project>/adr/NNNN-kebab-title.md`, numbered from 0001, never renumbered, never deleted.
A decision that stops being true is **superseded**, not edited — the record of what was once
true is the point.

```markdown
---
id: 0012
title: Money is stored as integer minor units, never float
status: accepted          # proposed | accepted | superseded-by-0012
date: 2026-09-10
---

## Context
What forced a decision. The constraint, not the preference.

## Decision
One sentence, in the present tense, stating what is now true.

## Consequences
What this costs. An ADR with no cost section is a preference wearing a decision's clothes.

## Alternatives rejected
What else was considered and why it lost. This is what stops the question being reopened
every third phase — and what tells a future agent that the obvious approach was already
weighed.

## Enforcement
```json
{
  "governs": ["app/**/*.py", "alembic/versions/*.py"],
  "forbid": [
    {
      "pattern": "\\b(Float|Numeric|REAL|DOUBLE)\\s*\\(",
      "where": "alembic/versions/*.py",
      "message": "Amounts are integer minor units. Use Integer or BigInteger in migrations."
    },
    {
      "pattern": "\\bfloat\\(\\s*[a-z_]*amount",
      "message": "Never coerce an amount to float — rounding loses minor units."
    }
  ],
  "review": [
    "Any new column, field or API value that holds money is an integer count of minor units."
  ]
}
```
```

**`forbid`** is machine-checked on every write, by regex, at zero model cost.
**`review`** is prose the commit-time verifier judges, for what regex cannot see.

**The block is JSON, not YAML, on purpose.** A hook must never fail because a library is
missing, and `json` is in every Python's standard library while `PyYAML` is installed on
neither Python on this machine. The checker reads only this block plus the `status:` line — so
the frontmatter above stays purely human-facing and no fragile parser sits in the hot path.

## Two tiers of enforcement, and why the split matters

| Tier | When | Cost | Catches |
|---|---|---|---|
| `forbid` regexes | every `Write`/`Edit`, via `scripts/adr-check.py` | none — no model call | the literal, mechanical violations |
| `review` prose | once per `git commit`, over the staged diff | one small model call per commit | intent-level drift regex cannot express |

**The expensive check is deliberately not per-edit.** An agentic verifier on every keystroke-
sized edit would add a model call to each one, and the binding constraint is
the usage quota, not the context window. A per-commit check catches the same violation before
it can possibly reach anyone, and costs a fraction as much.

## Writing a good `forbid`

- **Anchor it to what a violation actually looks like**, not to what the rule is about.
  `float(amount` is checkable; "money must be precise" is not.
- **Scope it with `where`** when the pattern is only wrong in some files — a regex that fires
  in tests and fixtures gets the whole ADR ignored.
- **Prefer a false negative to a false positive.** A rule that misfires teaches an agent to
  route around the checker, which is worse than the rule not existing. The `review` line is
  where the uncertain half belongs.
- Every `message` is a **repair instruction** naming the correct construct, not a complaint.

## Superseding

Set the old ADR's `status: superseded-by-NNNN` and write the new one. Never delete, never
rewrite history — a future reader needs to know the old rule existed, or they will
re-derive it and be confused when the code disagrees.

---

## The founding set

Ten ADRs live here and are **copied into every new app-lane project** at scaffold time, before
its first phase. They are not suggestions and they are not anyone's taste — each one is
a failure that has already happened here, written in a form `adr-check.py` can apply:

| | Decision | The failure it closes |
|---|---|---|
| `0001` | A schema change is expand → migrate → contract | 43 migrations in one project, each one a deploy risk it did not need to be |
| `0002` | Money is an integer count of the smallest currency unit, never float | Reconciliation drift nobody can source |
| `0003` | Stored instants are UTC; the display zone is a setting | A local-time helper defined 6 independent times, disagreeing about what it stores |
| `0004` | Lists are bounded from the first version | "It doesn't scale" — a query written against ten rows |
| `0005` | JavaScript is enhancement, never mechanism | A page that looks complete and does nothing when the script does not arrive |
| `0006` | User input is normalised at the boundary — digits of any script, one spelling | 4 independent implementations, and the fifth path nobody added one to |
| `0007` | Every address, limit, timeout and interval is a typed setting | A value that only a deploy can change, written twice and drifting |
| `0008` | Every outside call has a time limit, every retry stops | A slow service holding every worker until the app stops answering |
| `0009` | Every app reports its own health | A nightly export dead for 16 days, 17 days of data lost, nothing showing it |
| `0010` | Every write to an outside system is guarded — off by default, capped, stopped when it repeats | the first factory app wrote one folder into a customer's own account 70,565 times in five days, health said «ready» |

`0004`, `0009` and `0010` deliberately carry **no `forbid`** — every regex considered fires on correct code more
often than on the failure. That is recorded in the ADR itself, because "we chose not to enforce
this mechanically, and here is why" is a decision worth as much as the rule.

**Every `forbid` in them is tested both ways** in `tests/test_adrs.py`: each pattern must fire on a
real violation *and* stay silent on correct code. A rule that only passes the first test is how
an agent learns to route around the hook.

A project numbers its own ADRs from `0100` — the founding set grows (0010 joined on 2026-09-30),
and a project's own numbers must never collide with a founding decision added after it started.

### `except` — where a pattern is legitimate

A `forbid` rule may list `except` globs. `0007` forbids reading the environment everywhere except
the settings module — the one place that must. Without `except` that rule could only be written as
a false positive, and a rule that cries wolf teaches an agent to route around the hook.
