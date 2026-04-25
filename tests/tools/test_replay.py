from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

from httpx import ASGITransport, AsyncClient

from app.core.config import Settings, get_settings
from app.main import app
from app.schemas.webhook import IngestEvent
from app.services.patcher.apply import PatchApplyResult
from app.services.supervisor import SupervisorResult, get_supervisor
from app.tools.replay import iter_day_events, replay_day


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


def _build_day(tmp_path: Path) -> Path:
    day = tmp_path / "day-01"
    (day / "emails" / "2026-01").mkdir(parents=True)
    (day / "rechnungen" / "2026-01").mkdir(parents=True)
    (day / "bank").mkdir(parents=True)

    (day / "emails" / "2026-01" / "20260101_083800_EMAIL-06547.eml").write_text(
        "Subject: hi\n\nbody\n", encoding="utf-8"
    )
    (day / "emails" / "2026-01" / "20260102_103800_EMAIL-06550.eml").write_text(
        "Subject: re\n\nbody\n", encoding="utf-8"
    )
    (day / "rechnungen" / "2026-01" / "20260101_DL-001_INV-00195.pdf").write_bytes(b"%PDF-fake")

    with (day / "emails_index.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            ["id", "datetime", "thread_id", "from_email", "category", "filename", "month_dir"]
        )
        writer.writerow(
            [
                "EMAIL-06547",
                "2026-01-01T08:38:00",
                "T1",
                "x@y",
                "mieter/heizung",
                "20260101_083800_EMAIL-06547.eml",
                "2026-01",
            ]
        )
        writer.writerow(
            [
                "EMAIL-06550",
                "2026-01-02T10:38:00",
                "T1",
                "x@y",
                "mieter/heizung",
                "20260102_103800_EMAIL-06550.eml",
                "2026-01",
            ]
        )

    with (day / "rechnungen_index.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            ["id", "rechnungsnr", "datum", "dienstleister_id", "brutto", "filename", "month_dir"]
        )
        writer.writerow(
            [
                "INV-00195",
                "INV-2026-0195",
                "2026-01-01",
                "DL-001",
                "1088.85",
                "20260101_DL-001_INV-00195.pdf",
                "2026-01",
            ]
        )

    with (day / "bank" / "bank_index.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["id", "datum", "typ", "betrag", "referenz_id"])
        writer.writerow(["TX-01620", "2026-01-06", "DEBIT", "1088.85", "INV-00195"])

    return day


def test_iter_day_events_chronological(tmp_path: Path) -> None:
    day = _build_day(tmp_path)

    events = list(iter_day_events(day))
    ids = [e.event_id for e in events]

    assert ids == ["EMAIL-06547", "INV-00195", "EMAIL-06550", "TX-01620"]
    types = [e.event_type for e in events]
    assert types == ["email", "invoice", "email", "bank"]


def test_iter_day_events_attaches_source_paths(tmp_path: Path) -> None:
    day = _build_day(tmp_path)

    by_type = {e.event_type: e for e in iter_day_events(day)}

    assert by_type["email"].source_path is not None
    assert by_type["email"].source_path.is_file()
    assert by_type["invoice"].source_path is not None
    assert by_type["invoice"].source_path.is_file()
    assert by_type["bank"].payload["row"]["referenz_id"] == "INV-00195"


async def test_replay_day_signs_and_posts(tmp_path: Path, settings: Settings) -> None:
    day = _build_day(tmp_path)
    secret = "shh"
    settings.webhook_hmac_secret = secret
    spy = CapturingSupervisor()
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_supervisor] = lambda: spy
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            responses = await replay_day(client, day, secret=secret)
    finally:
        app.dependency_overrides.clear()

    assert [r.status_code for r in responses] == [200, 200, 200, 200]
    assert [e.event_id for e in spy.seen] == [
        "EMAIL-06547",
        "INV-00195",
        "EMAIL-06550",
        "TX-01620",
    ]


async def test_replay_day_rejects_when_secret_mismatches(
    tmp_path: Path, settings: Settings
) -> None:
    day = _build_day(tmp_path)
    settings.webhook_hmac_secret = "right"
    app.dependency_overrides[get_settings] = lambda: settings
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            responses = await replay_day(client, day, secret="wrong")
    finally:
        app.dependency_overrides.clear()

    assert all(r.status_code == 401 for r in responses)


async def test_replay_day_limit(tmp_path: Path, settings: Settings) -> None:
    day = _build_day(tmp_path)
    settings.webhook_hmac_secret = "shh"
    spy = CapturingSupervisor()
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_supervisor] = lambda: spy
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            responses = await replay_day(client, day, secret="shh", limit=2)
    finally:
        app.dependency_overrides.clear()

    assert len(responses) == 2
    assert len(spy.seen) == 2
