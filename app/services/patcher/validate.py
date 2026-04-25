from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.services.patcher.atomic import atomic_write_text


@dataclass(frozen=True)
class ValidationIssue:
    op: Mapping[str, Any]
    reason: str


def parse_vocabulary(path: Path) -> dict[str, set[str]]:
    text = path.read_text(encoding="utf-8")
    vocab: dict[str, set[str]] = {}
    heading: str | None = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("## "):
            heading = line[3:].split("(", 1)[0].strip().lower()
            continue
        if heading is None:
            continue
        values = set(re.findall(r"`([^`]+)`", line))
        if not values:
            continue
        for key in _field_names_for_heading(heading):
            vocab.setdefault(key, set()).update(values)
    return vocab


def _field_names_for_heading(heading: str) -> set[str]:
    names = {heading.replace(" ", "_").replace("-", "_")}
    if "status" in heading or "lifecycle" in heading:
        names.add("status")
    if "priority" in heading:
        names.add("priority")
    if "event type" in heading:
        names.add("event_type")
    if "risk" in heading:
        names.add("risk")
    if "confidence" in heading:
        names.add("confidence")
    if "signal" in heading:
        names.add("signal")
    if "patcher op names" in heading:
        names.add("op")
    return names


def validate_keyed_values(
    ops: Iterable[Mapping[str, Any]],
    vocabulary: Mapping[str, set[str]],
) -> tuple[list[Mapping[str, Any]], list[ValidationIssue]]:
    valid_ops: list[Mapping[str, Any]] = []
    issues: list[ValidationIssue] = []
    for op in ops:
        reason = _invalid_reason(op, vocabulary)
        if reason is None:
            valid_ops.append(op)
        else:
            issues.append(ValidationIssue(op=op, reason=reason))
    return valid_ops, issues


def _invalid_reason(op: Mapping[str, Any], vocabulary: Mapping[str, set[str]]) -> str | None:
    for field, value in _iter_keyed_values(op):
        allowed = vocabulary.get(field)
        if allowed is None:
            continue
        if _matches_allowed(str(value), allowed):
            continue
        return f"unknown vocab: {field}={value!r}"
    return None


def _iter_keyed_values(op: Mapping[str, Any]) -> Iterable[tuple[str, object]]:
    for field, value in op.items():
        if isinstance(value, dict):
            for subfield, subvalue in value.items():
                yield str(subfield), subvalue
        elif field in {"values", "fields"}:
            continue
        else:
            yield str(field), value


def _matches_allowed(value: str, allowed: set[str]) -> bool:
    if value in allowed:
        return True
    for candidate in allowed:
        if "<N>" in candidate:
            pattern = re.escape(candidate).replace(r"<N>", r"\d+")
            if re.fullmatch(pattern, value):
                return True
    return False


def append_pending_review(property_root: Path, issues: Iterable[ValidationIssue]) -> None:
    issues = list(issues)
    if not issues:
        return
    path = property_root / "_pending_review.md"
    text = path.read_text(encoding="utf-8") if path.exists() else _default_pending_review()
    marker = "\n# Human Notes"
    boundary = text.find(marker)
    if boundary == -1:
        boundary = len(text)
        suffix = "\n# Human Notes\n"
    else:
        suffix = text[boundary:]

    entries = []
    now = datetime.now(UTC).isoformat()
    for issue in issues:
        op_name = issue.op.get("op", "unknown")
        entries.append(
            "\n".join(
                [
                    "",
                    f"### {now} vocab validation failed",
                    f"- reason: {issue.reason}",
                    f"- op: `{op_name}`",
                    f"- payload: `{dict(issue.op)}`",
                    "",
                ]
            )
        )
    atomic_write_text(path, text[:boundary].rstrip() + "\n" + "\n".join(entries) + suffix)


def _default_pending_review() -> str:
    return (
        "---\n"
        "name: pending-review\n"
        "description: Open conflicts awaiting PM resolution.\n"
        "---\n\n"
        "## Open Conflicts\n\n"
        "<!-- agent-managed: one ### entry per conflict -->\n\n"
        "# Human Notes\n"
    )
