"""${message}

Revision: ${up_revision}
Revises: ${down_revision | comma,n}

ADR 0001 — expand, migrate, contract. Say which of the three this migration is.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
${imports if imports else ""}

revision: str = ${repr(up_revision)}
down_revision: str | None = ${repr(down_revision)}
branch_labels: str | Sequence[str] | None = ${repr(branch_labels)}
depends_on: str | Sequence[str] | None = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    raise RuntimeError("No downgrade: reverse this with a contract migration (ADR 0001).")
