from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path

import structlog

from app.services.hermes.proposals import (
    PROPOSALS_FILENAME,
    ProposalReport,
    render_proposals_markdown,
)
from app.services.patcher.git import head_sha, run_git

log = structlog.get_logger(__name__)

_BRANCH_PREFIX = "hermes/proposals-"
_SLUG_RE = re.compile(r"[^a-z0-9]+")


def commit_proposals_to_branch(
    *,
    wiki_dir: Path,
    property_id: str,
    report: ProposalReport,
    branch_name: str | None = None,
    now: datetime | None = None,
) -> str | None:
    """Commit the rendered proposals onto a fresh `hermes/proposals-<date>` branch.

    The current branch is preserved: we create the new branch from HEAD,
    write the proposal markdown, commit it with `event_id` evidence in the
    body, and switch back. Returns the branch name or None when there are
    no proposals to commit.
    """
    if not report.proposals:
        log.info("hermes_branch_skipped", reason="no_proposals", property_id=property_id)
        return None

    if head_sha(wiki_dir) is None:
        log.warning("hermes_branch_skipped", reason="no_head", property_id=property_id)
        return None

    when = now or datetime.now(UTC)
    name = branch_name or f"{_BRANCH_PREFIX}{when.date().isoformat()}-{property_id.lower()}"
    original = _current_branch(wiki_dir)

    run_git(["checkout", "-B", name], cwd=wiki_dir)
    try:
        target = wiki_dir / property_id / PROPOSALS_FILENAME
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_proposals_markdown(report), encoding="utf-8")
        run_git(["add", target.relative_to(wiki_dir).as_posix()], cwd=wiki_dir)
        diff = run_git(["diff", "--cached", "--quiet"], cwd=wiki_dir, check=False)
        if diff.returncode == 0:
            log.info(
                "hermes_branch_no_change",
                branch=name,
                property_id=property_id,
            )
            return name
        run_git(
            ["commit", "-m", _commit_message(report, property_id, when)],
            cwd=wiki_dir,
        )
        log.info(
            "hermes_branch_committed",
            branch=name,
            property_id=property_id,
            proposals=len(report.proposals),
        )
        return name
    finally:
        if original and original != name:
            run_git(["checkout", original], cwd=wiki_dir)


def _current_branch(wiki_dir: Path) -> str | None:
    result = run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=wiki_dir, check=False)
    if result.returncode != 0:
        return None
    name = result.stdout.strip()
    return name or None


def _commit_message(report: ProposalReport, property_id: str, when: datetime) -> str:
    title = (
        f"hermes: {len(report.proposals)} schema proposal(s) for {property_id} "
        f"({when.date().isoformat()})"
    )
    body_lines = [
        title,
        "",
        f"Scanned {report.total_events} ingest events: "
        f"{report.misses} miss(es), {report.conflicts} conflict(s).",
        "",
    ]
    for prop in report.proposals:
        body_lines.append(f"- [{prop.kind}] {prop.target}")
        body_lines.append(f"  evidence: {', '.join(prop.evidence_event_ids[:8])}")
    return "\n".join(body_lines).rstrip() + "\n"
