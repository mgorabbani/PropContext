from __future__ import annotations

from pathlib import Path

import pytest

from app.storage.wiki_chunks import WikiChunksStore, open_wiki_chunks


def _row_count(store: WikiChunksStore) -> int:
    row = store._conn.execute("SELECT count(*) FROM wiki_chunks;").fetchone()
    return int(row[0]) if row else 0


def _require_fts(store: WikiChunksStore) -> None:
    if not store._fts_available:
        pytest.skip("DuckDB fts extension not available in this environment")


def test_init_schema_creates_table(tmp_path: Path) -> None:
    store = open_wiki_chunks(tmp_path / "wiki.duckdb")
    row = store._conn.execute(
        """
        SELECT count(*) FROM duckdb_tables()
        WHERE schema_name = 'main' AND table_name = 'wiki_chunks';
        """
    ).fetchone()
    assert row is not None
    assert row[0] == 1


def test_upsert_inserts_then_updates(tmp_path: Path) -> None:
    store = open_wiki_chunks(tmp_path / "wiki.duckdb")

    store.upsert("LIE-001", "foo.md", "Open Issues", "body1", ["EH-014"])
    assert _row_count(store) == 1

    store.upsert("LIE-001", "foo.md", "Open Issues", "body2", ["EH-014", "MIE-014"])
    assert _row_count(store) == 1

    rows = store.find_by_entity("LIE-001", "MIE-014")
    assert len(rows) == 1
    assert rows[0]["body"] == "body2"
    assert rows[0]["entity_refs"] == ["EH-014", "MIE-014"]


def test_find_by_entity_filters_by_property_and_ref(tmp_path: Path) -> None:
    store = open_wiki_chunks(tmp_path / "wiki.duckdb")

    store.upsert("LIE-001", "A.md", "Sec", "body A", ["EH-014", "MIE-014"])
    store.upsert("LIE-001", "B.md", "Sec", "body B", ["EH-099"])
    store.upsert("LIE-002", "C.md", "Sec", "body C", ["EH-014"])

    rows = store.find_by_entity("LIE-001", "EH-014")
    assert len(rows) == 1
    assert rows[0]["file"] == "A.md"
    assert rows[0]["body"] == "body A"


def test_query_ranks_relevant_higher(tmp_path: Path) -> None:
    store = open_wiki_chunks(tmp_path / "wiki.duckdb")
    _require_fts(store)
    store.upsert("LIE-001", "f1.md", "S", "Heizung defekt im Erdgeschoss", ["EH-014"])
    store.upsert("LIE-001", "f2.md", "S", "Aufzug Wartung fällig", ["EH-015"])
    store.upsert("LIE-001", "f3.md", "S", "Allgemeine Hausordnung Müll", ["EH-016"])
    store.build_index()

    hits = store.query("Heizung")
    assert len(hits) >= 1
    assert hits[0]["file"] == "f1.md"


def test_query_filters_by_property(tmp_path: Path) -> None:
    store = open_wiki_chunks(tmp_path / "wiki.duckdb")
    _require_fts(store)
    store.upsert("LIE-001", "f.md", "S", "Heizung defekt im Erdgeschoss", ["EH-014"])
    store.upsert("LIE-002", "f.md", "S", "Heizung defekt im Erdgeschoss", ["EH-014"])
    store.build_index()

    hits = store.query("Heizung", property_id="LIE-001")
    assert len(hits) == 1
    assert hits[0]["property_id"] == "LIE-001"


def test_query_raises_if_no_index(tmp_path: Path) -> None:
    store = open_wiki_chunks(tmp_path / "wiki.duckdb")
    _require_fts(store)
    store.upsert("LIE-001", "f.md", "S", "Heizung defekt", ["EH-014"])

    with pytest.raises(RuntimeError, match="build_index"):
        store.query("Heizung")


def test_query_stems_german_plural(tmp_path: Path) -> None:
    store = open_wiki_chunks(tmp_path / "wiki.duckdb")
    _require_fts(store)
    store.upsert("LIE-001", "a.md", "S", "Heizungen sind defekt", ["EH-014"])
    store.upsert("LIE-001", "b.md", "S", "Aufzug Wartung fällig", ["EH-015"])
    store.build_index()

    hits = store.query("Heizung")
    assert len(hits) == 1
    assert hits[0]["file"] == "a.md"


def test_has_property(tmp_path: Path) -> None:
    store = open_wiki_chunks(tmp_path / "wiki.duckdb")
    assert store.has_property("LIE-001") is False
    store.upsert("LIE-001", "f.md", "S", "x", [])
    assert store.has_property("LIE-001") is True
    assert store.has_property("LIE-002") is False
