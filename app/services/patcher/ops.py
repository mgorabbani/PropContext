from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

HUMAN_NOTES_HEADING = "# Human Notes"


class PatchOperationError(ValueError):
    """Raised when a patch operation would touch unmanaged markdown."""


def _human_notes_start(content: str) -> int:
    marker = f"\n{HUMAN_NOTES_HEADING}"
    idx = content.find(marker)
    if idx == -1:
        if content.startswith(HUMAN_NOTES_HEADING):
            return 0
        raise PatchOperationError("missing # Human Notes boundary")
    return idx + 1


def _managed_content_end(content: str) -> int:
    return _human_notes_start(content)


def _section_bounds(content: str, section: str) -> tuple[int, int]:
    managed_end = _managed_content_end(content)
    managed = content[:managed_end]
    heading_re = re.compile(rf"^## {re.escape(section)}\s*$", re.MULTILINE)
    match = heading_re.search(managed)
    if match is None:
        raise PatchOperationError(f"section not found before # Human Notes: {section}")

    next_heading = re.search(r"^## .*$", managed[match.end() :], re.MULTILINE)
    end = managed_end if next_heading is None else match.end() + next_heading.start()
    if end > managed_end:
        raise PatchOperationError("operation would cross # Human Notes boundary")
    return match.end(), end


def _section_lines(content: str, section: str) -> tuple[int, int, list[str]]:
    start, end = _section_bounds(content, section)
    return start, end, content[start:end].splitlines(keepends=True)


def _replace_section_lines(content: str, section: str, lines: Sequence[str]) -> str:
    start, end = _section_bounds(content, section)
    body = "".join(lines)
    if body and not body.endswith("\n"):
        body += "\n"
    return f"{content[:start]}{body}{content[end:]}"


def _ensure_section_spacing(lines: list[str]) -> list[str]:
    if not lines:
        return ["\n"]
    if lines[0].strip():
        lines.insert(0, "\n")
    if lines[-1].strip():
        lines.append("\n")
    return lines


def _strip_empty_state(lines: list[str]) -> list[str]:
    return [line for line in lines if not line.lstrip().startswith("_Keine ")]


def _keyed_bullet_re(key: str) -> re.Pattern[str]:
    return re.compile(rf"^\s*-\s+.*\*\*{re.escape(key)}:\*\*")


def _normalize_bullet(key: str, text: str) -> str:
    line = text.strip()
    if not line.startswith("- "):
        line = f"- **{key}:** {line}"
    elif f"**{key}:**" not in line:
        line = f"- **{key}:** {line[2:].strip()}"
    return f"{line}\n"


def upsert_bullet(content: str, *, section: str, key: str, text: str) -> str:
    _, _, lines = _section_lines(content, section)
    lines = _strip_empty_state(lines)
    new_line = _normalize_bullet(key, text)
    keyed = _keyed_bullet_re(key)

    for idx, line in enumerate(lines):
        if keyed.match(line):
            lines[idx] = new_line
            return _replace_section_lines(content, section, _ensure_section_spacing(lines))

    insert_at = len(lines)
    while insert_at > 0 and not lines[insert_at - 1].strip():
        insert_at -= 1
    lines.insert(insert_at, new_line)
    return _replace_section_lines(content, section, _ensure_section_spacing(lines))


def delete_bullet(content: str, *, section: str, key: str) -> str:
    _, _, lines = _section_lines(content, section)
    keyed = _keyed_bullet_re(key)
    lines = [line for line in lines if not keyed.match(line)]
    return _replace_section_lines(content, section, _ensure_section_spacing(lines))


def _normalize_cells(row: str | Sequence[object]) -> list[str]:
    if isinstance(row, str):
        stripped = row.strip().strip("|")
        return [cell.strip() for cell in stripped.split("|")]
    return [str(cell).strip() for cell in row]


def _render_row(cells: str | Sequence[object]) -> str:
    return "| " + " | ".join(_normalize_cells(cells)) + " |\n"


def _is_table_row(line: str) -> bool:
    return line.lstrip().startswith("|") and line.rstrip().endswith("|")


