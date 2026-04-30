from __future__ import annotations

import json
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import anyio
import structlog
from anthropic import AsyncAnthropic
from fastmcp.exceptions import ToolError

from app.core.config import Settings

log = structlog.get_logger(__name__)

_SYSTEM_PROMPT = """You are an autonomous PropContext property-management agent.

You answer questions about a property's living-memory wiki. The wiki is on
the local filesystem at the path provided in your first user message — referred to
below as the WIKI ROOT.

**Constraints (soft — enforced by you, not by sandbox):**
- ONLY read and analyze files inside the WIKI ROOT directory.
- NEVER touch files outside the WIKI ROOT.
- NEVER run destructive commands (rm, mv, dd, > overwrite, kill, sudo, curl to mutate, etc.).
- NEVER write or edit wiki files unless the user explicitly asks you to.
- NEVER make network calls except web_search/web_fetch when the user explicitly asks.
- Bash is for analysis: cat, grep, find, wc, awk, jq, python -c. Read-only commands only.

**Wiki layout:**
- `index.md` at the root — catalog with one-line descriptions of every page
- `entities/` — people, companies, units (e.g. DL-010.md is a service provider)
- `contracts/` — service contracts, leases
- `04_assets/` — building, units, equipment
- `05_finances/` — invoices, payments, reconciliation
- Section anchors and `[[wikilinks]]` cross-reference pages

**Workflow per question:**
1. Read `index.md` first to understand what's available.
2. Use `grep` / `find` / `read_file` to drill into relevant pages.
3. Use bash freely for analysis (text processing, math, data extraction).
4. Cite specific page paths in your answer (e.g. `entities/DL-010.md`).
5. Show brief reasoning when computing a result.
6. Answer in the language of the question (German or English).
7. If the wiki doesn't contain the answer, say so plainly. Do not invent facts.

Domain context: German property management (WEG / BGB / BetrKV)."""


_TOOLS: list[dict[str, Any]] = [
    {
        "name": "bash",
        "description": (
            "Run a read-only bash command for analysis. Use for grep, find, cat, "
            "wc, awk, jq, python -c, etc. Working directory is the WIKI ROOT. "
            "Output is captured (stdout + stderr, max 50KB)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Shell command to run. Stay inside WIKI ROOT.",
                }
            },
            "required": ["command"],
        },
    },
    {
        "name": "read_file",
        "description": "Read a file from the WIKI ROOT. Path is relative to WIKI ROOT.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative path inside WIKI ROOT."}
            },
            "required": ["path"],
        },
    },
    {
        "name": "list_dir",
        "description": "List entries of a directory inside WIKI ROOT.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path inside WIKI ROOT (use '.' for root).",
                    "default": ".",
                }
            },
        },
    },
]

_MAX_OUT = 50_000


@dataclass(frozen=True, slots=True)
class AgentResult:
    answer: str
    iters: int
    tool_calls: int
    usage_tokens: dict[str, int]


