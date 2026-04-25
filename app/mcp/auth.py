from __future__ import annotations

import structlog
from fastmcp.server.auth.providers.workos import AuthKitProvider

from app.core.config import Settings

log = structlog.get_logger(__name__)


def build_auth_provider(settings: Settings) -> AuthKitProvider | None:
    if not settings.workos_authkit_domain:
        log.warning("mcp_auth_disabled", reason="workos_authkit_domain unset")
        return None
    return AuthKitProvider(
        authkit_domain=settings.workos_authkit_domain,
        base_url=settings.mcp_base_url,
        required_scopes=settings.mcp_required_scopes,
        resource_name="Buena Context",
    )
