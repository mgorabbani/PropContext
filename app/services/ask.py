from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated

import structlog
from fastapi import Depends

from app.core.config import Settings, get_settings
from app.services.llm.client import LLMClient, UsageRecorder, get_llm_client
from app.services.llm.json import parse_json_object
from app.services.patcher.atomic import atomic_write_text
from app.services.patcher.git import commit_all
from app.services.patcher.ops import render_page
from app.services.wiki import TreeNode, WikiService, get_wiki_service
from app.services.wiki_index import regenerate_index

log = structlog.get_logger(__name__)

_PICK_SYSTEM_PROMPT = (
    "You route a question to the most relevant page(s) in a property's markdown "
    "wiki. You receive a per-page digest with each file's path, name, and a "
    "one-paragraph description pulled from its frontmatter.\n\n"
    "Pick up to 8 pages whose FULL content the answerer will need. The "
    "answerer already has the digest, so DO NOT pick pages just to enumerate "
    "or list them — return [] for pure listing or counting questions. Pick "
    "pages only when the question needs data the short description omits "
    "(specific amounts, dates, contract terms, named events). Return paths "
    "relative to the property root (e.g. '07_timeline.md', "
    "'04_dienstleister/DL-001.md'). Do NOT return 'index.md'.\n\n"
    'Respond with a single JSON object: {"paths": string[]}. No prose outside the JSON.'
)

_ANSWER_SYSTEM_PROMPT = (
    "You answer questions against a property's markdown wiki. You receive: a "
    "per-page digest (path + name + frontmatter description for EVERY page), "
    "the file tree, the full content of pages the router pre-fetched, the "
    "prior conversation, and the new question.\n\n"
    "The digest is COMPLETE and AUTHORITATIVE — it lists every file in the "
    "property. RESPECT the user's question:\n"
    "- If they ask for ALL of something (\"name all 35 owners\", \"liste alle "
    "Dienstleister\"), enumerate every matching item from the digest. Do NOT "
    "abbreviate with \"and N more\" or \"available in individual files\" — the "
    "names are right there in the digest descriptions; pull them out.\n"
    "- For counts (\"how many X\"), give the count plus the full list when the "
    "set is ≤ 50 items.\n"
    "- For lookups about specific data (amounts, dates), use the picked "
    "pages.\n"
    "- For follow-ups (\"that one\", \"before\"), use prior turns.\n\n"
    "If neither the digest nor the picked pages cover the question, say so "
    "plainly — never claim you cannot access a file. If one specific page "
    "best grounds the answer, return its path (relative to the property "
    "root) in `path`; otherwise null. Match the user's language. Length "
    "should match the request: short for short questions, long for "
    "enumerations.\n\n"
    'Respond with a single JSON object: {"answer": string|null, "path": string|null}. '
    "No prose outside the JSON."
)

_SLUG_RE = re.compile(r"[^a-z0-9]+")
_MAX_PICKED = 8
_MAX_PAGE_CHARS = 6000
_MAX_PICKED_TOTAL_CHARS = 32000
_MAX_DIGEST_DESC_CHARS = 280
_MAX_DIGEST_CHARS = 120000
_MAX_HISTORY_TURNS = 8
_MAX_HISTORY_ANSWER_CHARS = 1200


@dataclass(frozen=True, slots=True)
class AskUsage:
    input_tokens: int
    output_tokens: int
    cache_read_input_tokens: int
    cache_creation_input_tokens: int
    sections: dict[str, int]


@dataclass(frozen=True, slots=True)
class AskStep:
    label: str
    detail: str | None = None
    paths: list[str] | None = None


@dataclass(frozen=True, slots=True)
class AskResult:
    answer: str | None
    path: str | None
    pinned_path: str | None = None
    usage: AskUsage | None = None
    steps: list[AskStep] | None = None


