from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager
from http import HTTPStatus
from pathlib import Path

import structlog
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import FileResponse, Response
from starlette.types import Lifespan, Scope

from app.api.v1.router import api_router
from app.core.config import REPO_ROOT, get_settings
from app.core.logging import configure_logging
from app.core.middleware import RequestIdMiddleware
from app.mcp import build_mcp

PRM_LOCAL_PATH = "/mcp/.well-known/oauth-protected-resource"

log = structlog.get_logger(__name__)


class SPAStaticFiles(StaticFiles):
    """Static mount that falls back to index.html for unknown HTML paths (SPA routes)."""

    async def get_response(self, path: str, scope: Scope) -> Response:  # type: ignore[override]
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code != HTTPStatus.NOT_FOUND or "." in path.rsplit("/", 1)[-1]:
                raise
            directory = Path(str(self.directory)) if self.directory else None
            if directory is None:
                raise
            index = directory / "index.html"
            if not index.is_file():
                raise
            return FileResponse(index)


def _make_lifespan(child: Lifespan | None) -> Lifespan:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        settings = get_settings()
        configure_logging(settings)
        log.info("startup", env=settings.env, version=app.version)
        async with AsyncExitStack() as stack:
            if child is not None:
                await stack.enter_async_context(child(app))
            yield
        log.info("shutdown")

    return lifespan


def create_app() -> FastAPI:
    settings = get_settings()

    mcp_app = None
    if settings.mcp_enabled:
        mcp_app = build_mcp(settings).http_app(path="/")

    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        lifespan=_make_lifespan(mcp_app.lifespan if mcp_app else None),
        docs_url="/docs" if settings.env != "prod" else None,
        redoc_url=None,
    )
    app.add_middleware(RequestIdMiddleware)
    app.include_router(api_router, prefix="/api/v1")
    if mcp_app is not None:

        @app.get("/.well-known/oauth-protected-resource", include_in_schema=False)
        @app.get("/.well-known/oauth-protected-resource/mcp", include_in_schema=False)
        async def _prm_redirect() -> RedirectResponse:
            return RedirectResponse(url=PRM_LOCAL_PATH, status_code=307)

        app.mount("/mcp", mcp_app)
    static_dir = REPO_ROOT / "app" / "static"
    if static_dir.is_dir():
        app.mount("/", SPAStaticFiles(directory=static_dir, html=True), name="static")
    return app


app = create_app()
