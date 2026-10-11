"""The pages every app starts with: sign in, sign out, home, and the switches.

Every form is a real form that works with no JavaScript (ADR 0005). The app's own screens come
from its prototype (ARCHITECTURE.md → Frontend source) and replace `home.html`.
"""

from __future__ import annotations

from urllib.parse import parse_qs

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy import select

from app.auth import session as tickets
from app.auth.gate import Me, Role, require, set_cookie
from app.auth.passwords import password_matches
from app.core.switches import all_switches, set_switch
from app.core.text import normalize_digits, utc_now
from app.db.models import Colleague
from app.db.session import session_scope

router = APIRouter()
# What each page needs, decided once (app/auth/gate.py is the only place a role is enforced).
VIEWER = require(Role.VIEWER)
OWNER = require(Role.OWNER)
SEE_OTHER = 303


def page(request: Request, name: str, status_code: int = 200, **context: object) -> HTMLResponse:
    template = request.app.state.templates.get_template(name)
    return HTMLResponse(template.render(request=request, **context), status_code=status_code)


async def form_of(request: Request) -> dict[str, str]:
    body = (await request.body()).decode()
    return {k: v[0] for k, v in parse_qs(body, keep_blank_values=True).items()}


def _safe_next(value: str | None) -> str:
    return value if value and value.startswith("/") and not value.startswith("//") else "/"


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request) -> HTMLResponse:
    return page(request, "login.html", next=_safe_next(request.query_params.get("next")))


@router.post("/login")
async def login(request: Request) -> Response:
    settings = request.app.state.settings
    form = await form_of(request)
    name = normalize_digits(form.get("name", ""))
    async with request.app.state.session_factory() as session:
        row = (await session.scalars(select(Colleague).where(Colleague.name == name))).first()
    if (
        row is None
        or not row.active
        or not password_matches(settings.auth, row.password_hash, form.get("password", ""))
    ):
        return page(
            request,
            "login.html",
            status_code=401,
            next=_safe_next(form.get("next")),
            error=True,
        )
    response = RedirectResponse(_safe_next(form.get("next")), status_code=SEE_OTHER)
    set_cookie(
        request,
        response,
        tickets.issue(
            settings.auth, colleague_id=row.id, password_changed_at=row.password_changed_at
        ),
    )
    return response


@router.post("/logout")
async def logout(request: Request) -> Response:
    response = RedirectResponse("/login", status_code=SEE_OTHER)
    response.delete_cookie(request.app.state.settings.auth.session_cookie_name)
    return response


@router.get("/", response_class=HTMLResponse)
async def home(request: Request, me: Me = Depends(VIEWER)) -> HTMLResponse:
    return page(request, "home.html", me=me)


@router.get("/switches", response_class=HTMLResponse)
async def switches_page(request: Request, me: Me = Depends(OWNER)) -> HTMLResponse:
    limit = request.app.state.settings.database.list_max_rows_count
    async with request.app.state.session_factory() as session:
        rows = await all_switches(session, limit=limit)
    return page(request, "switches.html", me=me, switches=rows)


@router.post("/switches")
async def switch(request: Request, me: Me = Depends(OWNER)) -> Response:
    form = await form_of(request)
    name = form.get("name", "").strip()
    if name:
        async with session_scope(request.app.state.session_factory) as session:
            await set_switch(session, name, on=form.get("on") == "1", by=me.id, at=utc_now())
    return RedirectResponse("/switches", status_code=SEE_OTHER)
