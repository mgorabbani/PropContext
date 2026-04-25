from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from app.storage.bank import open_bank

REPO_ROOT = Path(__file__).resolve().parents[2]
BANK_CSV = REPO_ROOT / "data" / "bank" / "bank_index.csv"


def test_init_schema_creates_table(tmp_path: Path) -> None:
    store = open_bank(tmp_path / "bank.duckdb")
    rows = store._conn.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_name = 'bank_tx'"
    ).fetchall()
    assert rows == [("bank_tx",)]


def test_load_from_csv_loads_real_fixture(tmp_path: Path) -> None:
    store = open_bank(tmp_path / "bank.duckdb")
    store.load_from_csv(BANK_CSV)
    count = store._conn.execute("SELECT COUNT(*) FROM bank_tx").fetchone()
    assert count is not None
    assert count[0] == 1619


def test_load_is_idempotent(tmp_path: Path) -> None:
    store = open_bank(tmp_path / "bank.duckdb")
    store.load_from_csv(BANK_CSV)
    store.load_from_csv(BANK_CSV)
    count = store._conn.execute("SELECT COUNT(*) FROM bank_tx").fetchone()
    assert count is not None
    assert count[0] == 1619


def test_find_by_referenz(tmp_path: Path) -> None:
    store = open_bank(tmp_path / "bank.duckdb")
    store.load_from_csv(BANK_CSV)
    results = store.find_by_referenz("MIE-006")
    assert len(results) >= 1
    assert any(row["id"] == "TX-00001" for row in results)
    assert all(row["referenz_id"] == "MIE-006" for row in results)


def test_find_by_id(tmp_path: Path) -> None:
    store = open_bank(tmp_path / "bank.duckdb")
    store.load_from_csv(BANK_CSV)
    row = store.find_by_id("TX-00001")
    assert row is not None
    assert row["kategorie"] == "miete"
    assert Decimal(str(row["betrag"])) == Decimal("1256.00")
