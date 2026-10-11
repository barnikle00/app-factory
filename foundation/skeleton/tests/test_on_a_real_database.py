"""The foundation on a real PostgreSQL: migrations, sign-in, switches, and the write guard.

A fake database has no transactions, no constraints and no concurrency — the first factory app's fakes
passed a query that died on the real server and a race that lost data silently. So the pieces
that touch data are proven here, against the real thing.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth.owner import make_owner
from app.core.outside import Refused, guarded_write
from app.core.switches import set_switch, write_switch
from app.core.text import utc_now
from app.db.session import create_engine, create_session_factory, session_scope
from app.web.app import create_app
from tests.conftest import make_settings

pytestmark = pytest.mark.realdb


def with_db(dsn: str, work):
    """Run `work(factory)` on its own engine and loop, and close both."""

    async def go():
        engine = create_engine(make_settings(dsn).database)
        try:
            return await work(create_session_factory(engine))
        finally:
            await engine.dispose()

    return asyncio.run(go())


@pytest.fixture
def db_client(migrated_url: str) -> Iterator[TestClient]:
    with TestClient(create_app(make_settings(migrated_url)), follow_redirects=False) as c:
        yield c


def test_an_owner_signs_in_and_reaches_the_switches(migrated_url, db_client):
    async def owner(factory: async_sessionmaker[AsyncSession]) -> str:
        async with session_scope(factory) as s:
            return await make_owner(s, make_settings().auth, name="Ada Lovelace", reset=True)

    password = with_db(migrated_url, owner)
    wrong = db_client.post("/login", data={"name": "Ada Lovelace", "password": "wrong"})
    assert wrong.status_code == 401
    r = db_client.post(
        "/login", data={"name": "Ada Lovelace", "password": password, "next": "/switches"}
    )
    assert r.status_code == 303 and r.headers["location"] == "/switches"
    assert 'action="/switches"' in db_client.get("/switches").text


def test_a_second_owner_is_not_made_by_accident(migrated_url):
    async def twice(factory):
        async with session_scope(factory) as s:
            await make_owner(s, make_settings().auth, name="Ada Lovelace", reset=True)
        async with session_scope(factory) as s:
            return await make_owner(s, make_settings().auth, name="Second Owner", reset=False)

    assert "already exists" in with_db(migrated_url, twice)


def test_the_guard_stops_a_write_loop_and_health_names_it(migrated_url, db_client):
    """The the first factory app loop, replayed: the same folder written every tick. Off → nothing is
    written; on → three writes land and the fourth opens the breaker; health says 503 and names
    it; switching off and on again is what resets it."""
    target, sent = "telegram-loop", []
    outside = make_settings(migrated_url).outside

    async def tick(factory):
        await guarded_write(
            factory,
            outside,
            target,
            key="folder:31",
            content="same 150 people",
            write=lambda: asyncio.sleep(0, sent.append(1)),
        )

    with pytest.raises(Refused, match="switched off"):
        with_db(migrated_url, tick)
    assert sent == []

    async def turn(factory, on: bool):
        async with session_scope(factory) as s:
            await set_switch(s, write_switch(target), on=on, by=None, at=utc_now())

    with_db(migrated_url, lambda f: turn(f, True))
    for _ in range(3):
        with_db(migrated_url, tick)
    with pytest.raises(Refused, match="not sticking"):
        with_db(migrated_url, tick)
    assert len(sent) == 3

    ready = db_client.get("/health/ready")
    assert ready.status_code == 503
    assert any(f.startswith(f"writes:{target}") for f in ready.json()["failed"])
    assert write_switch(target) in ready.json()["switches_on"]

    with_db(migrated_url, lambda f: turn(f, False))
    with_db(migrated_url, lambda f: turn(f, True))
    with_db(migrated_url, tick)
    assert len(sent) == 4
    assert not any(
        f.startswith(f"writes:{target}") for f in db_client.get("/health/ready").json()["failed"]
    )
