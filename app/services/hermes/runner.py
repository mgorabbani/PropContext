from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import structlog

from app.services.hermes.proposals import (
    ProposalReport,
    propose_schema_amendments,
    write_proposals_markdown,
)
from app.services.hermes.skills import (
    DEFAULT_PROMOTION_THRESHOLD,
    SkillCandidate,
    propose_skills,
    write_skills_markdown,
)

log = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class HermesReport:
    property_id: str
    skills: tuple[SkillCandidate, ...]
    proposals: ProposalReport
    skills_path: Path | None
    proposals_path: Path | None


def run_hermes_loops(
    *,
    wiki_dir: Path,
    property_id: str,
    skill_threshold: int = DEFAULT_PROMOTION_THRESHOLD,
    write: bool = True,
) -> HermesReport:
    """Run the inner skill loop and outer schema loop over a property's substrate.

    When ``write`` is True (default), the report is materialised as
    ``06_skills.md`` and ``_hermes_proposals.md`` under the property root.
    """
    property_root = wiki_dir / property_id
    skills = tuple(propose_skills(property_root, threshold=skill_threshold))
    proposals = propose_schema_amendments(property_root)

    skills_path = write_skills_markdown(property_root, skills) if write else None
    proposals_path = write_proposals_markdown(property_root, proposals) if write else None

    log.info(
        "hermes_loops_done",
        property_id=property_id,
        skills=len(skills),
        proposals=len(proposals.proposals),
    )

    return HermesReport(
        property_id=property_id,
        skills=skills,
        proposals=proposals,
        skills_path=skills_path,
        proposals_path=proposals_path,
    )
