from __future__ import annotations

import json
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from app.services.patcher.atomic import atomic_write_text
from app.services.patcher.ops import (
    delete_bullet,
    delete_row,
    gc_footnotes,
    prepend_row,
    prune_ring,
    update_state,
    upsert_bullet,
    upsert_footnote,
    upsert_row,
)
from app.services.patcher.validate import (
    append_pending_review,
    parse_vocabulary,
    validate_keyed_values,
)


@dataclass(frozen=True)
class PatchApplyResult:
    event_id: str
    applied_ops: int
    deferred_ops: int
    commit_sha: str | None
    idempotent: bool = False


def apply_patch_plan(
    plan: Mapping[str, Any],
    *,
    wiki_dir: Path,
    vocabulary_path: Path,
) -> PatchApplyResult:
    event_id = str(plan["event_id"])
    property_id = str(plan["property_id"])
    property_root = wiki_dir / property_id
    feedback_path = property_root / "_hermes_feedback.jsonl"

    if _feedback_contains_event(feedback_path, event_id):
        return PatchApplyResult(
            event_id=event_id,
            applied_ops=0,
            deferred_ops=0,
            commit_sha=_head_sha(wiki_dir),
            idempotent=True,
        )

    ops = [op for op in plan.get("ops", []) if isinstance(op, dict)]
    vocabulary = parse_vocabulary(vocabulary_path)
    valid_ops, issues = validate_keyed_values(ops, vocabulary)
    append_pending_review(property_root, issues)

    touched: set[Path] = set()
    for op in valid_ops:
        touched.update(_apply_one(property_root, op))

    _append_feedback(feedback_path, plan, applied_ops=len(valid_ops), deferred_ops=len(issues))
    touched.add(feedback_path)
    if issues:
        touched.add(property_root / "_pending_review.md")

    commit_sha = _git_commit(
        wiki_dir,
        message=f"ingest({event_id}): {str(plan.get('summary', 'patch')).strip()}",
    )
    return PatchApplyResult(
        event_id=event_id,
        applied_ops=len(valid_ops),
        deferred_ops=len(issues),
        commit_sha=commit_sha,
    )


def _apply_one(property_root: Path, op: Mapping[str, Any]) -> set[Path]:
    op_name = str(op["op"])
    if op_name == "update_state":
        path = property_root / str(op.get("file", "_state.json"))
        state = update_state(
            path,
            updates=_mapping_or_none(op.get("updates")),
            counters=_mapping_or_none(op.get("counters")),
        )
        atomic_write_text(path, json.dumps(state, indent=2, ensure_ascii=False) + "\n")
        return {path}

    file_path = property_root / str(op["file"])
    content = file_path.read_text(encoding="utf-8")
    section = str(op.get("section", ""))

    if op_name == "upsert_bullet":
        content = upsert_bullet(
            content,
            section=section,
            key=str(op["key"]),
            text=str(op["text"]),
        )
    elif op_name == "delete_bullet":
        content = delete_bullet(content, section=section, key=str(op["key"]))
    elif op_name == "upsert_row":
        content = upsert_row(
            content,
            section=section,
            key=str(op["key"]),
            row=op["row"],
            header=_sequence_or_none(op.get("header")),
        )
    elif op_name == "delete_row":
        content = delete_row(content, section=section, key=str(op["key"]))
    elif op_name == "prepend_row":
        content = prepend_row(
            content,
            section=section,
            row=op["row"],
            header=_sequence_or_none(op.get("header")),
        )
    elif op_name == "prune_ring":
        content = prune_ring(content, section=section, max_rows=int(op["max_rows"]))
    elif op_name == "upsert_footnote":
        content = upsert_footnote(content, key=str(op["key"]), text=str(op["text"]))
    elif op_name == "gc_footnotes":
        content = gc_footnotes(content, ref_counts=_mapping_or_none(op.get("ref_counts")))
    else:
        raise ValueError(f"unknown patch op: {op_name}")

    atomic_write_text(file_path, content)
    return {file_path}


def _sequence_or_none(value: object) -> list[object] | None:
    if value is None:
        return None
    if isinstance(value, list):
        return cast("list[object]", value)
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _mapping_or_none(value: object) -> dict[str, Any] | None:
    if value is None:
        return None
    if isinstance(value, dict):
        return cast("dict[str, Any]", value)
    raise TypeError(f"expected mapping, got {type(value).__name__}")


def _append_feedback(
    path: Path,
    plan: Mapping[str, Any],
    *,
    applied_ops: int,
    deferred_ops: int,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    record = {
        "kind": "ingest",
        "event_id": plan["event_id"],
        "property_id": plan["property_id"],
        "summary": plan.get("summary", ""),
        "applied_ops": applied_ops,
        "deferred_ops": deferred_ops,
    }
    atomic_write_text(path, existing + json.dumps(record, ensure_ascii=False) + "\n")


def _feedback_contains_event(path: Path, event_id: str) -> bool:
    if not path.exists():
        return False
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if record.get("event_id") == event_id:
            return True
    return False


def _git(args: list[str], cwd: Path, *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        ["git", *args],  # noqa: S607
        cwd=cwd,
        check=check,
        capture_output=True,
        text=True,
    )


def _git_commit(wiki_dir: Path, *, message: str) -> str | None:
    _git(["add", "-A"], cwd=wiki_dir)
    diff = _git(["diff", "--cached", "--quiet"], cwd=wiki_dir, check=False)
    if diff.returncode == 0:
        return _head_sha(wiki_dir)
    if diff.returncode != 1:
        raise subprocess.CalledProcessError(diff.returncode, diff.args, diff.stdout, diff.stderr)
    _git(["commit", "-m", message], cwd=wiki_dir)
    return _head_sha(wiki_dir)


def _head_sha(wiki_dir: Path) -> str | None:
    result = _git(["rev-parse", "HEAD"], cwd=wiki_dir, check=False)
    if result.returncode != 0:
        return None
    return result.stdout.strip()
