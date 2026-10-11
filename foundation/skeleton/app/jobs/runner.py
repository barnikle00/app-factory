"""The `jobs` process: every scheduled job, and each one's last success and failure (ADR 0009).

A job is declared in `SCHEDULE` with an interval from `TimingSettings` and registered in
`HANDLERS` under the same name. A job on the schedule with no handler has never succeeded, so
/health/ready reports it overdue — a job nobody wired up shows on the first deploy.
"""

from __future__ import annotations

import asyncio
import contextlib
import signal
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from prometheus_client import start_http_server
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings, TimingSettings, get_settings
from app.core.logging import configure_logging, get_logger
from app.core.metrics import JOB_LAST_SUCCESS_AGE_SECONDS, PROCESS_UP
from app.core.text import utc_now
from app.db.models import JobRun
from app.db.session import create_engine, create_session_factory, session_scope

log = get_logger("jobs")


@dataclass(frozen=True)
class ScheduledJob:
    name: str
    interval_seconds: float


def build_schedule(timing: TimingSettings) -> tuple[ScheduledJob, ...]:
    """Every job and how often it runs. Each phase that adds a job adds its line here."""
    return ()


HANDLERS: dict[str, Callable[[AsyncSession], Awaitable[None]]] = {}


@dataclass(frozen=True)
class JobStanding:
    name: str
    last_success_at: datetime | None
    last_failure_at: datetime | None
    overdue: bool


async def record(session: AsyncSession, name: str, *, success: bool, at: datetime) -> None:
    values = {"last_success_at": at} if success else {"last_failure_at": at}
    await session.execute(
        insert(JobRun)
        .values(name=name, **values)
        .on_conflict_do_update(index_elements=[JobRun.name], set_=values)
    )


async def standings(
    session: AsyncSession,
    schedule: tuple[ScheduledJob, ...],
    *,
    grace_seconds: float,
    now: datetime,
) -> list[JobStanding]:
    rows = {r.name: r for r in (await session.scalars(select(JobRun))).all()}
    out = []
    for job in schedule:
        row = rows.get(job.name)
        last = row.last_success_at if row else None
        overdue = last is None or now - last > timedelta(
            seconds=job.interval_seconds + grace_seconds
        )
        if last is not None:
            JOB_LAST_SUCCESS_AGE_SECONDS.labels(job=job.name).set((now - last).total_seconds())
        out.append(JobStanding(job.name, last, row.last_failure_at if row else None, overdue))
    return out


async def run_once(factory: async_sessionmaker[AsyncSession], job: ScheduledJob) -> None:
    handler = HANDLERS.get(job.name)
    if handler is None:
        return
    started = utc_now()
    try:
        async with session_scope(factory) as session:
            await handler(session)
    except Exception:
        log.exception("job.failed", job=job.name)
        async with session_scope(factory) as session:
            await record(session, job.name, success=False, at=utc_now())
        return
    async with session_scope(factory) as session:
        await record(session, job.name, success=True, at=started)


async def run(settings: Settings, stop: asyncio.Event) -> None:
    engine = create_engine(settings.database)
    factory = create_session_factory(engine)
    schedule = build_schedule(settings.timing)
    due = dict.fromkeys((j.name for j in schedule), 0.0)
    PROCESS_UP.labels(process="jobs").set(1)
    try:
        while not stop.is_set():
            now = asyncio.get_running_loop().time()
            for job in schedule:
                if now >= due[job.name]:
                    await run_once(factory, job)
                    due[job.name] = now + job.interval_seconds
            wait = max(0.0, min(due.values(), default=now + 60) - asyncio.get_running_loop().time())
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(stop.wait(), timeout=wait)
    finally:
        PROCESS_UP.labels(process="jobs").set(0)
        await engine.dispose()


def main() -> None:
    settings = get_settings()
    configure_logging(settings.observability)
    start_http_server(settings.observability.jobs_metrics_port_number)

    async def serve() -> None:
        stop = asyncio.Event()
        for sig in (signal.SIGINT, signal.SIGTERM):
            asyncio.get_running_loop().add_signal_handler(sig, stop.set)
        await run(settings, stop)

    asyncio.run(serve())


if __name__ == "__main__":
    main()
