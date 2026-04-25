from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Any

import duckdb

from app.storage.db import connect

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS invoices (
    id VARCHAR PRIMARY KEY,
    dl_id VARCHAR NOT NULL,
    datum DATE NOT NULL,
    pdf_path VARCHAR NOT NULL,
    betrag DECIMAL(12,2),
    sha256 VARCHAR
)
"""

_INDEX_SQL: tuple[str, ...] = (
    "CREATE INDEX IF NOT EXISTS idx_invoices_dl ON invoices(dl_id)",
    "CREATE INDEX IF NOT EXISTS idx_invoices_datum ON invoices(datum)",
)

_FILENAME_RE = re.compile(
    r"^(?P<datum>\d{8})_(?P<dl_id>DL-\d{3})_(?P<inv_id>INV-\d{5})\.pdf$",
    re.IGNORECASE,
)

_COLUMNS: tuple[str, ...] = ("id", "dl_id", "datum", "pdf_path", "betrag", "sha256")


def _parse_filename(name: str) -> tuple[str, str, date] | None:
    match = _FILENAME_RE.match(name)
    if match is None:
        return None
    raw = match.group("datum")
    try:
        parsed = date(int(raw[0:4]), int(raw[4:6]), int(raw[6:8]))
    except ValueError:
        return None
    return match.group("inv_id").upper(), match.group("dl_id").upper(), parsed


def _row_to_dict(row: tuple[Any, ...] | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return dict(zip(_COLUMNS, row, strict=False))


class InvoicesStore:
    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        self._conn = conn

    def init_schema(self) -> None:
        self._conn.execute(_SCHEMA_SQL)
        for stmt in _INDEX_SQL:
            self._conn.execute(stmt)

    def index_directory(self, rechnungen_dir: Path) -> int:
        count = 0
        for pdf_path in sorted(rechnungen_dir.rglob("*.pdf")):
            parsed = _parse_filename(pdf_path.name)
            if parsed is None:
                continue
            inv_id, dl_id, datum = parsed
            self._conn.execute(
                """
                INSERT INTO invoices (id, dl_id, datum, pdf_path)
                VALUES (?, ?, ?, ?)
                ON CONFLICT (id) DO UPDATE SET
                    dl_id = EXCLUDED.dl_id,
                    datum = EXCLUDED.datum,
                    pdf_path = EXCLUDED.pdf_path
                """,
                [inv_id, dl_id, datum, str(pdf_path)],
            )
            count += 1
        return count

    def find_by_id(self, inv_id: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            f"SELECT {', '.join(_COLUMNS)} FROM invoices WHERE id = ?",  # noqa: S608
            [inv_id],
        ).fetchone()
        return _row_to_dict(row)

    def find_by_dienstleister(self, dl_id: str) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            f"SELECT {', '.join(_COLUMNS)} FROM invoices WHERE dl_id = ? ORDER BY datum",  # noqa: S608
            [dl_id],
        ).fetchall()
        return [d for d in (_row_to_dict(r) for r in rows) if d is not None]


def open_invoices(db_path: Path) -> InvoicesStore:
    conn = connect(db_path)
    store = InvoicesStore(conn)
    store.init_schema()
    return store
