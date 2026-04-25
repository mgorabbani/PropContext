from __future__ import annotations

from httpx import AsyncClient


async def test_request_id_generated_when_missing(client: AsyncClient) -> None:
    r = await client.get("/api/v1/health")
    assert r.status_code == 200
    rid = r.headers.get("X-Request-Id")
    assert rid is not None
    assert len(rid) == 32  # uuid4().hex


async def test_request_id_echoed_when_provided(client: AsyncClient) -> None:
    r = await client.get("/api/v1/health", headers={"X-Request-Id": "abc123"})
    assert r.status_code == 200
    assert r.headers["X-Request-Id"] == "abc123"
