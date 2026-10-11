"""The one place a role is enforced. A route declares what it needs; nothing else decides.

    OWNER = require(Role.OWNER)            # once, at module level

    @router.get("/switches")
    async def page(me: Me = Depends(OWNER)): ...

A visitor with no valid session is sent to the sign-in page; a signed-in colleague without the
role gets 403. Add roles here, never as an `if` inside a route.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from urllib.parse import quote

from fastapi import HTTPException, Request, Response
from fastapi.responses import RedirectResponse

from app.auth import session as tickets
from app.core.config import SECONDS_PER_HOUR
from app.db.models import Colleague

LOGIN_PATH = "/login"


class Role(StrEnum):
    OWNER = "owner"
    MANAGER = "manager"
    VIEWER = "viewer"


# Who may do at least what: an owner may do everything a manager may, and so on.
RANK = {Role.VIEWER: 0, Role.MANAGER: 1, Role.OWNER: 2}


@dataclass(frozen=True)
class Me:
    id: int
    name: str
    role: Role


class SignInRequired(Exception):
    def __init__(self, next_path: str) -> None:
        self.next_path = next_path


def require(minimum: Role):
    async def dependency(request: Request, response: Response) -> Me:
        settings = request.app.state.settings
        ticket = tickets.read(settings.auth, request.cookies.get(settings.auth.session_cookie_name))
        if ticket is None:
            raise SignInRequired(request.url.path)
        async with request.app.state.session_factory() as session:
            row = await session.get(Colleague, ticket.colleague_id)
        if (
            row is None
            or not row.active
            or tickets.stamp(row.password_changed_at) != ticket.password_stamp
        ):
            raise SignInRequired(request.url.path)
        if RANK[Role(row.role)] < RANK[minimum]:
            raise HTTPException(status_code=403)
        # Sliding: every page answered re-issues the cookie, so the clock is time since last use.
        set_cookie(
            request,
            response,
            tickets.issue(
                settings.auth, colleague_id=row.id, password_changed_at=row.password_changed_at
            ),
        )
        return Me(row.id, row.name, Role(row.role))

    return dependency


def set_cookie(request: Request, response: Response, value: str) -> None:
    auth = request.app.state.settings.auth
    response.set_cookie(
        auth.session_cookie_name,
        value,
        httponly=True,
        samesite="lax",
        secure=auth.session_cookie_secure,
        max_age=auth.session_idle_timeout_hours * SECONDS_PER_HOUR,
    )


def to_sign_in(_request: Request, exc: SignInRequired) -> RedirectResponse:
    next_path = (
        exc.next_path
        if exc.next_path.startswith("/") and not exc.next_path.startswith("//")
        else "/"
    )
    return RedirectResponse(f"{LOGIN_PATH}?next={quote(next_path)}", status_code=303)
