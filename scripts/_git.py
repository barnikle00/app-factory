"""The two trees the commit lock compares: what the tests passed on, and what is being committed.

Both are computed without touching the real index: a copy of it goes into a temporary file, the
files are added there, and `git write-tree` names the result. Same content, same id — so a single
changed byte between the test run and the commit is visible as a different id.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path


def git(repo: Path, *args: str, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, env=env)


def toplevel(path: Path) -> Path | None:
    r = git(path, "rev-parse", "--show-toplevel")
    return Path(r.stdout.strip()) if r.returncode == 0 else None


def git_dir(repo: Path) -> Path:
    return Path(git(repo, "rev-parse", "--absolute-git-dir").stdout.strip())


def _tree_with(repo: Path, *add_args: str) -> str:
    real = git_dir(repo) / "index"
    with tempfile.TemporaryDirectory() as tmp:
        index = Path(tmp) / "index"
        if real.exists():
            index.write_bytes(real.read_bytes())
            # Keep the index's own timestamp. Git trusts an entry's saved file size and time unless
            # the entry is as new as the index itself ("racily clean") — then it reads the file
            # again. A copy stamped «now» made every entry look safely older, so a same-size edit
            # made within the same tick as the last commit was not seen: 12 of 600 trees measured
            # stale, and one flaky commit-lock test, before this line (2026-09-24).
            st = real.stat()
            os.utime(index, ns=(st.st_atime_ns, st.st_mtime_ns))
        env = dict(os.environ, GIT_INDEX_FILE=str(index))
        if add_args:
            git(repo, "add", *add_args, env=env)
        return git(repo, "write-tree", env=env).stdout.strip()


def working_tree_id(repo: Path) -> str:
    """Everything `git add -A` would stage: what a test run actually ran against."""
    return _tree_with(repo, "-A")


def commit_tree_id(repo: Path, all_tracked: bool) -> str:
    """The tree `git commit` (or `git commit -a`) is about to record."""
    return _tree_with(repo, "-u") if all_tracked else _tree_with(repo)


def has_head(repo: Path) -> bool:
    return git(repo, "rev-parse", "--verify", "-q", "HEAD").returncode == 0
