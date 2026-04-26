from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import ValidationError

from app.core.config import Settings, get_settings
from app.schemas.webhook import IngestEvent, IngestResponse
from app.services.events import EventBroker, IngestPulse, get_event_broker
from app.services.supervisor import Supervisor, get_supervisor
from app.storage.idempotency import open_idempotency

router = APIRouter()
log = structlog.get_logger(__name__)


@router.post("/ingest", response_model=IngestResponse)
async def ingest_webhook(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    supervisor: Annotated[Supervisor, Depends(get_supervisor)],
    broker: Annotated[EventBroker, Depends(get_event_broker)],
) -> IngestResponse:
    raw_body = await request.body()
    _verify_hmac(raw_body, request=request, settings=settings)
    event = _parse_event(raw_body)
    event = _validate_source_path(event, settings=settings)

    store = open_idempotency(settings.output_dir / "idempotency.duckdb")
    if not store.claim(event.event_id):
        return IngestResponse(event_id=event.event_id, status="duplicate", idempotent=True)

    try:
        result = await supervisor.handle(event)
    except HTTPException:
        store.mark_failed(event.event_id)
        supervisor.record_failed_event(event, "http_exception")
        raise
    except Exception as exc:
        store.mark_failed(event.event_id)
        supervisor.record_failed_event(event, type(exc).__name__)
        log.exception("ingest_failed", event_id=event.event_id, event_type=event.event_type)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ingest failed",
        ) from exc

    store.mark_done(event.event_id)
    patch = result.patch
    response = IngestResponse(
        event_id=event.event_id,
        status=result.status,
        applied_ops=patch.applied_ops if patch is not None else 0,
        commit_sha=patch.commit_sha if patch is not None else None,
        idempotent=patch.idempotent if patch is not None else False,
    )
    await broker.publish(
        IngestPulse(
            event_id=event.event_id,
            property_id=event.property_id,
            event_type=event.event_type,
            status=result.status,
            applied_ops=response.applied_ops,
            commit_sha=response.commit_sha,
        )
    )
    return response


def _verify_hmac(raw_body: bytes, *, request: Request, settings: Settings) -> None:
    if settings.webhook_hmac_secret is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "webhook secret is not configured")
    signature = (
        request.headers.get("x-buena-signature")
        or request.headers.get("x-hub-signature-256")
        or request.headers.get("x-signature")
    )
    if not signature:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing webhook signature")
    expected = hmac.new(
        settings.webhook_hmac_secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    received = signature.removeprefix("sha256=").strip()
    if not hmac.compare_digest(expected, received):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "bad webhook signature")


def _parse_event(raw_body: bytes) -> IngestEvent:
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "invalid JSON body") from exc
    try:
        return IngestEvent.model_validate(payload)
    except ValidationError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "invalid ingest event") from exc


def _validate_source_path(event: IngestEvent, *, settings: Settings) -> IngestEvent:
    if event.source_path is None:
        return event

    resolved = _resolve_allowed_source_path(event.source_path, data_dir=settings.data_dir)
    if resolved is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "source_path is outside data_dir"
        )
    return event.model_copy(update={"source_path": resolved})


def _resolve_allowed_source_path(source_path: Path, *, data_dir: Path) -> Path | None:
    data_root = data_dir.resolve(strict=False)
    candidates = (
        [source_path]
        if source_path.is_absolute()
        else [Path.cwd() / source_path, data_dir / source_path]
    )
    for candidate in candidates:
        resolved = candidate.resolve(strict=False)
        if resolved.is_relative_to(data_root):
            return resolved
    return None
