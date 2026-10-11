---
id: NNNN
title: <one line, present tense, stating what is true — not "use X">
status: accepted
date: YYYY-MM-DD
---

## Context

<What forced a decision. The constraint that made this a choice at all, not the preference
that made this option attractive. If nothing forced it, this is not an ADR.>

## Decision

<One sentence, present tense. "Money is stored as integer minor units." Not "we will use integers."
A decision that reads as a plan is a plan.>

## Consequences

<What this costs, stated plainly — the thing it makes harder, slower, or uglier. An ADR with
no cost section has not been thought through, and the next person to hit the cost will assume
nobody saw it and reverse the decision.>

## Alternatives rejected

<What else was on the table and why it lost. This is the section that stops the question being
reopened every third phase, and the one that tells a future agent the obvious approach was
already weighed and found wanting.>

## Enforcement

```json
{
  "governs": ["app/**/*.py"],
  "forbid": [
    {
      "pattern": "<regex matching what a violation looks like in a diff>",
      "where": "<optional glob narrowing which governed files this pattern applies to>",
      "except": ["<optional globs where the pattern is legitimate, e.g. the settings module>"],
      "message": "<the repair: name the correct construct, do not just refuse>",
      "fires": ["<a real line of code this rule must catch>"],
      "silent": ["<a line of correct code it must NOT catch — the nearest legitimate look-alike>"]
    }
  ],
  "review": [
    "<a checkable sentence about intent, for what regex cannot see>"
  ]
}
```

<`fires` and `silent` are required on every `forbid` rule of a project ADR: architecture-check
runs the pattern against both, so a rule is tested both ways before it can block anything — the
founding set is tested the same way in `tests/test_adrs.py`. Once the edit hooks block,
a rule that fires on correct code stops work; this is where that is caught.

Drop `forbid` or `review` if it does not apply; keep `governs` always. An ADR with neither
is a note, not a decision — it will be forgotten within a month and nothing will notice.>
