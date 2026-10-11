---
id: 0004
title: Every list is bounded at the query, from its first version
status: accepted
date: 2026-09-12
---

## Context

"It doesn't scale" is almost never a missing index or a slow framework in applications this size.
It is a query written against the ten rows that existed the week it was written, which becomes a
full-table read at ten thousand and a timeout at a hundred thousand — and by then the page, the
export and three reports all depend on it returning everything. The cost of bounding a list on
the day it is written is one parameter. The cost of bounding it later is a redesign of whatever
grew on top of the unbounded version.

## Decision

Every query that can return more than one row carries an explicit bound — a `LIMIT` with an
offset or a keyset cursor — from the first version, including internal and admin screens, and
including exports. A screen shows a page; an export streams in chunks.

## Consequences

Every list needs pagination in the UI on day one, which is real work on a screen that has four
rows in it. Totals and aggregates must be computed by the database rather than by summing a
fetched list, because the fetched list is now a page. Some genuinely-bounded sets (a
seven-element status enum) carry a limit that will never be reached, which looks silly and costs
nothing.

## Alternatives rejected

**Add pagination when it becomes slow.** This is the status quo, and the measured result is that
it becomes slow after several screens already depend on getting the whole list back. **Cap in the
application after fetching.** The database still does the full read; the only thing capped is how
much of the damage reaches the page.

## Enforcement

```json
{
  "governs": ["app/**/*.py"],
  "review": [
    "Every query returning a collection has a LIMIT, a cursor, or a comment naming the hard bound that makes one unnecessary.",
    "No total or count is computed by summing a list that was fetched to compute it."
  ]
}
```

**This ADR deliberately has no `forbid`.** Every regex considered — `.all()`, `fetchall()`,
`.scalars().all()` — fires on correct code far more often than on the failure, and a rule that
cries wolf is worse than no rule: it teaches an agent to route around the hook, and an agent that
has learned to route around one hook has learned to route around all of them. This one is judged
at review time, where the judgement actually exists.
