from __future__ import annotations

import json
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import structlog

log = structlog.get_logger(__name__)

FEEDBACK_FILENAME = "_hermes_feedback.jsonl"


@dataclass(frozen=True, slots=True)
class FeedbackRecord:
    """One ingest row from `_hermes_feedback.jsonl`."""

    kind: str
    ts: str
    event_id: str
    event_type: str
    property_id: str
    summary: str
    applied_ops: int
    deferred_ops: int
    touched: tuple[str, ...] = field(default_factory=tuple)
    extra: dict[str, object] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, row: dict[str, object]) -> FeedbackRecord:
        known = {
            "kind",
            "ts",
            "event_id",
            "event_type",
            "property_id",
            "summary",
            "applied_ops",
            "deferred_ops",
            "touched",
        }
        extra = {k: v for k, v in row.items() if k not in known}
        touched_raw = row.get("touched") or ()
        touched = (
            tuple(str(t) for t in touched_raw) if isinstance(touched_raw, list | tuple) else ()
        )
        return cls(
            kind=str(row.get("kind", "ingest")),
            ts=str(row.get("ts", "")),
            event_id=str(row.get("event_id", "")),
            event_type=str(row.get("event_type", "")),
            property_id=str(row.get("property_id", "")),
            summary=str(row.get("summary", "")),
            applied_ops=_coerce_int(row.get("applied_ops")),
            deferred_ops=_coerce_int(row.get("deferred_ops")),
            touched=touched,
            extra=extra,
        )


def feedback_path(property_root: Path) -> Path:
    return property_root / FEEDBACK_FILENAME


def append_feedback(
    property_root: Path,
    *,
    event_id: str,
    event_type: str,
    property_id: str,
    summary: str,
    applied_ops: int,
    deferred_ops: int = 0,
    touched: Iterable[str] = (),
    kind: str = "ingest",
) -> bool:
    """Append one JSONL line to `_hermes_feedback.jsonl`.

    Idempotent on `event_id`: returns False without writing if a line with the
    same event_id is already present. Returns True when a new line is written.
    """
    path = feedback_path(property_root)
    if _has_event(path, event_id):
        log.info("hermes_feedback_skipped", event_id=event_id, reason="duplicate")
        return False

    record = {
        "kind": kind,
        "ts": datetime.now(UTC).isoformat(),
        "event_id": event_id,
        "event_type": event_type,
        "property_id": property_id,
        "summary": summary,
        "applied_ops": applied_ops,
        "deferred_ops": deferred_ops,
        "touched": list(touched),
    }
    line = json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(line)
    log.info(
        "hermes_feedback_appended",
        event_id=event_id,
        property_id=property_id,
        applied_ops=applied_ops,
    )
    return True


def iter_feedback(property_root: Path) -> Iterator[FeedbackRecord]:
    """Yield each `FeedbackRecord` from the substrate file. Empty if file is missing."""
    path = feedback_path(property_root)
    if not path.is_file():
        return
    with path.open("r", encoding="utf-8") as f:
        for raw in f:
            stripped = raw.strip()
            if not stripped:
                continue
            try:
                row = json.loads(stripped)
            except json.JSONDecodeError:
                log.warning("hermes_feedback_corrupt_line", line=stripped[:120])
                continue
            if not isinstance(row, dict):
                continue
            yield FeedbackRecord.from_dict(row)


def _coerce_int(value: object) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().lstrip("-").isdigit():
        return int(value)
    return 0


def _has_event(path: Path, event_id: str) -> bool:
    if not path.is_file():
        return False
    with path.open("r", encoding="utf-8") as f:
        for raw in f:
            stripped = raw.strip()
            if not stripped:
                continue
            try:
                row = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict) and row.get("event_id") == event_id:
                return True
    return False
