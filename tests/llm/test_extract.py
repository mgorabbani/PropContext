from __future__ import annotations

import pytest

from app.schemas.patch_plan import (
    AppendSectionOp,
    CreatePageOp,
    PatchPlan,
    PrependLogOp,
    UpsertSectionOp,
)
from app.services.extract import canonicalize_patch_plan


def test_canonicalize_accepts_four_op_shape() -> None:
    plan = canonicalize_patch_plan(
        {
            "summary": "manual leak",
            "ops": [
                {
                    "op": "create_page",
                    "path": "sources/EVT-1.md",
                    "frontmatter": {"name": "source-evt-1", "description": "Leak report"},
                    "body": "Leak in EH-014.",
                },
                {
                    "op": "upsert_section",
                    "path": "entities/EH-014.md",
                    "heading": "Status",
                    "body": "Heizung defekt seit 2026-04-23.",
                },
                {
                    "op": "append_section",
                    "path": "entities/EH-014.md",
                    "heading": "Timeline",
                    "line": "- 2026-04-25 leak reported [[sources/EVT-1.md]]",
                },
                {"op": "prepend_log", "line": "## [2026-04-25] manual | EH-014 leak"},
            ],
        },
        event_id="EVT-1",
        property_id="LIE-001",
        event_type="manual",
    )
    assert isinstance(plan, PatchPlan)
    assert len(plan.ops) == 4
    assert isinstance(plan.ops[0], CreatePageOp)
    assert isinstance(plan.ops[1], UpsertSectionOp)
    assert isinstance(plan.ops[2], AppendSectionOp)
    assert isinstance(plan.ops[3], PrependLogOp)


def test_canonicalize_normalizes_section_alias_to_heading() -> None:
    plan = canonicalize_patch_plan(
        {
            "ops": [
                {
                    "op": "upsert_section",
                    "path": "entities/MIE-014.md",
                    "section": "Contact",
                    "body": "phone: 030-...",
                }
            ],
        },
        event_id="EVT-2",
        property_id="LIE-001",
        event_type="email",
    )
    assert isinstance(plan.ops[0], UpsertSectionOp)
    assert plan.ops[0].heading == "Contact"


def test_canonicalize_overrides_runtime_managed_fields() -> None:
    plan = canonicalize_patch_plan(
        {
            "event_id": "INJECTED",
            "property_id": "LIE-999",
            "event_type": "spoof",
            "ops": [],
        },
        event_id="EVT-3",
        property_id="LIE-001",
        event_type="manual",
    )
    assert plan.event_id == "EVT-3"
    assert plan.property_id == "LIE-001"
    assert plan.event_type == "manual"


def test_canonicalize_rejects_unknown_op() -> None:
    with pytest.raises(Exception, match=r"literal_error|extra_forbidden|missing"):
        canonicalize_patch_plan(
            {"ops": [{"op": "upsert_bullet", "file": "x.md", "key": "k", "content": "v"}]},
            event_id="EVT-4",
            property_id="LIE-001",
            event_type="email",
        )
