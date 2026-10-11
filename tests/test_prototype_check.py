"""prototype-check.py — the mobile round, tested both ways.

Every failure below is one the first factory app's approved prototype actually had on 2026-09-15: no
viewport tag, a list cut off inside a box that hides overflow, controls too small to tap. Each
must fail by name; a clean page and a table that scrolls inside its own box must pass.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("playwright")
SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "prototype-check.py"

HEAD = '<meta name="viewport" content="width=device-width, initial-scale=1">'
STYLE = """<style>
:root{--bg:#FFFFFF;--ink:#1A1F1D}
:root[data-theme="dark"]{--bg:#101513;--ink:#E5ECE8}
body{margin:0;padding:12px;background:var(--bg);color:var(--ink);font:16px/1.6 sans-serif}
button{min-height:44px;padding:0 16px}
</style>"""


def page(tmp: Path, name: str, body: str, head: str = HEAD, style: str = STYLE) -> Path:
    f = tmp / f"{name}.html"
    f.write_text(f'<!doctype html><html dir="rtl" lang="fa"><head><meta charset="utf-8">{head}{style}</head>'
                 f"<body>{body}</body></html>", encoding="utf-8")
    return f


def run(*args: str) -> tuple[int, str]:
    p = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, timeout=120)
    return p.returncode, p.stdout + p.stderr


def test_a_clean_page_passes(tmp_path):
    code, out = run(str(page(tmp_path, "good", "<h1>پوشه‌ها</h1><button>پوشهٔ تازه</button>")))
    assert code == 0, out


def test_no_viewport_tag_fails_the_way_the_prototype_did(tmp_path):
    code, out = run(str(page(tmp_path, "noviewport", "<button>پوشهٔ تازه</button>", head="")))
    assert code != 0 and "no device-width viewport tag" in out


def test_a_row_cut_off_inside_a_hidden_box_fails(tmp_path):
    body = '<div class="flist" style="overflow:hidden"><div style="width:448px">ردیف پوشه</div></div>'
    code, out = run(str(page(tmp_path, "clipped", body)))
    assert code != 0 and "cut off" in out and "div.flist" in out


def test_a_wide_table_that_scrolls_inside_its_box_passes(tmp_path):
    body = '<div style="overflow-x:auto"><table style="width:561px"><tr><td>تشخیص</td></tr></table></div>'
    code, out = run(str(page(tmp_path, "scrolls", body)))
    assert code == 0, out


def test_controls_too_small_to_tap_fail(tmp_path):
    body = '<button style="min-height:0;height:24px">↑</button>'
    code, out = run(str(page(tmp_path, "tiny", body)))
    assert code != 0 and "shorter than 44px" in out


def test_text_that_fades_out_in_dark_mode_fails(tmp_path):
    style = STYLE.replace('--ink:#E5ECE8', '--ink:#2A302D')
    code, out = run(str(page(tmp_path, "darkfade", "<p>بر پایهٔ دادهٔ تا ۴ دقیقه پیش</p>", style=style)))
    assert code != 0 and "contrast in dark" in out and "contrast in light" in out.split("FAIL  contrast in dark")[0]


def test_each_screen_of_a_single_page_prototype_is_checked_by_name(tmp_path):
    body = ('<div id="view"></div><script>'
            'const SCREENS={a:"<p>خانه</p>",b:\'<div class="flist" style="overflow:hidden"><div style="width:448px">ردیف</div></div>\'};'
            'function show(v){document.getElementById("view").innerHTML=SCREENS[v];}show("a");</script>')
    f = page(tmp_path, "spa", body)
    code, out = run(str(f), "--view", "a", "--view", "b", "--show", "show('{view}')")
    assert code != 0
    first, second = out.split("\nb — 375px")
    assert "FAIL" not in first and "cut off" in second


def _raw(tmp: Path, name: str, html: str) -> Path:
    f = tmp / f"{name}.html"
    f.write_text(html, encoding="utf-8")
    return f


def test_rtl_set_on_the_app_wrapper_counts(tmp_path):
    """the first factory app's prototype sets dir on its own wrapper, not on <html>. That is right-to-left."""
    f = _raw(tmp_path, "wrap", f'<!doctype html><html lang="fa"><head><meta charset="utf-8">{HEAD}{STYLE}</head>'
             '<body><div class="app" dir="rtl"><p>پوشه‌های سلیمانی</p><button>پوشهٔ تازه</button></div></body></html>')
    code, out = run(str(f))
    assert code == 0, out


def test_persian_laid_out_left_to_right_fails(tmp_path):
    f = _raw(tmp_path, "ltr", f'<!doctype html><html lang="fa"><head><meta charset="utf-8">{HEAD}{STYLE}</head>'
             '<body><p>پوشه‌های سلیمانی</p><button>پوشهٔ تازه</button></body></html>')
    code, out = run(str(f))
    assert code != 0 and "right-to-left" in out


def test_a_missing_viewport_tag_still_reports_what_will_be_cut_off(tmp_path):
    """The tag's absence must not hide the next problem: the prototype's folder list passed as
    'nothing cut off' only because the phone had laid the page out at 980px."""
    body = '<div class="flist" style="overflow:hidden"><div style="width:448px">ردیف پوشه</div></div>'
    code, out = run(str(page(tmp_path, "both", body, head="")))
    assert code != 0 and "no device-width viewport tag" in out and "div.flist" in out
