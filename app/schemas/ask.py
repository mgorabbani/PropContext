from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.properties import PropertyId


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    lie: PropertyId
    pin: bool = False


class AskResponse(BaseModel):
    answer: str | None = None
    path: str | None = None
    pinned_path: str | None = None
