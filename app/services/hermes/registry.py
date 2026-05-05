from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

import structlog

from app.services.hermes.feedback import FeedbackRecord, iter_feedback

_ID_TOKEN_RE = re.compile(r"([A-Z]+)-\d+")

log = structlog.get_logger(__name__)

DEFAULT_MIN_OCCURRENCES = 3
_RECENT_SUMMARY_COUNT = 3


@dataclass(frozen=True, slots=True)
class SkillBriefing:
    """A summary of past patches for one event_type, ready to inject into a prompt."""

    event_type: str
    occurrences: int
    op_kinds: tuple[str, ...]
    op_shapes: tuple[tuple[tuple[str, str], ...], ...]
    touched_templates: tuple[str, ...]
    sample_summaries: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SkillRegistry:
    briefings: dict[str, SkillBriefing] = field(default_factory=dict)

    def find_for(self, event_type: str) -> SkillBriefing | None:
        return self.briefings.get(event_type)

    def __len__(self) -> int:
        return len(self.briefings)


def load_skill_registry(
    property_root: Path,
    *,
    min_occurrences: int = DEFAULT_MIN_OCCURRENCES,
) -> SkillRegistry:
    """Build a registry from the substrate, indexed by event_type.

    Only event_types with at least ``min_occurrences`` successful (applied_ops > 0)
    rows yield a briefing. The modal op-shape sequence and the union of touched
    path templates form the core of each briefing.
    """
    by_type: dict[str, list[FeedbackRecord]] = {}
    for record in iter_feedback(property_root):
        if record.kind != "ingest" or record.applied_ops <= 0:
            continue
        by_type.setdefault(record.event_type, []).append(record)

    briefings: dict[str, SkillBriefing] = {}
    for event_type, rows in by_type.items():
        if len(rows) < min_occurrences:
            continue
        rows.sort(key=lambda r: r.ts)
        modal_shapes = _modal_shape_sequence(rows)
        op_kinds = tuple(s["op"] for s in modal_shapes if "op" in s)
        op_shapes = tuple(tuple(sorted(s.items())) for s in modal_shapes)
        touched_templates = _touched_union(rows)
        samples = tuple(r.summary for r in rows[-_RECENT_SUMMARY_COUNT:] if r.summary)
        briefings[event_type] = SkillBriefing(
            event_type=event_type,
            occurrences=len(rows),
            op_kinds=op_kinds,
            op_shapes=op_shapes,
            touched_templates=touched_templates,
            sample_summaries=samples,
        )

    log.debug(
        "hermes_registry_loaded",
        property_root=str(property_root),
        event_types=list(briefings),
    )
    return SkillRegistry(briefings=briefings)


def format_briefing(briefing: SkillBriefing) -> str:
    """Render a briefing as the markdown chunk we inject into the extract prompt."""
    lines = [
        f"## Past patterns for `event_type = {briefing.event_type}` "
        f"({briefing.occurrences} prior events)",
        "",
        "When a new event of this type matches, the patch plan typically looks like:",
        "",
    ]
    for shape in briefing.op_shapes:
        attrs = dict(shape)
        kind = attrs.pop("op", "?")
        path = attrs.pop("path", None)
        heading = attrs.pop("heading", None)
        bits = [f"`{kind}`"]
        if path:
            bits.append(f"path=`{path}`")
        if heading:
            bits.append(f"heading=`{heading}`")
        lines.append(f"- {' '.join(bits)}")
    lines.append("")

    if briefing.touched_templates:
        lines.append("Frequently touched files (templates with `<id>` placeholders):")
        for tmpl in briefing.touched_templates:
            lines.append(f"- `{tmpl}`")
        lines.append("")

    if briefing.sample_summaries:
        lines.append("Recent event summaries:")
        for s in briefing.sample_summaries:
            lines.append(f"- {s}")
        lines.append("")

    lines.append(
        "Reuse this shape unless the new event genuinely differs. "
        "If it differs, explain the difference in the patch summary."
    )
    return "\n".join(lines)


_RowSignature = tuple[tuple[tuple[str, str], ...], ...]


def _modal_shape_sequence(rows: Iterable[FeedbackRecord]) -> list[dict[str, str]]:
    counts: Counter[_RowSignature] = Counter()
    last_for_signature: dict[_RowSignature, list[dict[str, str]]] = {}
    for r in rows:
        signature: _RowSignature = tuple(tuple(sorted(s.items())) for s in r.op_shapes)
        counts[signature] += 1
        last_for_signature[signature] = [dict(s) for s in r.op_shapes]
    if not counts:
        return []
    modal_signature, _ = counts.most_common(1)[0]
    return last_for_signature[modal_signature]


def _touched_union(rows: Iterable[FeedbackRecord]) -> tuple[str, ...]:
    templates: set[str] = set()
    for r in rows:
        for path in r.touched:
            templates.add(_ID_TOKEN_RE.sub(r"\1-<id>", path))
    return tuple(sorted(templates))
