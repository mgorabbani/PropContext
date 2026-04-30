from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from app.schemas.patch_plan import (
    AppendSectionOp,
    CreatePageOp,
    PatchPlan,
    PrependLogOp,
    UpsertSectionOp,
)
from app.services.patcher.apply import apply_patch_plan


def _git_init(wiki_dir: Path) -> None:
    subprocess.run(["git", "init"], cwd=wiki_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.test"],
        cwd=wiki_dir,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "test"], cwd=wiki_dir, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "config", "commit.gpgsign", "false"],
        cwd=wiki_dir,
        check=True,
        capture_output=True,
    )


def test_apply_creates_page_and_log(tmp_path: Path) -> None:
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    _git_init(wiki_dir)

    plan = PatchPlan(
        event_id="EVT-1",
        property_id="LIE-001",
        summary="manual leak",
        event_type="manual",
        ops=[
            CreatePageOp(
                path="entities/EH-014.md",
                frontmatter={"name": "unit-eh-014", "description": "Unit EH-014"},
                body="## Status\n\nLeak reported.",
            ),
            AppendSectionOp(
                path="entities/EH-014.md",
                heading="Timeline",
                line="- 2026-04-25 leak [[sources/EVT-1.md]]",
            ),
            PrependLogOp(line="## [2026-04-25] manual | EH-014 leak"),
        ],
    )
    result = apply_patch_plan(plan, wiki_dir=wiki_dir)
    assert result.applied_ops == 3
    assert result.commit_sha is not None

    page = (wiki_dir / "LIE-001/entities/EH-014.md").read_text(encoding="utf-8")
    assert "name: unit-eh-014" in page
    assert "## Timeline" in page
    assert "leak [[sources/EVT-1.md]]" in page

    log = (wiki_dir / "LIE-001/log.md").read_text(encoding="utf-8")
    assert "EH-014 leak" in log


def test_apply_rejects_path_escape(tmp_path: Path) -> None:
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    _git_init(wiki_dir)
    plan = PatchPlan(
        event_id="EVT-2",
        property_id="LIE-001",
        ops=[
            UpsertSectionOp(path="../escape.md", heading="x", body="y"),
        ],
    )
    with pytest.raises(ValueError, match="inside the property"):
        apply_patch_plan(plan, wiki_dir=wiki_dir)


def test_apply_rejects_invalid_property_id(tmp_path: Path) -> None:
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    _git_init(wiki_dir)
    plan = PatchPlan(event_id="x", property_id="../bad", ops=[])
    with pytest.raises(ValueError, match="property_id"):
        apply_patch_plan(plan, wiki_dir=wiki_dir)
