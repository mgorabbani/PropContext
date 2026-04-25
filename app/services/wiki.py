from __future__ import annotations

from pathlib import Path
from typing import Annotated

import anyio
from fastapi import Depends

from app.core.config import Settings, get_settings
from app.schemas.buildings import BuildingId
from app.schemas.properties import PropertyId


class WikiService:
    """Reads markdown entries from the property wiki tree.

    Layout: `<wiki_dir>/<LIE-id>/index.md` for properties,
    `<wiki_dir>/<LIE-id>/02_buildings/<HAUS-id>/index.md` for buildings.
    """

    def __init__(self, wiki_dir: Path) -> None:
        self._wiki_dir = wiki_dir

    def _property_path(self, property_id: PropertyId) -> Path:
        return self._wiki_dir / property_id / "index.md"

    def _building_path(self, property_id: PropertyId, building_id: BuildingId) -> Path:
        return self._wiki_dir / property_id / "02_buildings" / building_id / "index.md"

    async def read_property(self, property_id: PropertyId) -> str | None:
        path = self._property_path(property_id)
        if not await anyio.Path(path).is_file():
            return None
        return await anyio.Path(path).read_text(encoding="utf-8")

    async def read_building(self, property_id: PropertyId, building_id: BuildingId) -> str | None:
        path = self._building_path(property_id, building_id)
        if not await anyio.Path(path).is_file():
            return None
        return await anyio.Path(path).read_text(encoding="utf-8")


def get_wiki_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> WikiService:
    return WikiService(wiki_dir=settings.wiki_dir)
