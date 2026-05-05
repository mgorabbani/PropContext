from __future__ import annotations

import structlog
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_access_token

from app.mcp.orgs import org_can_access, properties_for_org

log = structlog.get_logger(__name__)


def current_org_id() -> str | None:
    token = get_access_token()
    if token is None:
        log.debug("mcp_token_absent")
        return None
    claims = getattr(token, "claims", None) or {}
    org_id = claims.get("org_id") or claims.get("organization_id")
    if not org_id:
        log.warning("mcp_token_missing_org_claim", claim_keys=sorted(claims.keys()))
        return None
    return str(org_id)


def require_org_id() -> str:
    org_id = current_org_id()
    if org_id is None:
        raise ToolError("authenticated token missing org_id claim")
    return org_id


def assert_property_access(property_id: str) -> None:
    org_id = current_org_id()
    if org_can_access(org_id, property_id):
        return
    if org_id is None:
        raise ToolError("authenticated token missing org_id claim")
    raise ToolError(f"org {org_id!r} has no access to property {property_id!r}")


def allowed_properties() -> frozenset[str]:
    return properties_for_org(current_org_id())
