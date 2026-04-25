from __future__ import annotations

from app.services.patcher.ops import prepend_row, prune_ring


def _doc() -> str:
    return """---
name: test
description: Test doc.
---

## Recent Events

| Date | Event |
|---|---|
| 2026-01-01 | Old |
| 2026-01-02 | Older |

# Human Notes
"""


def test_prepend_row_inserts_above_existing_data() -> None:
    text = prepend_row(_doc(), section="Recent Events", row=["2026-01-03", "Newest"])

    assert text.index("| 2026-01-03 | Newest |") < text.index("| 2026-01-01 | Old |")


def test_prune_ring_keeps_first_n_data_rows() -> None:
    text = prepend_row(_doc(), section="Recent Events", row=["2026-01-03", "Newest"])
    text = prune_ring(text, section="Recent Events", max_rows=2)

    assert "| 2026-01-03 | Newest |" in text
    assert "| 2026-01-01 | Old |" in text
    assert "| 2026-01-02 | Older |" not in text
