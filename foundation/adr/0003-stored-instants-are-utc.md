---
id: 0003
title: Every stored instant is timezone-aware UTC; the display zone is a setting
status: accepted
date: 2026-09-12
---

## Context

A local-time helper was defined independently six times across the projects this factory grew out
of, and the projects that used one disagreed about whether the value they stored was local or UTC.
A calendar day also begins at a different instant for every reader, so "today" in a report is a
question about display, not about storage. Mixing the two produces reports that are off by a day
at the edges — the hardest class of bug to notice, because it is right most of the time.

## Decision

Every instant persisted anywhere is timezone-aware UTC. Conversion to the display zone
(`DISPLAY_TIMEZONE_NAME`, a setting) and to any non-Gregorian calendar happens in the presentation
layer and nowhere else.

## Consequences

Every naive `datetime` is a bug, including the ones a library hands back. Comparisons in queries
must be made in UTC, so a "today in the display zone" filter has to compute that zone's day
boundary and convert it — which is more code than `date(created_at) = today` and is the only
version that is correct. Test fixtures have to be explicit about zone.

## Alternatives rejected

**Store local time.** It makes the common report trivial and every other thing hard: the moment
data arrives from an external API in UTC, the database holds two meanings in one column with
nothing marking which is which. **Store naive UTC.** One `datetime.now()` written by anyone, ever,
silently poisons the column, and nothing raises.

## Enforcement

```json
{
  "governs": ["app/**/*.py", "scripts/**/*.py"],
  "forbid": [
    {
      "pattern": "\\bdatetime\\.utcnow\\s*\\(",
      "message": "datetime.utcnow() returns a NAIVE datetime and is deprecated. Use datetime.now(timezone.utc)."
    },
    {
      "pattern": "\\bdatetime\\.now\\s*\\(\\s*\\)",
      "message": "datetime.now() with no argument returns the machine's local time, naive. Use datetime.now(timezone.utc) for anything stored, or an explicit ZoneInfo(settings.display.timezone_name) when the value is being formatted for a person."
    }
  ],
  "review": [
    "Conversion to the display zone or to another calendar appears only in templates, serialisers or report builders — never before a write."
  ]
}
```
