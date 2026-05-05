from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import structlog
from fastapi import Depends

from app.core.config import Settings, get_settings
from app.services.llm.client import (
    AgentResponse,
    LLMClient,
    UsageRecorder,
    get_llm_client,
)
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
    '- If they ask for ALL of something ("name all 35 owners", "liste alle '
    'Dienstleister"), enumerate every matching item from the digest. Do NOT '
    'abbreviate with "and N more" or "available in individual files" — the '
    "names are right there in the digest descriptions; pull them out.\n"
    '- For counts ("how many X"), give the count plus the full list when the '
    "set is ≤ 50 items.\n"
    "- For lookups about specific data (amounts, dates), use the picked "
    "pages.\n"
    '- For follow-ups ("that one", "before"), use prior turns.\n\n'
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

_MAX_AGENT_TURNS = 6
_TOOL_FILE_CHAR_CAP = 12000
_TOOL_LIST_CAP = 200
_TOOL_GREP_MATCH_CAP = 60

_AGENT_SYSTEM_PROMPT = (
    "You answer questions about a property's markdown wiki by navigating it "
    "with tools.\n\n"
    "Tools available:\n"
    "  - list_dir(path): list .md files under a directory ('' for root).\n"
    "  - summary(path): for every .md file under the directory, return its "
    "frontmatter `name | description`. Cheap triage — prefer this to opening "
    "each file when the question is a list/count or you need to filter by "
    "category (Branche, type, status). One summary() of a 16-file directory "
    "costs ~1k tokens; reading all 16 files costs ~5k.\n"
    "  - read_file(path): full file content (12k char cap). Only after "
    "summary or grep narrows things down.\n"
    "  - grep(pattern): regex over all .md files; returns 'path:line: match'. "
    "Use to locate which files mention a keyword.\n\n"
    "Strategy:\n"
    "  1. Start with grep, list_dir, or summary — never blanket-read a "
    "directory.\n"
    "  2. For collection / filter questions ('list all X', 'how many Y', "
    "'which DL handles Z'), summary alone usually answers it; only read "
    "files when you need data the description doesn't cover (amounts, "
    "dates, contract terms, contact details).\n"
    "  3. Stop calling tools as soon as you can answer.\n\n"
    "When done, respond with a single JSON object and no prose outside it: "
    '{"answer": string|null, "path": string|null}. Set `path` to the file '
    "(relative to the property root) that best grounds the answer, or null. "
    "Answer in the language of the question. Use prior turns to resolve "
    "references like 'before' or 'that one'. Never claim you cannot access a "
    "file — if read_file errors, try a different path."
)

