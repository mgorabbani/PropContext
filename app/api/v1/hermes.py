from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status

from app.core.config import Settings, get_settings
from app.schemas.hermes import HermesDashboard
from app.schemas.properties import PropertyId as PropertyIdStr
from app.services.hermes.dashboard import build_dashboard

router = APIRouter()

PropertyId = Annotated[PropertyIdStr, Path(description="Canonical property id, e.g. LIE-001")]


@router.get("/{property_id}/hermes", response_model=HermesDashboard)
def get_property_hermes_dashboard(
    property_id: PropertyId,
    settings: Annotated[Settings, Depends(get_settings)],
) -> HermesDashboard:
    property_root = settings.wiki_dir / property_id
    if not property_root.is_dir():
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"property {property_id!r} not found")
    return build_dashboard(wiki_dir=settings.wiki_dir, property_id=property_id)
