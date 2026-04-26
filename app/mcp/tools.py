from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal, cast

import anyio
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import Field, StringConstraints

from app.core.config import Settings
from app.mcp.context import allowed_properties, assert_property_access
from app.services.agent_local import LocalAgentService
from app.services.ask import AskResult, AskService
from app.services.tavily import TavilyDisabled, search_web
from app.services.wiki import WikiService
from app.storage.wiki_chunks import open_wiki_chunks

PropertyIdParam = Annotated[
    str,
    StringConstraints(pattern=r"^[A-Z]+-\d+$", min_length=3, max_length=32),
    Field(description="Property identifier, e.g. LIE-001"),
]
RelPathParam = Annotated[
    str,
    StringConstraints(pattern=r"^[A-Za-z0-9._/-]+$", min_length=1, max_length=512),
    Field(description="Page path relative to property root, e.g. entities/DL-010.md"),
]
QuestionParam = Annotated[
    str,
    StringConstraints(min_length=1, max_length=4000),
    Field(description="Natural-language question about the property wiki"),
]
QueryParam = Annotated[
    str,
    StringConstraints(min_length=1, max_length=512),
    Field(description="Free-text query for BM25 search over wiki pages"),
]


def register_tools(
    mcp: FastMCP,
    wiki: WikiService,
    ask_service: AskService,
    *,
    wiki_chunks_db_path: Path | None = None,
    agent_service: LocalAgentService | None = None,
    settings: Settings | None = None,
) -> None:
    @mcp.tool
    async def list_properties() -> list[str]:
        """List property IDs the caller's organization can access."""
        on_disk = set(wiki.list_properties())
        allowed = allowed_properties()
        if "*" in allowed:
            return sorted(on_disk)
        return sorted(on_disk & allowed)

    @mcp.tool
    async def list_pages(property_id: PropertyIdParam) -> list[str]:
        """List all page paths inside a property (relative to the property root)."""
        assert_property_access(property_id)
        tree = wiki.walk_tree(property_id)
        if tree is None:
            raise ToolError(f"property {property_id!r} not found")
        return sorted(_collect_files(tree, prefix=property_id))

    @mcp.tool
    async def read_page(property_id: PropertyIdParam, path: RelPathParam) -> str:
        """Read a single page (relative path inside the property)."""
        assert_property_access(property_id)
        rel = f"{property_id}/{path}"
        try:
            body = await wiki.read_file(rel)
        except ValueError as exc:
            raise ToolError(str(exc)) from exc
        if body is None:
            raise ToolError(f"page {rel!r} not found")
        return body

    @mcp.tool
    async def search_pages(
        property_id: PropertyIdParam,
        query: QueryParam,
        limit: Annotated[int, Field(ge=1, le=20, default=8)] = 8,
    ) -> list[dict[str, str | float]]:
        """BM25 search across the property's pages. Returns hits with file/section/score."""
        assert_property_access(property_id)
        if wiki_chunks_db_path is None or not await anyio.Path(wiki_chunks_db_path).is_file():
            return []
        store = open_wiki_chunks(wiki_chunks_db_path)
        store.build_index()
        rows = store.query(query, property_id=property_id, limit=limit)
        return [
            {
                "path": str(r["file"]),
                "heading": str(r["section"]),
                "score": float(r["score"]),
                "snippet": str(r["body"])[:400],
            }
            for r in rows
        ]

    @mcp.tool
    async def ask_wiki(
        property_id: PropertyIdParam,
        question: QuestionParam,
    ) -> AskResult:
        """Answer a natural-language question against a property's wiki."""
        assert_property_access(property_id)
        return await ask_service.answer(property_id=property_id, question=question)

    if settings is not None and settings.tavily_api_key:

        @mcp.tool
        async def web_search(
            query: Annotated[
                str,
                StringConstraints(min_length=1, max_length=512),
                Field(description="Free-text query — vendor name, legal §, regulation, etc."),
            ],
            topic: Annotated[
                str,
                Field(
                    description="'general' (default) or 'news' for recent updates",
                    pattern=r"^(general|news)$",
                ),
            ] = "general",
            max_results: Annotated[int, Field(ge=1, le=10)] = 5,
            include_domains: Annotated[
                list[str] | None,
                Field(description="Optional domain allowlist (e.g. ['gesetze-im-internet.de'])"),
            ] = None,
        ) -> list[dict[str, object]]:
            """Search the public web (Tavily) for vendor profiles, legal references, regulations.

            Use for: looking up a Hausmeister/Dienstleister name, German legal § references
            (BGB, WEG, BauO Bln), recent BMJV/Senat updates. Not scoped to a property — web is
            global. Prefer ask_wiki / search_pages for anything inside the property memory.
            """
            try:
                hits = await search_web(
                    query,
                    settings=settings,
                    max_results=max_results,
                    topic=cast(Literal["general", "news"], topic),
                    include_domains=include_domains,
                )
            except TavilyDisabled as exc:
                raise ToolError(str(exc)) from exc
            return [
                {"title": h.title, "url": h.url, "content": h.content, "score": h.score}
                for h in hits
            ]

    if agent_service is not None:

        @mcp.tool
        async def agent_query(
            property_id: PropertyIdParam,
            prompt: QuestionParam,
        ) -> dict[str, object]:
            """Run autonomous Claude agent (bash, read, write, grep, web) over a property's wiki.

            Slower and more expensive than ask_wiki but handles multi-step questions,
            cross-page reasoning, and computations. Use for hard questions; use ask_wiki
            for simple lookups.
            """
            assert_property_access(property_id)
            result = await agent_service.query(property_id=property_id, prompt=prompt)
            return {
                "answer": result.answer,
                "session_id": result.session_id,
                "output_files": result.output_files,
                "usage_tokens": result.usage_tokens,
            }


def _collect_files(node: object, *, prefix: str) -> list[str]:
    out: list[str] = []
    children = getattr(node, "children", None)
    node_type = getattr(node, "type", None)
    node_path = getattr(node, "path", "")
    if (
        node_type == "file"
        and isinstance(node_path, str)
        and node_path.endswith(".md")
        and node_path.startswith(prefix + "/")
    ):
        out.append(node_path[len(prefix) + 1 :])
    if children:
        for child in children:
            out.extend(_collect_files(child, prefix=prefix))
    return out
