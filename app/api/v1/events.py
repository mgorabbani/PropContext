from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import StringConstraints

from app.services.events import EventBroker, IngestPulse, Subscription, get_event_broker

router = APIRouter()
log = structlog.get_logger(__name__)

PropertyId = Annotated[str, StringConstraints(pattern=r"^LIE-\d{3,}$", max_length=32)]


@router.get("/events")
async def stream_events(
    broker: Annotated[EventBroker, Depends(get_event_broker)],
    property_id: Annotated[PropertyId | None, Query()] = None,
) -> StreamingResponse:
    subscription = broker.register(property_id=property_id)
    return StreamingResponse(
        _sse_generator(broker, subscription),
        media_type="text/event-stream",
        headers={
            "cache-control": "no-cache",
            "connection": "keep-alive",
            "x-accel-buffering": "no",
        },
    )


async def _sse_generator(
    broker: EventBroker,
    subscription: Subscription,
) -> AsyncGenerator[str]:
    try:
        while True:
            pulse = await subscription.queue.get()
            yield _format_sse(pulse)
    finally:
        broker.unregister(subscription)


def _format_sse(pulse: IngestPulse) -> str:
    payload = json.dumps(pulse.to_payload(), separators=(",", ":"))
    return f"event: ingest\ndata: {payload}\n\n"