class LocalAgentService:
    def __init__(self, *, settings: Settings) -> None:
        if not settings.anthropic_api_key:
            raise RuntimeError("APP_ANTHROPIC_API_KEY missing")
        self._client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        self._model = settings.agent_model
        self._max_iters = settings.agent_max_iters
        self._wiki_root = settings.wiki_dir.resolve()

    async def query(self, *, property_id: str, prompt: str) -> AgentResult:
        prop_dir = (self._wiki_root / property_id).resolve()
        if not str(prop_dir).startswith(str(self._wiki_root)):
            raise ToolError("property path escapes wiki root")
        if not prop_dir.is_dir():
            raise ToolError(f"property {property_id!r} not found")

        kickoff = (
            f"WIKI ROOT: {prop_dir}\n"
            f"Property ID: {property_id}\n\n"
            f"Question:\n{prompt}"
        )
        messages: list[dict[str, Any]] = [{"role": "user", "content": kickoff}]
        tool_calls = 0
        usage_in = 0
        usage_out = 0

        for iteration in range(1, self._max_iters + 1):
            resp = await self._client.messages.create(
                model=self._model,
                max_tokens=8192,
                system=_SYSTEM_PROMPT,
                tools=_TOOLS,
                messages=messages,
            )
            usage_in += resp.usage.input_tokens or 0
            usage_out += resp.usage.output_tokens or 0

            messages.append({"role": "assistant", "content": resp.content})

            if resp.stop_reason == "end_turn":
                text = "".join(b.text for b in resp.content if b.type == "text").strip()
                log.info(
                    "agent_done",
                    iters=iteration,
                    tool_calls=tool_calls,
                    in_tokens=usage_in,
                    out_tokens=usage_out,
                )
                return AgentResult(
                    answer=text or "(empty answer)",
                    iters=iteration,
                    tool_calls=tool_calls,
                    usage_tokens={"input": usage_in, "output": usage_out},
                )

            if resp.stop_reason != "tool_use":
                log.warning("agent_unexpected_stop", reason=resp.stop_reason)
                text = "".join(b.text for b in resp.content if b.type == "text").strip()
                return AgentResult(
                    answer=text or f"(stopped: {resp.stop_reason})",
                    iters=iteration,
                    tool_calls=tool_calls,
                    usage_tokens={"input": usage_in, "output": usage_out},
                )

            tool_results: list[dict[str, Any]] = []
            for block in resp.content:
                if block.type != "tool_use":
                    continue
                tool_calls += 1
                output, is_error = await self._run_tool(block.name, block.input, cwd=prop_dir)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": output[:_MAX_OUT],
                        "is_error": is_error,
                    }
                )
            messages.append({"role": "user", "content": tool_results})

        log.warning("agent_max_iters", iters=self._max_iters, tool_calls=tool_calls)
        return AgentResult(
            answer="(max iterations reached without final answer)",
            iters=self._max_iters,
            tool_calls=tool_calls,
            usage_tokens={"input": usage_in, "output": usage_out},
        )

    async def _run_tool(
        self, name: str, args: dict[str, Any], *, cwd: Path
    ) -> tuple[str, bool]:
        try:
            if name == "bash":
                return await _exec_bash(args.get("command", ""), cwd=cwd)
            if name == "read_file":
                return await _read_file(args.get("path", ""), root=cwd)
            if name == "list_dir":
                return await _list_dir(args.get("path", "."), root=cwd)
            return f"unknown tool: {name}", True
        except Exception as exc:
            log.warning("tool_error", tool=name, err=str(exc))
            return f"error: {exc}", True


async def _exec_bash(command: str, *, cwd: Path) -> tuple[str, bool]:
    if not command.strip():
        return "empty command", True
    proc = await anyio.run_process(
        ["bash", "-lc", command],
        cwd=str(cwd),
        check=False,
    )
    out = proc.stdout.decode("utf-8", errors="replace")
    err = proc.stderr.decode("utf-8", errors="replace")
    body = out + (f"\n[stderr]\n{err}" if err.strip() else "")
    return body or "(no output)", proc.returncode != 0


async def _read_file(path: str, *, root: Path) -> tuple[str, bool]:
    if not path:
        return "path required", True
    target = (root / path).resolve()
    if not str(target).startswith(str(root)):
        return f"path escapes wiki root: {path}", True
    if not target.is_file():
        return f"not a file: {path}", True
    body = await anyio.Path(target).read_text(encoding="utf-8", errors="replace")
    return body, False


async def _list_dir(path: str, *, root: Path) -> tuple[str, bool]:
    target = (root / path).resolve() if path != "." else root
    if not str(target).startswith(str(root)):
        return f"path escapes wiki root: {path}", True
    if not target.is_dir():
        return f"not a directory: {path}", True
    entries = sorted(p.name + ("/" if p.is_dir() else "") for p in target.iterdir())
    return json.dumps(entries, indent=2), False


# unused but keep around if you want a future quoted-arg helper
def _safe_quote(s: str) -> str:
    return shlex.quote(s)
