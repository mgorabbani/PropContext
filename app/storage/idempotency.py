from __future__ import annotations

from pathlib import Path

import duckdb

from app.storage.db import connect

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS event_idempotency (
    event_id VARCHAR PRIMARY KEY,
    received_at TIMESTAMP DEFAULT current_timestamp,
    status VARCHAR NOT NULL DEFAULT 'pending'
)
"""


class IdempotencyStore:
    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        self._conn = conn

    def init_schema(self) -> None:
        self._conn.execute(_SCHEMA_SQL)

    def claim(self, event_id: str) -> bool:
        before = self._conn.execute(
            "SELECT COUNT(*) FROM event_idempotency WHERE event_id = ?",
            [event_id],
        ).fetchone()
        if before is not None and before[0] > 0:
            return False
        self._conn.execute(
            "INSERT INTO event_idempotency (event_id) VALUES (?) ON CONFLICT DO NOTHING",
            [event_id],
        )
        after = self._conn.execute(
            "SELECT COUNT(*) FROM event_idempotency WHERE event_id = ?",
            [event_id],
        ).fetchone()
        return after is not None and after[0] == 1

    def mark_done(self, event_id: str) -> None:
        self._conn.execute(
            "UPDATE event_idempotency SET status = 'done' WHERE event_id = ?",
            [event_id],
        )

    def mark_failed(self, event_id: str) -> None:
        self._conn.execute(
            "UPDATE event_idempotency SET status = 'failed' WHERE event_id = ?",
            [event_id],
        )

    def status(self, event_id: str) -> str | None:
        row = self._conn.execute(
            "SELECT status FROM event_idempotency WHERE event_id = ?",
            [event_id],
        ).fetchone()
        if row is None:
            return None
        return row[0]


def open_idempotency(db_path: Path) -> IdempotencyStore:
    conn = connect(db_path)
    store = IdempotencyStore(conn)
    store.init_schema()
    return store
