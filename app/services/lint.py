from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import structlog
from fastapi import Depends

from app.core.config import Settings, get_settings
from app.services.patcher.atomic import atomic_write_text
from app.services.patcher.git import commit_all
from app.services.patcher.ops import parse_frontmatter

log = structlog.get_logger(__name__)

_LINT_REPORT_NAME = "lint_report.md"
_INDEX_NAME = "index.md"
_LOG_NAME = "log.md"
_WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


@dataclass(frozen=True)
class LintFinding:
    kind: str
    path: str
    detail: str = ""


@dataclass(frozen=True)
class LintResult:
    property_id: str
    findings: list[LintFinding]
    report_path: Path | None
    commit_sha: str | None


class LintService:
    def __init__(self, *, wiki_dir: Path) -> None:
        self._wiki_dir = wiki_dir

    def lint(self, property_id: str, *, commit: bool = True) -> LintResult:
        property_root = self._wiki_dir / property_id
        if not property_root.is_dir():
            return LintResult(property_id, [], None, None)

        pages = sorted(property_root.rglob("*.md"))
        rel_paths = {p.relative_to(property_root).as_posix() for p in pages}
        findings: list[LintFinding] = []
        inbound: dict[str, int] = dict.fromkeys(rel_paths, 0)

        for page in pages:
            rel = page.relative_to(property_root).as_posix()
            if rel in {_INDEX_NAME, _LOG_NAME, _LINT_REPORT_NAME}:
                continue
            if any(part.startswith("_") for part in page.relative_to(property_root).parts):
                continue
            findings.extend(_inspect_page(page, rel=rel, inbound=inbound))

        for rel, count in inbound.items():
            if count == 0 and rel not in {_INDEX_NAME, _LOG_NAME, _LINT_REPORT_NAME}:
                findings.append(LintFinding("orphan_page", rel))

        report_path = property_root / _LINT_REPORT_NAME
        report_body = _render_report(property_id, findings)
        existing = report_path.read_text(encoding="utf-8") if report_path.is_file() else ""
        commit_sha = None
        if report_body != existing:
            atomic_write_text(report_path, report_body)
            if commit:
                commit_sha = commit_all(
                    self._wiki_dir, message=f"lint({property_id}): {len(findings)} findings"
                )
        return LintResult(property_id, findings, report_path, commit_sha)


def _inspect_page(page: Path, *, rel: str, inbound: dict[str, int]) -> list[LintFinding]:
    try:
        content = page.read_text(encoding="utf-8")
    except OSError as exc:
        return [LintFinding("read_error", rel, str(exc))]

    findings: list[LintFinding] = []
    frontmatter, body = parse_frontmatter(content)
    if not frontmatter.get("name"):
        findings.append(LintFinding("missing_frontmatter_name", rel))
    if not frontmatter.get("description"):
        findings.append(LintFinding("missing_frontmatter_description", rel))
    for raw_target in _WIKILINK_RE.findall(body):
        target = raw_target.strip().split("|", 1)[0]
        if target.endswith(".md") and target in inbound:
            inbound[target] = inbound.get(target, 0) + 1
    return findings


def _render_report(property_id: str, findings: list[LintFinding]) -> str:
    timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        f"# Lint Report — {property_id}",
        "",
        f"_Generated: {timestamp}_",
        "",
        f"**Findings: {len(findings)}**",
        "",
    ]
    if not findings:
        lines.append("_(no issues found)_")
        lines.append("")
        return "\n".join(lines)

    by_kind: dict[str, list[LintFinding]] = {}
    for f in findings:
        by_kind.setdefault(f.kind, []).append(f)

    for kind in sorted(by_kind):
        lines.append(f"## {kind} ({len(by_kind[kind])})")
        lines.append("")
        for finding in sorted(by_kind[kind], key=lambda f: f.path):
            suffix = f" — {finding.detail}" if finding.detail else ""
            lines.append(f"- `{finding.path}`{suffix}")
        lines.append("")
    return "\n".join(lines)


def get_lint_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> LintService:
    return LintService(wiki_dir=settings.wiki_dir)
