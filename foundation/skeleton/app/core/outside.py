"""The one door every write to an outside system goes through (ADR 0010).

A message sent, a folder written into someone's account, a record changed in another team's
system — the writes an app cannot take back. the first factory app wrote the same folder into a
a customer's own account 70,565 times in five days while its health said «ready»: the planner
compared Telegram with what it *intended*, the adapter sent something slightly different, and the
two never agreed. This guard does not need to know why a write repeats to stop it.

For each target:
  · **off by default** — nothing is written while `write:<target>` is off
  · **a ceiling** — more writes in an hour than the target's ceiling opens the breaker
  · **a breaker on repeats** — the same key written with the same content more than the repeat
    limit in an hour means the write is not sticking; the breaker opens
  · **an open breaker refuses everything** until a person switches the target off and on again,
    and /health/ready names it

Use it as the only caller of the outside client's writing methods:

    await guarded_write(factory, settings.outside, "telegram", key=f"folder:{fid}",
                        content=repr(members), write=lambda: client.update_folder(...))
"""

from __future__ import annotations

import hashlib
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import SECONDS_PER_HOUR, OutsideSettings
from app.core.switches import is_on, write_switch
from app.core.text import utc_now
from app.db.models import GuardState
from app.db.session import session_scope

WINDOW = timedelta(seconds=SECONDS_PER_HOUR)


class Refused(Exception):
    """The guard did not let this write through. The reason is for the log and the page."""

    def __init__(self, target: str, reason: str) -> None:
        super().__init__(f"{target}: {reason}")
        self.target = target
        self.reason = reason


@dataclass
class Guard:
    """The rules, with no database — so every one of them is tested directly."""

    target: str
    switched_on: bool
    hourly_ceiling: int
    repeat_limit: int
    window_started_at: datetime | None = None
    writes_in_window: int = 0
    repeats: dict[str, list] = field(default_factory=dict)
    breaker_reason: str | None = None
    breaker_opened_at: datetime | None = None

    def admit(self, key: str, content: str, *, now: datetime) -> None:
        """Record this write, or raise `Refused` — opening the breaker when the write is wrong."""
        if not self.switched_on:
            raise Refused(
                self.target,
                f"switched off — nothing is written until {write_switch(self.target)} is on",
            )
        if self.breaker_reason:
            raise Refused(
                self.target, f"breaker open since {self.breaker_opened_at}: {self.breaker_reason}"
            )
        if self.window_started_at is None or now - self.window_started_at >= WINDOW:
            self.window_started_at, self.writes_in_window, self.repeats = now, 0, {}
        fingerprint = hashlib.sha256(content.encode()).hexdigest()[:16]
        last = self.repeats.get(key)
        times = last[1] + 1 if last and last[0] == fingerprint else 1
        if times > self.repeat_limit:
            self._open(
                f"«{key}» written {times} times unchanged within an hour — the write is not sticking",
                now,
            )
        if self.writes_in_window + 1 > self.hourly_ceiling:
            self._open(f"more than {self.hourly_ceiling} writes within an hour", now)
        self.repeats[key] = [fingerprint, times]
        self.writes_in_window += 1

    def _open(self, reason: str, now: datetime) -> None:
        self.breaker_reason, self.breaker_opened_at = reason, now
        raise Refused(self.target, reason)


async def _load(
    session: AsyncSession, target: str, settings: OutsideSettings
) -> tuple[GuardState, Guard]:
    row = await session.get(GuardState, target, with_for_update=True)
    if row is None:
        row = GuardState(target=target, writes_in_window=0, repeats={})
        session.add(row)
    guard = Guard(
        target=target,
        switched_on=await is_on(session, write_switch(target)),
        hourly_ceiling=settings.ceiling_for(target),
        repeat_limit=settings.repeat_limit_for(target),
        window_started_at=row.window_started_at,
        writes_in_window=row.writes_in_window or 0,
        repeats=dict(row.repeats or {}),
        breaker_reason=row.breaker_reason,
        breaker_opened_at=row.breaker_opened_at,
    )
    return row, guard


async def guarded_write(
    factory: async_sessionmaker[AsyncSession],
    settings: OutsideSettings,
    target: str,
    *,
    key: str,
    content: str,
    write: Callable[[], Awaitable[object]],
) -> None:
    """Admit the write and remember it — committed on its own, so an opened breaker is kept even
    though the caller's work then fails — and only then perform it."""
    refused: Refused | None = None
    async with session_scope(factory) as session:
        row, guard = await _load(session, target, settings)
        try:
            guard.admit(key, content, now=utc_now())
        except Refused as exc:
            refused = exc
        row.window_started_at = guard.window_started_at
        row.writes_in_window = guard.writes_in_window
        row.repeats = guard.repeats
        row.breaker_reason, row.breaker_opened_at = guard.breaker_reason, guard.breaker_opened_at
    if refused is not None:
        raise refused
    await write()
