---
id: 0007
title: Every address, limit, timeout and interval is a typed setting, never a literal in code
status: accepted
date: 2026-09-15
---

## Context

A value written into code can only change with a deploy, and the same number gets written twice in
two places that then drift. The requirement for every app: nothing hardcoded — everything
configurable and measurable. The working shape, proven on an earlier project: seventy typed
settings in `app/core/config.py`, each with its unit in its name
(`health_ping_timeout_seconds`, `sale_amount_max_minor_units`).

## Decision

Every value that could differ between deployments or be tuned — addresses, credentials, limits,
timeouts, intervals, thresholds, switches — is a typed field in the settings module
(pydantic-settings), named with its unit, read from the environment. Code reads settings; it never
reads the environment itself and never writes such a value as a literal.

## Consequences

More fields, and longer names (`collection_page_delay_seconds`). Once the module grows it is split
by domain rather than kept as one class. Tests construct settings explicitly. A **fact of a
platform** — Telegram's 4,096-character message limit — is a named constant with its source in a
comment, not a setting: nobody tunes it.

## Alternatives rejected

**A constants module.** Still needs a deploy to change and still invites a second copy. **All
configuration in the database.** Hides configuration from review and from the deploy that depends
on it; business definitions that an admin edits are a separate thing and live in their own tables.

## Enforcement

```json
{
  "governs": ["app/**/*.py"],
  "forbid": [
    {
      "pattern": "\\bos\\.(?:environ|getenv)\\b",
      "except": ["app/core/config.py", "app/**/config.py", "app/**/settings.py"],
      "message": "Read configuration through the settings module, never the environment directly. Add a typed field with its unit in the name."
    },
    {
      "pattern": "[\"']https?://[^\"'\\s]+[\"']",
      "except": ["app/core/config.py", "app/**/config.py", "app/**/settings.py"],
      "message": "An address in code can only change with a deploy. Make it a settings field (e.g. manshoor_api_base_url) and read it from settings."
    }
  ],
  "review": [
    "Every limit, timeout, interval and threshold is a settings field whose name carries its unit (_seconds, _days, _minor_units, _count); platform facts are named constants with their source."
  ]
}
```
