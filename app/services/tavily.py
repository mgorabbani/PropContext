from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Literal

import structlog

from app.core.config import Settings

log = structlog.get_logger(__name__)


@dataclass(frozen=True)
class ExtractedPage:
    url: str
    raw_content: str


@dataclass(frozen=True)
class WebHit:
    title: str
    url: str
    content: str
    score: float


class TavilyDisabled(RuntimeError):
    """Raised when Tavily is requested but no API key is configured."""


@lru_cache(maxsize=1)
def _client_for_key(api_key: str) -> Any:
    from tavily import AsyncTavilyClient  # noqa: PLC0415  # lazy: avoid import cost when key absent

    return AsyncTavilyClient(api_key=api_key)


def get_tavily_client(settings: Settings) -> Any | None:
    if not settings.tavily_api_key:
        return None
    return _client_for_key(settings.tavily_api_key)


async def extract_url(
    url: str,
    *,
    settings: Settings,
    extract_depth: Literal["basic", "advanced"] = "basic",
) -> ExtractedPage | None:
    client = get_tavily_client(settings)
    if client is None:
        return None
    try:
        response = await client.extract(
            urls=url,
            extract_depth=extract_depth,
            format="markdown",
        )
    except Exception as exc:
        log.warning("tavily_extract_failed", url=url, err=str(exc))
        return None
    results = response.get("results") or []
    if not results:
        return None
    raw = (results[0].get("raw_content") or "").strip()
    if not raw:
        return None
    return ExtractedPage(url=results[0].get("url") or url, raw_content=raw)


async def search_web(
    query: str,
    *,
    settings: Settings,
    max_results: int = 5,
    topic: Literal["general", "news"] = "general",
    include_domains: list[str] | None = None,
) -> list[WebHit]:
    client = get_tavily_client(settings)
    if client is None:
        raise TavilyDisabled("APP_TAVILY_API_KEY not set")
    response = await client.search(
        query=query,
        max_results=max_results,
        topic=topic,
        include_domains=include_domains or [],
    )
    hits: list[WebHit] = []
    for item in response.get("results") or []:
        hits.append(
            WebHit(
                title=str(item.get("title") or ""),
                url=str(item.get("url") or ""),
                content=str(item.get("content") or ""),
                score=float(item.get("score") or 0.0),
            )
        )
    return hits
