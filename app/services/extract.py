from __future__ import annotations

import json
from typing import Any

from app.core.config import REPO_ROOT, Settings
from app.schemas.patch_plan import PatchPlan
from app.services.llm.client import LLMClient
from app.services.llm.json import parse_json_object
from app.services.locate import LocatedSection
from app.services.resolve import ResolutionResult


def extract_prompt(
    *,
    event_id: str,
    event_type: str,
    property_id: str,
    normalized_text: str,
    resolution: ResolutionResult,
    sections: list[LocatedSection],
    existing_pages: list[str],
) -> str:
    payload = {
        "event_id": event_id,
        "event_type": event_type,
        "property_id": property_id,
        "resolved_entities": [
            {"id": e.id, "role": e.role, "data": _trim_entity(e.data)} for e in resolution.entities
        ],
        "mentioned_ids": resolution.mentioned_ids,
        "source_ids": resolution.source_ids,
        "unresolved_ids": resolution.unresolved_ids,
        "existing_pages": existing_pages,
        "located_sections": [
            {
                "path": s.file,
                "heading": s.section,
                "entity_refs": s.entity_refs,
                "body": s.body,
            }
            for s in sections
        ],
        "normalized_document": normalized_text,
    }
    return (
        "Produce ONE PatchPlan JSON object that integrates this source into the wiki. "
        "Follow the system contract. Return JSON only — no markdown, no commentary.\n\n"
        f"{json.dumps(payload, ensure_ascii=False, default=str)}"
    )


async def extract_patch_plan(
    *,
    event_id: str,
    event_type: str,
    property_id: str,
    normalized_text: str,
    resolution: ResolutionResult,
    sections: list[LocatedSection],
    existing_pages: list[str],
    llm: LLMClient,
    settings: Settings,
) -> PatchPlan:
    response = await llm.complete(
        model=settings.smart_model,
        system_prompt=load_system_prompt(),
        user_prompt=extract_prompt(
            event_id=event_id,
            event_type=event_type,
            property_id=property_id,
            normalized_text=normalized_text,
            resolution=resolution,
            sections=sections,
            existing_pages=existing_pages,
        ),
    )
    payload = parse_json_object(response)
    return canonicalize_patch_plan(
        payload,
        event_id=event_id,
        property_id=property_id,
        event_type=event_type,
        source_ids=resolution.source_ids,
    )


def canonicalize_patch_plan(
    payload: dict[str, Any],
    *,
    event_id: str,
    property_id: str,
    event_type: str,
    source_ids: list[str] | None = None,
) -> PatchPlan:
    data = dict(payload)
    data["event_id"] = event_id
    data["property_id"] = property_id
    data["event_type"] = event_type
    if source_ids and not data.get("source_ids"):
        data["source_ids"] = source_ids
    raw_ops = data.get("ops") or []
    data["ops"] = [_canonical_op(op) for op in raw_ops if isinstance(op, dict)]
    return PatchPlan.model_validate(data)


def _canonical_op(raw: dict[str, Any]) -> dict[str, Any]:
    op = dict(raw)
    name = str(op.get("op", ""))
    if name == "create_page" and "frontmatter" in op and not isinstance(op["frontmatter"], dict):
        op["frontmatter"] = None
    if name in {"upsert_section", "append_section"} and "section" in op and "heading" not in op:
        op["heading"] = op.pop("section")
    return op


def load_system_prompt() -> str:
    parts: list[str] = []
    for relative in ("schema/CLAUDE.md", "schema/WIKI_SCHEMA.md"):
        path = REPO_ROOT / relative
        if path.is_file():
            parts.append(path.read_text(encoding="utf-8"))
    return "\n\n".join(parts) or _FALLBACK_PROMPT


def _trim_entity(data: dict[str, Any]) -> dict[str, Any]:
    keep = {"id", "role", "name", "vorname", "nachname", "email", "iban", "haus_id", "einheit_id"}
    return {k: v for k, v in data.items() if k in keep}


_FALLBACK_PROMPT = (
    "You maintain a Karpathy-style markdown wiki for a property. "
    "Emit a PatchPlan JSON with one or more of these ops only: "
    "create_page(path, frontmatter, body), upsert_section(path, heading, body), "
    "append_section(path, heading, line), prepend_log(line). "
    "Always create a sources/<event_id>.md page summarising the source. "
    "Always emit exactly one prepend_log op describing the event in one line."
)
