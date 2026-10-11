"""The tables every factory app starts with. The app's own tables arrive with the phases that
write them, each in its own migration (ADR 0001).

- `job_run` — each job's last success and failure, which /health/ready reads (ADR 0009)
- `colleague` — who may sign in, and with which role
- `switch` — what the app is allowed to do right now; every one is off until a person turns it on
- `guard_state` — each outside target's write count and breaker (ADR 0010)
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, BigInteger, Boolean, DateTime, Integer, MetaData, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Explicit names, so a contract migration can drop exactly what an expand migration created.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class JobRun(Base):
    __tablename__ = "job_run"

    name: Mapped[str] = mapped_column(String(64), primary_key=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_failure_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Colleague(Base):
    __tablename__ = "colleague"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    role: Mapped[str] = mapped_column(String(16))
    password_hash: Mapped[str] = mapped_column(String(255))
    password_changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Switch(Base):
    __tablename__ = "switch"

    name: Mapped[str] = mapped_column(String(64), primary_key=True)
    is_on: Mapped[bool] = mapped_column(Boolean, default=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    changed_by: Mapped[int | None] = mapped_column(BigInteger)


class GuardState(Base):
    __tablename__ = "guard_state"

    target: Mapped[str] = mapped_column(String(64), primary_key=True)
    window_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    writes_in_window: Mapped[int] = mapped_column(Integer, default=0)
    # key -> [content fingerprint, times written unchanged in this window]
    repeats: Mapped[dict] = mapped_column(JSON, default=dict)
    breaker_reason: Mapped[str | None] = mapped_column(String(255))
    breaker_opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
