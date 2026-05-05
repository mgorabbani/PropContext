from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import Annotated, Protocol

import structlog
from anthropic import AsyncAnthropic
from fastapi import Depends

from app.core.config import REPO_ROOT, Settings, get_settings

log = structlog.get_logger(__name__)


class LLMClient(Protocol):
    async def complete(self, *, model: str, system_prompt: str, user_prompt: str) -> str:
        """Return raw model text for a single prompt."""


def prompt_hash(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


class AnthropicClient:
    """Anthropic Messages API client (SDK-backed) used behind the LLMClient protocol.

    Uses prompt caching on the system prompt so large stable context (schema, wiki rules)
    is billed at the cache-read rate after the first call. Verify cache hits via the
    ``usage.cache_read_input_tokens`` field on the response.
    """

    _MAX_TOKENS = 16000

    def __init__(self, *, api_key: str, timeout: float = 60.0) -> None:
        self._client = AsyncAnthropic(api_key=api_key, timeout=timeout)

    async def complete(self, *, model: str, system_prompt: str, user_prompt: str) -> str:
        response = await self._client.messages.create(
            model=model,
            max_tokens=self._MAX_TOKENS,
            system=[
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_prompt}],
        )
        usage = response.usage
        log.debug(
            "anthropic_complete",
            model=model,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cache_read_input_tokens=getattr(usage, "cache_read_input_tokens", 0) or 0,
            cache_creation_input_tokens=getattr(usage, "cache_creation_input_tokens", 0) or 0,
        )
        return "".join(block.text for block in response.content if block.type == "text")


class FakeLLMClient:
    """Offline LLM test double keyed by (model, prompt_hash(user_prompt))."""

    def __init__(self, responses: Mapping[object, str] | None = None) -> None:
        self.responses = dict(responses or {})
        self.calls: list[dict[str, str]] = []

    def add_response(self, *, model: str, user_prompt: str, response: str) -> None:
        self.responses[(model, prompt_hash(user_prompt))] = response

    async def complete(self, *, model: str, system_prompt: str, user_prompt: str) -> str:
        self.calls.append(
            {
                "model": model,
                "system_hash": prompt_hash(system_prompt),
                "prompt_hash": prompt_hash(user_prompt),
                "user_prompt": user_prompt,
            }
        )
        keys = (
            (model, prompt_hash(user_prompt)),
            (model, user_prompt),
            prompt_hash(user_prompt),
            model,
            "*",
        )
        for key in keys:
            if key in self.responses:
                return self.responses[key]
        return (
            '{"event_id":"","property_id":"LIE-001","summary":"fake empty plan",'
            '"ops":[],"review_items":[]}'
        )


def _system_prompt() -> str:
    return (REPO_ROOT / "schema" / "CLAUDE.md").read_text(encoding="utf-8")


def get_llm_client(
    settings: Annotated[Settings, Depends(get_settings)],
) -> LLMClient:
    match settings.llm_provider:
        case "anthropic":
            if settings.anthropic_api_key is None:
                return FakeLLMClient()
            return AnthropicClient(api_key=settings.anthropic_api_key)
        case "fake":
            return FakeLLMClient()
