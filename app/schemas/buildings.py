from __future__ import annotations

from typing import Annotated

from pydantic import StringConstraints

BuildingId = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_-]{1,64}$")]
