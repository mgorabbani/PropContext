from __future__ import annotations

from app.services.patcher.ops import delete_row, upsert_row


def _doc() -> str:
    return """---
name: test
description: Test doc.
---

## Recent Invoices

| ID | Status | Amount |
|---|---|---|
| INV-001 | offen | 10.00 |

# Human Notes
"""


def test_upsert_row_inserts_new_key() -> None:
    text = upsert_row(
        _doc(),
        section="Recent Invoices",
        key="INV-002",
        row=["INV-002", "bezahlt", "20.00"],
    )

    assert "| INV-001 | offen | 10.00 |" in text
    assert "| INV-002 | bezahlt | 20.00 |" in text


def test_upsert_row_updates_existing_key() -> None:
    text = upsert_row(
        _doc(),
        section="Recent Invoices",
        key="INV-001",
        row=["INV-001", "bezahlt", "10.00"],
    )

    assert "| INV-001 | bezahlt | 10.00 |" in text
    assert "| INV-001 | offen | 10.00 |" not in text


def test_delete_row_removes_matching_key() -> None:
    text = delete_row(_doc(), section="Recent Invoices", key="INV-001")

    assert "| INV-001 |" not in text
    assert "| ID | Status | Amount |" in text
