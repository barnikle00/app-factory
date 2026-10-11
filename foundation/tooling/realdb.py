"""A real, throwaway PostgreSQL for every test that touches data.

Copied into a new factory project as `tests/realdb.py` by build-spec step 0, and registered in
`tests/conftest.py` with one line:

    from tests.realdb import realdb_url  # noqa: F401 — a pytest fixture

A test that takes `realdb_url` gets the address of an empty PostgreSQL started for this test run
and removed after it. The project's own fixture builds on it — run the migrations, open the
engine — so the data code is tested against the database it will run on.

WHY. the first factory app tested all of its data code against fake connections, and shipped two bugs no
fake can have. A table listing asked about a name without its schema: PostgreSQL resolved it
against the search path, the query died on the real database, and a working
connection was reported as «unreachable». And two processes creating the same person at once lost
a race: the loser rolled back everything its unit of work had written, twice in the first two
hours, silently. A fake has no search path and cannot race. A real database has both.

It needs Docker. Without Docker it FAILS — it never skips — because a data suite that quietly did
not run is the exact thing this file exists to end.
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import time
import uuid
from collections.abc import Iterator

import pytest

IMAGE = os.environ.get("REALDB_IMAGE", "postgres:17-alpine")
READY_SECONDS = 60


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def realdb_url() -> Iterator[str]:
    if shutil.which("docker") is None:
        pytest.fail(
            "realdb: Docker is not installed or not on PATH. The data tests did not run — "
            "this is a failure, not a skip."
        )
    name, port = f"realdb-{uuid.uuid4().hex[:10]}", _free_port()
    # A throwaway container's password: it guards an empty database on 127.0.0.1 for one test run.
    started = subprocess.run(
        [
            "docker",
            "run",
            "-d",
            "--rm",
            "--name",
            name,
            "-e",
            "POSTGRES_PASSWORD=realdb",
            "-e",
            "POSTGRES_DB=app",
            "-p",
            f"127.0.0.1:{port}:5432",
            IMAGE,
        ],
        capture_output=True,
        text=True,
    )
    if started.returncode != 0:
        pytest.fail(f"realdb: could not start {IMAGE}: {started.stderr.strip()[:300]}")
    try:
        # Ask over TCP, not the socket: during first start PostgreSQL runs a temporary server on the
        # socket only, answers «ready», and then shuts down — a socket check passes too early.
        deadline = time.monotonic() + READY_SECONDS
        while (
            subprocess.run(
                [
                    "docker",
                    "exec",
                    name,
                    "pg_isready",
                    "-h",
                    "127.0.0.1",
                    "-U",
                    "postgres",
                    "-d",
                    "app",
                ],
                capture_output=True,
            ).returncode
            != 0
        ):
            if time.monotonic() > deadline:
                pytest.fail(f"realdb: PostgreSQL was not ready after {READY_SECONDS} s")
            time.sleep(0.3)
        yield f"postgresql://postgres:realdb@127.0.0.1:{port}/app"
    finally:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True)
