"""press-check.py, budget-check.py and verdict-page.py — each way a build can look done and not be.

The site below is the first factory app's failures in miniature: a button that works, one that does nothing,
one that is disabled before the reader can use it (the «انتشار» that could never be pressed), one
that makes the server fail, one that is slower than its budget, and one whose screen needs an id.
"""

from __future__ import annotations

import http.server
import json
import subprocess
import sys
import textwrap
import threading
import time
from pathlib import Path

import pytest

pytest.importorskip("playwright")

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"

PAGES = {
    "/home": '<form action="/saved"><button>Save</button></form>',
    "/saved": "<p>saved</p>",
    "/list": '<button type="button">Spread</button>',
    "/dlg": '<form method="post" action="/pub"><button disabled>Publish</button></form>',
    "/boom": '<form method="post" action="/crash"><button>Crash</button></form>',
    "/slow": ('<button type="button" onclick="fetch(\'/wait\').then(r=>r.text())'
              '.then(t=>document.body.insertAdjacentText(\'beforeend\',t))">Recount</button>'),
    "/acc/7": '<a href="/saved">Open</a>',
    "/tabs": '<a href="/tabs?tab=cap">Capacity</a>',
    "/form": '<form action="/saved"><input name="n" required><button>Send</button></form>',
}


class Site(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):  # noqa: D401
        pass

    def _send(self, code: int, body: str) -> None:
        data = f"<!doctype html><html><body>{body}</body></html>".encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):  # noqa: N802
        if self.path == "/tabs?tab=cap":
            return self._send(200, '<form action="/saved"><button>Grow</button></form>')
        path = self.path.split("?")[0]
        if path == "/wait":
            time.sleep(0.4)
            return self._send(200, "done")
        self._send(200, PAGES[path]) if path in PAGES else self._send(404, "no")

    def do_POST(self):  # noqa: N802
        self._send(500, "boom") if self.path == "/crash" else self._send(200, "ok")


@pytest.fixture(scope="module")
def site():
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Site)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


SCREENS = [("4.1", "/home"), ("4.2", "/list"), ("4.3", "/dlg"), ("4.4", "/boom"), ("4.5", "/slow"),
           ("4.6", "/acc/{id}"), ("4.7", "/form")]
BUTTONS = [("Save", "4.1"), ("Spread", "4.2"), ("Publish", "4.3"), ("Crash", "4.4"),
           ("Recount", "4.5"), ("Open", "4.6"), ("Send", "4.7"), ("Vanished", "4.1")]


def project(tmp: Path, click_ms: int = 300, code_lines: int = 50) -> Path:
    (tmp / "design").mkdir(parents=True)
    (tmp / "design" / "40-screens.md").write_text(
        "".join(f"## {sid} Screen\n" for sid, _ in SCREENS), encoding="utf-8")
    rows = [f"| S-{sid} | 40-screens §{sid} | Screen | route: {rt} · app/x.py | 1 | tests/t.py | done |"
            for sid, rt in SCREENS]
    rows += [f"| B-{b} | 40-screens §{sid} | «{b}» | app/x.py | 1 | tests/t.py | done |"
             for b, sid in BUTTONS]
    (tmp / "TRACE.md").write_text(
        "| id | design | item | built in | phase | verified by | status |\n|---|---|---|---|---|---|---|\n"
        + "\n".join(rows) + "\n", encoding="utf-8")
    (tmp / "ARCHITECTURE.md").write_text(textwrap.dedent(f"""\
        ## Budgets
        - **Click** — {click_ms} ms: pressing to settled.
        - **Code** — {code_lines} lines: the app's own code.
        """), encoding="utf-8")
    (tmp / "app").mkdir()
    (tmp / "app" / "x.py").write_text(
        '"""A docstring is not code."""\n\n# nor is a comment\nx = 1\ny = 2\n', encoding="utf-8")
    return tmp


