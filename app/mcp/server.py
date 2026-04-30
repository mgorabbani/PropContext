from __future__ import annotations

import structlog
from fastmcp import FastMCP

from app.core.config import Settings
from app.mcp.auth import build_auth_provider
from app.mcp.prompts import register_prompts
from app.mcp.resources import register_resources
from app.mcp.tools import register_tools
from app.services.agent_local import LocalAgentService
from app.services.ask import AskService
from app.services.llm.client import AnthropicClient, FakeLLMClient, GeminiClient, LLMClient
from app.services.wiki import WikiService

log = structlog.get_logger(__name__)


def build_mcp(settings: Settings) -> FastMCP:
    auth = build_auth_provider(settings)
    mcp = FastMCP(
        name="PropContext",
        instructions=(
            "Living building memory for property management. "
            "Tools and resources are scoped to the caller's organization."
        ),
        auth=auth,
    )
    wiki = WikiService(wiki_dir=settings.wiki_dir)
    llm = _build_llm(settings)
    ask_service = AskService(wiki=wiki, llm=llm, model=settings.fast_model)
    wiki_chunks_db_path = settings.output_dir / "wiki_chunks.duckdb"
    agent_service: LocalAgentService | None = None
    if settings.anthropic_api_key:
        try:
            agent_service = LocalAgentService(settings=settings)
        except Exception as exc:
            log.warning("agent_disabled", err=str(exc))
    register_tools(
        mcp,
        wiki,
        ask_service,
        wiki_chunks_db_path=wiki_chunks_db_path,
        agent_service=agent_service,
        settings=settings,
    )
    register_resources(mcp, wiki)
    register_prompts(mcp)
    log.info(
        "mcp_built",
        auth_enabled=auth is not None,
        wiki_dir=str(settings.wiki_dir),
    )
    return mcp


def _build_llm(settings: Settings) -> LLMClient:
    match settings.llm_provider:
        case "gemini":
            if settings.gemini_api_key is None:
                return FakeLLMClient()
            return GeminiClient(api_key=settings.gemini_api_key)
        case "anthropic":
            if settings.anthropic_api_key is None:
                return FakeLLMClient()
            return AnthropicClient(api_key=settings.anthropic_api_key)
        case "fake":
            return FakeLLMClient()
