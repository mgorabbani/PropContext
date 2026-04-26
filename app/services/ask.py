from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated

import structlog
from fastapi import Depends

from app.core.config import Settings, get_settings
from app.services.llm.client import LLMClient, get_llm_client
from app.services.llm.json import parse_json_object
from app.services.patcher.atomic import atomic_write_text
from app.services.patcher.git import commit_all
from app.services.patcher.ops import render_page
from app.services.wiki import TreeNode, WikiService, get_wiki_service
from app.services.wiki_index import regenerate_index

log = structlog.get_logger(__name__)

_SYSTEM_PROMPT = (
    "You answer questions against a property's markdown wiki. You receive: the "
    "property's index.md (catalog of all pages with one-line descriptions), the "
    "file tree, and the question.\n\n"
    "Answer using ONLY the provided wiki content. If the answer is grounded in "
    "one specific page, return its path (relative to the property root) in "
    "`path`. Always fill `answer` with a concise plain-text answer "
    "(1-3 sentences). Cite headings or wikilinks when helpful. Answer in the "
    "language of the question.\n\n"
    'Respond with a single JSON object: {"answer": string|null, "path": string|null}. '
    "No prose outside the JSON."
)

_SLUG_RE = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True, slots=True)
class AskResult:
    answer: str | None
    path: str | None
    pinned_path: str | None = None


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
    ) -> AskResult:
        index = await self._wiki.read_property(property_id)
        if index is None:
            return AskResult(answer=f"property {property_id!r} not found", path=None)
        tree = self._wiki.walk_tree(property_id)
        tree_listing = _render_tree(tree) if tree is not None else ""
        user_prompt = (
            f"Property: {property_id}\n\n"
            f"=== File tree ===\n{tree_listing}\n\n"
            f"=== {property_id}/index.md ===\n{index}\n\n"
            f"=== Question ===\n{question}\n"
        )
        raw = await self._llm.complete(
            model=self._model,
            system_prompt=_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )
        result = _parse_result(raw)
        if pin and result.answer:
            pinned = self._pin_answer(
                property_id=property_id,
                question=question,
                answer=result.answer,
                cited_path=result.path,
            )
            return AskResult(answer=result.answer, path=result.path, pinned_path=pinned)
        return result

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