AGENT_TOOLS: list[dict] = [
    {
        "name": "list_dir",
        "description": (
            "List markdown files under a directory of the property's wiki. "
            "Path is relative to the property root; pass '' to list the root."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative directory path, e.g. '04_dienstleister' or ''.",
                }
            },
            "required": ["path"],
        },
    },
    {
        "name": "summary",
        "description": (
            "For every .md file under a directory, return its frontmatter "
            "name and description as 'path | name | description'. Cheap "
            "triage for list / count / filter questions — far less expensive "
            "than reading each file. Path is relative to the property root; "
            "'' for the whole property."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative directory path, e.g. '04_dienstleister'.",
                }
            },
            "required": ["path"],
        },
    },
    {
        "name": "read_file",
        "description": (
            "Read a markdown file from the property's wiki. Path is relative "
            "to the property root, e.g. '07_timeline.md' or "
            "'04_dienstleister/DL-001.md'. Truncated to ~12k chars."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative file path. Must end with .md.",
                }
            },
            "required": ["path"],
        },
    },
    {
        "name": "grep",
        "description": (
            "Regex-search the property's markdown files. Returns the first "
            "60 matches as 'path:line: match'. Use to find which files "
            "mention a keyword, ID, name, or Branche."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Python regex (case-insensitive).",
                }
            },
            "required": ["pattern"],
        },
    },
]


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
        on_step: Callable[[AskStep], Awaitable[None]] | None = None,
    ) -> AskResult:
        history = history or []
        if not (self._wiki._wiki_dir / property_id).is_dir():
            return AskResult(answer=f"property {property_id!r} not found", path=None)
        if hasattr(self._llm, "complete_agent"):
            return await self._answer_agent(
                property_id=property_id,
                question=question,
                pin=pin,
                history=history,
                on_step=on_step,
            )
        return await self._answer_digest(
            property_id=property_id,
            question=question,
            pin=pin,
            history=history,
        )

    async def _answer_digest(
        self,
        *,
        property_id: str,
        question: str,
        pin: bool,
        history: list[tuple[str, str]],
    ) -> AskResult:
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

        user_prompt = f"{page_blocks}{history_block}=== Question ===\n{question}\n"
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
        return AskResult(answer=result.answer, path=result.path, usage=usage, steps=steps)

    async def _answer_agent(
        self,
        *,
        property_id: str,
        question: str,
        pin: bool,
        history: list[tuple[str, str]],
        on_step: Callable[[AskStep], Awaitable[None]] | None = None,
    ) -> AskResult:
        from claude_agent_sdk import (
            AssistantMessage,
            ClaudeAgentOptions,
            ResultMessage,
            TextBlock,
            ToolUseBlock,
            query,
        )

        steps: list[AskStep] = []

        async def push_step(step: AskStep) -> None:
            steps.append(step)
            if on_step is not None:
                await on_step(step)

        prop_root = (self._wiki._wiki_dir / property_id).resolve()
        history_block = _render_history(history)
        prompt_text = f"{history_block}=== Question ===\n{question}\n"
        system_prompt = (
            "Answer questions about a property's markdown wiki via Read/Glob/Grep.\n"
            f"Root: {prop_root}. Cited paths in your reply MUST be relative "
            "(e.g. '07_timeline.md', '04_dienstleister/DL-001.md').\n\n"
            "Rules:\n"
            "- Issue independent Glob/Grep calls in PARALLEL in a single turn.\n"
            "- Listing/counting: Glob frontmatter, do NOT Read each file.\n"
            "- Read only when exact wording is required; use offset/limit.\n"
            "- Stop tools the moment you can answer.\n\n"
            'Final reply: ONE JSON object, no prose: {"answer": str|null, "path": str|null}.\n'
            "Match user language. Resolve 'that one'/'before' from prior turns."
        )
        options = ClaudeAgentOptions(
            system_prompt=system_prompt,
            allowed_tools=["Read", "Glob", "Grep"],
            permission_mode="default",
            cwd=str(prop_root),
            max_turns=_MAX_AGENT_TURNS,
            model=self._model,
        )

        final_text = ""
        sdk_usage: dict | None = None
        async for msg in query(prompt=prompt_text, options=options):
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, ToolUseBlock):
                        arg_repr = _summarize_sdk_tool_input(block.name, block.input)
                        paths = _sdk_tool_paths(block.name, block.input, prop_root)
                        await push_step(
                            AskStep(
                                label=f"{block.name}({arg_repr})",
                                detail=None,
                                paths=paths,
                            )
                        )
                    elif isinstance(block, TextBlock):
                        final_text = block.text
            elif isinstance(msg, ResultMessage):
                if msg.result:
                    final_text = msg.result
                if isinstance(msg.usage, dict):
                    sdk_usage = msg.usage
        await push_step(AskStep(label="Composed answer"))

        result = _parse_result(final_text)
        cited_path = _relativize_path(result.path, prop_root)
        u = sdk_usage or {}
        usage = AskUsage(
            input_tokens=int(u.get("input_tokens", 0) or 0),
            output_tokens=int(u.get("output_tokens", 0) or 0),
            cache_read_input_tokens=int(u.get("cache_read_input_tokens", 0) or 0),
            cache_creation_input_tokens=int(
                u.get("cache_creation_input_tokens", 0) or 0
            ),
            sections={
                "system": _approx_tokens(system_prompt),
                "history": _approx_tokens(history_block),
                "question": _approx_tokens(question),
            },
        )
        if pin and result.answer:
            pinned = self._pin_answer(
                property_id=property_id,
                question=question,
                answer=result.answer,
                cited_path=cited_path,
            )
            return AskResult(
                answer=result.answer,
                path=cited_path,
                pinned_path=pinned,
                usage=usage,
                steps=steps,
            )
        return AskResult(answer=result.answer, path=cited_path, usage=usage, steps=steps)

    async def _exec_tool(
        self, *, property_id: str, name: str, args: dict
    ) -> tuple[str, str, str | None]:
        if name == "list_dir":
            rel = str(args.get("path", "") or "").strip().lstrip("/")
            return self._tool_list_dir(property_id=property_id, rel=rel)
        if name == "summary":
            rel = str(args.get("path", "") or "").strip().lstrip("/")
            return self._tool_summary(property_id=property_id, rel=rel)
        if name == "read_file":
            rel = str(args.get("path", "") or "").strip().lstrip("/")
            return await self._tool_read_file(property_id=property_id, rel=rel)
        if name == "grep":
            pattern = str(args.get("pattern", "") or "")
            return self._tool_grep(property_id=property_id, pattern=pattern)
        return (f"error: unknown tool {name!r}", f"unknown tool {name!r}", None)

    def _tool_list_dir(self, *, property_id: str, rel: str) -> tuple[str, str, str | None]:
        root = self._wiki._wiki_dir / property_id
        target = (root / rel).resolve() if rel else root.resolve()
        try:
            target.relative_to(root.resolve())
        except ValueError:
            return ("error: path escapes property root", "rejected: out-of-tree", None)
        if not target.is_dir():
            return (f"error: not a directory: {rel}", f"missing: {rel or '.'}", None)
        rows: list[str] = []
        for p in sorted(target.rglob("*.md")):
            rel_path = p.relative_to(root).as_posix()
            if any(part.startswith("_") for part in p.relative_to(root).parts):
                continue
            rows.append(rel_path)
            if len(rows) >= _TOOL_LIST_CAP:
                rows.append(f"…[truncated at {_TOOL_LIST_CAP}]")
                break
        body = "\n".join(rows) if rows else "(empty)"
        return (body, f"{len(rows)} entries under {rel or '.'}", None)

    def _tool_summary(self, *, property_id: str, rel: str) -> tuple[str, str, str | None]:
        root = self._wiki._wiki_dir / property_id
        target = (root / rel).resolve() if rel else root.resolve()
        try:
            target.relative_to(root.resolve())
        except ValueError:
            return ("error: path escapes property root", "rejected: out-of-tree", None)
        if not target.is_dir():
            return (f"error: not a directory: {rel}", f"missing: {rel or '.'}", None)
        rows: list[str] = []
        for path in sorted(target.rglob("*.md")):
            relp = path.relative_to(root)
            if any(part.startswith("_") for part in relp.parts):
                continue
            if relp.name in {"index.md", "log.md", "lint_report.md"}:
                continue
            try:
                content = path.read_text(encoding="utf-8")
            except OSError:
                continue
            name, desc = _extract_frontmatter_pair(content, fallback_name=relp.stem)
            if len(desc) > _MAX_DIGEST_DESC_CHARS:
                desc = desc[:_MAX_DIGEST_DESC_CHARS] + "…"
            rows.append(f"{relp.as_posix()} | {name} | {desc}")
            if len(rows) >= _TOOL_LIST_CAP:
                rows.append(f"…[truncated at {_TOOL_LIST_CAP}]")
                break
        body = "\n".join(rows) if rows else "(no .md files)"
        return (body, f"{len(rows)} files summarised under {rel or '.'}", None)

    async def _tool_read_file(self, *, property_id: str, rel: str) -> tuple[str, str, str | None]:
        if not rel:
            return ("error: path required", "missing path arg", None)
        try:
            content = await self._wiki.read_file(f"{property_id}/{rel}")
        except ValueError:
            return ("error: invalid path", f"invalid: {rel}", None)
        if content is None:
            return (f"error: file not found: {rel}", f"missing: {rel}", None)
        truncated = len(content) > _TOOL_FILE_CHAR_CAP
        body = content[:_TOOL_FILE_CHAR_CAP] + "\n…[truncated]" if truncated else content
        summary = f"{len(content)} chars" + (" (truncated)" if truncated else "")
        return (body, summary, rel)

    def _tool_grep(self, *, property_id: str, pattern: str) -> tuple[str, str, str | None]:
        if not pattern:
            return ("error: pattern required", "missing pattern", None)
        try:
            regex = re.compile(pattern, re.IGNORECASE)
        except re.error as exc:
            return (f"error: bad regex: {exc}", "bad regex", None)
        root = self._wiki._wiki_dir / property_id
        matches: list[str] = []
        for path in sorted(root.rglob("*.md")):
            rel = path.relative_to(root)
            if any(part.startswith("_") for part in rel.parts):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            for lineno, line in enumerate(text.splitlines(), start=1):
                if regex.search(line):
                    snippet = line.strip()[:200]
                    matches.append(f"{rel.as_posix()}:{lineno}: {snippet}")
                    if len(matches) >= _TOOL_GREP_MATCH_CAP:
                        break
            if len(matches) >= _TOOL_GREP_MATCH_CAP:
                matches.append(f"…[truncated at {_TOOL_GREP_MATCH_CAP}]")
                break
        body = "\n".join(matches) if matches else "(no matches)"
        return (body, f"{len(matches)} match(es)", None)

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


def _summarize_tool_input(name: str, args: dict) -> str:
    if name == "grep":
        return repr(args.get("pattern", ""))[:60]
    return str(args.get("path", ""))[:80]


def _summarize_sdk_tool_input(name: str, args: dict) -> str:
    if name == "Grep":
        return repr(args.get("pattern", ""))[:60]
    if name == "Glob":
        return repr(args.get("pattern", ""))[:60]
    if name == "Read":
        path = str(args.get("file_path", ""))
        offset = args.get("offset")
        limit = args.get("limit")
        if offset is not None or limit is not None:
            return f"{path}, offset={offset}, limit={limit}"
        return path[:80]
    return str(args.get("path", "") or args.get("file_path", ""))[:80]


def _sdk_tool_paths(name: str, args: dict, prop_root: Path) -> list[str] | None:
    if name == "Read":
        rel = _relativize_path(str(args.get("file_path", "")), prop_root)
        return [rel] if rel else None
    return None


def _relativize_path(path: str | None, prop_root: Path) -> str | None:
    if not path:
        return None
    p = Path(path)
    try:
        if p.is_absolute():
            return p.resolve().relative_to(prop_root).as_posix()
    except ValueError:
        return None
    return path.lstrip("/")


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
