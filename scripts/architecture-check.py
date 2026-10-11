#!/usr/bin/env python3
"""Check the architecture document itself — the one artifact nothing else reads.

    architecture-check.py <project>

Everything else in the factory checks a file somebody wrote: a brand, a template, a migration, a
prototype, the trace. `ARCHITECTURE.md` was checked by nothing at all — its existence was a gate,
its content was a promise. It is also the most important document in a project: the spec is
transcribed from it, every phase prompt cites it, and it is where the owner's own requirements for
how an app must be built are supposed to become concrete.

So this reads it, and fails when:

  1. a required section is missing — data model, flows, chokepoints, known traps, how the suites
     are run, stack, operating principles, revisions (and frontend source when the design names a
     prototype);
  2. "how the suites are run" names no command that could actually be run — `run-phases` refuses
     to start without one and the commit lock records it;
  3. an operating principle is missing, or answered with a placeholder instead of a decision.
     These eight are the owner's own words, turned into the questions an architecture must answer;
  4. the Stack section names a library that is not in `foundation/stack.md` without
     saying why the listed pick does not fit;
  5. a founding ADR (every file in foundation/adr/) was not copied, or the project wrote
     none of its own — the project numbers its own from 0100;
  6. a question the review left for this stage is not quoted and answered anywhere;
  7. `## Budgets` does not state both numbers — the slowest a click may be, in ms, and the most code
     the app may grow to, in lines — which press-check and budget-check then hold it to;
  8. a `forbid` rule in the project's own ADRs has no `fires`/`silent` examples, misses one of its
     `fires`, or fires on one of its `silent` — the rule is tested both ways before it can block;
  9. `## Real runs` does not say how the data code is tested against a real database (`realdb`)
     and which outside systems the one real-run phase will touch.

Exit 0 when the document holds up, 1 otherwise.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _budgets  # noqa: E402

REQUIRED = [
    ("data model", ("data model",)),
    ("the flows that create or change the core row", ("flow",)),
    ("chokepoints", ("chokepoint",)),
    ("known traps", ("trap",)),
    ("how the suites are run", ("suite", "testing", "verification")),
    ("stack", ("stack",)),
    ("operating principles", ("operating principle",)),
    ("revisions", ("revision",)),
    ("budgets", ("budget",)),
    ("real runs", ("real run",)),
]
FRONTEND = ("frontend source", ("frontend source",))

PRINCIPLES = {
    "simple": "no layer or library without two real callers or a written reason",
    "under pressure": "time limits, bounded lists, slow work off the request path",
    "growth": "stateless processes, and the first thing that breaks, with its number",
    "database future": "expand/migrate/contract, and a plan for every table that only grows",
    "cheap change": "each rule has one home",
    "health": "/health, /health/ready, and every job's last success",
    "nothing hardcoded": "every address, limit, timeout and interval is a setting",
    "measurable": "the few numbers that show the app works",
}
PLACEHOLDER = re.compile(r"\b(tbd|todo|to be decided|to be determined|later|n/?a|\.\.\.|…)\s*$", re.I)
COMMAND = re.compile(r"`([^`]*(?:pytest|make|npm|uv |python|\./|bash|sh )[^`]*)`|^\s{4,}\S+.*$", re.M)
BACKTICKED = re.compile(r"`([a-zA-Z][\w.\-]{2,})`")
HEADING = re.compile(r"^#{2,4}\s+(.*)$", re.M)


def sections(text: str) -> dict[str, str]:
    """heading (lowercased) -> the text under it."""
    out, marks = {}, list(HEADING.finditer(text))
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        out[m.group(1).strip().lower()] = text[m.end():end]
    return out


def find(secs: dict[str, str], keys: tuple[str, ...]) -> tuple[str, str] | None:
    for head, body in secs.items():
        if any(k in head for k in keys):
            return head, body
    return None


def norm(s: str) -> str:
    return re.sub(r"[^\w\s]", " ", s.lower()).split() and " ".join(re.sub(r"[^\w\s]", " ", s.lower()).split()) or ""


def review_questions(project: Path) -> list[str]:
    review = project / "REVIEW.md"
    if not review.is_file():
        return []
    text = review.read_text(encoding="utf-8")
    # \Z matters: a review whose list of questions sits at the end of the file, or is followed by a
    # single newline, parsed as no questions at all — and the check then silently passed everything.
    m = re.search(r"\*\*For design-architecture:?\*\*\s*\n(.*?)(?:\n\s*\n|\n\*\*|\Z)", text, re.S)
    if not m:
        return []
    out = []
    for line in m.group(1).splitlines():
        line = line.strip()
        if line.startswith("- "):
            words = norm(line[2:]).split()
            if len(words) >= 4:
                out.append(" ".join(words[:5]))
    return out


def stack_names() -> set[str]:
    f = Path(__file__).resolve().parent.parent / "foundation" / "stack.md"
    if not f.is_file():
        return set()
    # One convention in both files: a package is written in backticks. Parsing the prose around
    # it does not work — the pick cell says "PostgreSQL · SQLAlchemy 2 async · asyncpg" in one row
    # and "a small in-process scheduler for a few timed jobs; Taskiq once work must survive a
    # restart" in another, and a split on punctuation found neither sqlalchemy nor taskiq.
    names: set[str] = set()
    for row in f.read_text(encoding="utf-8").splitlines():
        if row.startswith("|") and row.count("|") > 3:
            names.update(n.lower() for n in BACKTICKED.findall(row.split("|")[2]))
    return names


def design_index(project: Path) -> Path:
    """The newest locked design index — `DESIGN-V2.md` once a v2 is locked, else `DESIGN-V1.md`.

    the first factory app locked a v2 (2026-10-10) whose reference prototype differs from v1's; reading v1's
    index would trace the build against the prototype v2 replaced."""
    found = sorted(project.glob("DESIGN-V*.md"), key=lambda p: int(re.sub(r"\D", "", p.stem) or 0))
    return found[-1] if found else project / "DESIGN-V1.md"


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: architecture-check.py <project>", file=sys.stderr)
        return 2
    project = Path(argv[1]).expanduser().resolve()
    doc = project / "ARCHITECTURE.md"
    print(f"ARCHITECTURE — {project.name}")
    if not doc.is_file():
        print("  FAIL  there is no ARCHITECTURE.md")
        print("\nFAILED")
        return 1
    text = doc.read_text(encoding="utf-8")
    secs = sections(text)
    gaps: list[str] = []

    def verdict(ok: bool, text_: str) -> None:
        print(f"  {'PASS' if ok else 'FAIL'}  {text_}")
        if not ok:
            gaps.append(text_)

    wanted = list(REQUIRED)
    index = design_index(project)
    if index.is_file() and "prototype/" in index.read_text(encoding="utf-8"):
        wanted.append(FRONTEND)
    for label, keys in wanted:
        hit = find(secs, keys)
        verdict(bool(hit and hit[1].strip()), f"section: {label}" if hit and hit[1].strip()
                else f"section missing or empty: {label}")

    suites = find(secs, ("suite", "testing", "verification"))
    if suites:
        verdict(bool(COMMAND.search(suites[1])),
                "the verification command is written out" if COMMAND.search(suites[1])
                else "'how the suites are run' names no runnable command — run-phases refuses to "
                     "start without one, and the commit lock records it through verified.py")

    principles = find(secs, ("operating principle",))
    if principles:
        body = principles[1]
        for key, what in PRINCIPLES.items():
            line = next((ln for ln in body.splitlines() if key in ln.lower()), None)
            if not line:
                verdict(False, f"principle not answered: {key} — {what}")
            else:
                answer = re.sub(r"^[-*\s]*\*\*[^*]+\*\*\s*[—:-]?\s*", "", line).strip()
                verdict(bool(answer) and not PLACEHOLDER.search(answer) and len(answer) >= 15,
                        f"principle: {key}" if answer and not PLACEHOLDER.search(answer) and len(answer) >= 15
                        else f"principle answered with a placeholder, not a decision: {key}")

    stack = find(secs, ("stack",))
    if stack:
        known = stack_names()
        unknown = sorted({n.lower() for n in BACKTICKED.findall(stack[1])} - known)
        excused = [n for n in unknown
                   if re.search(rf"`{re.escape(n)}`[^\n]*(off-list|not in stack\.md|instead of)", stack[1], re.I)]
        left = [n for n in unknown if n not in excused]
        verdict(not left, "every library is from stack.md, or says why not" if not left
                else "libraries not in stack.md and with no reason given: " + ", ".join(left[:6]))

    if find(secs, ("budget",)):
        b = _budgets.read(project)
        verdict("click_ms" in b, f"click budget: {b['click_ms']} ms" if "click_ms" in b
                else "## Budgets states no click budget — a line like «**Click** — 800 ms: …»")
        verdict("code_lines" in b, f"code budget: {b['code_lines']:,} lines" if "code_lines" in b
                else "## Budgets states no code budget — a line like «**Code** — 12,000 lines: …»")

    real = find(secs, ("real run",))
    if real and real[1].strip():
        verdict("realdb" in real[1].lower(),
                "real runs: data code is tested on a real database" if "realdb" in real[1].lower()
                else "## Real runs does not say which tests use `realdb` — a real, throwaway PostgreSQL "
                     "(foundation/tooling/realdb.py). Tests on fakes shipped the first factory app's SQL and race bugs")

    adr_dir = project / "adr"
    # The founding set is whatever foundation/adr holds — ten since 2026-09-30, when 0010
    # (every outside write is guarded) joined after the first factory app's five-day write loop. Checked by
    # the four-digit id, not the file name: an app scaffolded before a founding decision was renamed
    # (0002 and 0006 were generalised when the factory became a plugin) still holds that decision, and
    # a later founding decision is required without editing this script.
    foundation = Path(__file__).resolve().parent.parent / "foundation" / "adr"
    founding = sorted(p.name for p in foundation.glob("[0-9][0-9][0-9][0-9]-*.md"))
    founding_ids = {n[:4] for n in founding}
    have = {p.name for p in adr_dir.glob("*.md")} if adr_dir.is_dir() else set()
    have_ids = {n[:4] for n in have}
    missing = [n for n in founding if n[:4] not in have_ids]
    own = sorted(n for n in have if n[:4].isdigit() and n[:4] not in founding_ids)
    verdict(not missing, f"the {len(founding)} founding ADRs are in adr/" if not missing
            else f"adr/ is missing {len(missing)} of the {len(founding)} founding decisions "
                 f"({', '.join(n[:4] for n in missing[:5])}) — copy them from foundation/adr/")
    verdict(bool(own), "the project wrote its own ADRs" if own
            else "the project wrote no ADR of its own — at minimum the scale it assumes (0100)")

    # Every forbid rule the project wrote itself is tested both ways against its own examples —
    # the founding set is, in tests/test_adrs.py. The edit hooks block now; a rule that
    # fires on correct code would stop work, and the first factory app's own ADR 0017 forbade *reading*
    # message.message anywhere but app/detect/, which fired on the adapter that has to read it.
    import importlib.util
    spec = importlib.util.spec_from_file_location("adr_check", Path(__file__).resolve().parent / "adr-check.py")
    adr_check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adr_check)  # type: ignore[union-attr]
    untested: list[str] = []
    if adr_dir.is_dir():
        for name, rules in adr_check.load_rules(adr_dir):
            if name[:4] in founding_ids:
                continue
            for rule in rules.get("forbid") or []:
                label = f"{name[:4]} «{rule.get('pattern', '')[:40]}»"
                fires, silent = rule.get("fires") or [], rule.get("silent") or []
                if not fires or not silent:
                    untested.append(f"{label} has no fires/silent examples")
                    continue
                try:
                    rx = re.compile(rule.get("pattern", ""))
                except re.error as e:
                    untested.append(f"{label} is not a valid pattern ({e})")
                    continue
                untested += [f"{label} misses its own example {x!r}" for x in fires if not rx.search(x)]
                untested += [f"{label} fires on correct code {x!r}" for x in silent if rx.search(x)]
    verdict(not untested, "every project forbid rule is tested both ways by its examples" if not untested
            else "project forbid rules not tested both ways: " + "; ".join(untested[:4]))

    questions = review_questions(project)
    if questions:
        haystack = norm(text) + " " + " ".join(norm(p.read_text(encoding="utf-8"))
                                               for p in (adr_dir.glob("*.md") if adr_dir.is_dir() else []))
        missing = [q for q in questions if q not in haystack]
        verdict(not missing, f"all {len(questions)} questions the review left here are answered"
                if not missing else "questions the review left here, not quoted and answered: "
                + "; ".join(f"«{q}…»" for q in missing[:4]))

    print("\nFAILED" if gaps else "\nOK — the architecture document holds up")
    return 1 if gaps else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
