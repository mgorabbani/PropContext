from __future__ import annotations

import contextlib
from pathlib import Path
from typing import Any

import duckdb

from app.storage.db import connect


class WikiChunksStore:
    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        self._conn = conn
        self._index_built = False
        self._fts_available = False

    def init_schema(self) -> None:
        self._fts_available = self._load_fts()
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS wiki_chunks (
                property_id VARCHAR NOT NULL,
                file VARCHAR NOT NULL,
                section VARCHAR NOT NULL,
                body TEXT NOT NULL,
                entity_refs VARCHAR[] NOT NULL,
                updated_at TIMESTAMP DEFAULT current_timestamp,
                PRIMARY KEY (property_id, file, section)
            );
            """
        )

    def upsert(
        self,
        property_id: str,
        file: str,
        section: str,
        body: str,
        entity_refs: list[str],
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO wiki_chunks (property_id, file, section, body, entity_refs)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT (property_id, file, section) DO UPDATE SET
                body = excluded.body,
                entity_refs = excluded.entity_refs,
                updated_at = now();
            """,
            [property_id, file, section, body, entity_refs],
        )
        self._index_built = False

    def has_property(self, property_id: str) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM wiki_chunks WHERE property_id = ? LIMIT 1",
            [property_id],
        ).fetchone()
        return row is not None

    def delete_file(self, property_id: str, file: str) -> None:
        self._conn.execute(
            "DELETE FROM wiki_chunks WHERE property_id = ? AND file = ?",
            [property_id, file],
        )
        self._index_built = False

    def find_by_entity(self, property_id: str, entity_id: str) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT file, section, body, entity_refs, updated_at
            FROM wiki_chunks
            WHERE property_id = ? AND list_contains(entity_refs, ?)
            """,
            [property_id, entity_id],
        ).fetchall()
        return [
            {
                "file": r[0],
                "section": r[1],
                "body": r[2],
                "entity_refs": list(r[3]) if r[3] is not None else [],
                "updated_at": r[4],
            }
            for r in rows
        ]

    def build_index(self) -> None:
        if not self._fts_available:
            self._index_built = False
            return
        self._conn.execute(
            "PRAGMA create_fts_index('wiki_chunks', 'rowid', 'body', "
            "stemmer='german', stopwords='none', overwrite=1);"
        )
        self._index_built = True

    def query(
        self,
        q: str,
        property_id: str | None = None,
        limit: int = 8,
    ) -> list[dict[str, Any]]:
        if not self._fts_available:
            return []
        if not self._index_built:
            raise RuntimeError("call build_index() first")
        if not q.strip():
            return []

        sql = """
            SELECT property_id, file, section, body, score
            FROM (
                SELECT
                    property_id,
                    file,
                    section,
                    body,
                    fts_main_wiki_chunks.match_bm25(rowid, ?) AS score
                FROM wiki_chunks
            ) t
            WHERE score IS NOT NULL
        """
        params: list[Any] = [q]
        if property_id is not None:
            sql += " AND property_id = ?"
            params.append(property_id)
        sql += " ORDER BY score DESC LIMIT ?"
        params.append(limit)

        rows = self._conn.execute(sql, params).fetchall()
        return [
            {
                "property_id": r[0],
                "file": r[1],
                "section": r[2],
                "body": r[3],
                "score": float(r[4]),
            }
            for r in rows
        ]

    def _load_fts(self) -> bool:
        with contextlib.suppress(duckdb.Error):
            self._conn.execute("INSTALL fts;")
        try:
            self._conn.execute("LOAD fts;")
        except duckdb.Error:
            return False
        return True


def open_wiki_chunks(db_path: Path) -> WikiChunksStore:
    conn = connect(db_path)
    store = WikiChunksStore(conn)
    store.init_schema()
    return store
