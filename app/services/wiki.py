from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Literal

import anyio
from fastapi import Depends

from app.core.config import Settings, get_settings
from app.schemas.buildings import BuildingId
from app.schemas.properties import PropertyId


@dataclass(frozen=True, slots=True)
class TreeNode:
    name: str
    path: str
    type: Literal["file", "dir"]
    children: tuple[TreeNode, ...] | None = None


class WikiService:
    """Reads markdown entries from the property wiki tree."""

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

    def _resolve_safe(self, rel_path: str) -> Path:
        if not rel_path or rel_path.startswith("/") or ".." in Path(rel_path).parts:
            raise ValueError("invalid path")
        full = (self._wiki_dir / rel_path).resolve()
        root = self._wiki_dir.resolve()
        if full != root and root not in full.parents:
            raise ValueError("path escapes wiki_dir")
        return full

    async def read_file(self, rel_path: str) -> str | None:
        full = self._resolve_safe(rel_path)
        if not await anyio.Path(full).is_file():
            return None
        return await anyio.Path(full).read_text(encoding="utf-8")

    def list_properties(self) -> list[str]:
        if not self._wiki_dir.is_dir():
            return []
        return sorted(
            p.name for p in self._wiki_dir.iterdir() if p.is_dir() and not p.name.startswith(".")
        )

    def walk_tree(self, lie_id: str) -> TreeNode | None:
        root = self._resolve_safe(lie_id)
        if not root.is_dir():
            return None
        return _walk(root, self._wiki_dir.resolve())


def _walk(node: Path, root: Path) -> TreeNode:
    rel = node.relative_to(root).as_posix()
    if node.is_dir():
        children = sorted(
            (c for c in node.iterdir() if not c.name.startswith(".")),
            key=lambda p: (p.is_file(), p.name),
        )
        return TreeNode(
            name=node.name,
            path=rel,
            type="dir",
            children=tuple(_walk(c, root) for c in children),
        )
    return TreeNode(name=node.name, path=rel, type="file")


def get_wiki_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> WikiService:
    return WikiService(wiki_dir=settings.wiki_dir)
