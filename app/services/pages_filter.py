from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path

import structlog

log = structlog.get_logger(__name__)

# Pages that the extractor always benefits from seeing — structural anchors.
ESSENTIAL_PAGE_PATHS: frozenset[str] = frozenset(
    {
        "index.md",
        "log.md",
        "building.md",
        "06_skills.md",
        "07_timeline.md",
    }
)

DEFAULT_PAGE_LIMIT = 50

_FRONTMATTER_RE = re.compile(r"\A---\s*\n(?P<body>.*?)\n---", re.DOTALL)
_DESCRIPTION_RE = re.compile(
    r"^description:\s*(?P<value>.+?)\s*$",
    re.MULTILINE,
)
_FRONTMATTER_PEEK_BYTES = 2048


def filter_relevant_pages(
    property_root: Path,
    *,
    entity_ids: Iterable[str],
    source_ids: Iterable[str] = (),
    limit: int = DEFAULT_PAGE_LIMIT,
) -> list[str]:
    """Return paths of pages whose path or frontmatter description mentions one
    of the resolved IDs, plus essential structural pages.

    Surgical retrieval per AGENTS.md "Token efficiency": instead of dumping
    every `.md` path under the property (grows linearly with property age),
    return only what an extractor needs to reason about *this* event.
    """
    if not property_root.is_dir():
        return []

    needles = {nid for nid in (*entity_ids, *source_ids) if nid}
    selected: list[str] = []
    seen: set[str] = set()

    for path in sorted(property_root.rglob("*.md")):
        rel = path.relative_to(property_root)
        rel_posix = rel.as_posix()
        if any(part.startswith("_") for part in rel.parts):
            continue
        if rel_posix in seen:
            continue

        if _is_essential(rel_posix) or _path_mentions_needle(rel_posix, needles):
            selected.append(rel_posix)
            seen.add(rel_posix)
            continue

        if needles and _description_mentions_needle(path, needles):
            selected.append(rel_posix)
            seen.add(rel_posix)

        if len(selected) >= limit:
            break

    log.debug(
        "pages_filter_done",
        property_root=str(property_root),
        selected=len(selected),
        needles=sorted(needles),
    )
    return selected[:limit]


def _is_essential(rel_posix: str) -> bool:
    return rel_posix in ESSENTIAL_PAGE_PATHS or rel_posix.endswith("/index.md")


def _path_mentions_needle(rel_posix: str, needles: set[str]) -> bool:
    return any(needle in rel_posix for needle in needles)


def _description_mentions_needle(path: Path, needles: set[str]) -> bool:
    try:
        with path.open("rb") as f:
            head = f.read(_FRONTMATTER_PEEK_BYTES)
    except OSError:
        return False
    try:
        text = head.decode("utf-8", errors="replace")
    except UnicodeDecodeError:
        return False
    fm = _FRONTMATTER_RE.search(text)
    if fm is None:
        return False
    desc = _DESCRIPTION_RE.search(fm.group("body"))
    if desc is None:
        return False
    value = desc.group("value")
    return any(needle in value for needle in needles)
