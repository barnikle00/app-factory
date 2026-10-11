"""architecture-check.py — the architecture document, tested both ways.

the owner's requirements for how an app must be built become concrete in exactly one place, and
until now nothing read it. Each way that document can quietly fail him must fail by name: a
missing section, a verification command nobody can run, a principle answered with "TBD", a library
picked off nobody's list, missing founding decisions, and a question the review left here that the
architecture never answers.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "architecture-check.py"
FOUNDING = sorted(p.name for p in (SCRIPT.parent.parent / "foundation" / "adr").glob("[0-9][0-9][0-9][0-9]-*.md"))

GOOD = textwrap.dedent("""\
    # Architecture — test-app

    ## 1. Data model
    One row per chat, `chat`, keyed by telegram id.

    ## 2. The flows that create or change the core row
    A folder publish moves people; the reconciler writes to Telegram.

    ## 3. Chokepoints
    The only writer of a folder membership is `app/folders/apply.py`.

    ## 4. Known traps
    A pinned chat consumes the folder's chat budget.

    ## 5. How the suites are run
    `scripts/verified.py . -- pytest tests -q`

    ## 6. Frontend source
    Ported from the prototype's `viewFolders`; its stylesheet becomes `app/static/app.css`.

    ## 7. Stack
    `fastapi`, `sqlalchemy`, `alembic`, `taskiq`, `rapidfuzz`.

    ## 8. Operating principles
    - **Simple** — no service layer until two callers need it; every module under 500 lines.
    - **Under pressure** — every Telegram and HTTP call takes its timeout from settings; lists paged at 50.
    - **Growth** — web processes hold no state; 40k chats today, the event table breaks first at ~50M rows.
    - **Database future** — expand/migrate/contract; `event` is partitioned by month with a BRIN index.
    - **Cheap change** — the rule sentence is built in one place, `app/rules/sentence.py`.
    - **Health** — `/health` and `/health/ready`; every job writes its last success to `job_run`.
    - **Nothing hardcoded** — addresses, caps and delays are settings named with their units.
    - **Measurable** — request time, queue length and job failures are exported to /metrics.

    ## 9. Budgets
    - **Click** — 800 ms: from pressing a button to the page settling, measured locally.
    - **Code** — 12,000 lines: the app's own code, without tests, comments or blank lines.

    ## 10. Real runs
    Every test of `app/data/` takes `realdb_url`, a throwaway PostgreSQL. Phase 06 is the real run:
    read-only against one Telegram account and the sales tracker's database.

    ## 11. Revisions
    - 2026-09-16 — written from the locked design.
    """)


def app(tmp_path: Path, doc: str = GOOD, *, adrs: int = len(FOUNDING), own: bool = True,
        review: str | None = None, prototype: bool = True) -> Path:
    p = tmp_path / f"test-app-{len(list(tmp_path.iterdir()))}"
    (p / "adr").mkdir(parents=True)
    (p / "ARCHITECTURE.md").write_text(doc, encoding="utf-8")
    for name in FOUNDING[:adrs]:
        (p / "adr" / name).write_text("copied\n", encoding="utf-8")
    if own:
        (p / "adr" / "0100-scale.md").write_text("40k chats today; the event table breaks first.\n", encoding="utf-8")
    if prototype:
        (p / "DESIGN-V1.md").write_text("Reference implementation: `prototype/v8.html`\n", encoding="utf-8")
    if review is not None:
        (p / "REVIEW.md").write_text(review, encoding="utf-8")
    return p


def run(project: Path) -> tuple[int, str]:
    r = subprocess.run([sys.executable, str(SCRIPT), str(project)], capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def test_a_complete_architecture_passes(tmp_path):
    code, out = run(app(tmp_path))
    assert code == 0, out


def test_a_missing_architecture_is_named(tmp_path):
    p = tmp_path / "empty"
    p.mkdir()
    code, out = run(p)
    assert code != 0 and "no ARCHITECTURE.md" in out


def test_a_missing_section_fails_by_name(tmp_path):
    doc = GOOD.replace("## 3. Chokepoints\nThe only writer of a folder membership is `app/folders/apply.py`.\n", "")
    code, out = run(app(tmp_path, doc))
    assert code != 0 and "chokepoint" in out


def test_a_verification_command_nobody_can_run_fails(tmp_path):
    doc = GOOD.replace("`scripts/verified.py . -- pytest tests -q`", "The suites are run regularly.")
    code, out = run(app(tmp_path, doc))
    assert code != 0 and "no runnable command" in out


def test_a_principle_left_out_fails_by_name(tmp_path):
    doc = GOOD.replace("- **Health** — `/health` and `/health/ready`; every job writes its last success to `job_run`.\n", "")
    code, out = run(app(tmp_path, doc))
    assert code != 0 and "principle not answered: health" in out


def test_a_principle_answered_with_a_placeholder_fails(tmp_path):
    doc = GOOD.replace("- **Growth** — web processes hold no state; 40k chats today, the event table breaks first at ~50M rows.",
                       "- **Growth** — TBD")
    code, out = run(app(tmp_path, doc))
    assert code != 0 and "placeholder" in out and "growth" in out


def test_a_library_off_the_list_fails_unless_it_says_why(tmp_path):
    doc = GOOD.replace("`rapidfuzz`.", "`rapidfuzz`, `mongoengine`.")
    code, out = run(app(tmp_path, doc))
    assert code != 0 and "mongoengine" in out
    doc = GOOD.replace("`rapidfuzz`.", "`rapidfuzz`, `mongoengine` — off-list: the source system is MongoDB.")
    code, out = run(app(tmp_path, doc))
    assert code == 0, out


def test_founding_decisions_must_have_arrived(tmp_path):
    code, out = run(app(tmp_path, adrs=6))
    assert code != 0 and f"missing {len(FOUNDING) - 6} of the {len(FOUNDING)} founding decisions" in out


def test_an_app_scaffolded_before_a_founding_decision_was_renamed_still_passes(tmp_path):
    """0002 and 0006 were generalised (rial -> minor units, Persian -> any script) when the factory
    became a plugin, and their file names changed. Apps built earlier keep the old names and the old
    text; they hold the decision, so the check goes by the four-digit id, not the file name."""
    p = app(tmp_path)
    (p / "adr" / next(n for n in FOUNDING if n.startswith("0002-"))).rename(
        p / "adr" / "0002-money-is-integer-rial.md")
    (p / "adr" / next(n for n in FOUNDING if n.startswith("0006-"))).rename(
        p / "adr" / "0006-persian-input-is-normalised-at-the-boundary.md")
    code, out = run(p)
    assert code == 0, out


def test_the_outside_write_guard_is_a_founding_decision(tmp_path):
    """the first factory app wrote one folder to a customer's own account 70,565 times in five days,
    and its health said «ready» throughout. That lesson travels to every new app as ADR 0010."""
    assert any(n.startswith("0010-") for n in FOUNDING)
    p = app(tmp_path)
    (p / "adr" / next(n for n in FOUNDING if n.startswith("0010-"))).unlink()
    code, out = run(p)
    assert code != 0 and "0010" in out


def test_the_project_must_write_at_least_its_own_scale_decision(tmp_path):
    code, out = run(app(tmp_path, own=False))
    assert code != 0 and "no ADR of its own" in out


def test_a_question_the_review_left_here_must_be_answered(tmp_path):
    review = ("**For design-architecture:**\n"
              "- The event table kept forever: partitioning, rollups or an archive table.\n"
              "- Data path to the sales tracker (internal endpoint vs read-only DB role).\n")
    code, out = run(app(tmp_path, review=review))
    assert code != 0 and "data path to the sales" in out.lower()
    doc = (GOOD + "\n## 10. Questions the review left here\n"
           "- Data path to the sales tracker: a read-only DB role on the tracker's database.\n"
           "- The event table kept forever: partitioned by month, dropped after two years.\n")
    code, out = run(app(tmp_path, doc, review=review))
    assert code == 0, out


def test_frontend_source_is_required_only_when_a_prototype_exists(tmp_path):
    doc = GOOD.replace("## 6. Frontend source\nPorted from the prototype's `viewFolders`; its stylesheet becomes `app/static/app.css`.\n", "")
    code, out = run(app(tmp_path, doc))
    assert code != 0 and "frontend source" in out
    code, out = run(app(tmp_path, doc, prototype=False))
    assert code == 0, out


def test_budgets_must_state_both_numbers(tmp_path):
    """«کند و سنگین است» and «خیلی بزرگ و پیچیده شد» — the first factory app said "simple" and "light" in
    words, and nothing measured either. A budget is a number a tool can hold the build to."""
    doc = GOOD.replace("- **Click** — 800 ms: from pressing a button to the page settling, measured locally.\n", "")
    code, out = run(app(tmp_path, doc))
    assert code != 0 and "no click budget" in out
    doc = GOOD.replace("- **Code** — 12,000 lines: the app's own code, without tests, comments or blank lines.\n", "")
    code, out = run(app(tmp_path, doc))
    assert code != 0 and "no code budget" in out
    doc = GOOD.replace("800 ms", "1.5 s")
    code, out = run(app(tmp_path, doc))
    assert code == 0 and "1500 ms" in out, out


def test_real_runs_must_name_the_real_database_tests(tmp_path):
    doc = GOOD.replace("Every test of `app/data/` takes `realdb_url`, a throwaway PostgreSQL.",
                       "Data code is tested with fakes.")
    code, out = run(app(tmp_path, doc))
    assert code != 0 and "realdb" in out
    doc = GOOD.replace("## 10. Real runs", "## 10. Notes")
    code, out = run(app(tmp_path, doc))
    assert code != 0 and "real runs" in out


OWN_RULE = """---
id: 0101
status: accepted
---
## Enforcement

