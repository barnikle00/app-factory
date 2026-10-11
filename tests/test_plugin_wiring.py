"""The plugin as Claude Code loads it: manifests agree, every hook command points at a real script and
behaves as wired, and every file a skill names inside the plugin exists.

The scripts have their own tests. This file proves the *wiring* — the part that breaks when a file is
renamed or a path in a skill goes stale, and that no other test would notice.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
HOOKS = json.loads((ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8"))["hooks"]
SKILLS = sorted(p.parent for p in (ROOT / "skills").glob("*/SKILL.md"))
EXPECTED_SKILLS = {"factory-guide", "design-task", "design-architecture", "build-spec",
                   "run-phases", "final-check", "design-system"}


def commands(event: str) -> list[str]:
    return [h["command"] for group in HOOKS[event] for h in group["hooks"]]


def run_hook(command: str, payload: dict, cwd: Path) -> subprocess.CompletedProcess:
    env = {**os.environ, "CLAUDE_PLUGIN_ROOT": str(ROOT), "XDG_CACHE_HOME": str(cwd / ".cache")}
    return subprocess.run(command, shell=True, input=json.dumps(payload), capture_output=True,
                          text=True, env=env, cwd=cwd, timeout=60)


def test_the_manifests_agree():
    plugin = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    market = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    entry = market["plugins"][0]
    assert plugin["name"] == entry["name"] == "app-factory"
    assert plugin["version"] == entry["version"]
    assert (ROOT / "LICENSE").is_file() and (ROOT / "README.md").is_file()


def test_the_plugin_ships_exactly_the_expected_skills():
    assert {p.name for p in SKILLS} == EXPECTED_SKILLS


@pytest.mark.parametrize("skill", SKILLS, ids=lambda p: p.name)
def test_every_skill_has_a_name_that_matches_its_folder_and_a_description(skill):
    text = (skill / "SKILL.md").read_text(encoding="utf-8")
    front = text.split("---", 2)[1]
    assert re.search(rf"^name:\s*{re.escape(skill.name)}\s*$", front, re.M), "name must equal the folder"
    assert re.search(r"^description:", front, re.M)
    assert len(front) < 3000, "a description that long is read on every session; keep it short"


@pytest.mark.parametrize("skill", SKILLS, ids=lambda p: p.name)
def test_every_plugin_path_a_skill_names_exists(skill):
    text = (skill / "SKILL.md").read_text(encoding="utf-8")
    for rel in set(re.findall(r"\$\{CLAUDE_PLUGIN_ROOT\}/([\w./*\-\[\]]+)", text)):
        rel = rel.rstrip(".,:;)`")
        if "*" in rel:
            assert list(ROOT.glob(rel)), f"{skill.name} names {rel}, which matches nothing"
        else:
            assert (ROOT / rel).exists(), f"{skill.name} names {rel}, which does not exist"


def test_no_skill_leaks_the_owners_workspace():
    for skill in SKILLS:
        text = (skill / "SKILL.md").read_text(encoding="utf-8")
        for word in ("Barnikle", "Workshop", "_factory", "vault", "Worker Constitution", "House Rules"):
            assert word not in text, f"{skill.name} still mentions {word!r}"


@pytest.mark.parametrize("event", sorted(HOOKS))
def test_every_hook_command_points_at_a_script_that_exists(event):
    for command in commands(event):
        script = re.search(r"\$\{CLAUDE_PLUGIN_ROOT\}/(scripts/[\w\-]+\.py)", command)
        assert script and (ROOT / script.group(1)).is_file(), command


def test_session_start_names_a_factory_project_and_stays_silent_elsewhere(tmp_path):
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / ".factory").write_text("x\n")
    (tmp_path / "other").mkdir()
    [command] = commands("SessionStart")
    hit = run_hook(command, {"cwd": str(tmp_path)}, tmp_path)
    assert hit.returncode == 0
    context = json.loads(hit.stdout)["hookSpecificOutput"]["additionalContext"]
    assert "app" in context and str(ROOT / "scripts" / "verified.py") in context
    miss = run_hook(command, {"cwd": str(tmp_path / "other")}, tmp_path)
    assert miss.returncode == 0 and miss.stdout.strip() == ""


def test_the_edit_hooks_refuse_a_giant_file_in_a_factory_project_and_ignore_other_projects(tmp_path):
    factory, plain = tmp_path / "factory-app", tmp_path / "plain"
    for d in (factory, plain):
        d.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=d, check=True)
    (factory / ".factory").write_text("x\n")
    big = "\n".join(f"x{i} = {i}" for i in range(600)) + "\n"
    for d in (factory, plain):
        (d / "big.py").write_text(big)
    results = {}
    for name, d in (("factory", factory), ("plain", plain)):
        payload = {"tool_input": {"file_path": str(d / "big.py")}, "cwd": str(d)}
        results[name] = [run_hook(c, payload, d).returncode for c in commands("PostToolUse")]
    assert 2 in results["factory"], "a 600-line file in a factory project must be refused"
    assert set(results["plain"]) == {0}, "a project the factory did not build must never be touched"


def test_the_commit_lock_refuses_an_untested_commit_in_a_factory_project(tmp_path):
    repo = tmp_path / "factory-app"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    (repo / ".factory").write_text("x\n")
    (repo / "app.py").write_text("x = 1\n")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    [command] = commands("PreToolUse")
    payload = {"tool_name": "Bash", "tool_input": {"command": "git commit -m wip"}, "cwd": str(repo)}
    r = run_hook(command, payload, repo)
    assert r.returncode == 2 and "verified.py" in r.stderr
