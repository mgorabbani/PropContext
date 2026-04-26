from __future__ import annotations

import json
import re
from typing import Any

import json_repair
import structlog

log = structlog.get_logger(__name__)


def parse_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        candidate = _largest_brace_block(cleaned) or cleaned
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError as exc:
            log.warning(
                "json_strict_parse_failed",
                err=str(exc),
                preview=candidate[:400],
            )
            repaired = json_repair.loads(candidate)
            if isinstance(repaired, list):
                log.warning("json_repair_returned_list_wrapping_ops", count=len(repaired))
                value = {"ops": repaired}
            elif isinstance(repaired, dict):
                value = repaired
            else:
                log.error(
                    "json_repair_unusable",
                    type=type(repaired).__name__,
                    raw_preview=cleaned[:1000],
                )
                raise ValueError(
                    f"json_repair returned {type(repaired).__name__}, "
                    f"raw head: {cleaned[:200]!r}"
                ) from exc
    if not isinstance(value, dict):
        raise ValueError("expected JSON object")
    return value


def _largest_brace_block(text: str) -> str | None:
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        return None
    return text[start : end + 1]
