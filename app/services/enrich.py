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

    return EnrichmentResult(
        enriched_text=_append_web_sources(normalized_text, pages),
        pages=pages,
        skipped=skipped,
    )


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
