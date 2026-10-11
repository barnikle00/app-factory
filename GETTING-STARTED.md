# Getting started with app-factory

This is the first-hour guide: install it, run your first interview, know what "working" looks like,
and tell us when it is not.

## 1. What you need

- **macOS or Linux**, with `git`, `bash`, `rsync` and **Python 3.11 or newer**.
- **Claude Code** (the plugin runs inside it).
- For building (not for the design steps): `ruff`, `uv`, **Docker** (running), and `playwright`.
  You can start the design interview without them and install them when you reach the build.

Not sure what you have? Install the plugin (next step), start Claude Code, and say
**"run the factory doctor"**. It lists what is missing and the exact command to fix each item.

## 2. Install

In Claude Code:

```text
/plugin marketplace add barnikle00/app-factory
/plugin install app-factory@app-factory
```

Restart the session if asked. Approve the plugin's hooks when Claude Code shows them — what they do
is described in the README under *What runs on your machine*.

## 3. Your first session

Make an **empty folder** for the app, open Claude Code in it, and say what you want in your own
words and your own language, starting with:

> design this: *(one or two sentences about the app you want)*

What should happen, in order:

| You say | The factory does | You must |
|---|---|---|
| "design this: …" | Checks the idea fits (server-rendered Python web apps), asks "quick task or real build?", then asks **what the finished thing looks like** before any technical question. Shows a clickable prototype and asks for your comments. | Answer; comment on the prototype on your phone too; say **"lock it"** when the design is right |
| "design the architecture" | Writes the architecture, ten founding decisions with machine-checkable rules, and a trace of every design item | Read the plain-language summary; say go |
| "build the spec" | Lays down a tested starter app and writes a phased spec | — |
| "start project *name*" | Builds **one phase**, tests it, reports, and stops | Approve each phase |
| "run phases" | Builds several phases in a row, stopping on any red test | Give the cap and what it may do on its own |
| "final check" | Proves the build matches the locked design, presses every button in a browser, and gives you a page with every promise green or red | Read the page |

It **never deploys** and **never builds while you are still deciding**. If it does either, that is a bug — report it.

## 4. Signs it is working

- The first minute includes a **fit check**, and the first real question is about *the finished result*.
- Choices come with **plain words and an everyday comparison**, not jargon, and a recommendation.
- Nothing is written to files until you say so; `REVIEW.md` appears when you ask for it.
- You see a **prototype you can click**, not a description of one.
- After the spec, a `git commit` in the project is **refused** until its tests have passed on exactly
  what is being committed. That refusal is the gate working.

## 5. Signs something is off (please report these)

- It starts writing code or a spec during the interview.
- It asks you technical questions you cannot answer instead of choosing and saying why.
- It calls the design "complete" before you do.
- It skips the prototype and only describes screens.
- A hook says a gate "did NOT run" — your Python is too old or a tool is missing; run the doctor.
- It talks about files or tools that do not exist in your folder.

## 6. Telling us what happened

Open an issue at <https://github.com/barnikle00/app-factory/issues/new/choose> and pick **Feedback
from a trial**. The useful details are the sentence you said, what it did, and what you expected.
Paste any error text exactly. Screenshots of the prototype or the verdict page help.

## 7. For the person handing this over

Suggested trial: a small real idea (a dashboard with two screens and a login). Ask the tester to go
as far as "build the spec", then compare the interview against what you would have asked yourself.
The two things we most want to learn: **did the interview ask the right questions**, and **did any
gate or hook fail to run on their machine**.
