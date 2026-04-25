from __future__ import annotations

from app.services.patcher.ops import delete_bullet, upsert_bullet


def _doc() -> str:
    return """---
name: test
description: Test doc.
---

## Open Issues

<!-- agent-managed: keyed bullets -->
- Human note without key stays here.
- 🟡 **EH-001:** Old leak [^old]

## Provenance

# Human Notes
"""


def test_upsert_bullet_inserts_new_key() -> None:
    text = upsert_bullet(_doc(), section="Open Issues", key="EH-002", text="🔴 New issue")

    assert "- **EH-002:** 🔴 New issue" in text
    assert "- Human note without key stays here." in text


def test_upsert_bullet_updates_existing_key() -> None:
    text = upsert_bullet(_doc(), section="Open Issues", key="EH-001", text="🟢 Fixed [^new]")

    assert "- **EH-001:** 🟢 Fixed [^new]" in text
    assert "Old leak" not in text
    assert "- Human note without key stays here." in text


def test_delete_bullet_removes_only_keyed_bullet() -> None:
    text = delete_bullet(_doc(), section="Open Issues", key="EH-001")

    assert "EH-001" not in text
    assert "- Human note without key stays here." in text
