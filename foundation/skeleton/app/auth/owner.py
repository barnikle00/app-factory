"""Make the first owner, or give the owner a new password — run once on the server:

    docker compose run --rm web python -m app.auth.owner --name "<name>" [--reset]

There is no sign-up page: the owner is made here, and adds colleagues from the panel. The password
is printed once and only its hash is kept.
"""

from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.gate import Role
from app.auth.passwords import hash_password, new_initial_password
from app.core.config import AuthSettings, get_settings
from app.core.text import normalize_digits, utc_now
from app.db.models import Colleague
from app.db.session import create_engine, create_session_factory, session_scope


async def make_owner(session: AsyncSession, auth: AuthSettings, *, name: str, reset: bool) -> str:
    """The new password, or a sentence saying why nothing was done."""
    owner = (await session.scalars(select(Colleague).where(Colleague.role == Role.OWNER))).first()
    if owner is not None and not reset:
        return f"An owner already exists ({owner.name}). Use --reset to give them a new password."
    password = new_initial_password(auth)
    if owner is None:
        session.add(
            Colleague(
                name=normalize_digits(name),
                role=Role.OWNER,
                active=True,
                password_hash=hash_password(auth, password),
                password_changed_at=utc_now(),
            )
        )
    else:
        owner.password_hash, owner.password_changed_at = hash_password(auth, password), utc_now()
    return password


async def _main(name: str, reset: bool) -> None:
    settings = get_settings()
    engine = create_engine(settings.database)
    try:
        async with session_scope(create_session_factory(engine)) as session:
            print(await make_owner(session, settings.auth, name=name, reset=reset))
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True)
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()
    asyncio.run(_main(args.name, args.reset))
