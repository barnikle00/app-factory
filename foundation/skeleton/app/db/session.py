"""The async engine and the unit of work. Every limit is a setting (ADR 0007, 0008)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import DatabaseSettings

MILLISECONDS_PER_SECOND = 1000


def create_engine(settings: DatabaseSettings) -> AsyncEngine:
    return create_async_engine(
        settings.dsn,
        pool_size=settings.pool_size_count,
        max_overflow=settings.pool_overflow_count,
        pool_timeout=settings.pool_timeout_seconds,
        pool_pre_ping=True,
        connect_args={
            "timeout": settings.connect_timeout_seconds,
            # Stopped by PostgreSQL itself, so a runaway query ends even if the client gave up.
            "server_settings": {
                "statement_timeout": str(
                    int(settings.statement_timeout_seconds * MILLISECONDS_PER_SECOND)
                )
            },
        },
    )


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


@asynccontextmanager
async def session_scope(factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[AsyncSession]:
    """One unit of work: committed if it returns, rolled back if it raises."""
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
