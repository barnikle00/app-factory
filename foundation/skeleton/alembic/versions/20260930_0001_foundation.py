"""The tables every factory app starts with — expand only.

Revision: 0001_foundation
Revises:

job_run (ADR 0009), colleague (sign-in), switch (what is allowed right now) and guard_state
(ADR 0010). The app's own tables arrive with the phases that write them.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_foundation"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "job_run",
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("last_success_at", sa.DateTime(timezone=True)),
        sa.Column("last_failure_at", sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint("name", name=op.f("pk_job_run")),
    )
    op.create_table(
        "colleague",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_colleague")),
        sa.UniqueConstraint("name", name=op.f("uq_colleague_name")),
    )
    op.create_table(
        "switch",
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("is_on", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("changed_by", sa.BigInteger()),
        sa.PrimaryKeyConstraint("name", name=op.f("pk_switch")),
    )
    op.create_table(
        "guard_state",
        sa.Column("target", sa.String(64), nullable=False),
        sa.Column("window_started_at", sa.DateTime(timezone=True)),
        sa.Column("writes_in_window", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("repeats", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("breaker_reason", sa.String(255)),
        sa.Column("breaker_opened_at", sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint("target", name=op.f("pk_guard_state")),
    )


def downgrade() -> None:
    """No downgrade (ADR 0001): reversing a shape is its own contract migration, written when it is
    needed. It also keeps one file from both adding and dropping, which the commit lock refuses."""
    raise RuntimeError("No downgrade: reverse this with a contract migration (ADR 0001).")
