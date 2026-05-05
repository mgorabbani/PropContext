from __future__ import annotations

from collections.abc import Iterable, Mapping

WILDCARD_ORG = "*"

_BASELINE: dict[str, frozenset[str]] = {
    "org_demo_berlin": frozenset({"LIE-001"}),
    "org_demo_hamburg": frozenset(),
}

ORG_PROPERTIES: dict[str, frozenset[str]] = dict(_BASELINE)


def configure_orgs(extra: Mapping[str, Iterable[str]] | None) -> None:
    ORG_PROPERTIES.clear()
    ORG_PROPERTIES.update(_BASELINE)
    if not extra:
        return
    for org_id, props in extra.items():
        merged = ORG_PROPERTIES.get(org_id, frozenset()) | frozenset(props)
        ORG_PROPERTIES[org_id] = merged


def properties_for_org(org_id: str | None) -> frozenset[str]:
    wildcard = ORG_PROPERTIES.get(WILDCARD_ORG, frozenset())
    if org_id is None:
        return wildcard
    return ORG_PROPERTIES.get(org_id, frozenset()) | wildcard


def org_can_access(org_id: str | None, property_id: str) -> bool:
    allowed = properties_for_org(org_id)
    return "*" in allowed or property_id in allowed
