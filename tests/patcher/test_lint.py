from __future__ import annotations

import subprocess
from pathlib import Path

from app.services.lint import LintService
from app.services.patcher.atomic import atomic_write_text
from app.services.patcher.ops import render_page


def _git_init(wiki_dir: Path) -> None:
    subprocess.run(["git", "init"], cwd=wiki_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@buena.local"],
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


def test_lint_flags_missing_frontmatter_and_orphans(tmp_path: Path) -> None:
    wiki_dir = tmp_path / "wiki"
    root = wiki_dir / "LIE-001"
    root.mkdir(parents=True)
    _git_init(wiki_dir)

    atomic_write_text(
        root / "entities/with-fm.md",
        render_page(frontmatter={"name": "with-fm", "description": "a"}, body="body"),
    )
    atomic_write_text(root / "entities/no-fm.md", "no frontmatter here\n")

    result = LintService(wiki_dir=wiki_dir).lint("LIE-001", commit=False)
    kinds = {f.kind for f in result.findings}
    assert "missing_frontmatter_name" in kinds
    assert "missing_frontmatter_description" in kinds
    assert "orphan_page" in kinds


def test_lint_returns_no_findings_on_clean_wiki(tmp_path: Path) -> None:
    wiki_dir = tmp_path / "wiki"
    root = wiki_dir / "LIE-001"
    root.mkdir(parents=True)
    _git_init(wiki_dir)

    atomic_write_text(
        root / "entities/a.md",
        render_page(
            frontmatter={"name": "a", "description": "a"},
            body="See [[entities/b.md]]",
        ),
    )
    atomic_write_text(
        root / "entities/b.md",
        render_page(
            frontmatter={"name": "b", "description": "b"},
            body="See [[entities/a.md]]",
        ),
    )

    result = LintService(wiki_dir=wiki_dir).lint("LIE-001", commit=False)
    kinds = {f.kind for f in result.findings}
    assert "missing_frontmatter_name" not in kinds
    assert "missing_frontmatter_description" not in kinds
    assert "orphan_page" not in kinds
