from __future__ import annotations

from pathlib import Path

import pytest

from app.storage.stammdaten import open_stammdaten

STAMMDATEN_JSON = Path(__file__).parents[2] / "data/stammdaten/stammdaten.json"

EXPECTED_TABLES = {
    "liegenschaft",
    "gebaeude",
    "einheiten",
    "eigentuemer",
    "mieter",
    "dienstleister",
}


@pytest.fixture
def store(tmp_path: Path):
    return open_stammdaten(tmp_path / "stammdaten.duckdb")


@pytest.fixture
def loaded_store(store):
    store.load_from_json(STAMMDATEN_JSON)
    return store


def test_init_schema_creates_tables(store) -> None:
    rows = store._conn.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
    ).fetchall()
    found = {r[0] for r in rows}
    assert EXPECTED_TABLES.issubset(found)


def test_load_from_json_row_counts(loaded_store) -> None:
    counts = {
        table: loaded_store._conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for table in ("gebaeude", "einheiten", "eigentuemer", "mieter", "dienstleister")
    }
    assert counts == {
        "gebaeude": 3,
        "einheiten": 52,
        "eigentuemer": 35,
        "mieter": 26,
        "dienstleister": 16,
    }


def test_load_is_idempotent(loaded_store) -> None:
    loaded_store.load_from_json(STAMMDATEN_JSON)
    counts = {
        table: loaded_store._conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for table in ("gebaeude", "einheiten", "eigentuemer", "mieter", "dienstleister")
    }
    assert counts == {
        "gebaeude": 3,
        "einheiten": 52,
        "eigentuemer": 35,
        "mieter": 26,
        "dienstleister": 16,
    }


def test_find_by_id_routes_by_prefix(loaded_store) -> None:
    mieter = loaded_store.find_entity_by_id("MIE-001")
    assert mieter is not None
    assert mieter["role"] == "mieter"
    assert mieter["vorname"] == "Julius"

    eig = loaded_store.find_entity_by_id("EIG-001")
    assert eig is not None
    assert eig["role"] == "eigentuemer"
    assert eig["nachname"] == "Dowerg"

    dl = loaded_store.find_entity_by_id("DL-001")
    assert dl is not None
    assert dl["role"] == "dienstleister"
    assert dl["firma"] == "Hausmeister Mueller GmbH"

    einheit = loaded_store.find_entity_by_id("EH-001")
    assert einheit is not None
    assert einheit["haus_id"] == "HAUS-12"

    assert loaded_store.find_entity_by_id("MIE-999") is None
    assert loaded_store.find_entity_by_id("XYZ-001") is None


def test_find_by_email_case_insensitive(loaded_store) -> None:
    found = loaded_store.find_entity_by_email("JULIUS.NETTE@OUTLOOK.COM")
    assert found is not None
    assert found["id"] == "MIE-001"
    assert found["role"] == "mieter"

    missing = loaded_store.find_entity_by_email("nobody@example.com")
    assert missing is None


def test_find_by_iban_normalizes_spaces(loaded_store) -> None:
    raw_iban = "DE94120300004034471349"
    spaced_iban = "DE94 1203 0000 4034 4713 49"

    direct = loaded_store.find_entity_by_iban(raw_iban)
    assert direct is not None
    assert direct["id"] == "MIE-001"
    assert direct["role"] == "mieter"

    spaced = loaded_store.find_entity_by_iban(spaced_iban)
    assert spaced is not None
    assert spaced["id"] == "MIE-001"

    lower = loaded_store.find_entity_by_iban(raw_iban.lower())
    assert lower is not None
    assert lower["id"] == "MIE-001"
