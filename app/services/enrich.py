from __future__ import annotations

import asyncio
import ipaddress
import re
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

import structlog

from app.core.config import Settings
from app.services.llm.client import LLMClient
from app.services.tavily import ExtractedPage, extract_url

ToolCallback = Callable[[str, dict[str, Any]], Awaitable[None]]

log = structlog.get_logger(__name__)

_URL_RE = re.compile(
    r"https?://[^\s<>\"'\)\]\}]+",
    re.IGNORECASE,
)
_TRAILING_PUNCT = ".,;:!?)\"'»"

_PRIVATE_HOST_SUFFIXES = (".local", ".internal", ".lan", ".intranet")
_PRIVATE_HOST_NAMES = {"localhost"}
_MAX_PAGE_CHARS = 4000
_SUMMARISE_MIN_CHARS = 800
_SUMMARISE_INPUT_CAP = 12000

_SUMMARISER_SYSTEM_PROMPT = (
    "You compress fetched web pages into a tight bullet summary for a "
    "property-management AI extractor. Output at most 200 words. Keep "
    "dates, monetary amounts, IDs, names, addresses, and legal references "
    "verbatim. Drop boilerplate, navigation, and prose padding. Output "
    "markdown bullets, no headings, no preamble."
)


@dataclass(frozen=True)
class EnrichmentResult:
    enriched_text: str
    pages: list[ExtractedPage]
    skipped: list[str]


def extract_urls(text: str, *, limit: int) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for match in _URL_RE.finditer(text):
        url = match.group(0).rstrip(_TRAILING_PUNCT)
        if url in seen or not _is_public_url(url):
            continue
        seen.add(url)
        out.append(url)
        if len(out) >= limit:
            break
    return out


def _is_public_url(url: str) -> bool:
    try:
        parts = urlsplit(url)
    except ValueError:
        return False
    host = (parts.hostname or "").lower()
    if (
        not host
        or "." not in host
        or host in _PRIVATE_HOST_NAMES
        or any(host.endswith(suffix) for suffix in _PRIVATE_HOST_SUFFIXES)
    ):
        return False
    try:
        addr = ipaddress.ip_address(host)
    except ValueError:
        return True
    return not (addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved)


async def enrich_with_web_sources(
    *,
    normalized_text: str,
    settings: Settings,
    llm: LLMClient | None = None,
    on_tool_call: ToolCallback | None = None,
) -> EnrichmentResult:
    if not settings.enrich_urls or not settings.tavily_api_key or settings.enrich_max_urls == 0:
        return EnrichmentResult(enriched_text=normalized_text, pages=[], skipped=[])

    urls = extract_urls(normalized_text, limit=settings.enrich_max_urls)
    if not urls:
        return EnrichmentResult(enriched_text=normalized_text, pages=[], skipped=[])

    pages_or_none = await asyncio.gather(
        *(_fetch_with_event(url, settings=settings, emit=on_tool_call) for url in urls),
        return_exceptions=False,
    )
    pages: list[ExtractedPage] = []
    skipped: list[str] = []
    for url, page in zip(urls, pages_or_none, strict=True):
        if page is None:
            skipped.append(url)
        else:
            pages.append(page)

    if not pages:
        return EnrichmentResult(enriched_text=normalized_text, pages=[], skipped=skipped)

    if llm is not None:
        pages = await _summarise_pages(pages, llm=llm, settings=settings, emit=on_tool_call)

    return EnrichmentResult(
        enriched_text=_append_web_sources(normalized_text, pages),
        pages=pages,
        skipped=skipped,
    )


async def _summarise_pages(
    pages: list[ExtractedPage],
    *,
    llm: LLMClient,
    settings: Settings,
    emit: ToolCallback | None,
) -> list[ExtractedPage]:
    return await asyncio.gather(
        *(summarise_page(page, llm=llm, settings=settings, emit=emit) for page in pages)
    )


async def summarise_page(
    page: ExtractedPage,
    *,
    llm: LLMClient,
    settings: Settings,
    emit: ToolCallback | None = None,
) -> ExtractedPage:
    """Replace a fetched page's body with a fast-model summary.

    Pages under ``_SUMMARISE_MIN_CHARS`` pass through unchanged — summarising
    them costs more tokens than it saves. Spending Haiku tokens to compress
    Sonnet input is net-positive at the current price ratio.
    """
    body = page.raw_content or ""
    if len(body) < _SUMMARISE_MIN_CHARS:
        return page

    prompt = f"URL: {page.url}\n\nContent:\n{body[:_SUMMARISE_INPUT_CAP]}"
    if emit is not None:
        await emit(
            "enrich.summarise",
            {"url": page.url, "input_chars": len(body), "status": "start"},
        )
    t0 = time.monotonic()
    try:
        summary = await llm.complete(
            model=settings.fast_model,
            system_prompt=_SUMMARISER_SYSTEM_PROMPT,
            user_prompt=prompt,
        )
    except Exception as exc:
        log.warning("enrich_summarise_failed", url=page.url, error=str(exc))
        if emit is not None:
            await emit(
                "enrich.summarise",
                {"url": page.url, "status": "fail", "error": str(exc)},
            )
        return page
    elapsed_ms = int((time.monotonic() - t0) * 1000)
    summary_text = summary.strip()
    if not summary_text:
        return page
    if emit is not None:
        await emit(
            "enrich.summarise",
            {
                "url": page.url,
                "input_chars": len(body),
                "output_chars": len(summary_text),
                "ms": elapsed_ms,
                "status": "ok",
            },
        )
    return ExtractedPage(url=page.url, raw_content=summary_text)


async def _fetch_with_event(
    url: str, *, settings: Settings, emit: ToolCallback | None
) -> ExtractedPage | None:
    if emit is not None:
        await emit("enrich.tool", {"tool": "tavily_extract", "url": url, "status": "start"})
    t0 = time.monotonic()
    page = await extract_url(url, settings=settings)
    elapsed_ms = int((time.monotonic() - t0) * 1000)
    if emit is not None:
        await emit(
            "enrich.tool",
            {
                "tool": "tavily_extract",
                "url": url,
                "status": "ok" if page is not None else "fail",
                "ms": elapsed_ms,
                "chars": len(page.raw_content) if page is not None else 0,
            },
        )
    return page


def _append_web_sources(normalized_text: str, pages: list[ExtractedPage]) -> str:
    chunks: list[str] = [normalized_text.rstrip(), "", "## Linked web sources", ""]
    for idx, page in enumerate(pages, start=1):
        body = page.raw_content.strip()
        if len(body) > _MAX_PAGE_CHARS:
            body = body[:_MAX_PAGE_CHARS].rstrip() + "\n\n[...truncated]"
        chunks.append(f"### [{idx}] {page.url}")
        chunks.append("")
        chunks.append(body)
        chunks.append("")
    return "\n".join(chunks).rstrip() + "\n"
