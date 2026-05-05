from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

import structlog

from app.services.hermes.feedback import iter_feedback

log = structlog.get_logger(__name__)

PROPOSALS_FILENAME = "_hermes_proposals.md"

_MIN_MISS_COUNT = 2
_MIN_CONFLICT_COUNT = 1
_MIN_UNRESOLVED_COUNT = 3
_EVIDENCE_LIMIT = 8
_ID_TOKEN_RE = re.compile(r"[A-Z]+-\d+")


@dataclass(frozen=True, slots=True)
class SchemaProposal:
    kind: str
    target: str
    rationale: str
    evidence_event_ids: tuple[str, ...]

    def title(self) -> str:
        return f"{self.kind} → {self.target}"


@dataclass(frozen=True, slots=True)
class ProposalReport:
    proposals: tuple[SchemaProposal, ...] = field(default_factory=tuple)
    total_events: int = 0
    misses: int = 0
    conflicts: int = 0


def propose_schema_amendments(property_root: Path) -> ProposalReport:
    """Read the substrate and emit proposals for misses, conflicts, and frequent
    unresolved id tokens.
    """
    misses_by_type: Counter[str] = Counter()
    conflict_events_by_type: dict[str, list[str]] = {}
    miss_events_by_type: dict[str, list[str]] = {}
    unresolved_tokens: Counter[str] = Counter()
    unresolved_events: dict[str, list[str]] = {}
    total = 0

    for record in iter_feedback(property_root):
        if record.kind != "ingest":
            continue
        if _had_upstream_error(record):
            continue
        total += 1

        if record.applied_ops == 0:
            misses_by_type[record.event_type] += 1
            miss_events_by_type.setdefault(record.event_type, []).append(record.event_id)

        if record.deferred_ops > 0:
            conflict_events_by_type.setdefault(record.event_type, []).append(record.event_id)

        for token in _ID_TOKEN_RE.findall(record.summary):
            if not _looks_resolved(record.touched, token):
                unresolved_tokens[token] += 1
                unresolved_events.setdefault(token, []).append(record.event_id)

    proposals: list[SchemaProposal] = []

    for event_type, count in misses_by_type.items():
        if count < _MIN_MISS_COUNT:
            continue
        proposals.append(
            SchemaProposal(
                kind="schema-gap",
                target=f"WIKI_SCHEMA.md (event_type={event_type})",
                rationale=(
                    f"{count} `{event_type}` events produced zero applied ops — "
                    "extractor lacks a place to land this content. Consider a new "
                    "section convention or a dedicated topic page."
                ),
                evidence_event_ids=tuple(miss_events_by_type[event_type]),
            )
        )

    for event_type, events in conflict_events_by_type.items():
        if len(events) < _MIN_CONFLICT_COUNT:
            continue
        proposals.append(
            SchemaProposal(
                kind="vocabulary-gap",
                target=f"VOCABULARY.md (event_type={event_type})",
                rationale=(
                    f"{len(events)} `{event_type}` events landed in `_pending_review.md` "
                    "due to vocabulary or conflict-scan rejection. Likely a missing "
                    "controlled value."
                ),
                evidence_event_ids=tuple(events),
            )
        )

    for token, count in unresolved_tokens.items():
        if count < _MIN_UNRESOLVED_COUNT:
            continue
        proposals.append(
            SchemaProposal(
                kind="unresolved-entity",
                target=f"stammdaten / entities (id={token})",
                rationale=(
                    f"`{token}` is referenced in {count} event summaries but no "
                    "patched file mentions it — likely missing from stammdaten or "
                    "needs a new entity page."
                ),
                evidence_event_ids=tuple(unresolved_events[token]),
            )
        )

    proposals.sort(key=lambda p: (p.kind, p.target))

    return ProposalReport(
        proposals=tuple(proposals),
        total_events=total,
        misses=sum(misses_by_type.values()),
        conflicts=sum(len(v) for v in conflict_events_by_type.values()),
    )


def render_proposals_markdown(report: ProposalReport) -> str:
    header = (
        "<!-- runtime-managed; Hermes outer loop output. Do not hand-edit. -->\n"
        "# Hermes Schema Proposals\n\n"
        f"- Total ingest events scanned: **{report.total_events}**\n"
        f"- Misses (zero ops applied): **{report.misses}**\n"
        f"- Conflicts (deferred ops > 0): **{report.conflicts}**\n\n"
    )
    if not report.proposals:
        return header + "_No schema gaps detected. Substrate looks healthy._\n"

    parts = [header, "## Open proposals\n"]
    for prop in report.proposals:
        parts.append(_render_one(prop))
    return "".join(parts).rstrip() + "\n"


def write_proposals_markdown(property_root: Path, report: ProposalReport) -> Path:
    path = property_root / PROPOSALS_FILENAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_proposals_markdown(report), encoding="utf-8")
    log.info(
        "hermes_proposals_written",
        path=str(path),
        proposals=len(report.proposals),
    )
    return path


def _looks_resolved(touched: Iterable[str], token: str) -> bool:
    return any(token in path for path in touched)


def _had_upstream_error(record: object) -> bool:
    extra = getattr(record, "extra", {}) or {}
    if extra.get("retrieval_success") is False:
        return True
    if extra.get("error"):
        return True
    return False


def _render_one(prop: SchemaProposal) -> str:
    lines = [
        f"### {prop.title()}",
        "",
        f"- **Kind**: `{prop.kind}`",
        f"- **Rationale**: {prop.rationale}",
        f"- **Evidence**: {', '.join(f'`{e}`' for e in prop.evidence_event_ids[:_EVIDENCE_LIMIT])}"
        + (
            f" _(+{len(prop.evidence_event_ids) - _EVIDENCE_LIMIT} more)_"
            if len(prop.evidence_event_ids) > _EVIDENCE_LIMIT
            else ""
        ),
        "",
    ]
    return "\n".join(lines) + "\n"
