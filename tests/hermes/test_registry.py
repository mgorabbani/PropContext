from __future__ import annotations

from pathlib import Path

from app.services.hermes.feedback import append_feedback
from app.services.hermes.registry import format_briefing, load_skill_registry


def _seed(root: Path, n: int) -> None:
    for i in range(n):
        append_feedback(
            root,
            event_id=f"EMAIL-{i:03d}",
            event_type="email",
            property_id="LIE-001",
            summary=f"heating outage in EH-0{i:02d}",
            applied_ops=3,
            touched=[
                f"02_buildings/HAUS-{12 + i % 2}/index.md",
                f"entities/EH-0{i:02d}.md",
                f"sources/EMAIL-{i:03d}.md",
            ],
            op_shapes=[
                {"op": "create_page", "path": "sources/EMAIL-<id>.md"},
                {
                    "op": "upsert_section",
                    "path": "02_buildings/HAUS-<id>/index.md",
                    "heading": "Open Issues",
                },
                {"op": "prepend_log"},
            ],
        )


def test_registry_indexes_event_types_above_threshold(tmp_path: Path) -> None:
    root = tmp_path / "LIE-001"
    _seed(root, 4)
    registry = load_skill_registry(root, min_occurrences=3)
    briefing = registry.find_for("email")
    assert briefing is not None
    assert briefing.occurrences == 4
    assert briefing.op_kinds == ("create_page", "upsert_section", "prepend_log")
    assert "02_buildings/HAUS-<id>/index.md" in briefing.touched_templates
    assert any("heating outage" in s for s in briefing.sample_summaries)


def test_registry_skips_event_types_below_threshold(tmp_path: Path) -> None:
    root = tmp_path / "LIE-001"
    _seed(root, 2)
    registry = load_skill_registry(root, min_occurrences=3)
    assert registry.find_for("email") is None
    assert len(registry) == 0


def test_registry_skips_zero_op_rows(tmp_path: Path) -> None:
    root = tmp_path / "LIE-001"
    for i in range(5):
        append_feedback(
            root,
            event_id=f"VOICE-{i}",
            event_type="voicenote",
            property_id="LIE-001",
            summary="silence",
            applied_ops=0,
            touched=[],
            op_shapes=[],
        )
    registry = load_skill_registry(root, min_occurrences=3)
    assert registry.find_for("voicenote") is None


def test_format_briefing_renders_op_kinds_and_paths(tmp_path: Path) -> None:
    root = tmp_path / "LIE-001"
    _seed(root, 3)
    briefing = load_skill_registry(root, min_occurrences=3).find_for("email")
    assert briefing is not None

    rendered = format_briefing(briefing)
    assert "Past patterns for `event_type = email`" in rendered
    assert "`create_page` path=`sources/EMAIL-<id>.md`" in rendered
    assert "heading=`Open Issues`" in rendered
    assert "`02_buildings/HAUS-<id>/index.md`" in rendered
    assert "Reuse this shape" in rendered


def test_registry_picks_modal_op_signature(tmp_path: Path) -> None:
    root = tmp_path / "LIE-001"
    # Two events with shape A, one with shape B; A should win.
    for i in range(2):
        append_feedback(
            root,
            event_id=f"A-{i}",
            event_type="email",
            property_id="LIE-001",
            summary="A",
            applied_ops=2,
            touched=["entities/EH-001.md"],
            op_shapes=[
                {"op": "create_page", "path": "entities/EH-<id>.md"},
                {"op": "prepend_log"},
            ],
        )
    append_feedback(
        root,
        event_id="B-0",
        event_type="email",
        property_id="LIE-001",
        summary="B",
        applied_ops=1,
        touched=["topics/heizung.md"],
        op_shapes=[{"op": "upsert_section", "path": "topics/heizung.md", "heading": "Status"}],
    )
    briefing = load_skill_registry(root, min_occurrences=3).find_for("email")
    assert briefing is not None
    assert briefing.op_kinds == ("create_page", "prepend_log")