class AskService:
    def __init__(self, *, wiki: WikiService, llm: LLMClient, model: str) -> None:
        self._wiki = wiki
        self._llm = llm
        self._model = model

    async def answer(
        self,
        *,
        property_id: str,
        question: str,
        pin: bool = False,
        history: list[tuple[str, str]] | None = None,
    ) -> AskResult:
        history = history or []
        steps: list[AskStep] = []
        usage_rec = UsageRecorder()
        index = await self._wiki.read_property(property_id)
        if index is None:
            return AskResult(answer=f"property {property_id!r} not found", path=None)
        tree = self._wiki.walk_tree(property_id)
        tree_listing = _render_tree(tree) if tree is not None else ""
        digest = self._build_digest(property_id)
        steps.append(
            AskStep(
                label="Built page digest",
                detail=f"{digest.count(chr(10)) + 1 if digest else 0} pages indexed from frontmatter",
            )
        )

        cached_context = _render_cached_context(
            property_id=property_id, tree_listing=tree_listing, digest=digest
        )
        history_block = _render_history(history)
        routing_question = _route_question(history, question)
        picked = await self._pick_pages(
            property_id=property_id,
            cached_context=cached_context,
            question=routing_question,
            usage=usage_rec,
        )
        if picked:
            steps.append(
                AskStep(
                    label=f"Router pulled {len(picked)} page(s)",
                    paths=list(picked),
                )
            )
        else:
            steps.append(
                AskStep(
                    label="Router used digest only",
                    detail="no full page bodies needed",
                )
            )
        page_blocks = await self._read_picked(property_id=property_id, paths=picked)
        log.info(
            "ask_routed",
            property_id=property_id,
            picked=picked,
            turns=len(history),
            digest_chars=len(digest),
        )

        user_prompt = (
            f"{page_blocks}"
            f"{history_block}"
            f"=== Question ===\n{question}\n"
        )
        raw = await self._llm.complete(
            model=self._model,
            system_prompt=_ANSWER_SYSTEM_PROMPT + "\n\n" + cached_context,
            user_prompt=user_prompt,
            usage=usage_rec,
        )
        steps.append(AskStep(label="Composed answer"))
        sections = {
            "system": _approx_tokens(_ANSWER_SYSTEM_PROMPT),
            "tree": _approx_tokens(tree_listing),
            "digest": _approx_tokens(digest),
            "picked": _approx_tokens(page_blocks),
            "history": _approx_tokens(history_block),
            "question": _approx_tokens(question),
        }
        usage = AskUsage(
            input_tokens=usage_rec.input_tokens,
            output_tokens=usage_rec.output_tokens,
            cache_read_input_tokens=usage_rec.cache_read_input_tokens,
            cache_creation_input_tokens=usage_rec.cache_creation_input_tokens,
            sections=sections,
        )
        result = _parse_result(raw)
        if pin and result.answer:
            pinned = self._pin_answer(
                property_id=property_id,
                question=question,
                answer=result.answer,
                cited_path=result.path,
            )
            return AskResult(
                answer=result.answer,
                path=result.path,
                pinned_path=pinned,
                usage=usage,
                steps=steps,
            )
        return AskResult(
            answer=result.answer, path=result.path, usage=usage, steps=steps
        )

    async def _pick_pages(
        self,
        *,
        property_id: str,
        cached_context: str,
        question: str,
        usage: UsageRecorder | None = None,
    ) -> list[str]:
        raw = await self._llm.complete(
            model=self._model,
            system_prompt=_PICK_SYSTEM_PROMPT + "\n\n" + cached_context,
            user_prompt=f"=== Question ===\n{question}\n",
            usage=usage,
        )
        try:
            data = parse_json_object(raw)
        except ValueError as exc:
            log.warning("ask_router_parse_failed", error=str(exc))
            return []
        raw_paths = data.get("paths") or []
        if not isinstance(raw_paths, list):
            return []
        out: list[str] = []
        for p in raw_paths:
            if not isinstance(p, str):
                continue
            cleaned = p.strip().lstrip("/")
            if not cleaned or cleaned == "index.md" or ".." in cleaned.split("/"):
                continue
            if cleaned in out:
                continue
            out.append(cleaned)
            if len(out) >= _MAX_PICKED:
                break
        return out

    def _build_digest(self, property_id: str) -> str:
        root = self._wiki._wiki_dir / property_id
        if not root.is_dir():
            return ""
        lines: list[str] = []
        running = 0
        for path in sorted(root.rglob("*.md")):
            rel = path.relative_to(root)
            rel_posix = rel.as_posix()
            if rel.name in {"index.md", "log.md", "lint_report.md"}:
                continue
            if any(part.startswith("_") for part in rel.parts):
                continue
            try:
                content = path.read_text(encoding="utf-8")
            except OSError:
                continue
            name, desc = _extract_frontmatter_pair(content, fallback_name=rel.stem)
            if len(desc) > _MAX_DIGEST_DESC_CHARS:
                desc = desc[:_MAX_DIGEST_DESC_CHARS] + "…"
            line = f"- {rel_posix} | {name} | {desc}"
            if running + len(line) + 1 > _MAX_DIGEST_CHARS:
                lines.append("- …[digest truncated]")
                break
            lines.append(line)
            running += len(line) + 1
        return "\n".join(lines)

    async def _read_picked(self, *, property_id: str, paths: list[str]) -> str:
        if not paths:
            return ""
        chunks: list[str] = []
        running = 0
        for rel in paths:
            content = await self._wiki.read_file(f"{property_id}/{rel}")
            if content is None:
                log.warning("ask_picked_missing", property_id=property_id, rel=rel)
                continue
            if len(content) > _MAX_PAGE_CHARS:
                content = content[:_MAX_PAGE_CHARS] + "\n…[truncated]"
            block = f"=== {property_id}/{rel} ===\n{content}\n"
            if running + len(block) > _MAX_PICKED_TOTAL_CHARS:
                log.info("ask_picked_budget_hit", consumed=running, dropped=rel)
                break
            chunks.append(block)
            running += len(block)
        return ("\n".join(chunks) + "\n") if chunks else ""

    def _pin_answer(
        self,
        *,
        property_id: str,
        question: str,
        answer: str,
        cited_path: str | None,
    ) -> str | None:
        wiki_dir = self._wiki._wiki_dir
        property_root = wiki_dir / property_id
        if not property_root.is_dir():
            return None
        slug = _slug(question)
        date = datetime.now(UTC).strftime("%Y-%m-%d")
        rel = f"topics/{date}-{slug}.md"
        target = property_root / rel
        if target.exists():
            return rel
        body_lines = [
            f"**Question:** {question}",
            "",
            f"**Answer:** {answer}",
        ]
        if cited_path:
            body_lines.extend(["", f"**Cited:** [[{cited_path}]]"])
        frontmatter = {
            "name": f"topic-{slug}",
            "description": f"Pinned answer to: {question[:200]}",
        }
        atomic_write_text(target, render_page(frontmatter=frontmatter, body="\n".join(body_lines)))
        regenerate_index(property_root)
        commit_all(wiki_dir, message=f"ask({property_id}): pin {slug}")
        return rel