```json
{"governs": ["app/**/*.py"], "forbid": [%s]}
```
"""


def test_a_project_rule_must_be_tested_both_ways_before_it_can_block(tmp_path):
    """the first factory app's own ADR 0017 forbade reading `message.message` outside app/detect/, and it
    fired on the Telegram adapter, which has to read it to hand it over. Once the hooks block, a
    rule like that stops correct work — so every project rule carries an example it must catch
    and the nearest correct look-alike it must not."""
    p = app(tmp_path)
    rule = '{"pattern": "\\\\bmessage\\\\.message\\\\b", "message": "keep text in memory"%s}'
    (p / "adr" / "0101-no-text.md").write_text(OWN_RULE % (rule % ""), encoding="utf-8")
    code, out = run(p)
    assert code != 0 and "no fires/silent examples" in out
    examples = ', "fires": ["row.body = message.message"], "silent": ["text = message.message or \\"\\""]'
    (p / "adr" / "0101-no-text.md").write_text(OWN_RULE % (rule % examples), encoding="utf-8")
    code, out = run(p)
    assert code != 0 and "fires on correct code" in out
    ok = ', "fires": ["row.body = message.message"], "silent": ["text = event.raw"]'
    (p / "adr" / "0101-no-text.md").write_text(OWN_RULE % (rule % ok), encoding="utf-8")
    code, out = run(p)
    assert code == 0, out
