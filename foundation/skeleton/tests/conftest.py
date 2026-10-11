"""Fixtures every suite builds on. Pages and rules need no database; data code gets a real one.

`realdb_url` is a throwaway PostgreSQL per test run (tests/realdb.py — needs Docker, and fails
rather than skips without it). `migrated_url` is that database with every migration applied.
"""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import (
    AuthSettings,
    DatabaseSettings,
    DisplaySettings,
    ObservabilitySettings,
    OutsideSettings,
    Settings,
    TimingSettings,
    WebSettings,
)
from app.web.app import create_app
from tests.realdb import realdb_url

ROOT = Path(__file__).resolve().parent.parent


def make_settings(dsn: str | None = None) -> Settings:
    return Settings(
        database=DatabaseSettings(**({"dsn": dsn} if dsn else {})),
        web=WebSettings(readiness_check_timeout_seconds=2.0),
        # Signs nothing outside a test run; the real key is an environment variable on the server.
        auth=AuthSettings(
            session_signing_key="tests-only-key-signing-nothing-real",
            session_cookie_secure=False,
            password_hash_memory_cost_kib=8_192,
            password_hash_time_cost_count=1,
        ),
        observability=ObservabilitySettings(log_as_json=False),
        outside=OutsideSettings(),
        display=DisplaySettings(),
        timing=TimingSettings(),
    )


@pytest.fixture
def settings() -> Settings:
    return make_settings()


@pytest.fixture
def panel(settings: Settings) -> FastAPI:
    return create_app(settings)


@pytest.fixture
def client(panel: FastAPI) -> Iterator[TestClient]:
    with TestClient(panel, follow_redirects=False) as opened:
        yield opened


@pytest.fixture(scope="session")
def migrated_url(realdb_url: str) -> str:
    """The real database with `alembic upgrade head` applied, as the app's async address."""
    dsn = realdb_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    done = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=ROOT,
        env={**os.environ, "DB_DSN": dsn},
        capture_output=True,
        text=True,
    )
    assert done.returncode == 0, done.stderr
    return dsn
