from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import duckdb

from app.storage.db import connect

_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


def _tokenize(text: str) -> list[str]:
    return [m.group(0).lower() for m in _TOKEN_RE.finditer(text)]


class WikiChunksStore:
    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        self._conn = conn
        self._index_built = False

    def init_schema(self) -> None:
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
        self._index_built = True

    def query(
        self,
        q: str,
        property_id: str | None = None,
        limit: int = 8,
    ) -> list[dict[str, Any]]:
        if not self._index_built:
            raise RuntimeError("call build_index() first")

        sql = "SELECT property_id, file, section, body FROM wiki_chunks"
        params: list[Any] = []
        if property_id is not None:
            sql += " WHERE property_id = ?"
            params.append(property_id)
        rows = self._conn.execute(sql, params).fetchall()

        q_tokens = set(_tokenize(q))
        if not q_tokens:
            return []

        scored: list[tuple[float, dict[str, Any]]] = []
        for r in rows:
            body_tokens = _tokenize(r[3])
            if not body_tokens:
                continue
            body_token_set = set(body_tokens)
            distinct_hits = len(q_tokens & body_token_set)
            if distinct_hits == 0:
                continue
            term_freq = sum(1 for t in body_tokens if t in q_tokens)
            score = distinct_hits + term_freq / (len(body_tokens) + 1.0)
            scored.append(
                (
                    score,
                    {
                        "property_id": r[0],
                        "file": r[1],
                        "section": r[2],
                        "body": r[3],
                        "score": score,
                    },
                )
            )
        scored.sort(key=lambda x: x[0], reverse=True)
        return [hit for _, hit in scored[:limit]]


def open_wiki_chunks(db_path: Path) -> WikiChunksStore:
    conn = connect(db_path)
    store = WikiChunksStore(conn)
    store.init_schema()
    return store
