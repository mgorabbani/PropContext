from __future__ import annotations

import pytest

from app.services.patcher.ops import PatchOperationError, upsert_bullet


def test_op_refuses_section_after_human_notes() -> None:
    text = """---
name: test
description: Test doc.
---

# Human Notes

## Open Issues

- human-owned
"""

    with pytest.raises(PatchOperationError, match="section not found before # Human Notes"):
        upsert_bullet(text, section="Open Issues", key="EH-001", text="new")
