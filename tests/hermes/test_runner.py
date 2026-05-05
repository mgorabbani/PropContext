from __future__ import annotations

from pathlib import Path

from app.services.hermes.feedback import append_feedback
from app.services.hermes.proposals import PROPOSALS_FILENAME
from app.services.hermes.runner import run_hermes_loops
from app.services.hermes.skills import SKILLS_FILENAME


def _seed(root: Path) -> None:
    for i in range(5):
        append_feedback(
            root,
            event_id=f"EMAIL-{i:03d}",
            event_type="email",
            property_id="LIE-001",
            summary=f"heating in EH-{i:03d}",
            applied_ops=4,
            touched=[
                f"02_buildings/HAUS-{12 + (i % 2)}/index.md",
                f"entities/EH-{i:03d}.md",
                f"sources/EMAIL-{i:03d}.md",
            ],
        )
    for i in range(2):
        append_feedback(
            root,
            event_id=f"VOICE-{i}",
            event_type="voicenote",
            property_id="LIE-001",
            summary="recorded note",
            applied_ops=0,
        )


def test_runner_writes_both_artifacts(tmp_path: Path) -> None:
    wiki_dir = tmp_path / "wiki"
    property_root = wiki_dir / "LIE-001"
    _seed(property_root)

    report = run_hermes_loops(wiki_dir=wiki_dir, property_id="LIE-001", skill_threshold=5)

    assert report.property_id == "LIE-001"
    assert len(report.skills) == 1
    assert any(p.kind == "schema-gap" for p in report.proposals.proposals)
    assert (property_root / SKILLS_FILENAME).is_file()
    assert (property_root / PROPOSALS_FILENAME).is_file()


def test_runner_dry_run_writes_nothing(tmp_path: Path) -> None:
    wiki_dir = tmp_path / "wiki"
    property_root = wiki_dir / "LIE-001"
    _seed(property_root)

    report = run_hermes_loops(
        wiki_dir=wiki_dir,
        property_id="LIE-001",
        skill_threshold=5,
        write=False,
    )

    assert report.skills_path is None
    assert report.proposals_path is None
    assert not (property_root / SKILLS_FILENAME).exists()
    assert not (property_root / PROPOSALS_FILENAME).exists()
