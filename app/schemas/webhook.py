from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

from pydantic import BaseModel, Field, StringConstraints

from app.schemas.properties import PropertyId

EventId = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$",
    ),
]
EventType = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=32,
        pattern=r"^[a-z][a-z0-9_-]*$",
    ),
]


class IngestEvent(BaseModel):
    event_id: EventId
    event_type: EventType
    property_id: PropertyId = "LIE-001"
    source_path: Path | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class IngestResponse(BaseModel):
    event_id: str
    status: str
    applied_ops: int = 0
    commit_sha: str | None = None
    idempotent: bool = False
