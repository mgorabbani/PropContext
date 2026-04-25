from __future__ import annotations

from datetime import date
from pathlib import Path

from app.storage.invoices import open_invoices


def _seed_fixture(tmp_path: Path) -> Path:
    base = tmp_path / "rechnungen" / "2024-01"
    base.mkdir(parents=True)
    (base / "20240101_DL-001_INV-00001.pdf").touch()
    (base / "20240115_DL-003_INV-00002.pdf").touch()
    return tmp_path / "rechnungen"


def test_init_schema_creates_table(tmp_path: Path) -> None:
    store = open_invoices(tmp_path / "inv.duckdb")
    rows = store._conn.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_name = 'invoices'"
    ).fetchall()
    assert rows == [("invoices",)]


def test_index_directory_against_fixture_subset(tmp_path: Path) -> None:
    rechnungen_dir = _seed_fixture(tmp_path)
    store = open_invoices(tmp_path / "inv.duckdb")
    n = store.index_directory(rechnungen_dir)
    assert n == 2


def test_index_directory_idempotent(tmp_path: Path) -> None:
    rechnungen_dir = _seed_fixture(tmp_path)
    store = open_invoices(tmp_path / "inv.duckdb")
    store.index_directory(rechnungen_dir)
    store.index_directory(rechnungen_dir)
    count = store._conn.execute("SELECT COUNT(*) FROM invoices").fetchone()
    assert count is not None
    assert count[0] == 2


def test_find_by_id_and_by_dienstleister(tmp_path: Path) -> None:
    rechnungen_dir = _seed_fixture(tmp_path)
    store = open_invoices(tmp_path / "inv.duckdb")
    store.index_directory(rechnungen_dir)

    row = store.find_by_id("INV-00001")
    assert row is not None
    assert row["dl_id"] == "DL-001"
    assert row["datum"] == date(2024, 1, 1)

    by_dl = store.find_by_dienstleister("DL-001")
    assert len(by_dl) == 1
    assert by_dl[0]["id"] == "INV-00001"
