from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from fastapi.responses import PlainTextResponse

from app.schemas.buildings import BuildingId as BuildingIdStr
from app.services.building_memory import BuildingMemoryService, get_building_memory_service

router = APIRouter()

BuildingId = Annotated[BuildingIdStr, Path(description="Canonical building id, e.g. HAUS-12")]


@router.get(
    "/{building_id}",
    response_class=PlainTextResponse,
    responses={200: {"content": {"text/markdown": {}}}},
)
async def get_building_md(
    building_id: BuildingId,
    service: Annotated[BuildingMemoryService, Depends(get_building_memory_service)],
) -> PlainTextResponse:
    md = await service.load(building_id)
    if md is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"building {building_id!r} not found")
    return PlainTextResponse(content=md, media_type="text/markdown; charset=utf-8")
