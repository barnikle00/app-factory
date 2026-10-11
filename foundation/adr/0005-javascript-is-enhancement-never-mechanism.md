---
id: 0005
title: JavaScript is enhancement; the mechanism is always HTML
status: accepted
date: 2026-09-12
---

## Context

These are server-rendered Python applications with no build step, used on slow and unreliable mobile networks
where a script can simply fail to arrive. When behaviour lives in JavaScript, a slow or blocked
script does not degrade the page — it produces a page that looks complete and does nothing when
touched, which is the worst failure mode available because the user cannot tell it apart from
their own mistake.

## Decision

Every action is a form submission or a real link. JavaScript may remove a step, never create one.
Deleting the script file must leave every page fully usable.

## Consequences

Some interactions take a round trip that a single-page approach would do locally, and a few
screens are plainer for it. Filtering means a `GET` with query parameters rather than live
updating; a confirmation is a real dialog element rather than a custom overlay. In exchange, the
back button works, a link can be shared, a page can be bookmarked, and the failure mode of a bad
network is a slow page rather than a dead one.

## Alternatives rejected

**HTMX or a similar library.** Genuinely good, and it makes the mechanism a library's attribute
rather than the browser's — which means the same dead-page failure when the library does not
load, plus a dependency in every template. **A front-end framework.** It buys interactivity these
applications do not need and costs the build step the whole workspace is organised around not
having.

## Enforcement

```json
{
  "governs": ["app/**/*.html", "app/**/*.jinja", "app/**/*.js", "templates/**/*.html"],
  "forbid": [
    {
      "pattern": "\\son(?:click|submit|change|input|load)\\s*=",
      "message": "Inline event handlers make the script the mechanism. Use a real <form> or a real <a href>, and attach optional enhancement from ds.js."
    },
    {
      "pattern": "href\\s*=\\s*[\"']javascript:",
      "message": "A javascript: href is a link that is not a link. Use a form button, or a real URL."
    },
    {
      "pattern": "\\.innerHTML\\s*=",
      "where": "*.js",
      "message": "Building markup in JavaScript makes the page's content depend on the script running. Render it on the server; use textContent for the rare text swap."
    }
  ],
  "review": [
    "With the script file removed, every action on the page still completes."
  ]
}
```
