from __future__ import annotations

from fastmcp import FastMCP
from fastmcp.exceptions import ResourceError

from app.mcp.context import allowed_properties, assert_property_access
from app.services.wiki import WikiService


def register_resources(mcp: FastMCP, wiki: WikiService) -> None:
    @mcp.resource(
        uri="property://{property_id}",
        name="property",
        description="Markdown index for a property",
        mime_type="text/markdown",
    )
    async def property_resource(property_id: str) -> str:
        assert_property_access(property_id)
        body = await wiki.read_property(property_id)
        if body is None:
            raise ResourceError(f"property {property_id!r} not found")
        return body

    @mcp.resource(
        uri="building://{property_id}/{building_id}",
        name="building",
        description="Markdown index for a building inside a property",
        mime_type="text/markdown",
    )
    async def building_resource(property_id: str, building_id: str) -> str:
        assert_property_access(property_id)
        body = await wiki.read_building(property_id, building_id)
        if body is None:
            raise ResourceError(f"building {property_id}/{building_id} not found")
        return body

    @mcp.resource(
        uri="properties://list",
        name="properties_list",
        description="JSON list of property IDs the caller can access",
        mime_type="application/json",
    )
    async def properties_list() -> list[str]:
        on_disk = set(wiki.list_properties())
        return sorted(on_disk & allowed_properties())
