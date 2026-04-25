from __future__ import annotations

from app.services.patcher.ops import gc_footnotes, upsert_footnote


def _doc() -> str:
    return """---
name: test
description: Test doc.
---

## Open Issues

- **EH-001:** Leak [^keep]

## Provenance

[^keep]: old
[^drop]: unused

# Human Notes
"""


def test_upsert_footnote_updates_provenance_only() -> None:
    text = upsert_footnote(_doc(), key="keep", text="new source")

    assert "[^keep]: new source" in text
    assert "## Provenance" in text


def test_gc_footnotes_drops_zero_ref_entries() -> None:
    text = gc_footnotes(_doc(), ref_counts={"keep": 1, "drop": 0})

    assert "[^keep]: old" in text
    assert "[^drop]: unused" not in text
