from __future__ import annotations

import asyncio
import json

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.events import _format_sse, _sse_generator
from app.core.config import Settings, get_settings
from app.main import app
from app.services.events import (
    EventBroker,
    IngestPulse,
    get_event_broker,
    reset_event_broker,
)


@pytest.fixture(autouse=True)
def fresh_broker():
    reset_event_broker()
    yield
    reset_event_broker()


def _pulse(event_id: str, property_id: str = "LIE-001") -> IngestPulse:
    return IngestPulse(
        event_id=event_id,
        property_id=property_id,
        event_type="email",
        status="applied",
        applied_ops=1,
        commit_sha="abc1234",
    )


def test_sse_format_roundtrips() -> None:
    framed = _format_sse(_pulse("EVT-1"))
    assert framed.startswith("event: ingest\ndata: ")
    assert framed.endswith("\n\n")
    payload = json.loads(framed.split("\n")[1].removeprefix("data: "))
    assert payload["event_id"] == "EVT-1"
    assert payload["status"] == "applied"


async def test_broker_delivers_to_registered_subscriber() -> None:
    broker = EventBroker()
    sub = broker.register()
    await broker.publish(_pulse("EVT-1"))
    pulse = await asyncio.wait_for(sub.queue.get(), timeout=1.0)
    assert pulse.event_id == "EVT-1"
    broker.unregister(sub)


async def test_broker_filters_by_property() -> None:
    broker = EventBroker()
    sub = broker.register(property_id="LIE-002")
    await broker.publish(_pulse("EVT-A", property_id="LIE-001"))
    await broker.publish(_pulse("EVT-B", property_id="LIE-002"))
    pulse = await asyncio.wait_for(sub.queue.get(), timeout=1.0)
    assert pulse.event_id == "EVT-B"
    assert sub.queue.empty()
    broker.unregister(sub)


async def test_broker_drops_oldest_on_overflow() -> None:
    broker = EventBroker(max_queue=2)
    sub = broker.register()
    await broker.publish(_pulse("EVT-1"))
    await broker.publish(_pulse("EVT-2"))
    await broker.publish(_pulse("EVT-3"))
    drained = []
    while not sub.queue.empty():
        drained.append(sub.queue.get_nowait().event_id)
    assert drained == ["EVT-2", "EVT-3"]
    broker.unregister(sub)


async def test_sse_generator_unregisters_on_close() -> None:
    broker = EventBroker()
    sub = broker.register()
    gen = _sse_generator(broker, sub)
    await broker.publish(_pulse("EVT-1"))
    chunk = await asyncio.wait_for(anext(gen), timeout=1.0)
    assert "EVT-1" in chunk
    await gen.aclose()
    assert sub not in broker._subs


async def test_events_endpoint_validates_property_id(settings: Settings) -> None:
    broker = EventBroker()
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_event_broker] = lambda: broker
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/events", params={"property_id": "../etc/passwd"})
            assert resp.status_code == 422
    finally:
        app.dependency_overrides.clear()
