from __future__ import annotations

import json
from pathlib import Path

from httpx import AsyncClient

from app.main import app
from app.services.llm.client import FakeLLMClient, get_llm_client
from tests.conftest import write_property_index


async def test_ask_returns_answer_and_path(client: AsyncClient, wiki_dir: Path) -> None:
    write_property_index(wiki_dir, "LIE-001", "# LIE-001\n\nManager: Anna.")
    fake = FakeLLMClient(
        responses={
            "*": json.dumps(
                {"answer": "Manager is Anna.", "path": "LIE-001/index.md"}
            )
        }
    )
    app.dependency_overrides[get_llm_client] = lambda: fake
    try:
        resp = await client.post(
            "/api/v1/ask",
            json={"question": "Who is the manager?", "lie": "LIE-001"},
        )
    finally:
        app.dependency_overrides.pop(get_llm_client, None)
    assert resp.status_code == 200
    body = resp.json()
    assert body["answer"] == "Manager is Anna."
    assert body["path"] == "LIE-001/index.md"


async def test_ask_property_not_found(client: AsyncClient) -> None:
    fake = FakeLLMClient(responses={"*": "{}"})
    app.dependency_overrides[get_llm_client] = lambda: fake
    try:
        resp = await client.post(
            "/api/v1/ask",
            json={"question": "anything", "lie": "LIE-999"},
        )
    finally:
        app.dependency_overrides.pop(get_llm_client, None)
    assert resp.status_code == 200
    body = resp.json()
    assert "not found" in (body["answer"] or "")
    assert body["path"] is None


async def test_ask_rejects_bad_lie(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/ask",
        json={"question": "anything", "lie": "../etc"},
    )
    assert resp.status_code == 422


async def test_ask_falls_back_to_raw_text_on_bad_json(
    client: AsyncClient, wiki_dir: Path
) -> None:
    write_property_index(wiki_dir, "LIE-001", "# LIE-001")
    fake = FakeLLMClient(responses={"*": "not json at all"})
    app.dependency_overrides[get_llm_client] = lambda: fake
    try:
        resp = await client.post(
            "/api/v1/ask",
            json={"question": "hi", "lie": "LIE-001"},
        )
    finally:
        app.dependency_overrides.pop(get_llm_client, None)
    assert resp.status_code == 200
    body = resp.json()
    assert body["answer"] == "not json at all"
    assert body["path"] is None
