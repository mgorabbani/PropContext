from __future__ import annotations

from pathlib import Path

from httpx import AsyncClient

from tests.conftest import write_building_index, write_property_index


async def test_get_property_404_when_missing(client: AsyncClient) -> None:
    r = await client.get("/api/v1/properties/LIE-001")
    assert r.status_code == 404


async def test_get_property_returns_markdown(client: AsyncClient, wiki_dir: Path) -> None:
    write_property_index(wiki_dir, "LIE-001", "# LIE-001\nHello.\n")
    r = await client.get("/api/v1/properties/LIE-001")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/markdown")
    assert "LIE-001" in r.text


async def test_get_property_rejects_bad_id(client: AsyncClient) -> None:
    r = await client.get("/api/v1/properties/..%2Fetc%2Fpasswd")
    assert r.status_code in {404, 422}


async def test_get_property_rejects_wrong_pattern(client: AsyncClient) -> None:
    r = await client.get("/api/v1/properties/HAUS-12")
    assert r.status_code == 422


async def test_get_building_404_when_property_missing(client: AsyncClient) -> None:
    r = await client.get("/api/v1/properties/LIE-001/buildings/HAUS-12")
    assert r.status_code == 404


async def test_get_building_returns_markdown(client: AsyncClient, wiki_dir: Path) -> None:
    write_building_index(wiki_dir, "LIE-001", "HAUS-12", "# HAUS-12\nBody.\n")
    r = await client.get("/api/v1/properties/LIE-001/buildings/HAUS-12")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/markdown")
    assert "HAUS-12" in r.text


async def test_get_building_rejects_bad_building_id(client: AsyncClient) -> None:
    r = await client.get("/api/v1/properties/LIE-001/buildings/..%2Fetc%2Fpasswd")
    assert r.status_code in {404, 422}
