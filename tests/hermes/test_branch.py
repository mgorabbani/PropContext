from __future__ import annotations

import subprocess
from pathlib import Path

from app.services.hermes.branch import commit_proposals_to_branch
from app.services.hermes.feedback import append_feedback
from app.services.hermes.proposals import PROPOSALS_FILENAME, propose_schema_amendments


def _git_init(wiki_dir: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=wiki_dir, check=True, capture_output=True)
    for cmd in (
        ["git", "config", "user.email", "test@example.test"],
        ["git", "config", "user.name", "test"],
        ["git", "config", "commit.gpgsign", "false"],
    ):
        subprocess.run(cmd, cwd=wiki_dir, check=True, capture_output=True)
    seed = wiki_dir / "README.md"
    seed.write_text("seed\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=wiki_dir, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "seed"], cwd=wiki_dir, check=True, capture_output=True)


def _seed_misses(root: Path) -> None:
    for i in range(3):
        append_feedback(
            root,
            event_id=f"VOICE-{i}",
            event_type="voicenote",
            property_id="LIE-001",
            summary="recorded note",
            applied_ops=0,
        )


def test_commit_proposals_creates_branch_with_evidence(tmp_path: Path) -> None:
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    _git_init(wiki_dir)

    property_root = wiki_dir / "LIE-001"
    _seed_misses(property_root)
    report = propose_schema_amendments(property_root)

    branch = commit_proposals_to_branch(wiki_dir=wiki_dir, property_id="LIE-001", report=report)
    assert branch is not None
    assert branch.startswith("hermes/proposals-")

    on_branch = subprocess.run(
        ["git", "log", "-n", "1", "--format=%s%n%b", branch],
        cwd=wiki_dir,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert "schema proposal" in on_branch
    assert "VOICE-0" in on_branch

    target = property_root / PROPOSALS_FILENAME
    in_branch = subprocess.run(
        ["git", "show", f"{branch}:{target.relative_to(wiki_dir).as_posix()}"],
        cwd=wiki_dir,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert "schema-gap" in in_branch


def test_commit_proposals_returns_to_original_branch(tmp_path: Path) -> None:
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    _git_init(wiki_dir)

    starting = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=wiki_dir,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()

    property_root = wiki_dir / "LIE-001"
    _seed_misses(property_root)
    report = propose_schema_amendments(property_root)

    commit_proposals_to_branch(wiki_dir=wiki_dir, property_id="LIE-001", report=report)

    after = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=wiki_dir,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert after == starting


def test_commit_proposals_skipped_when_empty(tmp_path: Path) -> None:
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    _git_init(wiki_dir)

    property_root = wiki_dir / "LIE-001"
    property_root.mkdir()
    report = propose_schema_amendments(property_root)
    assert report.proposals == ()
    assert (
        commit_proposals_to_branch(wiki_dir=wiki_dir, property_id="LIE-001", report=report) is None
    )
