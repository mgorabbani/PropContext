from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from app.storage.wiki_chunks import open_wiki_chunks

_ENTITY_REF_RE = re.compile(r"\b(?:LIE|HAUS|EH|EIG|MIE|DL|INV|LTR|EMAIL|TX)-[A-Z]*-?\d{2,6}\b")


@dataclass(frozen=True)
class IndexedSection:
    file: str
    section: str
    body: str
    entity_refs: list[str]


def reindex_files(
    *,
    wiki_dir: Path,
    property_id: str,
    files: Sequence[Path | str],
    db_path: Path,
) -> int:
    store = open_wiki_chunks(db_path)
    property_root = wiki_dir / property_id
    count = 0
    for file in files:
        relative = Path(file)
        if relative.is_absolute():
            try:
                relative = relative.relative_to(property_root)
            except ValueError:
                continue
        if relative.suffix != ".md":
            continue
        store.delete_file(property_id, relative.as_posix())
        path = property_root / relative
        if not path.is_file():
            continue
        content = path.read_text(encoding="utf-8")
        for section in parse_markdown_sections(content, relative.as_posix()):
            store.upsert(
                property_id,
                section.file,
                section.section,
                section.body,
                section.entity_refs,
            )
            count += 1
    store.build_index()
    return count


def reindex_property(*, wiki_dir: Path, property_id: str, db_path: Path) -> int:
    property_root = wiki_dir / property_id
    files = [path.relative_to(property_root) for path in property_root.rglob("*.md")]
    return reindex_files(wiki_dir=wiki_dir, property_id=property_id, files=files, db_path=db_path)


def parse_markdown_sections(content: str, file: str) -> list[IndexedSection]:
    body = _strip_frontmatter(content)
    managed = body.split("\n# Human Notes", 1)[0]
    matches = list(re.finditer(r"^## (?P<section>.+?)\s*$", managed, flags=re.MULTILINE))
    sections: list[IndexedSection] = []
    if not matches and managed.strip():
        sections.append(
            IndexedSection(
                file=file,
                section="(body)",
                body=managed.strip(),
                entity_refs=_entity_refs(managed),
            )
        )
        return sections
    for idx, match in enumerate(matches):
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(managed)
        section_body = managed[start:end].strip()
        section_name = match.group("section").strip()
        sections.append(
            IndexedSection(
                file=file,
                section=section_name,
                body=section_body,
                entity_refs=_entity_refs(f"{section_name}\n{section_body}"),
            )
        )
    return sections


def _strip_frontmatter(content: str) -> str:
    if not content.startswith("---\n"):
        return content
    end = content.find("\n---\n", 4)
    if end == -1:
        return content
    return content[end + 5 :].lstrip("\n")


def _entity_refs(text: str) -> list[str]:
    seen: set[str] = set()
    refs: list[str] = []
    for match in _ENTITY_REF_RE.finditer(text):
        ref = match.group(0).upper()
        if ref in seen:
            continue
        seen.add(ref)
        refs.append(ref)
    return refs
