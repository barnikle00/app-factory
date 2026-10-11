---
id: 0008
title: Every call that leaves the process has a time limit, and every retry stops
status: accepted
date: 2026-09-15
---

## Context

Under load, a call to an outside service with no time limit does not fail — it waits, holding a
connection or a worker, until enough of them pile up that the whole app stops answering. Apps
talk to chat platforms, to partner services, to each other's databases and to language models. Library defaults
disagree: `requests` has no timeout at all, `timeout=None` switches httpx's off, and tenacity
retries forever unless told to stop. The requirement: apps must not break under pressure.

## Decision

Every outbound call — HTTP, database, a chat platform, a model API, a subprocess, a queue — carries an
explicit time limit taken from settings (ADR 0007), and every retry is bounded by attempts or by
time. A limit that fires is handled where the call is made.

## Consequences

Time limits have to be chosen, and some will be wrong at first — too short produces false failures,
too long hides the pile-up. Every call site handles the timeout error. Long jobs get their own
budget rather than borrowing a request's.

## Alternatives rejected

**Library defaults.** They differ per library and one of them is "wait forever". **A single global
request timeout.** It never reaches a background job, a chat-platform session or a database pool.

## Enforcement

```json
{
  "governs": ["app/**/*.py"],
  "forbid": [
    {
      "pattern": "\\brequests\\.(?:get|post|put|patch|delete|head|request)\\((?![^)]*timeout)",
      "message": "requests waits forever by default. Pass timeout=settings.<name>_seconds — or use httpx, the stack's pick."
    },
    {
      "pattern": "\\btimeout\\s*=\\s*None\\b",
      "message": "timeout=None switches the time limit off. Use a settings value."
    },
    {
      "pattern": "^\\s*@(?:tenacity\\.)?retry(?:\\(\\s*\\))?\\s*$",
      "message": "tenacity retries forever by default. Give it stop=stop_after_attempt(n) or stop_after_delay(seconds)."
    }
  ],
  "review": [
    "Every outbound call names its time limit from settings; the database pool sets pool_timeout and a statement timeout; every retry has a stop."
  ]
}
```
