from __future__ import annotations

import json
import subprocess
from pathlib import Path

from app.services.patcher.apply import apply_patch_plan
from app.tools.bootstrap_wiki import bootstrap

REPO_ROOT = Path(__file__).resolve().parents[2]
STAMMDATEN = REPO_ROOT / "data" / "stammdaten" / "stammdaten.json"
VOCABULARY = REPO_ROOT / "schema" / "VOCABULARY.md"


def test_apply_patch_plan_applies_ops_commits_and_is_idempotent(tmp_path: Path) -> None:
    wiki_dir = tmp_path / "wiki"
    root = bootstrap(STAMMDATEN, wiki_dir)
    plan = {
        "event_id": "EVT-001",
        "property_id": "LIE-001",
        "summary": "tenant leak report",
        "ops": [
            {
                "op": "upsert_bullet",
                "file": "index.md",
                "section": "Open Issues",
                "key": "EH-001",
                "text": "🔴 **EH-001:** Leak reported [^evt-001]",
                "status": "in_progress",
            },
            {
                "op": "upsert_footnote",
                "file": "index.md",
                "key": "evt-001",
                "text": "email EVT-001",
            },
            {
                "op": "update_state",
                "updates": {"last_event_id": "EVT-001"},
                "counters": {"open_issues": 1},
            },
        ],
    }

    result = apply_patch_plan(plan, wiki_dir=wiki_dir, vocabulary_path=VOCABULARY)
    again = apply_patch_plan(plan, wiki_dir=wiki_dir, vocabulary_path=VOCABULARY)

    assert result.applied_ops == 3
    assert result.deferred_ops == 0
    assert result.commit_sha is not None
    assert again.idempotent is True
    assert "Leak reported" in (root / "index.md").read_text(encoding="utf-8")
    state = json.loads((root / "_state.json").read_text(encoding="utf-8"))
    assert state["last_event_id"] == "EVT-001"
    assert state["counts"]["open_issues"] == 1
    feedback = (root / "_hermes_feedback.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(feedback) == 1

    log = subprocess.run(
        ["git", "log", "--oneline"],
        cwd=wiki_dir,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert "ingest(EVT-001): tenant leak report" in log
