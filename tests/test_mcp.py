from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from fastmcp.exceptions import ToolError
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.main import create_app
from app.mcp import build_mcp
from app.mcp.context import (
    allowed_properties,
    assert_property_access,
    current_org_id,
    require_org_id,
)
from app.mcp.orgs import ORG_PROPERTIES, org_can_access, properties_for_org


def test_org_property_map_lookup() -> None:
    sample_org = next(iter(ORG_PROPERTIES))
    assert isinstance(properties_for_org(sample_org), frozenset)
    assert properties_for_org("nonexistent") == frozenset()
    assert properties_for_org(None) == frozenset()


def test_org_can_access_rejects_unknown() -> None:
    assert org_can_access(None, "LIE-001") is False
    assert org_can_access("nonexistent", "LIE-001") is False
    if ORG_PROPERTIES.get("org_buena_berlin"):
        assert org_can_access("org_buena_berlin", "LIE-001") is True
        assert org_can_access("org_buena_berlin", "LIE-XYZ") is False


def test_context_helpers_no_token() -> None:
    with patch("app.mcp.context.get_access_token", return_value=None):
        assert current_org_id() is None
        assert allowed_properties() == frozenset()
        with pytest.raises(ToolError, match="org_id"):
            require_org_id()
        with pytest.raises(ToolError, match="org_id"):
            assert_property_access("LIE-001")


class _FakeToken:
    def __init__(self, org_id: str | None) -> None:
        self.claims = {"org_id": org_id} if org_id else {}


def test_context_helpers_with_token() -> None:
    fake = _FakeToken("org_buena_berlin")
    with patch("app.mcp.context.get_access_token", return_value=fake):
        assert current_org_id() == "org_buena_berlin"
        assert require_org_id() == "org_buena_berlin"
        if "LIE-001" in ORG_PROPERTIES.get("org_buena_berlin", frozenset()):
            assert_property_access("LIE-001")
        with pytest.raises(ToolError, match="no access"):
            assert_property_access("LIE-DOES-NOT-EXIST")


async def test_build_mcp_registers_tools_resources_prompts(tmp_path: Path) -> None:
    settings = Settings(
        wiki_dir=tmp_path / "wiki",
        normalize_dir=tmp_path / "normalize",
        output_dir=tmp_path / "output",
        env="dev",
        mcp_enabled=True,
        workos_authkit_domain=None,
    )
    mcp = build_mcp(settings)
    tool_names = {t.name for t in await mcp.list_tools()}
    assert {"list_properties", "get_property", "get_building", "read_wiki_file"} <= tool_names

    template_uris = {t.uri_template for t in await mcp.list_resource_templates()}
    assert any("property://" in u for u in template_uris)
    assert any("building://" in u for u in template_uris)

    prompt_names = {p.name for p in await mcp.list_prompts()}
    assert {"summarize_property", "compliance_check"} <= prompt_names


@pytest.fixture
def app_with_auth(tmp_path: Path):
    settings = Settings(
        wiki_dir=tmp_path / "wiki",
        normalize_dir=tmp_path / "normalize",
        output_dir=tmp_path / "output",
        env="dev",
        mcp_enabled=True,
        workos_authkit_domain="https://example.authkit.app",
    )
    with patch("app.main.get_settings", return_value=settings):
        yield create_app()


async def test_mcp_endpoint_requires_auth(app_with_auth) -> None:
    transport = ASGITransport(app=app_with_auth)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/mcp/",
            headers={
                "Accept": "application/json, text/event-stream",
                "Content-Type": "application/json",
            },
            json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        )
    assert resp.status_code == 401
    assert "WWW-Authenticate" in resp.headers
    assert "Bearer" in resp.headers["WWW-Authenticate"]


async def test_protected_resource_metadata_advertised(app_with_auth) -> None:
    transport = ASGITransport(app=app_with_auth)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/mcp/.well-known/oauth-protected-resource")
        assert resp.status_code == 200
        body = resp.json()
        assert "authorization_servers" in body
        assert any("authkit.app" in str(a) for a in body["authorization_servers"])

        for canonical in (
            "/.well-known/oauth-protected-resource",
            "/.well-known/oauth-protected-resource/mcp",
        ):
            r = await ac.get(canonical, follow_redirects=False)
            assert r.status_code == 307
            assert r.headers["location"].endswith("/mcp/.well-known/oauth-protected-resource")
