from __future__ import annotations

from pathlib import Path

from app.services.hermes.feedback import append_feedback
from app.services.hermes.proposals import (
    PROPOSALS_FILENAME,
    propose_schema_amendments,
    render_proposals_markdown,
    write_proposals_markdown,
)


def test_proposals_flag_repeated_misses(tmp_path: Path) -> None:
    root = tmp_path / "LIE-001"
    for i in range(3):
        append_feedback(
            root,
            event_id=f"VOICE-{i}",
            event_type="voicenote",
            property_id="LIE-001",
            summary="recorded message",
            applied_ops=0,
        )
    append_feedback(
        root,
        event_id="EMAIL-9",
        event_type="email",
        property_id="LIE-001",
        summary="ok",
        applied_ops=2,
        touched=["a.md"],
    )

    report = propose_schema_amendments(root)
    assert report.total_events == 4
    assert report.misses == 3
    kinds = [p.kind for p in report.proposals]
    assert "schema-gap" in kinds
    schema_gap = next(p for p in report.proposals if p.kind == "schema-gap")
    assert "voicenote" in schema_gap.target
    assert set(schema_gap.evidence_event_ids) == {"VOICE-0", "VOICE-1", "VOICE-2"}


def test_proposals_flag_conflicts(tmp_path: Path) -> None:
    root = tmp_path / "LIE-001"
    append_feedback(
        root,
        event_id="INV-1",
        event_type="invoice",
        property_id="LIE-001",
        summary="amount mismatch",
        applied_ops=2,
        deferred_ops=1,
        touched=["05_finances/overview.md"],
    )
    report = propose_schema_amendments(root)
    assert report.conflicts == 1
    kinds = [p.kind for p in report.proposals]
    assert "vocabulary-gap" in kinds


def test_proposals_flag_unresolved_ids(tmp_path: Path) -> None:
    root = tmp_path / "LIE-001"
    for i in range(3):
        append_feedback(
            root,
            event_id=f"E-{i}",
            event_type="email",
            property_id="LIE-001",
            summary="message about ZX-999",
            applied_ops=1,
            touched=["02_buildings/HAUS-12/index.md"],
        )

    report = propose_schema_amendments(root)
    unresolved = [p for p in report.proposals if p.kind == "unresolved-entity"]
    assert len(unresolved) == 1
    assert "ZX-999" in unresolved[0].target


def test_proposals_resolved_ids_are_not_flagged(tmp_path: Path) -> None:
    root = tmp_path / "LIE-001"
    for i in range(5):
        append_feedback(
            root,
            event_id=f"E-{i}",
            event_type="email",
            property_id="LIE-001",
            summary="touches EH-014",
            applied_ops=1,
            touched=["entities/EH-014.md"],
        )
    report = propose_schema_amendments(root)
    assert all(p.kind != "unresolved-entity" for p in report.proposals)


def test_render_and_write_proposals_markdown(tmp_path: Path) -> None:
    root = tmp_path / "LIE-001"
    for i in range(2):
        append_feedback(
            root,
            event_id=f"VOICE-{i}",
            event_type="voicenote",
            property_id="LIE-001",
            summary="message",
            applied_ops=0,
        )
    report = propose_schema_amendments(root)
    rendered = render_proposals_markdown(report)
    assert "# Hermes Schema Proposals" in rendered
    assert "Total ingest events scanned" in rendered
    assert "schema-gap" in rendered

    path = write_proposals_markdown(root, report)
    assert path.name == PROPOSALS_FILENAME
    assert path.is_file()


def test_render_empty_report_has_healthy_message(tmp_path: Path) -> None:
    report = propose_schema_amendments(tmp_path / "LIE-001")
    rendered = render_proposals_markdown(report)
    assert "Substrate looks healthy" in rendered
