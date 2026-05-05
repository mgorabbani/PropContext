from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

from app.schemas.patch_plan import (
    AppendSectionOp,
    CreatePageOp,
    PatchPlan,
    PrependLogOp,
    UpsertSectionOp,
)
from app.services.hermes.feedback import append_feedback, feedback_path
from app.services.hermes.runner import run_hermes_loops
from app.services.patcher.apply import apply_patch_plan


def _git_init(wiki_dir: Path) -> None:
    wiki_dir.mkdir(parents=True, exist_ok=True)
    if (wiki_dir / ".git").is_dir():
        return
    for cmd in (
        ["git", "init", "-q"],
        ["git", "config", "user.email", "sim@example.test"],
        ["git", "config", "user.name", "sim"],
        ["git", "config", "commit.gpgsign", "false"],
    ):
        subprocess.run(cmd, cwd=wiki_dir, check=True, capture_output=True)


def _heating_plan(i: int, property_id: str) -> PatchPlan:
    haus = 12 + (i % 3)
    eh = f"EH-{14 + i:03d}"
    eid = f"EMAIL-{12000 + i}"
    return PatchPlan(
        event_id=eid,
        property_id=property_id,
        event_type="email",
        summary=f"heating outage reported for {eh}",
        source_ids=[eid],
        ops=[
            CreatePageOp(
                path=f"sources/{eid}.md",
                frontmatter={"name": f"source-{eid.lower()}", "description": f"Heating email {eh}"},
                body=f"## Body\n\nKein Heizung in {eh}.\n",
            ),
            CreatePageOp(
                path=f"entities/{eh}.md",
                frontmatter={
                    "name": f"unit-{eh.lower()}",
                    "description": f"Unit {eh} dossier — tenant complaints, repairs.",
                },
                body=f"## Status\n\nNo heating reported [[sources/{eid}.md]]\n",
            ),
            UpsertSectionOp(
                path=f"02_buildings/HAUS-{haus}/index.md",
                heading="Open Issues",
                body=f"- 🔴 **{eh}:** Heating outage [^${eid}]\n",
            ),
            AppendSectionOp(
                path=f"entities/{eh}.md",
                heading="Timeline",
                line=f"- 2026-04-25 heating reported [[sources/{eid}.md]]",
            ),
            PrependLogOp(line=f"## [2026-04-25] email | {eh} heating outage"),
        ],
    )


def _voicenote_miss_plan(i: int, property_id: str) -> PatchPlan:
    eid = f"VOICE-{900 + i}"
    return PatchPlan(
        event_id=eid,
        property_id=property_id,
        event_type="voicenote",
        summary=f"voicemail mentions ZX-{500 + i}",
        source_ids=[eid],
        ops=[],
    )


def _invoice_conflict(property_id: str) -> tuple[PatchPlan, dict[str, int]]:
    eid = "INV-77"
    plan = PatchPlan(
        event_id=eid,
        property_id=property_id,
        event_type="invoice",
        summary="invoice amount mismatch vs bank tx",
        source_ids=[eid],
        ops=[
            CreatePageOp(
                path=f"sources/{eid}.md",
                frontmatter={"name": f"source-{eid.lower()}", "description": "Invoice 77"},
                body="## Total\n\n€420.00\n",
            ),
            PrependLogOp(line="## [2026-04-25] invoice | amount mismatch"),
        ],
    )
    return plan, {"deferred_ops": 1}


