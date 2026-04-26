from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

import yaml

HUMAN_NOTES_HEADING = "# Human Notes"

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)


class PatchOperationError(ValueError):
    """Raised when a patch operation cannot be applied safely."""


def split_human_notes(content: str) -> tuple[str, str]:
    """Return (managed, human) split. Human side is empty if no boundary present."""
    if content.startswith(HUMAN_NOTES_HEADING):
        return "", content
    marker = f"\n{HUMAN_NOTES_HEADING}"
    idx = content.find(marker)
    if idx == -1:
        return content, ""
    return content[: idx + 1], content[idx + 1 :]


def render_page(*, frontmatter: Mapping[str, Any] | None, body: str) -> str:
    """Render a page from optional frontmatter + body. Body is taken as-is."""
    body_norm = body.rstrip() + "\n" if body.strip() else ""
    if not frontmatter:
        return body_norm
    fm = yaml.safe_dump(dict(frontmatter), sort_keys=False, allow_unicode=True).strip()
    return f"---\n{fm}\n---\n\n{body_norm}"


def parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """Return (frontmatter, body). Empty dict if no frontmatter block."""
    if not content.startswith("---\n"):
        return {}, content
    end = content.find("\n---\n", 4)
    if end == -1:
        return {}, content
    raw = content[4:end]
    rest = content[end + 5 :]
    try:
        data = yaml.safe_load(raw) or {}
    except yaml.YAMLError:
        return {}, content
    if not isinstance(data, dict):
        return {}, content
    return data, rest.lstrip("\n")


def create_page(
    *,
    path_exists: bool,
    existing: str,
    frontmatter: Mapping[str, Any] | None,
    body: str,
) -> str:
    """Create a page if missing. If it exists, return existing unchanged (idempotent)."""
    if path_exists and existing.strip():
        return existing
    return render_page(frontmatter=frontmatter, body=body)


def upsert_section(content: str, *, heading: str, body: str) -> str:
    """Replace the body of `## {heading}`; append the section if absent.

    Refuses to write below `# Human Notes` if a boundary is present.
    """
    managed, human = split_human_notes(content)
    new_body = body.rstrip() + "\n" if body.strip() else "\n"

    section_re = re.compile(rf"^##\s+{re.escape(heading)}\s*$", re.MULTILINE)
    match = section_re.search(managed)
    if match is None:
        prefix = managed.rstrip()
        sep = "\n\n" if prefix else ""
        new_managed = f"{prefix}{sep}## {heading}\n\n{new_body}"
        return _join_managed_human(new_managed, human)

    start = match.end()
    next_match = _HEADING_RE.search(managed, pos=start)
    end = next_match.start() if next_match else len(managed)
    new_managed = managed[:start] + "\n\n" + new_body + managed[end:].lstrip("\n")
    if not new_managed.endswith("\n"):
        new_managed += "\n"
    return _join_managed_human(new_managed, human)


def append_section(content: str, *, heading: str, line: str) -> str:
    """Append a single line to `## {heading}`; create the section if absent."""
    managed, human = split_human_notes(content)
    line_norm = line.rstrip("\n") + "\n"

    section_re = re.compile(rf"^##\s+{re.escape(heading)}\s*$", re.MULTILINE)
    match = section_re.search(managed)
    if match is None:
        prefix = managed.rstrip()
        sep = "\n\n" if prefix else ""
        new_managed = f"{prefix}{sep}## {heading}\n\n{line_norm}"
        return _join_managed_human(new_managed, human)

    start = match.end()
    next_match = _HEADING_RE.search(managed, pos=start)
    end = next_match.start() if next_match else len(managed)
    section_body = managed[start:end]
    trimmed = section_body.rstrip("\n")
    new_section = trimmed + "\n" + line_norm
    if not new_section.startswith("\n"):
        new_section = "\n" + new_section
    new_managed = managed[:start] + new_section + managed[end:].lstrip("\n")
    if not new_managed.endswith("\n"):
        new_managed += "\n"
    return _join_managed_human(new_managed, human)


def prepend_log(content: str, *, line: str) -> str:
    """Prepend a single line to log.md, after any leading H1 + blank line."""
    line_norm = line.rstrip("\n") + "\n"
    if not content.strip():
        return line_norm

    # If file starts with a single H1 ("# Title"), insert below it.
    first_match = _HEADING_RE.match(content)
    if first_match and first_match.group(1) == "#":
        head_end = first_match.end()
        rest = content[head_end:]
        rest_lstripped = rest.lstrip("\n")
        return content[:head_end] + "\n\n" + line_norm + rest_lstripped

    return line_norm + content if content.endswith("\n") else line_norm + content + "\n"


def _join_managed_human(managed: str, human: str) -> str:
    if not human:
        return managed
    if not managed.endswith("\n"):
        managed += "\n"
    return managed + human
