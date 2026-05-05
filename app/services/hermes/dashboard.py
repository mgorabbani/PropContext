from __future__ import annotations

from collections import Counter
from pathlib import Path

from app.schemas.hermes import (
    ArtifactPaths,
    HermesDashboard,
    ProposalItem,
    ProposalsBlock,
    SkillItem,
    SkillsBlock,
    SubstrateStats,
)
from app.services.hermes.feedback import FEEDBACK_FILENAME, feedback_path, iter_feedback
from app.services.hermes.proposals import PROPOSALS_FILENAME, propose_schema_amendments
from app.services.hermes.registry import DEFAULT_MIN_OCCURRENCES, load_skill_registry
from app.services.hermes.skills import (
    DEFAULT_PROMOTION_THRESHOLD,
    SKILLS_FILENAME,
    enumerate_buckets,
    propose_skills,
)

_EVIDENCE_PER_PROPOSAL = 8


def build_dashboard(
    *,
    wiki_dir: Path,
    property_id: str,
    skill_threshold: int = DEFAULT_PROMOTION_THRESHOLD,
    registry_threshold: int = DEFAULT_MIN_OCCURRENCES,
) -> HermesDashboard:
    """Read-only summary of the Hermes state for one property.

    Computes substrate stats, runs the skill detector and proposal detector
    in-memory, and reports artifact paths if they have been materialised on
    disk. Does not write anything.
    """
    property_root = wiki_dir / property_id
    return HermesDashboard(
        property_id=property_id,
        substrate=_substrate_stats(property_root),
        skills=_skills_block(property_root, skill_threshold, registry_threshold),
        proposals=_proposals_block(property_root),
        artifacts=_artifacts(property_root),
    )


def _substrate_stats(property_root: Path) -> SubstrateStats:
    path = feedback_path(property_root)
    if not path.is_file():
        return SubstrateStats(exists=False)

    total = 0
    applied = 0
    misses = 0
    conflicts = 0
    errors = 0
    last_event_id: str | None = None
    last_ts: str | None = None
    for r in iter_feedback(property_root):
        if r.kind != "ingest":
            continue
        total += 1
        last_event_id = r.event_id or last_event_id
        last_ts = r.ts or last_ts
        if _had_upstream_error(r):
            errors += 1
            continue
        if r.applied_ops > 0:
            applied += 1
        else:
            misses += 1
        if r.deferred_ops > 0:
            conflicts += 1
    return SubstrateStats(
        exists=True,
        total_events=total,
        applied_events=applied,
        miss_events=misses,
        conflict_events=conflicts,
        error_events=errors,
        last_event_id=last_event_id,
        last_ts=last_ts,
    )


def _had_upstream_error(record: object) -> bool:
    extra = getattr(record, "extra", {}) or {}
    if extra.get("retrieval_success") is False:
        return True
    if extra.get("error"):
        return True
    return False


def _skills_block(
    property_root: Path,
    skill_threshold: int,
    registry_threshold: int,
) -> SkillsBlock:
    def to_item(c: object) -> SkillItem:
        return SkillItem(
            slug=getattr(c, "slug"),
            event_type=getattr(c, "event_type"),
            occurrences=getattr(c, "occurrences"),
            last_event_id=getattr(c, "last_event_id"),
            path_templates=list(getattr(c, "path_templates")),
            sample_summaries=list(getattr(c, "sample_summaries")),
        )

    candidates = propose_skills(property_root, threshold=skill_threshold)
    buckets = enumerate_buckets(property_root, min_occurrences=1)
    registry = load_skill_registry(property_root, min_occurrences=registry_threshold)
    return SkillsBlock(
        promoted_count=len(candidates),
        candidates=[to_item(c) for c in candidates],
        buckets=[to_item(b) for b in buckets],
        registry_event_types=sorted(registry.briefings.keys()),
        registry_briefings={
            et: b.occurrences for et, b in registry.briefings.items()
        },
        promotion_threshold=skill_threshold,
        registry_threshold=registry_threshold,
    )


def _proposals_block(property_root: Path) -> ProposalsBlock:
    report = propose_schema_amendments(property_root)
    by_kind: Counter[str] = Counter()
    items: list[ProposalItem] = []
    for p in report.proposals:
        by_kind[p.kind] += 1
        items.append(
            ProposalItem(
                kind=p.kind,
                target=p.target,
                rationale=p.rationale,
                evidence_count=len(p.evidence_event_ids),
                evidence_event_ids=list(p.evidence_event_ids[:_EVIDENCE_PER_PROPOSAL]),
            )
        )
    return ProposalsBlock(total=len(items), by_kind=dict(by_kind), items=items)


def _artifacts(property_root: Path) -> ArtifactPaths:
    skills = property_root / SKILLS_FILENAME
    proposals = property_root / PROPOSALS_FILENAME
    feedback = property_root / FEEDBACK_FILENAME
    return ArtifactPaths(
        skills_md=SKILLS_FILENAME if skills.is_file() else None,
        proposals_md=PROPOSALS_FILENAME if proposals.is_file() else None,
        feedback_jsonl=FEEDBACK_FILENAME if feedback.is_file() else None,
    )
