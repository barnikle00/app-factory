"""What the app is allowed to do right now — every switch is off until a person turns it on.

On the first factory app, writing to an outside account was switched on from the panel and no record
anywhere knew it until a five-day write loop was found. A switch here is a row: who turned it on
and when, listed by /health/ready and on the switches page.

A write switch is named `write:<target>`. Turning one on also closes that target's breaker
(ADR 0010): switching off and on again is the deliberate human act that resets it.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import GuardState, Switch

WRITE_PREFIX = "write:"


def write_switch(target: str) -> str:
    return f"{WRITE_PREFIX}{target}"


async def is_on(session: AsyncSession, name: str) -> bool:
    row = await session.get(Switch, name)
    return bool(row and row.is_on)


async def set_switch(
    session: AsyncSession, name: str, *, on: bool, by: int | None, at: datetime
) -> None:
    values = {"is_on": on, "changed_at": at, "changed_by": by}
    await session.execute(
        insert(Switch)
        .values(name=name, **values)
        .on_conflict_do_update(index_elements=[Switch.name], set_=values)
    )
    if on and name.startswith(WRITE_PREFIX):
        await session.execute(
            update(GuardState)
            .where(GuardState.target == name[len(WRITE_PREFIX) :])
            .values(breaker_reason=None, breaker_opened_at=None, repeats={}, writes_in_window=0)
        )


async def all_switches(session: AsyncSession, *, limit: int) -> list[Switch]:
    return list((await session.scalars(select(Switch).order_by(Switch.name).limit(limit))).all())
