from __future__ import annotations

ORG_PROPERTIES: dict[str, frozenset[str]] = {
    "org_demo_berlin": frozenset({"LIE-001"}),
    "org_demo_hamburg": frozenset(),
}


def properties_for_org(org_id: str | None) -> frozenset[str]:
    if org_id is None:
        return frozenset()
    return ORG_PROPERTIES.get(org_id, frozenset())


def org_can_access(org_id: str | None, property_id: str) -> bool:
    return property_id in properties_for_org(org_id)
