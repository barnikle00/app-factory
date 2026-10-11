"""/health, /health/ready and /metrics (ADR 0009, 0010).

/health touches nothing, so a database outage never restarts a healthy process in a loop.
/health/ready answers 503 naming what failed: the database, a job past its window, or an outside
target whose breaker is open. It also lists every switch that is on — what this app is allowed to
write to right now is one request away.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import select, text

from app.core.metrics import registry
from app.core.text import utc_now
from app.db.models import GuardState, Switch
from app.jobs.runner import build_schedule, standings

router = APIRouter()


@router.get("/health")
async def alive() -> dict[str, str]:
    return {"status": "alive"}


@router.get("/health/ready")
async def ready(request: Request, response: Response) -> dict[str, object]:
    settings = request.app.state.settings
    failed: list[str] = []
    jobs: list[dict[str, object]] = []
    switches_on: list[str] = []
    try:
        async with asyncio.timeout(settings.web.readiness_check_timeout_seconds):
            async with request.app.state.session_factory() as session:
                await session.execute(text("SELECT 1"))
                for s in await standings(
                    session,
                    build_schedule(settings.timing),
                    grace_seconds=settings.web.job_overdue_grace_seconds,
                    now=utc_now(),
                ):
                    jobs.append(
                        {
                            "name": s.name,
                            "overdue": s.overdue,
                            "last_success_at": s.last_success_at and s.last_success_at.isoformat(),
                        }
                    )
                    if s.overdue:
                        failed.append(f"job:{s.name}")
                broken = await session.scalars(
                    select(GuardState).where(GuardState.breaker_reason.is_not(None))
                )
                failed += [f"writes:{g.target} — {g.breaker_reason}" for g in broken]
                switches_on = list(await session.scalars(select(Switch.name).where(Switch.is_on)))
    except Exception:
        failed.append("database")
    if failed:
        response.status_code = 503
    return {
        "status": "not ready" if failed else "ready",
        "failed": failed,
        "jobs": jobs,
        "switches_on": switches_on,
    }


@router.get("/metrics")
async def metrics() -> Response:
    return Response(generate_latest(registry()), media_type=CONTENT_TYPE_LATEST)
