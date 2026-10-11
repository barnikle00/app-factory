"""The web process: `python -m app.web.app`.

The template environment is built outside the lifespan, so a page can be rendered and tested with
no database; the lifespan opens and closes the engine.
"""

from __future__ import annotations

import importlib
import importlib.util
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.auth.gate import SignInRequired, to_sign_in
from app.core.config import DisplaySettings, Settings, get_settings
from app.core.logging import configure_logging
from app.core.metrics import PROCESS_UP
from app.core.text import DS_OPTIONS, template_filters
from app.db.session import create_engine, create_session_factory
from app.web import health, pages

HERE = Path(__file__).parent


def build_templates(display: DisplaySettings) -> Environment:
    env = Environment(
        loader=FileSystemLoader(HERE / "templates"),
        autoescape=select_autoescape(("html",)),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters.update(template_filters(display.timezone_name))
    # The generic design system, only when build-spec step 0 copied it in as app/ds.py.
    if importlib.util.find_spec("app.ds") is not None:
        importlib.import_module("app.ds").install(
            env, brand="slate", app_name="factory-app", **DS_OPTIONS
        )
    return env


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or get_settings()
    configure_logging(resolved.observability)

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        engine = create_engine(resolved.database)
        application.state.session_factory = create_session_factory(engine)
        PROCESS_UP.labels(process="web").set(1)
        try:
            yield
        finally:
            PROCESS_UP.labels(process="web").set(0)
            await engine.dispose()

    # No /docs or /openapi.json: they describe every route to anyone who asks, unauthenticated.
    application = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    application.state.settings = resolved
    application.state.templates = build_templates(resolved.display)
    application.mount("/static", StaticFiles(directory=HERE / "static"), name="static")
    application.add_exception_handler(SignInRequired, to_sign_in)  # type: ignore[arg-type]
    application.include_router(health.router)
    application.include_router(pages.router)
    return application


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        create_app(settings),
        host=settings.web.bind_host,
        port=settings.web.bind_port_number,
        proxy_headers=True,
    )


if __name__ == "__main__":
    main()
