from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class HealthStatus(BaseModel):
    status: Literal["ok"]
    env: Literal["dev", "staging", "prod"]
    version: str
