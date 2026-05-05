from __future__ import annotations

from pathlib import Path

from app.services.hermes.feedback import append_feedback
from app.services.hermes.skills import (
    SKILLS_FILENAME,
    propose_skills,
    render_skills_markdown,
    write_skills_markdown,
)


def _seed_heating_events(root: Path, n: int) -> None:
    for i in range(n):
        append_feedback(
            root,
            event_id=f"EMAIL-1{i:03d}",
            event_type="email",
            property_id="LIE-001",
            summary=f"heating outage in EH-0{i:02d}",
            applied_ops=4,
            touched=[
                f"02_buildings/HAUS-{12 + (i % 3)}/index.md",
                f"entities/EH-0{i:02d}.md",
                f"sources/EMAIL-1{i:03d}.md",
            ],
        )


def test_propose_skills_promotes_only_above_threshold(tmp_path: Path) -> None:
    root = tmp_path / "LIE-001"
    _seed_heating_events(root, 5)

    candidates = propose_skills(root, threshold=5)
    assert len(candidates) == 1
    skill = candidates[0]
    assert skill.event_type == "email"
    assert skill.occurrences == 5
    assert skill.last_event_id == "EMAIL-1004"
    assert skill.path_templates == (
        "02_buildings/HAUS-<id>/index.md",
        "entities/EH-<id>.md",
        "sources/EMAIL-<id>.md",
    )


def test_propose_skills_below_threshold_returns_empty(tmp_path: Path) -> None:
    root = tmp_path / "LIE-001"
    _seed_heating_events(root, 4)
    assert propose_skills(root, threshold=5) == []


def test_propose_skills_skips_zero_op_events(tmp_path: Path) -> None:
    root = tmp_path / "LIE-001"
    for i in range(6):
        append_feedback(
            root,
            event_id=f"NOOP-{i}",
            event_type="email",
            property_id="LIE-001",
            summary="nothing happened",
            applied_ops=0,
            touched=[],
        )
    assert propose_skills(root, threshold=3) == []


def test_render_and_write_skills_markdown(tmp_path: Path) -> None:
    root = tmp_path / "LIE-001"
    _seed_heating_events(root, 5)

    candidates = propose_skills(root, threshold=5)
    rendered = render_skills_markdown(candidates)
    assert "# Skills" in rendered
    assert "skill: email-" in rendered
    assert "Occurrences**: 5" in rendered

    path = write_skills_markdown(root, candidates)
    assert path.name == SKILLS_FILENAME
    assert "skill: email-" in path.read_text(encoding="utf-8")


def test_render_empty_skills_has_placeholder(tmp_path: Path) -> None:
    rendered = render_skills_markdown([])
    assert "No skills promoted yet" in rendered
