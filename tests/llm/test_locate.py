from __future__ import annotations

from pathlib import Path

import pytest

from app.services.locate import locate_sections
from app.storage.wiki_chunks import open_wiki_chunks


def test_locate_returns_entity_sections_ranked_before_search(tmp_path: Path) -> None:
    store = open_wiki_chunks(tmp_path / "wiki.duckdb")
    if not store._fts_available:
        pytest.skip("DuckDB fts extension not available in this environment")
    store.upsert("LIE-001", "index.md", "Open Issues", "Heizung EH-014 defekt", ["EH-014"])
    store.upsert("LIE-001", "other.md", "Summary", "Heizung allgemein", [])

    hits = locate_sections(
        wiki_chunks=store,
        property_id="LIE-001",
        entity_ids=["EH-014"],
        query_text="Heizung",
    )

    assert hits[0].file == "index.md"
    assert hits[0].section == "Open Issues"
