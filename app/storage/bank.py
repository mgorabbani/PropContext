from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Any

import duckdb

from app.storage.db import connect

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS bank_tx (
    id VARCHAR PRIMARY KEY,
    datum DATE NOT NULL,
    typ VARCHAR NOT NULL,
    betrag DECIMAL(12,2) NOT NULL,
    kategorie VARCHAR,
    gegen_name VARCHAR,
    verwendungszweck VARCHAR,
    referenz_id VARCHAR,
    error_types VARCHAR
)
"""

_INDEX_SQL: tuple[str, ...] = (
    "CREATE INDEX IF NOT EXISTS idx_bank_tx_referenz ON bank_tx(referenz_id)",
    "CREATE INDEX IF NOT EXISTS idx_bank_tx_kategorie ON bank_tx(kategorie)",
    "CREATE INDEX IF NOT EXISTS idx_bank_tx_datum ON bank_tx(datum)",
)

_COLUMNS: tuple[str, ...] = (
    "id",
    "datum",
    "typ",
    "betrag",
    "kategorie",
    "gegen_name",
    "verwendungszweck",
    "referenz_id",
    "error_types",
)


def _row_to_dict(row: tuple[Any, ...] | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return dict(zip(_COLUMNS, row, strict=False))


class BankStore:
    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        self._conn = conn

    def init_schema(self) -> None:
        self._conn.execute(_SCHEMA_SQL)
        for stmt in _INDEX_SQL:
            self._conn.execute(stmt)

    def load_from_csv(self, csv_path: Path) -> None:
        self._conn.execute("DELETE FROM bank_tx")
        self._conn.execute(
            """
            COPY bank_tx FROM ? (
                FORMAT CSV,
                HEADER TRUE,
                NULL '',
                DATEFORMAT '%Y-%m-%d'
            )
            """,
            [str(csv_path)],
        )

    def find_by_referenz(self, ref: str) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            f"SELECT {', '.join(_COLUMNS)} FROM bank_tx WHERE referenz_id = ? ORDER BY datum",  # noqa: S608
            [ref],
        ).fetchall()
        return [d for d in (_row_to_dict(r) for r in rows) if d is not None]

    def find_by_id(self, tx_id: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            f"SELECT {', '.join(_COLUMNS)} FROM bank_tx WHERE id = ?",  # noqa: S608
            [tx_id],
        ).fetchone()
        result = _row_to_dict(row)
        if result is not None and isinstance(result.get("betrag"), Decimal):
            pass
        return result


def open_bank(db_path: Path) -> BankStore:
    conn = connect(db_path)
    store = BankStore(conn)
    store.init_schema()
    return store
