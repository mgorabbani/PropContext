from __future__ import annotations

from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_access_token

from app.mcp.orgs import org_can_access, properties_for_org


def current_org_id() -> str | None:
    token = get_access_token()
    if token is None:
        return None
    claims = getattr(token, "claims", None) or {}
    org_id = claims.get("org_id") or claims.get("organization_id")
    return str(org_id) if org_id else None


def require_org_id() -> str:
    org_id = current_org_id()
    if org_id is None:
        raise ToolError("authenticated token missing org_id claim")
    return org_id


def assert_property_access(property_id: str) -> None:
    org_id = current_org_id()
    if org_id is None:
        return  # no auth configured — open access
    if not org_can_access(org_id, property_id):
        raise ToolError(f"org {org_id!r} has no access to property {property_id!r}")


_OPEN_ACCESS: frozenset[str] = frozenset({"*"})


def allowed_properties() -> frozenset[str]:
    org_id = current_org_id()
    if org_id is None:
        # No auth configured — open access (dev / no-WorkOS mode)
        return _OPEN_ACCESS
    return properties_for_org(org_id)
