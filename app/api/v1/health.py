from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.schemas.health import HealthStatus

router = APIRouter()


@router.get("/health", response_model=HealthStatus)
async def health(settings: Annotated[Settings, Depends(get_settings)]) -> HealthStatus:
    return HealthStatus(status="ok", env=settings.env, version=settings.version)
