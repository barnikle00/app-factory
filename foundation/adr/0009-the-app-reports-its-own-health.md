---
id: 0009
title: Every app reports its own health — alive, ready, and each job's last success
status: accepted
date: 2026-09-15
---

## Context

The requirement: the system can measure its own health. The cost of not having it was measured
on an earlier project: a nightly export died silently for 16 days, and 17 days of data could never
be recovered, because nothing showed it was failing. Another app reported health only as a
summary message, and its compose file health-checked only the database — a dead dependency and a
dead app look the same from outside.

## Decision

Every app serves `GET /health` — alive: answers fast and touches no dependency — and
`GET /health/ready` — ready: checks the database and every backing service, each within a time
limit (ADR 0008), and answers 503 naming the one that failed. Every scheduled job records its last
success and last failure where `/health/ready` and the panel can read them, and a job that has
missed its window makes the app not ready. The container's healthcheck calls `/health`.

## Consequences

A small health module in every app, and a last-run record per job. Readiness checks must be cheap
and time-limited, or the health check becomes the outage. Liveness must never check the database:
a database outage would then restart a healthy app in a loop and make recovery harder.

## Alternatives rejected

**Logs only.** Nobody reads them until after the damage. **An external uptime ping only.** It sees
a web server answering, not a session that died or a job that stopped firing.

## Enforcement

```json
{
  "governs": ["app/**/*.py"],
  "review": [
    "GET /health exists and touches no dependency; GET /health/ready checks the database and every backing service within a time limit and names the failure.",
    "Every scheduled job writes its last success and last failure, and /health/ready reports a job that has missed its window."
  ]
}
```

**This ADR deliberately has no `forbid`.** Whether an endpoint exists cannot be read from one edited
line. It is checked where it can be: `final-check` calls both endpoints on the running app.
