from __future__ import annotations

from pathlib import Path

from app.services.patcher.validate import (
    append_pending_review,
    parse_vocabulary,
    validate_keyed_values,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_vocab_accepts_known_status() -> None:
    vocab = parse_vocabulary(REPO_ROOT / "schema" / "VOCABULARY.md")
    valid, issues = validate_keyed_values(
        [{"op": "upsert_bullet", "file": "index.md", "status": "in_progress"}],
        vocab,
    )

    assert len(valid) == 1
    assert issues == []


def test_vocab_rejects_unknown_status_and_writes_pending_review(tmp_path: Path) -> None:
    vocab = parse_vocabulary(REPO_ROOT / "schema" / "VOCABULARY.md")
    valid, issues = validate_keyed_values(
        [{"op": "upsert_bullet", "file": "index.md", "status": "wip"}],
        vocab,
    )
    root = tmp_path / "LIE-001"
    root.mkdir()

    append_pending_review(root, issues)

    assert valid == []
    text = (root / "_pending_review.md").read_text(encoding="utf-8")
    assert "unknown vocab: status='wip'" in text
    assert "# Human Notes" in text
