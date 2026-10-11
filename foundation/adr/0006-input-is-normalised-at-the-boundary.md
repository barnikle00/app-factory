---
id: 0006
title: User input is normalised at the boundary, never inside business logic
status: accepted
date: 2026-09-12
---

## Context

A phone keyboard set to Persian produces `۱۲۳`; one set to Arabic produces `١٢٣`; one set to
Hindi `१२३`. `int()` raises on all of them, and text typed on such keyboards often arrives in more
than one spelling of the same letter. On the projects this factory grew out of there were four
independent implementations of digit normalisation, applied in four different places — one at the
form, one in a service, one in a template filter, one inline at a call site. The result is that
whether a number works depends on which path it took through the application, and the failure
appears as a 500 on one screen and correct behaviour on another.

## Decision

Every value arriving from a person — form field, query parameter, uploaded file, bot message — is
normalised at the point it enters the application: digits of any script become ASCII, text is
composed and trimmed (`normalize_digits()` in `app/core/text.py`). Past that boundary, business
logic assumes the normalised form and never normalises again. A language profile may add
language-specific letter folding to the same function.

## Consequences

Every entry point needs the conversion, including new ones, and forgetting it produces a clear
error at the boundary rather than a wrong number deeper in. Anything genuinely textual that
contains native digits — an address, a note — must not be passed through the normaliser, so the
boundary has to know which fields are numeric. Output is a separate decision: figures are
rendered in Latin tabular digits by default because a column of money must line up and be
copy-pasteable, and in native digits only in prose.

## Alternatives rejected

**Normalise inside each parser.** That is the measured state of the earlier projects: four
implementations, and the fifth path that nobody added one to. **Normalise in the template layer.**
It fixes display and leaves every write path broken.

## Enforcement

```json
{
  "governs": ["app/**/*.py"],
  "forbid": [
    {
      "pattern": "\\b(?:int|float|Decimal)\\s*\\(\\s*(?:request|form|params|query|payload|message\\.text)\\b",
      "message": "Raw user input goes through normalize_digits() first — a keyboard set to another script sends digits that int() rejects. Normalise at the boundary, once."
    }
  ],
  "review": [
    "Every new entry point normalises numeric input at the boundary, and no business-logic function normalises again."
  ]
}
```
