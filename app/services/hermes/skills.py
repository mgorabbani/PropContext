from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import structlog

from app.services.hermes.feedback import FeedbackRecord, iter_feedback

log = structlog.get_logger(__name__)

SKILLS_FILENAME = "06_skills.md"
DEFAULT_PROMOTION_THRESHOLD = 5

_ID_TOKEN_RE = re.compile(r"([A-Z]+)-\d+")


@dataclass(frozen=True, slots=True)
class SkillCandidate:
    slug: str
    event_type: str
    path_templates: tuple[str, ...]
    occurrences: int
    last_event_id: str
    sample_summaries: tuple[str, ...]

    def signature(self) -> tuple[str, tuple[str, ...]]:
        return (self.event_type, self.path_templates)


def propose_skills(
    property_root: Path,
    *,
    threshold: int = DEFAULT_PROMOTION_THRESHOLD,
) -> list[SkillCandidate]:
    """Group feedback rows by `(event_type, path_template_set)` and return groups
    that have hit the promotion threshold.
    """
    groups: dict[tuple[str, tuple[str, ...]], list[FeedbackRecord]] = defaultdict(list)
    for record in iter_feedback(property_root):
        if record.kind != "ingest" or record.applied_ops <= 0:
            continue
        sig = (record.event_type, _path_template_set(record.touched))
        groups[sig].append(record)

    candidates: list[SkillCandidate] = []
    for (event_type, templates), rows in groups.items():
        if len(rows) < threshold:
            continue
        rows_sorted = sorted(rows, key=lambda r: r.ts)
        last = rows_sorted[-1]
        samples = tuple(r.summary for r in rows_sorted[-3:] if r.summary)
        slug = _slug(event_type, templates)
        candidates.append(
            SkillCandidate(
                slug=slug,
                event_type=event_type,
                path_templates=templates,
                occurrences=len(rows),
                last_event_id=last.event_id,
                sample_summaries=samples,
            )
        )

    candidates.sort(key=lambda c: (-c.occurrences, c.slug))
    return candidates


def render_skills_markdown(candidates: Iterable[SkillCandidate]) -> str:
    items = list(candidates)
    if not items:
        return (
            _skills_header()
            + "_No skills promoted yet — Hermes inner loop has not seen enough repetition._\n"
        )

    parts = [_skills_header()]
    for cand in items:
        parts.append(_render_one(cand))
    return "\n".join(parts).rstrip() + "\n"


def write_skills_markdown(property_root: Path, candidates: Iterable[SkillCandidate]) -> Path:
    path = property_root / SKILLS_FILENAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_skills_markdown(candidates), encoding="utf-8")
    log.info("hermes_skills_written", path=str(path))
    return path


def _path_template_set(touched: Iterable[str]) -> tuple[str, ...]:
    templates = sorted({_path_template(p) for p in touched if p})
    return tuple(templates)


def _path_template(path: str) -> str:
    return _ID_TOKEN_RE.sub(r"\1-<id>", path)


def _slug(event_type: str, templates: tuple[str, ...]) -> str:
    head = event_type or "unknown"
    leaf = templates[0].rsplit("/", 1)[-1] if templates else "any"
    leaf = leaf.removesuffix(".md")
    leaf_clean = re.sub(r"[^a-zA-Z0-9]+", "-", leaf).strip("-").lower() or "any"
    return f"{head}-{leaf_clean}"


def _skills_header() -> str:
    return (
        "---\n"
        "name: skills\n"
        "description: Hermes-promoted patch skills. Each entry is a recurring "
        "(event_type, touched-path) signature seen often enough to be worth a "
        "named handler. Auto-managed; do not hand-edit above `# Human Notes`.\n"
        "---\n\n"
        "# Skills\n\n"
    )


def _render_one(cand: SkillCandidate) -> str:
    lines = [
        f"## skill: {cand.slug}",
        "",
        f"- **Trigger**: `event_type = {cand.event_type}`",
        f"- **Touched template**: {', '.join(f'`{t}`' for t in cand.path_templates) or '_none_'}",
        f"- **Occurrences**: {cand.occurrences}",
        f"- **Last event**: `{cand.last_event_id}`",
    ]
    if cand.sample_summaries:
        lines.append("- **Recent summaries**:")
        for s in cand.sample_summaries:
            lines.append(f"  - {s}")
    lines.append("")
    return "\n".join(lines)
