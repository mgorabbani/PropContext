from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.core.config import REPO_ROOT, Settings
from app.services.hermes.runner import run_hermes_loops


def _build_settings(args: argparse.Namespace) -> Settings:
    if args.wiki_dir:
        return Settings(wiki_dir=Path(args.wiki_dir).resolve())
    return Settings()


def _run(args: argparse.Namespace) -> int:
    settings = _build_settings(args)
    if not (settings.wiki_dir / args.property_id).is_dir():
        print(
            f"property root not found: {settings.wiki_dir / args.property_id}",
            file=sys.stderr,
        )
        return 2

    report = run_hermes_loops(
        wiki_dir=settings.wiki_dir,
        property_id=args.property_id,
        skill_threshold=args.skill_threshold,
        write=not args.dry_run,
        auto_branch=args.auto_branch,
    )

    print(f"property: {report.property_id}")
    print(f"wiki_dir: {settings.wiki_dir}")
    print(
        f"events scanned: {report.proposals.total_events} "
        f"(misses={report.proposals.misses}, conflicts={report.proposals.conflicts})"
    )
    print(f"skills promoted: {len(report.skills)}")
    for skill in report.skills:
        templates = ", ".join(skill.path_templates) or "—"
        print(
            f"  - {skill.slug} ({skill.event_type}, n={skill.occurrences}) "
            f"last={skill.last_event_id} templates=[{templates}]"
        )

    print(f"proposals: {len(report.proposals.proposals)}")
    for prop in report.proposals.proposals:
        print(f"  - [{prop.kind}] {prop.target}")
    if report.proposals_branch:
        print(f"proposals branch: {report.proposals_branch}")

    if not args.dry_run:
        if report.skills_path:
            print(
                f"wrote: {report.skills_path.relative_to(REPO_ROOT) if report.skills_path.is_relative_to(REPO_ROOT) else report.skills_path}"
            )
        if report.proposals_path:
            print(
                f"wrote: {report.proposals_path.relative_to(REPO_ROOT) if report.proposals_path.is_relative_to(REPO_ROOT) else report.proposals_path}"
            )

    return 0


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Run the Hermes inner (skills) and outer (schema proposals) loops "
        "against a property's `_hermes_feedback.jsonl` substrate.",
    )
    p.add_argument("--property-id", default="LIE-001")
    p.add_argument("--wiki-dir", help="wiki dir (default: settings.wiki_dir)")
    p.add_argument(
        "--skill-threshold",
        type=int,
        default=5,
        help="minimum occurrences of a (event_type, path-template) signature to promote (default: 5)",
    )
    p.add_argument("--dry-run", action="store_true", help="print report; do not write markdown")
    p.add_argument(
        "--auto-branch",
        action="store_true",
        help="commit proposals onto a fresh hermes/proposals-<date> branch",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    return _run(_parse_args(argv if argv is not None else sys.argv[1:]))


if __name__ == "__main__":
    raise SystemExit(main())
