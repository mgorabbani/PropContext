from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class IngestPulse:
    event_id: str
    property_id: str
    event_type: str
    status: str
    applied_ops: int
    commit_sha: str | None

    def to_payload(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "property_id": self.property_id,
            "event_type": self.event_type,
            "status": self.status,
            "applied_ops": self.applied_ops,
            "commit_sha": self.commit_sha,
        }


@dataclass
class Subscription:
    queue: asyncio.Queue[IngestPulse]
    property_id: str | None = None


class EventBroker:
    """Process-local in-memory pub/sub for ingest pulses.

    One asyncio.Queue per Subscription. Slow consumers do not block publishers;
    on overflow the oldest pulse for that subscription is dropped.
    """

    def __init__(self, *, max_queue: int = 256) -> None:
        self._subs: list[Subscription] = []
        self._max_queue = max_queue

    def register(self, *, property_id: str | None = None) -> Subscription:
        sub = Subscription(queue=asyncio.Queue(maxsize=self._max_queue), property_id=property_id)
        self._subs.append(sub)
        return sub

    def unregister(self, sub: Subscription) -> None:
        with contextlib.suppress(ValueError):
            self._subs.remove(sub)

    async def publish(self, pulse: IngestPulse) -> None:
        for sub in list(self._subs):
            if sub.property_id is not None and sub.property_id != pulse.property_id:
                continue
            try:
                sub.queue.put_nowait(pulse)
            except asyncio.QueueFull:
                with contextlib.suppress(asyncio.QueueEmpty):
                    sub.queue.get_nowait()
                with contextlib.suppress(asyncio.QueueFull):
                    sub.queue.put_nowait(pulse)


class _BrokerSingleton:
    instance: EventBroker | None = None


def get_event_broker() -> EventBroker:
    if _BrokerSingleton.instance is None:
        _BrokerSingleton.instance = EventBroker()
    return _BrokerSingleton.instance


def reset_event_broker() -> None:
    _BrokerSingleton.instance = None
