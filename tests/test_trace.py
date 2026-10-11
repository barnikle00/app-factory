"""trace-check.py — the design trace, tested both ways.

the owner's requirement: the build comes out exactly as designed, backend, logic and what every
button is wired to, with nothing lost or forgotten. The trace is the mechanism, so these tests
hold both halves of it: a complete trace passes, and each specific way an item can be forgotten
fails by name — a section, a dialog, a button, a phase, a test, a button missing from its page.
"""

from __future__ import annotations

import functools
import http.server
import subprocess
import sys
import textwrap
import threading
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "trace-check.py"


def run(project: Path, *args: str) -> tuple[int, str]:
    p = subprocess.run([sys.executable, str(SCRIPT), str(project), *args],
                       capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


@pytest.fixture
def project(tmp_path: Path) -> Path:
    (tmp_path / "design").mkdir()
    (tmp_path / "prototype").mkdir()
    (tmp_path / "DESIGN-V1.md").write_text(
        "Reference implementation: `prototype/p-v1.html`.\n", encoding="utf-8")
    (tmp_path / "design" / "40-screens.md").write_text(textwrap.dedent("""\
        # Part 4 — Screens
        ## 4.1 Home
        Buttons: «Save». See §4.2.
        ## 4.2 List
        ## 4.3 Dialogs
        | Dialog | Job |
        |---|---|
        | **Publish** | movers |
        """), encoding="utf-8")
    (tmp_path / "prototype" / "p-v1.html").write_text(
        '<script>const x = `<button class="b">Save</button>'
        '<button>${n} Spread</button><button>×</button>`;</script>', encoding="utf-8")
    return tmp_path


ROWS = [
    "| S-4.1 | 40-screens §4.1 | Home | route: /home · app/web/home.py | 1 | tests/test_home.py | {st} |",
    "| S-4.2 | 40-screens §4.2 | List | route: /list · app/web/list.py | 1 | tests/test_home.py | {st} |",
    "| S-4.3 | 40-screens §4.3 | Dialogs | templates/dialogs.html | 1 | tests/test_home.py | {st} |",
    "| D-Publish | 40-screens §4.3 | Publish | templates/publish.html | 1 | tests/test_home.py | {st} |",
    "| B-Save | 40-screens §4.1 | «Save» → POST /save | app/web/home.py | 1 | tests/test_home.py | {st} |",
    "| B-⟨…⟩ Spread | 40-screens §4.2 | «⟨…⟩ Spread» → the spread dialog | app/web/list.py | 1 | tests/test_home.py | {st} |",
]
HEAD = "| id | design | item | built in | phase | verified by | status |\n|---|---|---|---|---|---|---|\n"


def trace(p: Path, rows: list[str], st: str = "planned", drop: str | None = None,
          extra: list[str] = ()) -> None:
    body = [r.format(st=st) for r in rows if not (drop and r.startswith(f"| {drop} |"))]
    (p / "TRACE.md").write_text(HEAD + "\n".join([*body, *extra]) + "\n", encoding="utf-8")


def progress(p: Path, *nums: int, real_run: bool = True) -> None:
    lines = [f"- [ ] {n:02d} phase" + (" — real run" if real_run and i == 0 else "")
             for i, n in enumerate(nums)]
    (p / "PROGRESS.md").write_text("".join(ln + "\n" for ln in lines), encoding="utf-8")


# ── skeleton ─────────────────────────────────────────────────────────────────

def test_the_skeleton_lists_every_item_and_says_what_it_cannot_trace(project):
    code, out = run(project, "--skeleton")
    assert code == 0
    for item in ("S-4.1", "S-4.2", "S-4.3", "D-Publish", "B-Save", "Spread"):
        assert item in out, item
    assert "| B-× |" not in out and "not traced" in out


def test_the_skeleton_never_replaces_a_trace_in_progress(project):
    trace(project, ROWS)
    assert run(project, "--skeleton")[0] != 0


def test_a_skeleton_is_itself_a_starting_point_that_fails_until_filled(project):
    _, out = run(project, "--skeleton")
    (project / "TRACE.md").write_text(out, encoding="utf-8")
    code, report = run(project, "--stage", "architecture")
    assert code != 0 and "nothing says where it is built" in report


# ── architecture ─────────────────────────────────────────────────────────────

def test_a_complete_trace_passes_architecture(project):
    trace(project, ROWS)
    code, out = run(project, "--stage", "architecture")
    assert code == 0, out


def test_a_forgotten_section_fails_by_number(project):
    trace(project, ROWS, drop="S-4.2")
    code, out = run(project, "--stage", "architecture")
    assert code != 0 and "section 4.2" in out


def test_a_forgotten_dialog_fails_by_name(project):
    trace(project, ROWS, drop="D-Publish")
    code, out = run(project, "--stage", "architecture")
    assert code != 0 and "«Publish»" in out


def test_a_forgotten_button_fails_by_label(project):
    trace(project, ROWS, drop="B-Save")
    code, out = run(project, "--stage", "architecture")
    assert code != 0 and "«Save»" in out


def test_a_reference_to_a_section_that_does_not_exist_fails(project):
    trace(project, ROWS, extra=["| S-9.9x | 40-screens §9.9 | ghost | x.py |  |  | planned |"])
    code, out = run(project, "--stage", "architecture")
    assert code != 0 and "§9.9" in out


def test_a_button_that_does_not_say_which_screen_it_is_on_fails(project):
    rows = [r.replace("| 40-screens §4.1 | «Save»", "|  | «Save»") for r in ROWS]
    trace(project, rows)
    code, out = run(project, "--stage", "architecture")
    assert code != 0 and "does not cite the screen" in out


def test_a_draft_trace_outside_the_project_can_be_checked(project, tmp_path_factory):
    draft = tmp_path_factory.mktemp("scratch") / "TRACE.md"
    draft.write_text(HEAD + "\n".join(r.format(st="planned") for r in ROWS) + "\n", encoding="utf-8")
    code, out = run(project, "--stage", "architecture", "--trace", str(draft))
    assert code == 0, out
    assert not (project / "TRACE.md").exists()


def test_a_deviation_is_shown_at_architecture_and_blocks_final_until_approved(project):
    dev = "| S-4.2x | 40-screens §4.2 | list loads on scroll instead of pages | app/web/list.py | 1 | tests/test_home.py | deviation |"
    trace(project, ROWS, extra=[dev])
    code, out = run(project, "--stage", "architecture")
    assert code == 0 and "DEVIATIONS" in out
    trace(project, ROWS, st="done", extra=[dev])
    progress(project, 1)
    (project / "tests").mkdir()
    (project / "tests" / "test_home.py").write_text("")
    assert run(project, "--stage", "final")[0] != 0
    trace(project, ROWS, st="done", extra=[dev.replace("instead of pages", "instead of pages — approved 2026-09-16")])
    code, out = run(project, "--stage", "final")
    assert code == 0, out


# ── spec ─────────────────────────────────────────────────────────────────────

def test_spec_needs_every_row_in_a_phase_that_exists(project):
    trace(project, ROWS)
    progress(project, 1)
    assert run(project, "--stage", "spec")[0] == 0
    trace(project, [r.replace("| 1 |", "| 2 |", 1) if r.startswith("| B-Save") else r for r in ROWS])
    code, out = run(project, "--stage", "spec")
    assert code != 0 and "phase 2 is not in PROGRESS.md" in out


# ── final ────────────────────────────────────────────────────────────────────

def test_final_refuses_a_row_that_is_still_planned(project):
    trace(project, ROWS)
    progress(project, 1)
    code, out = run(project, "--stage", "final")
    assert code != 0 and "still planned" in out


def test_final_needs_the_test_that_proves_each_row_to_exist(project):
    trace(project, ROWS, st="done")
    progress(project, 1)
    code, out = run(project, "--stage", "final")
    assert code != 0 and "does not exist" in out
    (project / "tests").mkdir()
    (project / "tests" / "test_home.py").write_text("")
    code, out = run(project, "--stage", "final")
    assert code == 0, out


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):  # noqa: D401
        pass


