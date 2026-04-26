from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from app.schemas.patch_plan import (
    AppendSectionOp,
    CreatePageOp,
    PatchOp,
    PatchPlan,
    PrependLogOp,
    UpsertSectionOp,
)
from app.services.patcher.atomic import atomic_write_text
from app.services.patcher.git import commit_all, head_sha
from app.services.patcher.ops import (
    PatchOperationError,
    append_section,
    create_page,
    prepend_log,
    render_page,
    upsert_section,
)
from app.services.patcher.paths import property_file_path

_PROPERTY_ID_RE = re.compile(r"^[A-Z]+-\d+$")
_LOG_PATH = "log.md"


@dataclass(frozen=True)
class PatchApplyResult:
    event_id: str
    applied_ops: int
    commit_sha: str | None
    touched: tuple[str, ...]
    idempotent: bool = False


def apply_patch_plan(plan: PatchPlan, *, wiki_dir: Path) -> PatchApplyResult:
    if _PROPERTY_ID_RE.fullmatch(plan.property_id) is None:
        raise ValueError(f"invalid property_id: {plan.property_id!r}")

    property_root = wiki_dir / plan.property_id
    property_root.mkdir(parents=True, exist_ok=True)

    touched: list[Path] = []
    for op in plan.ops:
        path = _apply_one(property_root, op)
        if path is not None:
            touched.append(path)

    summary = plan.summary.strip() or plan.event_type
    commit_sha = commit_all(wiki_dir, message=f"ingest({plan.event_id}): {summary}".strip())
    rels = tuple(_relative_posix(p, property_root) for p in touched)
    return PatchApplyResult(
        event_id=plan.event_id,
        applied_ops=len(touched),
        commit_sha=commit_sha,
        touched=rels,
    )


def head_commit(wiki_dir: Path) -> str | None:
    return head_sha(wiki_dir)


def _apply_one(property_root: Path, op: PatchOp) -> Path | None:
    if isinstance(op, CreatePageOp):
        return _do_create_page(property_root, op)
    if isinstance(op, UpsertSectionOp):
        return _do_upsert_section(property_root, op)
    if isinstance(op, AppendSectionOp):
        return _do_append_section(property_root, op)
    if isinstance(op, PrependLogOp):
        return _do_prepend_log(property_root, op)
    raise PatchOperationError(f"unknown op: {op!r}")


def _do_create_page(property_root: Path, op: CreatePageOp) -> Path | None:
    file_path = property_file_path(property_root, op.path)
    _require_md(file_path)
    existing = file_path.read_text(encoding="utf-8") if file_path.is_file() else ""
    new_content = create_page(
        path_exists=file_path.is_file(),
        existing=existing,
        frontmatter=op.frontmatter,
        body=op.body,
    )
    if new_content == existing:
        return None
    atomic_write_text(file_path, new_content)
    return file_path


def _do_upsert_section(property_root: Path, op: UpsertSectionOp) -> Path | None:
    file_path = property_file_path(property_root, op.path)
    _require_md(file_path)
    existing = file_path.read_text(encoding="utf-8") if file_path.is_file() else ""
    base = existing or render_page(frontmatter=None, body="")
    new_content = upsert_section(base, heading=op.heading, body=op.body)
    if new_content == existing:
        return None
    atomic_write_text(file_path, new_content)
    return file_path


def _do_append_section(property_root: Path, op: AppendSectionOp) -> Path | None:
    file_path = property_file_path(property_root, op.path)
    _require_md(file_path)
    existing = file_path.read_text(encoding="utf-8") if file_path.is_file() else ""
    base = existing or render_page(frontmatter=None, body="")
    new_content = append_section(base, heading=op.heading, line=op.line)
    if new_content == existing:
        return None
    atomic_write_text(file_path, new_content)
    return file_path


def _do_prepend_log(property_root: Path, op: PrependLogOp) -> Path | None:
    file_path = property_root / _LOG_PATH
    existing = file_path.read_text(encoding="utf-8") if file_path.is_file() else "# Log\n\n"
    new_content = prepend_log(existing, line=op.line)
    if new_content == existing:
        return None
    atomic_write_text(file_path, new_content)
    return file_path


def _require_md(path: Path) -> None:
    if path.suffix != ".md":
        raise PatchOperationError(f"path must be a markdown file: {path.name}")


def _relative_posix(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.name


def touched_for_reindex(touched: Sequence[str]) -> list[str]:
    return [t for t in touched if t.endswith(".md") and not t.startswith("_")]
