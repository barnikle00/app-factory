"""foundation/tooling/realdb.py — a real PostgreSQL for data tests, and a loud failure without one.

the first factory app's data tests all ran on fakes, and two bugs only a real database can have went live:
a query that depended on the search path, and a race between two writers. This proves the fixture
starts a real server that speaks PostgreSQL, and that without Docker the suite FAILS — a data suite
that silently did not run is the thing the fixture exists to end.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

TOOLING = Path(__file__).resolve().parent.parent / "foundation" / "tooling"
sys.path.insert(0, str(TOOLING))

needs_docker = pytest.mark.skipif(
    shutil.which("docker") is None
    or subprocess.run(["docker", "info"], capture_output=True).returncode != 0,
    reason="Docker is not running on this machine — the factory's own test of the fixture needs it")


@needs_docker
def test_it_starts_a_server_that_speaks_postgresql(tmp_path):
    test = tmp_path / "test_db.py"
    test.write_text(textwrap.dedent("""\
        import socket, struct
        from urllib.parse import urlparse
        from realdb import realdb_url  # noqa: F401

        def test_speaks_postgres(realdb_url):
            u = urlparse(realdb_url)
            with socket.create_connection((u.hostname, u.port), timeout=5) as s:
                s.sendall(struct.pack("!ii", 8, 80877103))      # PostgreSQL's SSLRequest
                assert s.recv(1) in (b"S", b"N")                # only a PostgreSQL answers this
        """), encoding="utf-8")
    env = {**os.environ, "PYTHONPATH": str(TOOLING)}
    p = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", str(test)],
                       capture_output=True, text=True, env=env, timeout=180)
    assert p.returncode == 0, p.stdout + p.stderr
    left = subprocess.run(["docker", "ps", "-q", "--filter", "name=realdb-"], capture_output=True, text=True)
    assert left.stdout.strip() == "", "the container must be removed after the run"


def test_without_docker_the_data_tests_fail_rather_than_skip(tmp_path):
    test = tmp_path / "test_db.py"
    test.write_text("from realdb import realdb_url  # noqa: F401\n\n"
                    "def test_needs_db(realdb_url):\n    pass\n", encoding="utf-8")
    env = {**os.environ, "PYTHONPATH": str(TOOLING), "PATH": str(tmp_path)}   # no docker on PATH
    p = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", str(test)],
                       capture_output=True, text=True, env=env)
    out = p.stdout + p.stderr
    assert p.returncode != 0 and "skipped" not in out and "Docker is not installed" in out, out

