from __future__ import annotations

from pathlib import Path

from app.services.patcher.atomic import atomic_write_text
from app.services.patcher.ops import render_page
from app.services.wiki_index import regenerate_index


def _write(path: Path, frontmatter: dict[str, str], body: str = "") -> None:
    atomic_write_text(path, render_page(frontmatter=frontmatter, body=body))


def test_regenerate_index_lists_pages_with_descriptions(tmp_path: Path) -> None:
    root = tmp_path / "LIE-001"
    root.mkdir()
    _write(
        root / "entities/DL-010.md",
        {"name": "vendor-dl-010", "description": "Heating contractor for HAUS-12"},
    )
    _write(
        root / "topics/2026-04-aufzug.md",
        {"name": "topic-aufzug-2026-04", "description": "Elevator outage tracking"},
    )

    index_path = regenerate_index(root)
    assert index_path is not None
    body = index_path.read_text(encoding="utf-8")
    assert "vendor-dl-010" in body
    assert "Heating contractor for HAUS-12" in body
    assert "topic-aufzug-2026-04" in body
    assert "Elevator outage tracking" in body


def test_regenerate_index_skips_hidden_and_runtime_files(tmp_path: Path) -> None:
    root = tmp_path / "LIE-001"
    root.mkdir()
    _write(root / "entities/x.md", {"name": "x", "description": "X"})
    _write(root / "_pending.md", {"name": "pending", "description": "should not appear"})
    (root / "log.md").write_text("# Log\n", encoding="utf-8")
    (root / "lint_report.md").write_text("# Lint Report\n", encoding="utf-8")

    index_path = regenerate_index(root)
    assert index_path is not None
    body = index_path.read_text(encoding="utf-8")
    assert "x" in body
    assert "pending" not in body
    assert "lint_report.md" not in body


def test_regenerate_index_is_idempotent(tmp_path: Path) -> None:
    root = tmp_path / "LIE-001"
    root.mkdir()
    _write(root / "entities/x.md", {"name": "x", "description": "X"})
    first = regenerate_index(root)
    assert first is not None
    second = regenerate_index(root)
    assert second is None  # no change → no write
