from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class HealthStatus(BaseModel):
    status: Literal["ok"]
    env: str
    version: str
