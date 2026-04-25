from __future__ import annotations

from pathlib import Path
from typing import Annotated

import anyio
from fastapi import Depends

from app.core.config import Settings, get_settings


class BuildingMemoryService:
    """Loads `building.md` for a given canonical building id.

    Storage is a flat directory of `<building_id>.md` under settings.output_dir.
    Real ingestion pipeline writes here; the API reads.
    """

    def __init__(self, output_dir: Path) -> None:
        self._output_dir = output_dir

    def _path(self, building_id: str) -> Path:
        return self._output_dir / f"{building_id}.md"

    async def load(self, building_id: str) -> str | None:
        path = self._path(building_id)
        if not await anyio.Path(path).is_file():
            return None
        return await anyio.Path(path).read_text(encoding="utf-8")


def get_building_memory_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> BuildingMemoryService:
    return BuildingMemoryService(output_dir=settings.output_dir)