_FRONTMATTER_KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*):\s?(.*)$")


def _approx_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, len(text) // 4)


def _extract_frontmatter_pair(content: str, *, fallback_name: str) -> tuple[str, str]:
    """Permissive frontmatter pull: returns (name, description).

    Doesn't rely on YAML — descriptions in this wiki contain bare colons
    (e.g. ``scope (Branche X)``) that yaml.safe_load rejects. Walks the
    leading ``---`` block line by line, picks up ``name`` and
    ``description`` keys, ignores the rest.
    """
    if not content.startswith("---\n"):
        return fallback_name, ""
    end = content.find("\n---\n", 4)
    if end == -1:
        return fallback_name, ""
    raw = content[4:end]
    name = fallback_name
    description = ""
    for line in raw.splitlines():
        match = _FRONTMATTER_KEY_RE.match(line)
        if not match:
            continue
        key, value = match.group(1), match.group(2).strip()
        if key == "name" and value:
            name = value
        elif key == "description" and value:
            description = value.strip("\"'")
    return name, description


def _render_cached_context(*, property_id: str, tree_listing: str, digest: str) -> str:
    return (
        f"Property: {property_id}\n\n"
        f"=== File tree ===\n{tree_listing}\n\n"
        f"=== Pages digest (path | name | description) ===\n{digest}\n"
    )


def _render_history(history: list[tuple[str, str]]) -> str:
    if not history:
        return ""
    turns = history[-_MAX_HISTORY_TURNS:]
    lines = ["=== Prior conversation (oldest first) ==="]
    for q, a in turns:
        trimmed = a if len(a) <= _MAX_HISTORY_ANSWER_CHARS else a[:_MAX_HISTORY_ANSWER_CHARS] + "…"
        lines.append(f"User: {q}")
        lines.append(f"Assistant: {trimmed}")
    return "\n".join(lines) + "\n\n"


def _route_question(history: list[tuple[str, str]], question: str) -> str:
    if not history:
        return question
    recent = history[-_MAX_HISTORY_TURNS:]
    recap = " | ".join(q for q, _ in recent)
    return f"Recent user questions: {recap}\nNew question: {question}"


def _render_tree(node: TreeNode, depth: int = 0) -> str:
    indent = "  " * depth
    line = f"{indent}{node.path}{'/' if node.type == 'dir' else ''}"
    if node.children:
        return "\n".join([line, *(_render_tree(c, depth + 1) for c in node.children)])
    return line


def _parse_result(raw: str) -> AskResult:
    try:
        data = parse_json_object(raw)
    except ValueError as exc:
        log.warning("ask_parse_failed", error=str(exc))
        return AskResult(answer=raw.strip() or None, path=None)
    answer = data.get("answer")
    path = data.get("path")
    return AskResult(
        answer=str(answer) if isinstance(answer, str) and answer.strip() else None,
        path=str(path) if isinstance(path, str) and path.strip() else None,
    )


def _slug(text: str) -> str:
    base = _SLUG_RE.sub("-", text.lower()).strip("-")
    return (base[:48] or "topic").rstrip("-")


def get_ask_service(
    settings: Annotated[Settings, Depends(get_settings)],
    wiki: Annotated[WikiService, Depends(get_wiki_service)],
    llm: Annotated[LLMClient, Depends(get_llm_client)],
) -> AskService:
    return AskService(wiki=wiki, llm=llm, model=settings.fast_model)