def _run(args: argparse.Namespace) -> int:
    workspace = (
        Path(tempfile.mkdtemp(prefix="sim_hermes_"))
        if not args.workspace
        else Path(args.workspace).resolve()
    )
    workspace.mkdir(parents=True, exist_ok=True)
    wiki_dir = workspace / "wiki"
    _git_init(wiki_dir)

    property_id = args.property_id
    print(f"workspace: {workspace}")
    print(f"wiki_dir:  {wiki_dir}")
    print(f"property:  {property_id}")
    print()

    print(f"=== seeding {args.heating} heating events + {args.misses} voicenote misses ===")
    for i in range(args.heating):
        plan = _heating_plan(i, property_id)
        result = apply_patch_plan(plan, wiki_dir=wiki_dir)
        print(
            f"  applied {plan.event_id}: ops={result.applied_ops} commit={result.commit_sha[:8] if result.commit_sha else '—'}"
        )

    for i in range(args.misses):
        plan = _voicenote_miss_plan(i, property_id)
        append_feedback(
            wiki_dir / property_id,
            event_id=plan.event_id,
            event_type=plan.event_type,
            property_id=property_id,
            summary=plan.summary,
            applied_ops=0,
            deferred_ops=0,
            touched=(),
        )
        print(f"  recorded miss {plan.event_id}: applied_ops=0 (zero-op event)")

    if args.conflict:
        plan, extras = _invoice_conflict(property_id)
        result = apply_patch_plan(plan, wiki_dir=wiki_dir)
        # Re-write the feedback line with deferred_ops=1 to simulate conflict-scan rejection.
        fb = feedback_path(wiki_dir / property_id)
        lines = fb.read_text(encoding="utf-8").splitlines()
        lines[-1] = lines[-1].replace(
            '"deferred_ops":0', f'"deferred_ops":{extras["deferred_ops"]}'
        )
        fb.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(
            f"  applied {plan.event_id}: ops={result.applied_ops} (deferred_ops patched to {extras['deferred_ops']})"
        )

    print()
    print("=== running Hermes loops ===")
    report = run_hermes_loops(
        wiki_dir=wiki_dir,
        property_id=property_id,
        skill_threshold=args.skill_threshold,
    )

    print(
        f"events scanned: {report.proposals.total_events} "
        f"(misses={report.proposals.misses}, conflicts={report.proposals.conflicts})"
    )
    print(f"skills promoted: {len(report.skills)}")
    for skill in report.skills:
        templates = ", ".join(skill.path_templates)
        print(
            f"  - {skill.slug} ({skill.event_type}, n={skill.occurrences}) templates=[{templates}]"
        )
    print(f"proposals: {len(report.proposals.proposals)}")
    for prop in report.proposals.proposals:
        print(f"  - [{prop.kind}] {prop.target}")
        print(f"      {prop.rationale}")

    if report.skills_path:
        print()
        print(f"=== {report.skills_path.relative_to(wiki_dir)} ===")
        print(report.skills_path.read_text(encoding="utf-8").rstrip())
    if report.proposals_path:
        print()
        print(f"=== {report.proposals_path.relative_to(wiki_dir)} ===")
        print(report.proposals_path.read_text(encoding="utf-8").rstrip())

    print()
    print(f"=== {feedback_path(wiki_dir / property_id).relative_to(wiki_dir)} (last 3 lines) ===")
    fb_lines = feedback_path(wiki_dir / property_id).read_text(encoding="utf-8").splitlines()
    for line in fb_lines[-3:]:
        print(line)

    return 0


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Synthesise a feedback substrate by applying canned PatchPlans, "
        "then run the Hermes loops over it. Demonstrates the full self-healing flow "
        "without an LLM in the loop.",
    )
    p.add_argument("--property-id", default="LIE-001")
    p.add_argument("--workspace", help="reuse a workspace dir (default: fresh tmp dir)")
    p.add_argument("--heating", type=int, default=5, help="count of heating events (default: 5)")
    p.add_argument(
        "--misses", type=int, default=3, help="count of zero-op voicenote events (default: 3)"
    )
    p.add_argument("--conflict", action="store_true", help="seed one invoice conflict event")
    p.add_argument("--skill-threshold", type=int, default=5)
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    return _run(_parse_args(argv if argv is not None else sys.argv[1:]))


if __name__ == "__main__":
    raise SystemExit(main())
