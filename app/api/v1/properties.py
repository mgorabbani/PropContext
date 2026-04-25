from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from fastapi.responses import PlainTextResponse

from app.schemas.buildings import BuildingId as BuildingIdStr
from app.schemas.properties import PropertyId as PropertyIdStr
from app.services.wiki import WikiService, get_wiki_service

router = APIRouter()

PropertyId = Annotated[PropertyIdStr, Path(description="Canonical property id, e.g. LIE-001")]
BuildingId = Annotated[BuildingIdStr, Path(description="Canonical building id, e.g. HAUS-12")]


@router.get(
    "/{property_id}",
    response_class=PlainTextResponse,
    responses={200: {"content": {"text/markdown": {}}}},
)
async def get_property_md(
    property_id: PropertyId,
    service: Annotated[WikiService, Depends(get_wiki_service)],
) -> PlainTextResponse:
    md = await service.read_property(property_id)
    if md is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"property {property_id!r} not found")
    return PlainTextResponse(content=md, media_type="text/markdown; charset=utf-8")


@router.get(
    "/{property_id}/buildings/{building_id}",
    response_class=PlainTextResponse,
    responses={200: {"content": {"text/markdown": {}}}},
)
async def get_building_md(
    property_id: PropertyId,
    building_id: BuildingId,
    service: Annotated[WikiService, Depends(get_wiki_service)],
) -> PlainTextResponse:
    md = await service.read_building(property_id, building_id)
    if md is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            f"building {building_id!r} not found in property {property_id!r}",
        )
    return PlainTextResponse(content=md, media_type="text/markdown; charset=utf-8")
