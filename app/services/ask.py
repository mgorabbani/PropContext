from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

import structlog
from fastapi import Depends

from app.core.config import Settings, get_settings
from app.services.llm.client import LLMClient, get_llm_client
from app.services.llm.json import parse_json_object
from app.services.wiki import TreeNode, WikiService, get_wiki_service

log = structlog.get_logger(__name__)

_SYSTEM_PROMPT = (
    "You are the Buena property wiki assistant. The user asks questions about a "
    "single property. You have:\n"
    "  • the property index (`index.md`)\n"
    "  • a directory tree of all wiki files for the property\n\n"
    "Answer the user's question using only the provided wiki content. If the "
    "answer lives in a specific wiki file, return its path (relative to wiki_dir) "
    "in the `path` field so the UI can open it. If you can answer in plain text, "
    "use the `answer` field. You may use both. Be concise. Cite section headings "
    "when helpful.\n\n"
    'Respond with a single JSON object: `{"answer": string|null, "path": string|null}`. '
    "No prose outside the JSON."
)


@dataclass(frozen=True, slots=True)
class AskResult:
    answer: str | None
    path: str | None


class AskService:
    def __init__(self, *, wiki: WikiService, llm: LLMClient, model: str) -> None:
        self._wiki = wiki
        self._llm = llm
        self._model = model

    async def answer(self, *, property_id: str, question: str) -> AskResult:
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
        return _parse_result(raw)


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


def get_ask_service(
    settings: Annotated[Settings, Depends(get_settings)],
    wiki: Annotated[WikiService, Depends(get_wiki_service)],
    llm: Annotated[LLMClient, Depends(get_llm_client)],
) -> AskService:
    return AskService(wiki=wiki, llm=llm, model=settings.fast_model)
