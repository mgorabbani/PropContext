from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from app.services.patcher.atomic import atomic_write_text
from app.services.patcher.ops import parse_frontmatter

_INDEX_NAME = "index.md"
_LOG_NAME = "log.md"
_LINT_NAME = "lint_report.md"
_HIDDEN_PREFIX = "_"


def regenerate_index(property_root: Path) -> Path | None:
    """Walk the property tree and rewrite index.md with a catalog of pages.

    Returns the index path if written, else None. Skips the index itself,
    log.md, lint_report.md, hidden files (starting with `_`), and the wiki
    .git directory. Pages without frontmatter are still listed.
    """
    if not property_root.is_dir():
        return None

    pages = _collect_pages(property_root)
    body = _render_index(property_id=property_root.name, pages=pages)
    index_path = property_root / _INDEX_NAME
    existing = index_path.read_text(encoding="utf-8") if index_path.is_file() else ""
    if existing == body:
        return None
    atomic_write_text(index_path, body)
    return index_path


def _collect_pages(property_root: Path) -> list[tuple[str, str, str]]:
    """Return list of (relative_posix_path, name, description) tuples."""
    rows: list[tuple[str, str, str]] = []
    for path in sorted(property_root.rglob("*.md")):
        rel = path.relative_to(property_root)
        rel_posix = rel.as_posix()
        if rel.name in {_INDEX_NAME, _LOG_NAME, _LINT_NAME}:
            continue
        if any(part.startswith(_HIDDEN_PREFIX) for part in rel.parts):
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except OSError:
            continue
        frontmatter, _ = parse_frontmatter(content)
        name = str(frontmatter.get("name") or rel.stem)
        description = str(frontmatter.get("description") or "").strip().replace("\n", " ")
        rows.append((rel_posix, name, description))
    return rows


def _render_index(*, property_id: str, pages: list[tuple[str, str, str]]) -> str:
    by_group: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    for rel, name, desc in pages:
        group = rel.split("/", 1)[0] if "/" in rel else "."
        by_group[group].append((rel, name, desc))

    lines = [f"# Index — {property_id}", ""]
    if (property_id_root := by_group.pop(".", None)) is not None:
        lines.append("## Pages")
        lines.append("")
        for rel, name, desc in property_id_root:
            lines.append(_render_row(rel, name, desc))
        lines.append("")

    for group in sorted(by_group):
        lines.append(f"## {group}/")
        lines.append("")
        for rel, name, desc in sorted(by_group[group]):
            lines.append(_render_row(rel, name, desc))
        lines.append("")

    if not pages:
        lines.append("_(no pages yet)_")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _render_row(rel: str, name: str, description: str) -> str:
    base = f"- [{name}]({rel})"
    if description:
        return f"{base} — {description}"
    return base
