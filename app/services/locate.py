from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.storage.wiki_chunks import WikiChunksStore

# Slicer thresholds — see AGENTS.md "Token efficiency" section.
_SLICE_MIN_CHARS = 500
_PROSE_HEAD_CHARS = 400
_PROSE_TAIL_CHARS = 200
_KEYED_BULLET_RE = re.compile(r"^\s*[-*]\s+(?:[\U0001F300-\U0001FAFF☀-➿]\s+)?\*\*[A-Z]+-\d+:\*\*")
_TABLE_ROW_RE = re.compile(r"^\s*\|.*\|\s*$")
_FOOTNOTE_DEF_RE = re.compile(r"^\s*\[\^[^\]]+\]:")
_HEADING_RE = re.compile(r"^\s*#{1,6}\s+")


@dataclass(frozen=True)
class LocatedSection:
    file: str
    section: str
    body: str
    entity_refs: list[str]
    score: float = 0.0


def slice_section_body(body: str) -> str:
    """Compress a section body to the lines an extractor actually needs.

    Keeps keyed bullets (`- 🔴 **EH-014:** …`), table rows, footnote definitions
    and any heading lines; collapses the rest into a single elision marker.
    Falls back to a head+tail prose slice when the section has no keyed content.
    Bodies under ``_SLICE_MIN_CHARS`` are returned unchanged — slicing them
    would not save tokens.
    """
    if len(body) <= _SLICE_MIN_CHARS:
        return body

    lines = body.splitlines()
    kept: list[str] = []
    elided = 0
    has_keyed = False

    def flush_elision() -> None:
        nonlocal elided
        if elided:
            kept.append(f"<!-- … {elided} line(s) elided … -->")
            elided = 0

    for line in lines:
        if _is_kept_line(line):
            if _KEYED_BULLET_RE.match(line) or _TABLE_ROW_RE.match(line):
                has_keyed = True
            flush_elision()
            kept.append(line)
        else:
            elided += 1
    flush_elision()

    if has_keyed:
        return "\n".join(kept)

    # Prose fallback: head + tail with a marker.
    if len(body) <= _PROSE_HEAD_CHARS + _PROSE_TAIL_CHARS:
        return body
    head = body[:_PROSE_HEAD_CHARS].rstrip()
    tail = body[-_PROSE_TAIL_CHARS:].lstrip()
    elided_chars = len(body) - len(head) - len(tail)
    return f"{head}\n<!-- … {elided_chars} chars elided … -->\n{tail}"


def _is_kept_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    return bool(
        _HEADING_RE.match(line)
        or _KEYED_BULLET_RE.match(line)
        or _TABLE_ROW_RE.match(line)
        or _FOOTNOTE_DEF_RE.match(line)
    )


def locate_sections(
    *,
    wiki_chunks: WikiChunksStore,
    property_id: str,
    entity_ids: list[str],
    query_text: str = "",
    limit: int = 8,
) -> list[LocatedSection]:
    wiki_chunks.build_index()
    found: dict[tuple[str, str], LocatedSection] = {}

    for entity_id in entity_ids:
        for row in wiki_chunks.find_by_entity(property_id, entity_id):
            key = (str(row["file"]), str(row["section"]))
            found[key] = LocatedSection(
                file=str(row["file"]),
                section=str(row["section"]),
                body=slice_section_body(str(row["body"])),
                entity_refs=list(row.get("entity_refs") or []),
                score=max(found.get(key, _empty_section()).score, 10.0),
            )
            if len(found) >= limit:
                return list(found.values())[:limit]

    if query_text:
        for row in wiki_chunks.query(query_text, property_id=property_id, limit=limit):
            key = (str(row["file"]), str(row["section"]))
            if key in found:
                continue
            found[key] = LocatedSection(
                file=str(row["file"]),
                section=str(row["section"]),
                body=slice_section_body(str(row["body"])),
                entity_refs=list(_refs(row)),
                score=float(row.get("score", 0.0)),
            )
            if len(found) >= limit:
                break

    return list(found.values())[:limit]


def _refs(row: dict[str, Any]) -> list[str]:
    refs = row.get("entity_refs", [])
    if isinstance(refs, list):
        return [str(ref) for ref in refs]
    return []


def _empty_section() -> LocatedSection:
    return LocatedSection(file="", section="", body="", entity_refs=[], score=0.0)
