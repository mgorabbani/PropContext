from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass

from httpx import AsyncClient

from app.core.config import Settings
from app.main import app
from app.schemas.webhook import IngestEvent
from app.services.patcher.apply import PatchApplyResult
from app.services.supervisor import SupervisorResult, get_supervisor


@dataclass
class DummySupervisor:
    calls: int = 0

    async def handle(self, event: IngestEvent) -> SupervisorResult:
        self.calls += 1
        return SupervisorResult(
            event.event_id,
            "applied",
            None,
            PatchApplyResult(
                event_id=event.event_id,
                applied_ops=0,
                commit_sha="deadbeef",
                touched=(),
            ),
        )

    def record_failed_event(self, event: IngestEvent, reason: str) -> None:
        self.calls += 1


def _signed(body: bytes, secret: str) -> dict[str, str]:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return {"x-buena-signature": f"sha256={digest}", "content-type": "application/json"}


def _body(event_id: str = "EVT-001") -> bytes:
    return json.dumps(
        {"event_id": event_id, "event_type": "manual", "property_id": "LIE-001", "payload": {}},
        separators=(",", ":"),
    ).encode("utf-8")


async def test_webhook_rejects_missing_signature(
    client: AsyncClient,
    settings: Settings,
) -> None:
    settings.webhook_hmac_secret = "secret"

    response = await client.post("/api/v1/webhook/ingest", content=_body())

    assert response.status_code == 401


async def test_webhook_rejects_bad_signature(client: AsyncClient, settings: Settings) -> None:
    settings.webhook_hmac_secret = "secret"

    response = await client.post(
        "/api/v1/webhook/ingest",
        content=_body(),
        headers={"x-buena-signature": "sha256=bad"},
    )

    assert response.status_code == 401


async def test_webhook_rejects_invalid_event_body(client: AsyncClient, settings: Settings) -> None:
    secret = "secret"
    settings.webhook_hmac_secret = secret
    body = json.dumps(
        {"event_type": "manual", "property_id": "LIE-001", "payload": {}},
        separators=(",", ":"),
    ).encode("utf-8")

    response = await client.post(
        "/api/v1/webhook/ingest", content=body, headers=_signed(body, secret)
    )

    assert response.status_code == 422


async def test_webhook_rejects_bad_property_id(client: AsyncClient, settings: Settings) -> None:
    secret = "secret"
    settings.webhook_hmac_secret = secret
    body = json.dumps(
        {"event_id": "EVT-BAD", "event_type": "manual", "property_id": "../escape", "payload": {}},
        separators=(",", ":"),
    ).encode("utf-8")

    response = await client.post(
        "/api/v1/webhook/ingest", content=body, headers=_signed(body, secret)
    )

    assert response.status_code == 422


async def test_webhook_rejects_source_path_outside_data_dir(
    client: AsyncClient,
    settings: Settings,
) -> None:
    secret = "secret"
    settings.webhook_hmac_secret = secret
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    body = json.dumps(
        {
            "event_id": "EVT-SOURCE",
            "event_type": "manual",
            "property_id": "LIE-001",
            "source_path": "/etc/passwd",
            "payload": {},
        },
        separators=(",", ":"),
    ).encode("utf-8")

    response = await client.post(
        "/api/v1/webhook/ingest", content=body, headers=_signed(body, secret)
    )

    assert response.status_code == 422


async def test_webhook_replay_is_idempotent(client: AsyncClient, settings: Settings) -> None:
    secret = "secret"
    settings.webhook_hmac_secret = secret
    supervisor = DummySupervisor()
    app.dependency_overrides[get_supervisor] = lambda: supervisor
    body = _body("EVT-REPLAY")
    headers = _signed(body, secret)

    first = await client.post("/api/v1/webhook/ingest", content=body, headers=headers)
    second = await client.post("/api/v1/webhook/ingest", content=body, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["idempotent"] is True
    assert supervisor.calls == 1
