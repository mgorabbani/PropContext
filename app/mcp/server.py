from __future__ import annotations

import structlog
from fastmcp import FastMCP

from app.core.config import Settings
from app.mcp.auth import build_auth_provider
from app.mcp.prompts import register_prompts
from app.mcp.resources import register_resources
from app.mcp.tools import register_tools
from app.services.wiki import WikiService

log = structlog.get_logger(__name__)


def build_mcp(settings: Settings) -> FastMCP:
    auth = build_auth_provider(settings)
    mcp = FastMCP(
        name="Buena Context",
        instructions=(
            "Living building memory for Berlin property management. "
            "Tools and resources are scoped to the caller's organization."
        ),
        auth=auth,
    )
    wiki = WikiService(wiki_dir=settings.wiki_dir)
    register_tools(mcp, wiki)
    register_resources(mcp, wiki)
    register_prompts(mcp)
    log.info(
        "mcp_built",
        auth_enabled=auth is not None,
        wiki_dir=str(settings.wiki_dir),
    )
    return mcp
