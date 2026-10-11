"""The factory's rules apply only to projects the factory built.

The owner decided that explicitly — new projects only, no retrofit — and until
the `.factory` marker existed nothing enforced it. The failure that proved it
mattered was measured, not imagined: on a copy of an older project, one
edit let the lint hook delete an import that app/help.py re-imports at startup.

These tests hold both halves of the promise:
  · an existing project (no marker) is left byte-for-byte as it was;
  · a factory project gets the rules — and even there, no import is deleted.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
RE_EXPORT = (
    "from collections import OrderedDict   # unused here, re-exported to another module\n"
    "x  =  1\n"
)
BAD_TEMPLATE = '<table>\n  <button style="color:#fff">ok</button>\n</table>\n'


def hook(script: str, f: Path, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPTS / script)],
                          input=json.dumps({"tool_input": {"file_path": str(f)}}),
                          capture_output=True, text=True, env=env)


def make(tmp_path: Path, marked: bool) -> Path:
    root = tmp_path / ("new-app" if marked else "old-app")
    (root / "app").mkdir(parents=True)
    if marked:
        (root / ".factory").write_text("factory project — test\n")
    return root


needs_ruff = pytest.mark.skipif(not shutil.which("ruff"), reason="ruff not installed")


@needs_ruff
def test_an_existing_project_is_left_byte_for_byte(tmp_path):
    f = make(tmp_path, marked=False) / "app" / "mod.py"
    f.write_text(RE_EXPORT)
    r = hook("lint-touched.py", f)
    assert r.returncode == 0
    assert f.read_text() == RE_EXPORT, "the hook changed a file in a project it did not build"


@needs_ruff
def test_a_factory_project_is_formatted_but_never_loses_an_import(tmp_path):
    f = make(tmp_path, marked=True) / "app" / "mod.py"
    f.write_text(RE_EXPORT)
    hook("lint-touched.py", f)
    out = f.read_text()
    assert "x = 1" in out, "formatting did not run in a factory project"
    assert "import OrderedDict" in out, (
        "the hook deleted an import. That is exactly the edit that stopped the sales "
        "tracker's web app and bot from starting — it must be reported, never fixed")


def test_the_design_linter_is_silent_in_an_existing_project(tmp_path):
    f = make(tmp_path, marked=False) / "app" / "page.html"
    f.write_text(BAD_TEMPLATE)
    r = hook("ds-lint.py", f)
    assert r.returncode == 0 and not r.stderr, (
        "ds-lint spoke in a project with no ds.html — 'use ds.table()' there is an "
        "instruction to break the page")


def test_the_design_linter_fires_in_a_factory_project(tmp_path):
    f = make(tmp_path, marked=True) / "app" / "page.html"
    f.write_text(BAD_TEMPLATE)
    r = hook("ds-lint.py", f)
    assert r.returncode != 0 and "[D5]" in r.stderr


def test_the_size_guard_is_silent_in_an_existing_project(tmp_path):
    f = make(tmp_path, marked=False) / "app" / "big.py"
    f.write_text("x = 1\n" * 600)
    assert hook("size-guard.py", f).returncode == 0


def test_the_marker_is_found_from_deep_inside_the_project(tmp_path):
    sys.path.insert(0, str(SCRIPTS))
    from _project import factory_root
    root = make(tmp_path, marked=True)
    deep = root / "app" / "web" / "routes" / "x.py"
    deep.parent.mkdir(parents=True)
    deep.write_text("")
    assert factory_root(deep) == root.resolve()
    assert factory_root(make(tmp_path, marked=False) / "app") is None


def test_ruff_is_found_without_the_shells_path(tmp_path):
    """A hook does not get the terminal's PATH. ruff lives in ~/.local/bin, which a plain PATH lacks,
    and the hook used to return 0 when it could not see it — linting nothing, silently."""
    import os
    if not (Path.home() / ".local" / "bin" / "ruff").is_file():
        pytest.skip("ruff is not in ~/.local/bin on this machine")
    f = make(tmp_path, marked=True) / "app" / "mod.py"
    f.write_text(RE_EXPORT)
    env = {"PATH": "/usr/bin:/bin", "HOME": os.environ["HOME"]}
    hook("lint-touched.py", f, env=env)
    assert "x = 1" in f.read_text(), "the hook did not format — it could not find ruff without the shell's PATH"


def test_a_missing_ruff_is_said_out_loud(tmp_path):
    import os
    f = make(tmp_path, marked=True) / "app" / "mod.py"
    f.write_text(RE_EXPORT)
    env = dict(os.environ, FACTORY_RUFF=str(tmp_path / "no-such-ruff"))
    r = hook("lint-touched.py", f, env=env)
    assert r.returncode == 1 and "ruff was not found" in r.stderr and "not a pass" in r.stderr
