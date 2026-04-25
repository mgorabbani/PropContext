from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from httpx import ASGITransport, AsyncClient

from app.core.config import Settings, get_settings
from app.main import app
from app.schemas.webhook import IngestEvent
from app.services.patcher.apply import PatchApplyResult
from app.services.supervisor import SupervisorResult, get_supervisor
from app.tools.backfill import backfill, iter_archive_events


@dataclass
class CapturingSupervisor:
    seen: list[IngestEvent] = field(default_factory=list)

    async def handle(self, event: IngestEvent) -> SupervisorResult:
        self.seen.append(event)
        return SupervisorResult(
            event.event_id,
            "applied",
            None,
            PatchApplyResult(event.event_id, 0, 0, "deadbeef"),
        )

    def record_failed_event(self, event: IngestEvent, reason: str) -> None:
        return None


def _build_archive(tmp_path: Path) -> Path:
    root = tmp_path / "archive"
    (root / "emails" / "2024-01").mkdir(parents=True)
    (root / "emails" / "2024-02").mkdir(parents=True)
    (root / "rechnungen" / "2024-01").mkdir(parents=True)
    (root / "bank").mkdir(parents=True)

    (root / "emails" / "2024-01" / "20240105_101600_EMAIL-00001.eml").write_text("a", "utf-8")
    (root / "emails" / "2024-01" / "20240115_111900_EMAIL-00002.eml").write_text("b", "utf-8")
    (root / "emails" / "2024-02" / "20240210_120000_EMAIL-00003.eml").write_text("c", "utf-8")
    (root / "rechnungen" / "2024-01" / "20240120_DL-001_INV-00001.pdf").write_bytes(b"%PDF-fake")

    with (root / "bank" / "bank_index.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "datum", "typ", "betrag", "referenz_id"])
        w.writerow(["TX-00001", "2024-01-25", "DEBIT", "100.00", "INV-00001"])
        w.writerow(["TX-00002", "2024-02-15", "CREDIT", "200.00", ""])

    return root


def test_iter_archive_events_orders_chronologically(tmp_path: Path) -> None:
    root = _build_archive(tmp_path)

    ids = [e.event_id for e in iter_archive_events(root)]

    assert ids == [
        "EMAIL-00001",
        "EMAIL-00002",
        "INV-00001",
        "TX-00001",
        "EMAIL-00003",
        "TX-00002",
    ]


def test_iter_archive_events_filters_by_window(tmp_path: Path) -> None:
    root = _build_archive(tmp_path)

    ids = [
        e.event_id for e in iter_archive_events(root, start=date(2024, 2, 1), end=date(2024, 2, 28))
    ]

    assert ids == ["EMAIL-00003", "TX-00002"]


async def test_backfill_limit_caps_posts(tmp_path: Path, settings: Settings) -> None:
    root = _build_archive(tmp_path)
    settings.webhook_hmac_secret = "shh"
    spy = CapturingSupervisor()
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_supervisor] = lambda: spy
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            responses = await backfill(client, root, secret="shh", limit=3)
    finally:
        app.dependency_overrides.clear()

    assert len(responses) == 3
    assert [e.event_id for e in spy.seen] == [
        "EMAIL-00001",
        "EMAIL-00002",
        "INV-00001",
    ]


async def test_backfill_chronological_order(tmp_path: Path, settings: Settings) -> None:
    root = _build_archive(tmp_path)
    settings.webhook_hmac_secret = "shh"
    spy = CapturingSupervisor()
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_supervisor] = lambda: spy
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            responses = await backfill(client, root, secret="shh", limit=10)
    finally:
        app.dependency_overrides.clear()

    assert all(r.status_code == 200 for r in responses)
    assert [e.event_id for e in spy.seen] == [
        "EMAIL-00001",
        "EMAIL-00002",
        "INV-00001",
        "TX-00001",
        "EMAIL-00003",
        "TX-00002",
    ]