def run(script: str, *args: str) -> tuple[int, str]:
    p = subprocess.run([sys.executable, str(SCRIPTS / script), *args], capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def results(out_dir: Path) -> dict[str, str]:
    data = json.loads((out_dir / "press.json").read_text(encoding="utf-8"))
    return {r["id"]: r["result"] for r in data["results"]}


def test_every_way_a_button_can_fail_is_named(tmp_path, site):
    p = project(tmp_path / "p")
    out = tmp_path / "press"
    code, text = run("press-check.py", str(p), "--base-url", site, "--out", str(out))
    got = results(out)
    assert code == 1, text
    assert got["B-Save"] == "ok"
    assert got["B-Spread"] == "dead"          # pressed, nothing happened
    assert got["B-Publish"] == "disabled"     # the «انتشار» that could never be pressed
    assert got["B-Crash"] == "error"          # the server answered 500
    assert got["B-Recount"] == "slow"         # 400 ms against a 300 ms budget
    assert got["B-Open"] == "skipped"         # /acc/{id} and nobody said which id
    assert got["B-Send"] == "needs-input"     # listed, not proven
    assert got["B-Vanished"] == "missing"
    assert "SKIPPED is not a pass" in text
    assert list((out / "screens").glob("*.jpg")), "one picture per screen, for the verdict page"


def test_a_route_parameter_fills_in_the_screen(tmp_path, site):
    p = project(tmp_path / "p")
    out = tmp_path / "press"
    run("press-check.py", str(p), "--base-url", site, "--param", "id=7", "--out", str(out))
    assert results(out)["B-Open"] == "ok"


def test_a_click_is_timed_by_the_page_not_by_the_network_going_quiet(tmp_path, site):
    """Waiting for the network to be idle adds half a second to every press; a budget of 300 ms
    would then fail every button. Save navigates to a tiny page and must come in well under it."""
    p = project(tmp_path / "p")
    out = tmp_path / "press"
    run("press-check.py", str(p), "--base-url", site, "--out", str(out))
    save = next(r for r in json.loads((out / "press.json").read_text())["results"] if r["id"] == "B-Save")
    assert save["ms"] < 300, save


def test_it_refuses_to_press_buttons_on_a_live_panel(tmp_path):
    p = project(tmp_path / "p")
    code, text = run("press-check.py", str(p), "--base-url", "https://leader.example.org")
    assert code == 2 and "REFUSED" in text


def test_budget_check_counts_code_only_and_holds_the_line(tmp_path):
    p = project(tmp_path / "p", code_lines=2)
    code, text = run("budget-check.py", str(p))
    assert code == 0 and "2 lines of code" in text, text      # docstring, comment, blanks not counted
    (p / "app" / "y.py").write_text("z = 3\n", encoding="utf-8")
    code, text = run("budget-check.py", str(p))
    assert code == 1 and "OVER BUDGET" in text
    (p / "ARCHITECTURE.md").write_text("## Budgets\n- **Click** — 1 s\n", encoding="utf-8")
    code, text = run("budget-check.py", str(p))
    assert code == 1 and "no code budget" in text


def test_the_verdict_page_shows_every_promise_and_says_what_it_cannot_prove(tmp_path, site):
    p = project(tmp_path / "p", code_lines=1)
    out = tmp_path / "press"
    run("press-check.py", str(p), "--base-url", site, "--out", str(out))
    page = tmp_path / "verdict.html"
    code, text = run("verdict-page.py", str(p), "--press", str(out), "--out", str(page))
    html = page.read_text(encoding="utf-8")
    assert code == 0, text
    assert 'lang="en" dir="ltr"' in html and "prefers-color-scheme:dark" in html
    assert "pressed, nothing happened" in html and "disabled, cannot be pressed" in html  # by name
    assert "no recorded test run" in html                                              # no suite run
    assert "limit: 1" in html                                                          # code budget
    assert "What this page does not prove" in html
    assert "data:image/jpeg;base64," in html
    assert "fonts.googleapis" not in html, "a verdict page must not call out to a third party"


def test_the_verdict_page_can_be_written_in_persian(tmp_path, site):
    p = project(tmp_path / "p", code_lines=1)
    out = tmp_path / "press"
    run("press-check.py", str(p), "--base-url", site, "--out", str(out))
    page = tmp_path / "verdict.html"
    code, text = run("verdict-page.py", str(p), "--press", str(out), "--lang", "fa", "--out", str(page))
    html = page.read_text(encoding="utf-8")
    assert code == 0, text
    assert 'lang="fa" dir="rtl"' in html
    assert "زده شد، هیچ اتفاقی نیفتاد" in html and "غیرفعال" in html
    assert "هیچ اجرای ثبت‌شده‌ای از تست‌ها نیست" in html
    assert "سقف: ۱" in html
    assert "این صفحه چه چیزی را ثابت نمی‌کند" in html


def test_a_button_inside_a_tab_is_found_through_its_own_route(tmp_path, site):
    """43 of the first factory app's 79 buttons sat in tabs, dialogs and later steps, and press-check only
    opened each screen's first view. A row that names the state that shows it is pressed there."""
    p = project(tmp_path / "p")
    (p / "design" / "40-screens.md").write_text("## 4.8 Tabs\n", encoding="utf-8")
    base = "| id | design | item | built in | phase | verified by | status |\n|---|---|---|---|---|---|---|\n"
    screen = "| S-4.8 | 40-screens §4.8 | Tabs | route: /tabs · app/x.py | 1 | tests/t.py | done |\n"
    (p / "TRACE.md").write_text(
        base + screen + "| B-Grow | 40-screens §4.8 | «Grow» | app/x.py | 1 | tests/t.py | done |\n",
        encoding="utf-8")
    out = tmp_path / "press"
    run("press-check.py", str(p), "--base-url", site, "--out", str(out))
    assert results(out)["B-Grow"] == "missing"
    (p / "TRACE.md").write_text(
        base + screen + "| B-Grow | 40-screens §4.8 | «Grow» | tab: route: /tabs?tab=cap · app/x.py | 1 | tests/t.py | done |\n",
        encoding="utf-8")
    run("press-check.py", str(p), "--base-url", site, "--out", str(out))
    assert results(out)["B-Grow"] == "ok"
