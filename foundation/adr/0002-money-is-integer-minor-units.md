---
id: 0002
title: Money is stored and computed as an integer count of the smallest unit, never as a float
status: accepted
date: 2026-09-12
---

## Context

Every application that handles money meets the same trap: a float carries 15–17 significant
decimal digits, so a sum of a few thousand transactions drifts — silently, and in a direction
nobody predicts. In a currency with no subunit (the rial, the yen) amounts routinely run to ten
digits; in one with cents the drift shows up in the last cent of every report. A reconciliation
that is off by one unit is indistinguishable from a bug in the reconciliation, and the search for
it costs more than this decision ever will.

## Decision

Monetary values are integers of the currency's smallest unit (cents, rial, yen), end to end: the
column is `BigInteger`, the Python value is `int`, the API sends an integer, and only the display
layer divides or formats.

## Consequences

Every amount arriving from a form or an external API must be converted at the boundary, and a
source that quotes in a larger unit (toman for rial, dollars for cents) needs an explicit
multiplication with the conversion written down. Percentages and splits need deliberate rounding
rules — the code cannot fall back on "close enough". Anything genuinely fractional (a rate, a
coefficient) must be stored separately from the amounts it multiplies.

## Alternatives rejected

**`Decimal`.** Correct, and it survives round-tripping through JSON and ORMs badly enough that
half the codebase ends up converting anyway — at which point the guarantee is gone but the
ceremony remains. **Float with rounding at the edges.** This is what "we'll be careful" produces,
and the error it creates is invisible until a total is wrong by an amount nobody can source.

## Enforcement

```json
{
  "governs": ["app/**/*.py", "alembic/versions/*.py", "migrations/versions/*.py"],
  "forbid": [
    {
      "pattern": "\\b(?:Float|Numeric|REAL|DOUBLE_PRECISION)\\s*\\(",
      "where": "*versions/*.py",
      "message": "Amounts are integers of the smallest currency unit. Use BigInteger in migrations. If this column is genuinely a rate or a coefficient rather than money, name it so and supersede this ADR for that case."
    },
    {
      "pattern": "\\bfloat\\s*\\(\\s*[\\w.\\[\\]'\\\"]*(?:amount|price|total|balance|rial|toman|cents|payment)",
      "message": "Never coerce an amount to float — the rounding loses units and the loss is invisible. Keep it int; format only at the point of display."
    }
  ],
  "review": [
    "Any division of an amount states its rounding rule explicitly, rather than relying on the language's default."
  ]
}
```