def _is_separator(line: str) -> bool:
    return bool(re.match(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$", line))


def _table_bounds(lines: Sequence[str]) -> tuple[int, int] | None:
    start = None
    for idx, line in enumerate(lines):
        if _is_table_row(line):
            start = idx
            break
    if start is None:
        return None
    end = start
    while end < len(lines) and (_is_table_row(lines[end]) or not lines[end].strip()):
        if not _is_table_row(lines[end]) and end > start:
            break
        end += 1
    return start, end


def _row_key(line: str) -> str | None:
    if not _is_table_row(line) or _is_separator(line):
        return None
    cells = _normalize_cells(line)
    if not cells:
        return None
    return cells[0]


def _table_insert_index(lines: Sequence[str], start: int, end: int) -> int:
    if start + 1 < end and _is_separator(lines[start + 1]):
        return start + 2
    return start + 1


def upsert_row(
    content: str,
    *,
    section: str,
    key: str,
    row: str | Sequence[object],
    header: Sequence[object] | None = None,
) -> str:
    _, _, lines = _section_lines(content, section)
    lines = _strip_empty_state(lines)
    rendered = _render_row(row)
    bounds = _table_bounds(lines)

    if bounds is None:
        table = []
        if header is not None:
            header_cells = _normalize_cells(header)
            table.append(_render_row(header_cells))
            table.append(_render_row(["---"] * len(header_cells)))
        table.append(rendered)
        insert_at = len(lines)
        while insert_at > 0 and not lines[insert_at - 1].strip():
            insert_at -= 1
        lines[insert_at:insert_at] = table
        return _replace_section_lines(content, section, _ensure_section_spacing(lines))

    start, end = bounds
    for idx in range(start, end):
        if _row_key(lines[idx]) == key:
            lines[idx] = rendered
            return _replace_section_lines(content, section, _ensure_section_spacing(lines))

    lines.insert(end, rendered)
    return _replace_section_lines(content, section, _ensure_section_spacing(lines))


def delete_row(content: str, *, section: str, key: str) -> str:
    _, _, lines = _section_lines(content, section)
    bounds = _table_bounds(lines)
    if bounds is None:
        return content
    start, end = bounds
    kept = [
        line for idx, line in enumerate(lines) if idx < start or idx >= end or _row_key(line) != key
    ]
    return _replace_section_lines(content, section, _ensure_section_spacing(kept))


def prepend_row(
    content: str,
    *,
    section: str,
    row: str | Sequence[object],
    header: Sequence[object] | None = None,
) -> str:
    _, _, lines = _section_lines(content, section)
    lines = _strip_empty_state(lines)
    rendered = _render_row(row)
    bounds = _table_bounds(lines)

    if bounds is None:
        table = []
        if header is not None:
            header_cells = _normalize_cells(header)
            table.append(_render_row(header_cells))
            table.append(_render_row(["---"] * len(header_cells)))
        table.append(rendered)
        insert_at = len(lines)
        while insert_at > 0 and not lines[insert_at - 1].strip():
            insert_at -= 1
        lines[insert_at:insert_at] = table
        return _replace_section_lines(content, section, _ensure_section_spacing(lines))

    start, end = bounds
    lines.insert(_table_insert_index(lines, start, end), rendered)
    return _replace_section_lines(content, section, _ensure_section_spacing(lines))


def prune_ring(content: str, *, section: str, max_rows: int) -> str:
    if max_rows < 0:
        raise PatchOperationError("max_rows must be non-negative")
    _, _, lines = _section_lines(content, section)
    bounds = _table_bounds(lines)
    if bounds is None:
        bullet_indexes = [idx for idx, line in enumerate(lines) if line.lstrip().startswith("- ")]
        for idx in reversed(bullet_indexes[max_rows:]):
            del lines[idx]
        return _replace_section_lines(content, section, _ensure_section_spacing(lines))

    start, end = bounds
    first_data = _table_insert_index(lines, start, end)
    data_indexes = [
        idx
        for idx in range(first_data, end)
        if _is_table_row(lines[idx]) and not _is_separator(lines[idx])
    ]
    for idx in reversed(data_indexes[max_rows:]):
        del lines[idx]
    return _replace_section_lines(content, section, _ensure_section_spacing(lines))


def upsert_footnote(content: str, *, key: str, text: str) -> str:
    section = "Provenance"
    _, _, lines = _section_lines(content, section)
    new_line = f"[^{key}]: {text.strip()}\n"
    pattern = re.compile(rf"^\[\^{re.escape(key)}\]:")
    for idx, line in enumerate(lines):
        if pattern.match(line):
            lines[idx] = new_line
            return _replace_section_lines(content, section, _ensure_section_spacing(lines))
    insert_at = len(lines)
    while insert_at > 0 and not lines[insert_at - 1].strip():
        insert_at -= 1
    lines.insert(insert_at, new_line)
    return _replace_section_lines(content, section, _ensure_section_spacing(lines))


def gc_footnotes(content: str, *, ref_counts: Mapping[str, int] | None = None) -> str:
    _, _, lines = _section_lines(content, "Provenance")
    if ref_counts is None:
        start, _ = _section_bounds(content, "Provenance")
        before_provenance = content[:start]
        refs = set(re.findall(r"\[\^([^\]]+)\]", before_provenance))
    else:
        refs = {key for key, count in ref_counts.items() if count > 0}

    kept = []
    footnote_re = re.compile(r"^\[\^([^\]]+)\]:")
    for line in lines:
        match = footnote_re.match(line)
        if match is not None and match.group(1) not in refs:
            continue
        kept.append(line)
    return _replace_section_lines(content, "Provenance", _ensure_section_spacing(kept))


def update_state(
    state_path: Path,
    *,
    updates: Mapping[str, Any] | None = None,
    counters: Mapping[str, int] | None = None,
) -> dict[str, Any]:
    state = json.loads(state_path.read_text(encoding="utf-8"))
    for key, value in (updates or {}).items():
        state[key] = value
    if counters:
        counts = state.setdefault("counts", {})
        for key, delta in counters.items():
            counts[key] = int(counts.get(key, 0)) + delta
    state["last_patched"] = datetime.now(UTC).isoformat()
    return state
