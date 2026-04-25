from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings, get_settings
from app.main import app


@pytest.fixture
def wiki_dir(tmp_path: Path) -> Path:
    d = tmp_path / "wiki"
    d.mkdir()
    return d


@pytest.fixture
def settings(wiki_dir: Path, tmp_path: Path) -> Settings:
    return Settings(
        wiki_dir=wiki_dir,
        normalize_dir=tmp_path / "normalize",
        output_dir=tmp_path / "output",
        env="dev",
    )


@pytest.fixture
async def client(settings: Settings) -> AsyncIterator[AsyncClient]:
    app.dependency_overrides[get_settings] = lambda: settings
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


def write_property_index(wiki_dir: Path, property_id: str, body: str) -> Path:
    p = wiki_dir / property_id / "index.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")
    return p


def write_building_index(wiki_dir: Path, property_id: str, building_id: str, body: str) -> Path:
    p = wiki_dir / property_id / "02_buildings" / building_id / "index.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")
    return p
