---
id: 0010
title: Every write to an outside system goes through one guard — off by default, capped, and stopped when it repeats
status: accepted
date: 2026-09-30
---

## Context

the first factory app writes folders into its users' own chat accounts. Its reconciler started
writing the same folder to one customer's personal account on every 5-second tick, and nothing
stopped it for five days: **70,565 writes and 104,090 reads**, the account's first flood waits
ever, and `/health/ready` answering "ready" the whole time. Writing had been switched on from the
panel three days earlier, and no record anywhere knew it. The cause was ordinary — the planner
compared the platform with what it *intended*, the adapter silently sent something slightly
different, so the two never agreed and it wrote again — and ordinary causes will happen
again. What must not happen again is that nothing notices.

A write to someone else's system is the one thing an app does that it cannot take back: a message
sent, a folder written into a person's account, a payment requested, a record changed in another
team's database. The cost of a loop there is not a slow page; it is an account flagged, a customer
spammed, or money moved.

## Decision

Every write to an outside system goes through **one guard per target**, and the guard enforces
four things no caller can skip:

1. **Off by default.** Each target has a switch, stored in the database, off until a person turns
   it on. Turning it on and off is audited — who and when.
2. **A ceiling.** Each target has a maximum number of writes per hour, from settings (ADR 0007).
   Reaching it opens the breaker.
3. **A breaker on repeats.** Writing the same thing to the same place again and again — the same
   key with the same content — means the write is not sticking. Past a small number of repeats in
   an hour, the breaker opens. An open breaker refuses every write to that target until a person
   switches the target off and on again.
4. **Health tells the truth.** `/health/ready` answers 503 naming any target whose breaker is
   open, and lists every switch that is on — so «what is this app allowed to write to right now» is
   one request away, not a question nobody can answer.

The guard is the chokepoint for that target: `ARCHITECTURE.md → Chokepoints` names it, and no other
code calls the outside system's writing methods.

## Consequences

A table for switches and one for each target's guard state; a guard call around every write; a
ceiling and a repeat limit to choose per target, which will be wrong at first and are settings so
they can change without a deploy. A legitimate burst — a first sync, a bulk publish — needs its
ceiling sized for it or a person present to reset the breaker. That friction is the point: it is
where a human looks.

## Alternatives rejected

**Rate limiting only.** the first factory app's loop wrote at a steady rate well inside any sensible limit
per minute; it was the repetition that was wrong. **Alerting on logs.** Nobody was reading them.
**A per-feature kill switch without a breaker.** The switch was on; the loop needed something that
turns itself off.

## Enforcement

```json
{
  "governs": ["app/**/*.py"],
  "review": [
    "Every write to an outside system (a message, a folder, a record in another system, a payment) goes through the target's guard in app/core/outside.py — no caller reaches the client's writing methods directly.",
    "Each target has a switch that is off by default, an hourly ceiling and a repeat limit from settings, and /health/ready names an open breaker and lists every switch that is on."
  ]
}
```

**This ADR deliberately has no `forbid`.** Which method of which client writes cannot be read
from one line — it differs per library and per target. The guard itself is in the starter kit
(`foundation/skeleton/app/core/outside.py`, tested there), the per-phase design review
asks the two questions above of every phase that touches an outside system, and `final-check`
reads `/health/ready` on the running app.
