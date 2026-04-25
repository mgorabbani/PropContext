from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import duckdb

from app.storage.db import connect

_TABLES: tuple[str, ...] = (
    "liegenschaft",
    "gebaeude",
    "einheiten",
    "eigentuemer",
    "mieter",
    "dienstleister",
)

_SCHEMA_SQL: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS liegenschaft (
        id VARCHAR PRIMARY KEY,
        name VARCHAR,
        strasse VARCHAR,
        plz VARCHAR,
        ort VARCHAR,
        baujahr INTEGER,
        sanierung INTEGER,
        verwalter VARCHAR,
        verwalter_strasse VARCHAR,
        verwalter_plz VARCHAR,
        verwalter_ort VARCHAR,
        verwalter_email VARCHAR,
        verwalter_telefon VARCHAR,
        verwalter_iban VARCHAR,
        verwalter_bic VARCHAR,
        verwalter_bank VARCHAR,
        verwalter_steuernummer VARCHAR,
        weg_bankkonto_iban VARCHAR,
        weg_bankkonto_bic VARCHAR,
        weg_bankkonto_bank VARCHAR,
        ruecklage_iban VARCHAR,
        ruecklage_bic VARCHAR
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS gebaeude (
        id VARCHAR PRIMARY KEY,
        hausnr VARCHAR,
        einheiten INTEGER,
        etagen INTEGER,
        fahrstuhl BOOLEAN,
        baujahr INTEGER
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS einheiten (
        id VARCHAR PRIMARY KEY,
        haus_id VARCHAR,
        einheit_nr VARCHAR,
        lage VARCHAR,
        typ VARCHAR,
        wohnflaeche_qm DOUBLE,
        zimmer DOUBLE,
        miteigentumsanteil INTEGER
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS eigentuemer (
        id VARCHAR PRIMARY KEY,
        anrede VARCHAR,
        vorname VARCHAR,
        nachname VARCHAR,
        firma VARCHAR,
        strasse VARCHAR,
        plz VARCHAR,
        ort VARCHAR,
        land VARCHAR,
        email VARCHAR,
        telefon VARCHAR,
        iban VARCHAR,
        bic VARCHAR,
        einheit_ids VARCHAR[],
        selbstnutzer BOOLEAN,
        sev_mandat BOOLEAN,
        beirat BOOLEAN,
        sprache VARCHAR
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS mieter (
        id VARCHAR PRIMARY KEY,
        anrede VARCHAR,
        vorname VARCHAR,
        nachname VARCHAR,
        email VARCHAR,
        telefon VARCHAR,
        einheit_id VARCHAR,
        eigentuemer_id VARCHAR,
        mietbeginn DATE,
        mietende DATE,
        kaltmiete DOUBLE,
        nk_vorauszahlung DOUBLE,
        kaution DOUBLE,
        iban VARCHAR,
        bic VARCHAR,
        sprache VARCHAR
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS dienstleister (
        id VARCHAR PRIMARY KEY,
        firma VARCHAR,
        branche VARCHAR,
        ansprechpartner VARCHAR,
        email VARCHAR,
        telefon VARCHAR,
        strasse VARCHAR,
        plz VARCHAR,
        ort VARCHAR,
        land VARCHAR,
        iban VARCHAR,
        bic VARCHAR,
        ust_id VARCHAR,
        steuernummer VARCHAR,
        stil VARCHAR,
        sprache VARCHAR,
        vertrag_monatlich DOUBLE,
        stundensatz DOUBLE
    )
    """,
)

_INDEX_SQL: tuple[str, ...] = (
    "CREATE INDEX IF NOT EXISTS idx_eigentuemer_email ON eigentuemer(email)",
    "CREATE INDEX IF NOT EXISTS idx_eigentuemer_iban ON eigentuemer(iban)",
    "CREATE INDEX IF NOT EXISTS idx_mieter_email ON mieter(email)",
    "CREATE INDEX IF NOT EXISTS idx_mieter_iban ON mieter(iban)",
    "CREATE INDEX IF NOT EXISTS idx_dienstleister_email ON dienstleister(email)",
    "CREATE INDEX IF NOT EXISTS idx_dienstleister_iban ON dienstleister(iban)",
    "CREATE INDEX IF NOT EXISTS idx_einheiten_haus ON einheiten(haus_id)",
    "CREATE INDEX IF NOT EXISTS idx_mieter_einheit ON mieter(einheit_id)",
)

_ID_PREFIX_TO_TABLE: dict[str, str] = {
    "MIE": "mieter",
    "EIG": "eigentuemer",
    "DL": "dienstleister",
    "EH": "einheiten",
    "HAUS": "gebaeude",
    "LIE": "liegenschaft",
}

_TABLE_TO_ROLE: dict[str, str] = {
    "mieter": "mieter",
    "eigentuemer": "eigentuemer",
    "dienstleister": "dienstleister",
}


def _normalize_iban(value: str | None) -> str | None:
    if value is None:
        return None
    return value.replace(" ", "").upper()


def _row_to_dict(
    conn: duckdb.DuckDBPyConnection, table: str, row: tuple[Any, ...]
) -> dict[str, Any]:
    columns = [c[0] for c in conn.execute(f"DESCRIBE {table}").fetchall()]
    return dict(zip(columns, row, strict=False))


class StammdatenStore:
    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        self._conn = conn

    def init_schema(self) -> None:
        for stmt in _SCHEMA_SQL:
            self._conn.execute(stmt)
        for stmt in _INDEX_SQL:
            self._conn.execute(stmt)

    def load_from_json(self, json_path: Path) -> None:
        payload = json.loads(json_path.read_text(encoding="utf-8"))

        for table in _TABLES:
            self._conn.execute(f"DELETE FROM {table}")  # noqa: S608

        liegenschaft = payload.get("liegenschaft")
        if liegenschaft:
            self._insert_liegenschaft(liegenschaft)

        for row in payload.get("gebaeude", []):
            self._insert_gebaeude(row)

        for row in payload.get("einheiten", []):
            self._insert_einheit(row)

        for row in payload.get("eigentuemer", []):
            self._insert_eigentuemer(row)

        for row in payload.get("mieter", []):
            self._insert_mieter(row)

        for row in payload.get("dienstleister", []):
            self._insert_dienstleister(row)

    def find_entity_by_email(self, email: str) -> dict[str, Any] | None:
        needle = email.strip().lower()
        for table in ("mieter", "eigentuemer", "dienstleister"):
            row = self._conn.execute(
                f"SELECT * FROM {table} WHERE LOWER(email) = ?",  # noqa: S608
                [needle],
            ).fetchone()
            if row is not None:
                return self._enrich(table, row)
        return None

    def find_entity_by_iban(self, iban: str) -> dict[str, Any] | None:
        needle = _normalize_iban(iban)
        if needle is None:
            return None
        for table in ("mieter", "eigentuemer", "dienstleister"):
            row = self._conn.execute(
                f"SELECT * FROM {table} WHERE iban = ?",  # noqa: S608
                [needle],
            ).fetchone()
            if row is not None:
                return self._enrich(table, row)
        return None

    def find_entity_by_id(self, entity_id: str) -> dict[str, Any] | None:
        if not entity_id or "-" not in entity_id:
            return None
        prefix = entity_id.split("-", 1)[0].upper()
        table = _ID_PREFIX_TO_TABLE.get(prefix)
        if table is None:
            return None
        row = self._conn.execute(
            f"SELECT * FROM {table} WHERE id = ?",  # noqa: S608
            [entity_id],
        ).fetchone()
        if row is None:
            return None
        return self._enrich(table, row)

    def _enrich(self, table: str, row: tuple[Any, ...]) -> dict[str, Any]:
        data = _row_to_dict(self._conn, table, row)
        role = _TABLE_TO_ROLE.get(table)
        if role is not None:
            data["role"] = role
        return data

    def _insert_liegenschaft(self, row: dict[str, Any]) -> None:
        self._conn.execute(
            """
            INSERT INTO liegenschaft (
                id, name, strasse, plz, ort, baujahr, sanierung, verwalter,
                verwalter_strasse, verwalter_plz, verwalter_ort, verwalter_email,
                verwalter_telefon, verwalter_iban, verwalter_bic, verwalter_bank,
                verwalter_steuernummer, weg_bankkonto_iban, weg_bankkonto_bic,
                weg_bankkonto_bank, ruecklage_iban, ruecklage_bic
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                row.get("id"),
                row.get("name"),
                row.get("strasse"),
                row.get("plz"),
                row.get("ort"),
                row.get("baujahr"),
                row.get("sanierung"),
                row.get("verwalter"),
                row.get("verwalter_strasse"),
                row.get("verwalter_plz"),
                row.get("verwalter_ort"),
                row.get("verwalter_email"),
                row.get("verwalter_telefon"),
                _normalize_iban(row.get("verwalter_iban")),
                row.get("verwalter_bic"),
                row.get("verwalter_bank"),
                row.get("verwalter_steuernummer"),
                _normalize_iban(row.get("weg_bankkonto_iban")),
                row.get("weg_bankkonto_bic"),
                row.get("weg_bankkonto_bank"),
                _normalize_iban(row.get("ruecklage_iban")),
                row.get("ruecklage_bic"),
            ],
        )

    def _insert_gebaeude(self, row: dict[str, Any]) -> None:
        self._conn.execute(
            """
            INSERT INTO gebaeude (id, hausnr, einheiten, etagen, fahrstuhl, baujahr)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                row.get("id"),
                row.get("hausnr"),
                row.get("einheiten"),
                row.get("etagen"),
                row.get("fahrstuhl"),
                row.get("baujahr"),
            ],
        )

    def _insert_einheit(self, row: dict[str, Any]) -> None:
        self._conn.execute(
            """
            INSERT INTO einheiten (
                id, haus_id, einheit_nr, lage, typ, wohnflaeche_qm, zimmer, miteigentumsanteil
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                row.get("id"),
                row.get("haus_id"),
                row.get("einheit_nr"),
                row.get("lage"),
                row.get("typ"),
                row.get("wohnflaeche_qm"),
                row.get("zimmer"),
                row.get("miteigentumsanteil"),
            ],
        )

    def _insert_eigentuemer(self, row: dict[str, Any]) -> None:
        self._conn.execute(
            """
            INSERT INTO eigentuemer (
                id, anrede, vorname, nachname, firma, strasse, plz, ort, land,
                email, telefon, iban, bic, einheit_ids, selbstnutzer, sev_mandat,
                beirat, sprache
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                row.get("id"),
                row.get("anrede"),
                row.get("vorname"),
                row.get("nachname"),
                row.get("firma"),
                row.get("strasse"),
                row.get("plz"),
                row.get("ort"),
                row.get("land"),
                row.get("email"),
                row.get("telefon"),
                _normalize_iban(row.get("iban")),
                row.get("bic"),
                list(row.get("einheit_ids") or []),
                row.get("selbstnutzer"),
                row.get("sev_mandat"),
                row.get("beirat"),
                row.get("sprache"),
            ],
        )

    def _insert_mieter(self, row: dict[str, Any]) -> None:
        self._conn.execute(
            """
            INSERT INTO mieter (
                id, anrede, vorname, nachname, email, telefon, einheit_id,
                eigentuemer_id, mietbeginn, mietende, kaltmiete, nk_vorauszahlung,
                kaution, iban, bic, sprache
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                row.get("id"),
                row.get("anrede"),
                row.get("vorname"),
                row.get("nachname"),
                row.get("email"),
                row.get("telefon"),
                row.get("einheit_id"),
                row.get("eigentuemer_id"),
                row.get("mietbeginn"),
                row.get("mietende"),
                row.get("kaltmiete"),
                row.get("nk_vorauszahlung"),
                row.get("kaution"),
                _normalize_iban(row.get("iban")),
                row.get("bic"),
                row.get("sprache"),
            ],
        )

    def _insert_dienstleister(self, row: dict[str, Any]) -> None:
        self._conn.execute(
            """
            INSERT INTO dienstleister (
                id, firma, branche, ansprechpartner, email, telefon, strasse,
                plz, ort, land, iban, bic, ust_id, steuernummer, stil, sprache,
                vertrag_monatlich, stundensatz
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                row.get("id"),
                row.get("firma"),
                row.get("branche"),
                row.get("ansprechpartner"),
                row.get("email"),
                row.get("telefon"),
                row.get("strasse"),
                row.get("plz"),
                row.get("ort"),
                row.get("land"),
                _normalize_iban(row.get("iban")),
                row.get("bic"),
                row.get("ust_id"),
                row.get("steuernummer"),
                row.get("stil"),
                row.get("sprache"),
                row.get("vertrag_monatlich"),
                row.get("stundensatz"),
            ],
        )


def open_stammdaten(db_path: Path) -> StammdatenStore:
    conn = connect(db_path)
    store = StammdatenStore(conn)
    store.init_schema()
    return store
