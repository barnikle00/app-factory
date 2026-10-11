---
id: 0001
title: A schema change is expand, migrate, then contract — never one migration
status: accepted
date: 2026-09-12
---

## Context

Across seventy-one phases of one real project, forty-three migrations were written. Only one
of them was corrective — so the volume is not the problem, and "write fewer migrations" is not
the fix. The problem is that a migration which adds a column, renames another and drops a third
in one step cannot be deployed without a window where the running code and the schema disagree.
That window is where the breakage lives, and it is the reason a schema change feels dangerous.

## Decision

A schema change happens in three separate migrations: **expand** (add the new shape beside the
old one, nullable), **migrate** (the code writes both and reads the new one), **contract** (drop
the old shape, once nothing reads it). Also called *parallel change*.

## Consequences

Three migrations instead of one, and a period — usually a phase or two — where both shapes
exist and the code is uglier for it. Someone must remember to come back and contract; an
un-contracted column is dead weight that outlives the reason for it. In exchange, no migration
in the sequence can take the application down, and any one of them can be deployed alone.

## Alternatives rejected

**One migration with a downgrade path.** The downgrade is written once and tested never; by the
time it matters it no longer matches the code. **A maintenance window.** Fine for a tool nobody
is using at 3am and wrong for anything a business depends on — and it makes every schema change
a scheduling problem, which is how schema changes get avoided and the model rots instead.

## Enforcement

```json
{
  "governs": ["alembic/versions/*.py", "migrations/versions/*.py"],
  "forbid": [
    {
      "pattern": "new_column_name\\s*=",
      "message": "A rename is a drop plus an add wearing one name. Add the new column, move the reads and writes across, then drop the old one in a later migration."
    },
    {
      "pattern": "op\\.add_column\\((?=.*nullable\\s*=\\s*False)(?!.*server_default)",
      "message": "A NOT NULL column with no server_default fails the moment an existing row is read. Add it nullable, backfill, then tighten it in a later migration — or give it a server_default here."
    }
  ],
  "review": [
    "No single migration both adds a shape and removes another. If it does, it is two migrations."
  ]
}
```

**The add-and-drop rule is checked at commit, not on each edit.** One edited line cannot show whether
the same migration also adds something. `scripts/commit-gate.py` reads the whole file and
refuses a migration that does both. A migration that only drops — the legitimate contract step —
passes. *(Until 2026-09-15 this ADR forbade every drop on each edit, which made that contract step
itself a violation.)*