def _serve(root: Path):
    srv = http.server.ThreadingHTTPServer(
        ("127.0.0.1", 0), functools.partial(_Quiet, directory=str(root)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def test_final_checks_each_button_on_the_page_that_serves_its_screen(project, tmp_path_factory):
    trace(project, ROWS, st="done")
    progress(project, 1)
    (project / "tests").mkdir()
    (project / "tests" / "test_home.py").write_text("")
    site = tmp_path_factory.mktemp("site")
    (site / "home").write_text("<main><h1>Home</h1></main>")          # Save is missing
    (site / "list").write_text("<button>12 Spread</button>")
    srv = _serve(site)
    try:
        url = f"http://127.0.0.1:{srv.server_address[1]}"
        code, out = run(project, "--stage", "final", "--base-url", url)
        assert code != 0 and "B-Save: the button is not on /home" in out
        (site / "home").write_text("<form><button type=submit>Save</button></form>")
        code, out = run(project, "--stage", "final", "--base-url", url)
        assert code == 0, out
    finally:
        srv.shutdown()


def test_an_unreachable_page_is_skipped_never_passed(project):
    trace(project, ROWS, st="done")
    progress(project, 1)
    (project / "tests").mkdir()
    (project / "tests" / "test_home.py").write_text("")
    code, out = run(project, "--stage", "final", "--base-url", "http://127.0.0.1:9")
    assert "SKIPPED" in out and "not a pass" in out


def test_a_project_without_a_design_pack_is_not_checked(tmp_path):
    code, out = run(tmp_path, "--stage", "final")
    assert code == 0 and "does not apply" in out


def test_new_rows_gives_a_later_version_a_way_forward(project):
    """The skeleton refuses to overwrite a trace in progress — right, but it left a second version
    of a design with no way to add its new sections. --new-rows prints only what has no row yet."""
    trace(project, ROWS)
    (project / "design" / "40-screens.md").write_text(
        (project / "design" / "40-screens.md").read_text(encoding="utf-8")
        + "\n## 4.4 Spread\nButtons: «Publish».\n", encoding="utf-8")
    code, out = run(project, "--new-rows")
    assert code == 0
    assert "| S-4.4 |" in out and "Spread" in out
    assert "S-4.1" not in out, "it must print only what is missing, not the whole trace again"
    (project / "TRACE.md").write_text(
        (project / "TRACE.md").read_text(encoding="utf-8")
        + "| S-4.4 | 40-screens §4.4 | Spread | route: /spread |  |  | planned |\n", encoding="utf-8")
    assert run(project, "--stage", "architecture")[0] == 0


def test_new_rows_says_so_when_nothing_is_missing(project):
    trace(project, ROWS)
    code, out = run(project, "--new-rows")
    assert code == 0 and "already has a row" in out


def test_spec_needs_a_phase_marked_as_the_real_run(project):
    """the first factory app met a real database and a real account only after its last phase, and found
    eight defects in a day. The register has to say where the build meets reality — early."""
    trace(project, ROWS)
    progress(project, 1, real_run=False)
    code, out = run(project, "--stage", "spec")
    assert code != 0 and "real run" in out
    progress(project, 1)
    code, out = run(project, "--stage", "spec")
    assert code == 0, out


def test_verified_by_is_read_however_the_row_writes_its_tests(project):
    """the first factory app wrote `tests/a.py` + `tests/b.py` (a note) — and the final check reported 236
    missing tests where there were none."""
    (project / "tests").mkdir()
    for n in ("test_home.py", "test_more.py"):
        (project / "tests" / n).write_text("")
    rows = [r.replace("tests/test_home.py", "`tests/test_home.py` + `tests/test_more.py` (measured)")
            for r in ROWS]
    trace(project, rows, st="done")
    progress(project, 1)
    code, out = run(project, "--stage", "final")
    assert code == 0, out
    trace(project, [r.replace("tests/test_home.py", "`tests/test_gone.py::test_x`") for r in ROWS], st="done")
    code, out = run(project, "--stage", "final")
    assert code != 0 and "tests/test_gone.py does not exist" in out
