from __future__ import annotations

from typing import Annotated

from pydantic import StringConstraints

PropertyId = Annotated[str, StringConstraints(pattern=r"^LIE-\d{3}$")]
