"""Optional smoke test for the Anthropic SDK migration.

Runs a single ``client.complete`` call against the live Anthropic API to confirm
end-to-end wiring (SDK import, model alias, prompt-cache header). Intentionally
skipped if ``ANTHROPIC_API_KEY`` is not set so it stays safe to run anywhere.

Usage::

    ANTHROPIC_API_KEY=sk-... uv run python scripts/_anthropic_smoke.py

This script is not invoked from CI or pytest; it exists only as a manual
verification helper for the gemini-removal / SDK swap.
"""

from __future__ import annotations

import asyncio
import os
import sys

from app.services.llm.client import AnthropicClient


async def _run() -> int:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ANTHROPIC_API_KEY not set — skipping live smoke test (intentional).")
        return 0

    client = AnthropicClient(api_key=api_key)
    text = await client.complete(
        model="claude-haiku-4-5",
        system_prompt="You are concise.",
        user_prompt="reply OK",
    )
    print(f"response: {text!r}")
    return 0 if text.strip() else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(_run()))
