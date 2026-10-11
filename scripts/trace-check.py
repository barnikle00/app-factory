#!/usr/bin/env python3
"""The design trace: prove nothing in a locked design is lost on the way to a build.

    trace-check.py <project> --skeleton                a starter TRACE.md, printed to stdout
    trace-check.py <project> --new-rows                rows for design items added since (a v2)
    trace-check.py <project> --stage architecture      every design item has a row and a home
    trace-check.py <project> --stage spec              ... and a phase that exists, and one
                                                       phase marked «real run» in PROGRESS.md
    trace-check.py <project> --stage final [--base-url URL [--cookie C]]
                                                       ... and is done, with a test that exists,
                                                       and every button is on its served page
    --trace PATH   check a draft trace instead of <project>/TRACE.md

WHY. the owner's requirement for the first factory app, the first app through the factory: the build must
come out exactly as designed — the backend, the logic, and what every button in the panel is
wired to — with nothing lost or forgotten. Per-phase gates prove each phase did what its prompt
said; nothing proved that the prompts, together, covered the design. A table a script checks
does. Prose cannot.

WHAT COUNTS AS A DESIGN ITEM is read from the project itself, never listed by hand:
  · every numbered section heading in design/*.md (`## 4.4`, `### 3.6.1`)  → its own S- row
  · every dialog in a design table whose first header cell is `Dialog`     → its own D- row
  · every labelled <button> in the prototype the newest DESIGN-V*.md names as the reference
    implementation                                                          → a B- row, or the
    label quoted «like this» in some row's item
Icon-only and fully dynamic buttons (×, ؟, `${label}`) are listed but not required: there is no
text to trace them by, and pretending otherwise would make the check lie.

A project with no numbered design pack is not checked at all: exit 0, and say so.
Exit 1 on any gap.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import html as _html
import re
import sys
from pathlib import Path
from urllib.request import Request, urlopen

COLUMNS = ["id", "design", "item", "built in", "phase", "verified by", "status"]
STATUSES = {"planned", "done", "out-of-v1", "deviation"}
DYN = "⟨…⟩"

HEADING = re.compile(r"^#{2,4}\s+(\d+(?:\.\d+)+[a-z]?)\b\s*(.*)$")
REF = re.compile(r"§\s?(\d+(?:\.\d+)*[a-z]?)")
BUTTON = re.compile(r"<button\b[^>]*>(.*?)</button>", re.S | re.I)
EXPR = re.compile(r"\$\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}")
PROTO_REF = re.compile(r"prototype/[\w.\-]+\.html")
ROUTE = re.compile(r"route:\s*(/\S*)")
QUOTED = re.compile(r"«([^«»]+)»")
# the first factory app met reality after its eighteenth phase, and found eight defects in a day that
# 2,682 tests on fakes had passed. The register must name where the build meets it — early.
REAL_RUN = re.compile(r"real run", re.I)


def _norm(s: str) -> str:
    return " ".join(s.split())


def _cells(line: str) -> list[str] | None:
    s = line.strip()
    if not s.startswith("|"):
        return None
    return [p.strip().replace("\\|", "|") for p in re.split(r"(?<!\\)\|", s.strip("|"))]


def _is_separator(cells: list[str]) -> bool:
    return bool(cells) and set("".join(cells)) <= set("-: ")


# ── The design pack ──────────────────────────────────────────────────────────

def design_items(project: Path):
    """(sections {id: (file-stem, title)}, duplicate ids, dialogs [(name, stem, section)])."""
    sections: dict[str, tuple[str, str]] = {}
    duplicates: list[str] = []
    dialogs: list[tuple[str, str, str]] = []
    for f in sorted((project / "design").glob("*.md")):
        lines = f.read_text(encoding="utf-8").splitlines()
        current = ""
        i = 0
        while i < len(lines):
            m = HEADING.match(lines[i])
            if m:
                current = m.group(1)
                if current in sections:
                    duplicates.append(f"{current} ({sections[current][0]} and {f.stem})")
                else:
                    sections[current] = (f.stem, m.group(2).strip())
            head = _cells(lines[i])
            if (head and head[0].strip("* ").lower() == "dialog"
                    and i + 1 < len(lines) and _is_separator(_cells(lines[i + 1]) or [])):
                j = i + 2
                while j < len(lines) and _cells(lines[j]):
                    name = _cells(lines[j])[0].strip("* ").strip()
                    if name:
                        dialogs.append((name, f.stem, current))
                    j += 1
                i = j
                continue
            i += 1
    return sections, duplicates, dialogs


def design_index(project: Path) -> Path:
    """The newest locked design index — `DESIGN-V2.md` once a v2 is locked, else `DESIGN-V1.md`.

    the first factory app locked a v2 (2026-10-10) whose reference prototype differs from v1's; reading v1's
    index would trace the build against the prototype v2 replaced."""
    found = sorted(project.glob("DESIGN-V*.md"), key=lambda p: int(re.sub(r"\D", "", p.stem) or 0))
    return found[-1] if found else project / "DESIGN-V1.md"


def reference_prototype(project: Path) -> Path | None:
    index = design_index(project)
    if index.is_file():
        m = PROTO_REF.search(index.read_text(encoding="utf-8"))
        if m and (project / m.group(0)).is_file():
            return project / m.group(0)
    return None


def prototype_buttons(proto: Path | None) -> tuple[list[str], list[str]]:
    """(labels with real text, icon-only or fully dynamic labels)."""
    if proto is None:
        return [], []
    seen: set[str] = set()
    labelled: list[str] = []
    bare: list[str] = []
    for raw in BUTTON.findall(proto.read_text(encoding="utf-8")):
        label = EXPR.sub(DYN, raw)
        label = _norm(_html.unescape(re.sub(r"<[^>]+>", " ", label)))
        if not label or label in seen:
            continue
        seen.add(label)
        (labelled if len(label.replace(DYN, "").strip()) > 1 else bare).append(label)
    return labelled, bare


# ── The trace ────────────────────────────────────────────────────────────────

def read_trace(path: Path) -> tuple[list[dict], bool]:
    rows: list[dict] = []
    header = False
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        c = _cells(line)
        if c is None:
            continue
        if not header:
            header = [x.lower() for x in c[: len(COLUMNS)]] == COLUMNS
            continue
        if _is_separator(c):
            continue
        c = (c + [""] * len(COLUMNS))[: len(COLUMNS)]
        row = dict(zip(COLUMNS, c))
        row["_line"] = n
        rows.append(row)
    return rows, header


def test_paths(cell: str) -> list[str]:
    """The test files a «verified by» cell names, however it writes them.

    the first factory app wrote `tests/a.py` + `tests/b.py` (what it measures) — backticks, a plus, and a
    note in brackets. Split on punctuation alone, every one of those became a "test that does not
    exist", and the final check reported 236 gaps where there were 14.
    """
    ticked = re.findall(r"`([^`]+)`", cell)
    parts = ticked or re.split(r"[,;·+]\s*", re.sub(r"\([^)]*\)", " ", cell))
    out = []
    for part in parts:
        path = part.split("::")[0].strip().split(" ")[0]
        if path and ("/" in path or path.endswith(".py")):
            out.append(path)
    return out


def _resolves(ref: str, sections: dict) -> bool:
    return ref in sections or any(k.startswith(ref + ".") for k in sections)


def _fetch(base: str, route: str, cookie: str | None) -> str | None:
    req = Request(base.rstrip("/") + route, headers={"Cookie": cookie} if cookie else {})
    try:
        with urlopen(req, timeout=10) as resp:
            return resp.read().decode("utf-8", "replace")
    except Exception:  # noqa: BLE001 — unreachable is reported as skipped, never as passing
        return None


def missing(sections: dict, dialogs: list, labelled: list, rows: list[dict]):
    """The design items with no row yet — what a first trace needs, and what a later version adds."""
    ids = {r["id"] for r in rows}
    quoted = {_norm(q) for r in rows for q in QUOTED.findall(r["item"])}
    items = [_norm(r["item"]) for r in rows]
    ms = [(sid, meta) for sid, meta in sections.items() if f"S-{sid}" not in ids]
    md = [d for d in dialogs if f"D-{d[0]}" not in ids and not any(d[0] in it for it in items)]
    mb = []
    for label in labelled:
        static = label.replace(DYN, "").strip()
        if f"B-{label}" not in ids and label not in quoted and not any(static in q for q in quoted):
            mb.append(label)
    return ms, md, mb


def _rows(ms, md, mb) -> list[str]:
    esc = lambda s: s.replace("|", "\\|")  # noqa: E731
    out = [f"| S-{sid} | {stem} §{sid} | {esc(title)} |  |  |  | planned |" for sid, (stem, title) in ms]
    out += [f"| D-{esc(name)} | {(stem + ' §' + sec) if sec else stem} | {esc(name)} |  |  |  | planned |"
            for name, stem, sec in md]
    out += [f"| B-{esc(label)} |  | «{esc(label)}» |  |  |  | planned |" for label in mb]
    return out


def new_rows(project: Path, trace: Path) -> int:
    """Rows for design items that appeared after the trace was written — a second version's
    sections, dialogs and buttons. The skeleton refuses to overwrite a trace in progress, which is
    right, and left a later version with no way forward: this is that way."""
    sections, _dups, dialogs = design_items(project)
    if not sections:
        print(f"{project.name}: no numbered design pack — nothing to trace")
        return 0
    labelled, _bare = prototype_buttons(reference_prototype(project))
    rows, header = read_trace(trace) if trace.is_file() else ([], True)
    if not header:
        print(f"{trace.name} has no table with the columns: {' | '.join(COLUMNS)}", file=sys.stderr)
        return 1
    lines = _rows(*missing(sections, dialogs, labelled, rows))
    if not lines:
        print(f"every design item already has a row in {trace.name}")
        return 0
    print(f"<!-- {len(lines)} design item(s) with no row yet — append these to {trace.name} and fill them in -->")
    print("\n".join(lines))
    return 0


def skeleton(project: Path, trace: Path) -> int:
    if trace.exists():
        print(f"{trace} already exists. The skeleton never replaces a trace in progress.",
              file=sys.stderr)
        return 1
    sections, _dups, dialogs = design_items(project)
    proto = reference_prototype(project)
    labelled, bare = prototype_buttons(proto)
    esc = lambda s: s.replace("|", "\\|")  # noqa: E731
    out = [
        f"# TRACE — {project.name}: every item of the locked design, where it is built, how it is proven",
        "",
        f"Generated {_dt.date.today()} by `scripts/trace-check.py --skeleton` from `design/*.md`"
        + (f" and `{proto.relative_to(project)}`" if proto else "") + ", then filled in by hand.",
        "Status: `planned` · `done` · `out-of-v1` (say why) · `deviation` (say what changes; "
        "write `approved YYYY-MM-DD` once the user agrees).",
        "",
        "| " + " | ".join(COLUMNS) + " |",
        "|" + "---|" * len(COLUMNS),
    ]
    out += _rows(*missing(sections, dialogs, labelled, []))
    if bare:
        out += ["", f"<!-- not traced (no text to trace by): {' · '.join(bare)} -->"]
    print("\n".join(out))
    return 0


def check(project: Path, trace: Path, stage: str, base_url: str | None, cookie: str | None) -> int:
    sections, duplicates, dialogs = design_items(project)
    if not sections:
        print(f"{project.name}: no numbered design pack (design/*.md) — the trace check does not apply")
        return 0
    proto = reference_prototype(project)
    labelled, bare = prototype_buttons(proto)
    gaps: list[str] = []
    notes: list[str] = []
    deviations: list[str] = []

    print(f"TRACE — {project.name} — stage: {stage}")
    print(f"  design pack: {len(sections)} sections · {len(dialogs)} dialogs · "
          f"{len(labelled)} prototype buttons"
          + (f" (+{len(bare)} icon-only/dynamic, not traced)" if bare else "")
          + ("" if proto else " · no reference prototype named in the design index"))

    for d in duplicates:
        gaps.append(f"section number {d} is used twice — a number that means two things cannot be traced")

    if not trace.is_file():
        gaps.append(f"{trace.name} does not exist — start it with: trace-check.py {project} --skeleton")
        return _finish(gaps, notes, deviations)
    rows, header = read_trace(trace)
    if not header:
        gaps.append(f"{trace.name} has no table with the columns: {' | '.join(COLUMNS)}")
        return _finish(gaps, notes, deviations)
    print(f"  {trace.name}: {len(rows)} rows")

    ms, md, mb = missing(sections, dialogs, labelled, rows)
    for sid, (stem, title) in ms:
        gaps.append(f"section {sid} ({stem}: {title[:50]}) has no S-{sid} row")
    for name, stem, _sec in md:
        gaps.append(f"dialog «{name}» ({stem}) has no row")
    for label in mb:
        gaps.append(f"button «{label}» in the prototype has no row")

    for r in rows:
        where = f"{trace.name}:{r['_line']} {r['id'] or '(no id)'}"
        st = r["status"].lower()
        if st not in STATUSES:
            gaps.append(f"{where}: status '{r['status']}' — use one of {', '.join(sorted(STATUSES))}")
        for ref in REF.findall(r["design"]):
            if not _resolves(ref, sections):
                gaps.append(f"{where}: cites §{ref}, which no design section carries")
        if st != "out-of-v1" and not r["built in"]:
            gaps.append(f"{where}: nothing says where it is built")
        if r["id"].startswith(("B-", "D-")) and not REF.search(r["design"]) and st != "out-of-v1":
            gaps.append(f"{where}: does not cite the screen section it belongs to (§…)")
        if st == "deviation":
            deviations.append(f"{r['id']}: {r['item']}")

    if stage in ("spec", "final"):
        phases: set[int] = set()
        progress = project / "PROGRESS.md"
        if progress.is_file():
            for line in progress.read_text(encoding="utf-8").splitlines():
                m = re.match(r"\s*-\s*\[[ xX]\]\s*0*(\d+)\b", line)
                if m:
                    phases.add(int(m.group(1)))
        else:
            gaps.append("PROGRESS.md does not exist — no phase register to assign rows to")
        if progress.is_file() and not REAL_RUN.search(progress.read_text(encoding="utf-8")):
            gaps.append("PROGRESS.md marks no phase «real run» — the first phase that reaches a real "
                        "database, service or account must end with a read-only run against it, "
                        "before the phases after it are built (build-spec §3)")
        for r in rows:
            if r["status"].lower() == "out-of-v1":
                continue
            m = re.search(r"\d+", r["phase"])
            if not m:
                gaps.append(f"{trace.name}:{r['_line']} {r['id']}: no phase builds it")
            elif phases and int(m.group()) not in phases:
                gaps.append(f"{trace.name}:{r['_line']} {r['id']}: phase {m.group()} is not in PROGRESS.md")

    if stage == "final":
        for r in rows:
            where = f"{trace.name}:{r['_line']} {r['id']}"
            st = r["status"].lower()
            if st == "planned":
                gaps.append(f"{where}: still planned — not built")
            elif st == "deviation" and "approved" not in r["item"].lower():
                gaps.append(f"{where}: a deviation the user has not approved")
            elif st == "done":
                if not r["verified by"]:
                    gaps.append(f"{where}: done, but no test says so")
                for path in test_paths(r["verified by"]):
                    if not (project / path).exists():
                        gaps.append(f"{where}: its test {path} does not exist")
        if base_url:
            _check_pages(rows, base_url, cookie, gaps, notes)

    return _finish(gaps, notes, deviations)


def _check_pages(rows, base_url, cookie, gaps, notes) -> None:
    """Every traced button must be on the page of the screen it cites — as served."""
    routes = {r["id"][2:]: ROUTE.findall(r["built in"]) for r in rows if r["id"].startswith("S-")}
    pages: dict[str, str | None] = {}
    for r in rows:
        if not r["id"].startswith("B-") or r["status"].lower() == "out-of-v1":
            continue
        label = _norm(r["id"][2:].replace(DYN, " "))
        targets = [rt for ref in REF.findall(r["design"]) for rt in routes.get(ref, [])]
        if not targets:
            notes.append(f"{r['id']}: its screen row has no `route:` — not checked on a page")
            continue
        reached = found = False
        for rt in targets:
            if rt not in pages:
                raw = _fetch(base_url, rt, cookie)
                pages[rt] = None if raw is None else _norm(_html.unescape(re.sub(r"<[^>]+>", " ", raw)))
            if pages[rt] is None:
                continue
            reached = True
            if all(part in pages[rt] for part in label.split(" ") if part):
                found = True
                break
        if not reached:
            notes.append(f"{r['id']}: SKIPPED — {', '.join(targets)} not reachable (this is not a pass)")
        elif not found:
            gaps.append(f"{r['id']}: the button is not on {', '.join(targets)}")


def _finish(gaps: list[str], notes: list[str], deviations: list[str]) -> int:
    if deviations:
        print(f"\nDEVIATIONS for the user ({len(deviations)})")
        for d in deviations:
            print(f"  - {d}")
    if notes:
        print(f"\nNOTES ({len(notes)})")
        for n in notes:
            print(f"  - {n}")
    # One stream, so the report reads top to bottom. Split across stdout and stderr,
    # the gaps printed before the header whenever both were captured together.
    if gaps:
        print(f"\nGAPS ({len(gaps)})")
        for g in gaps:
            print(f"  - {g}")
        print("\nFAILED")
        return 1
    print("\nOK")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("project", type=Path)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--skeleton", action="store_true")
    mode.add_argument("--new-rows", action="store_true",
                      help="rows for design items that have no row yet — a later version's additions")
    mode.add_argument("--stage", choices=["architecture", "spec", "final"])
    ap.add_argument("--trace", type=Path, help="a draft trace to check instead of <project>/TRACE.md")
    ap.add_argument("--base-url", help="final stage: check each traced button on its served page")
    ap.add_argument("--cookie", help="final stage: a Cookie header for pages behind a login")
    a = ap.parse_args()
    project = a.project.resolve()
    trace = (a.trace or project / "TRACE.md").resolve()
    if a.skeleton:
        return skeleton(project, trace)
    if a.new_rows:
        return new_rows(project, trace)
    return check(project, trace, a.stage, a.base_url, a.cookie)


if __name__ == "__main__":
    sys.exit(main())
