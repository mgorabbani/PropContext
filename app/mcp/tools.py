from __future__ import annotations

from typing import Annotated

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import Field, StringConstraints

from app.mcp.context import allowed_properties, assert_property_access
from app.services.ask import AskResult, AskService
from app.services.wiki import WikiService

PropertyIdParam = Annotated[
    str,
    StringConstraints(pattern=r"^[A-Z]+-\d+$", min_length=3, max_length=32),
    Field(description="Property identifier, e.g. LIE-001"),
]
BuildingIdParam = Annotated[
    str,
    StringConstraints(pattern=r"^[A-Z]+-\d+$", min_length=3, max_length=32),
    Field(description="Building identifier, e.g. HAUS-12"),
]
RelPathParam = Annotated[
    str,
    StringConstraints(pattern=r"^[A-Za-z0-9._/-]+$", min_length=1, max_length=512),
    Field(description="Path relative to wiki_dir"),
]
QuestionParam = Annotated[
    str,
    StringConstraints(min_length=1, max_length=4000),
    Field(description="Natural-language question about the property wiki"),
]


def register_tools(mcp: FastMCP, wiki: WikiService, ask_service: AskService) -> None:
    @mcp.tool
    async def list_properties() -> list[str]:
        """List property IDs the caller's organization can access."""
        on_disk = set(wiki.list_properties())
        return sorted(on_disk & allowed_properties())

    @mcp.tool
    async def get_property(property_id: PropertyIdParam) -> str:
        """Return the markdown index for a property the caller can access."""
        assert_property_access(property_id)
        body = await wiki.read_property(property_id)
        if body is None:
            raise ToolError(f"property {property_id!r} not found")
        return body

    @mcp.tool
    async def get_building(
        property_id: PropertyIdParam,
        building_id: BuildingIdParam,
    ) -> str:
        """Return the markdown index for a building inside a property."""
        assert_property_access(property_id)
        body = await wiki.read_building(property_id, building_id)
        if body is None:
            raise ToolError(f"building {property_id}/{building_id} not found")
        return body

    @mcp.tool
    async def read_wiki_file(path: RelPathParam) -> str:
        """Read any markdown file inside the wiki, scoped to the caller's properties."""
        first_segment = path.split("/", 1)[0]
        assert_property_access(first_segment)
        try:
            body = await wiki.read_file(path)
        except ValueError as exc:
            raise ToolError(str(exc)) from exc
        if body is None:
            raise ToolError(f"file {path!r} not found")
        return body

    @mcp.tool
    async def ask_wiki(
        property_id: PropertyIdParam,
        question: QuestionParam,
    ) -> AskResult:
        """Answer a natural-language question against a property's wiki."""
        assert_property_access(property_id)
        return await ask_service.answer(property_id=property_id, question=question)
