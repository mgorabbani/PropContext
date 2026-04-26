from __future__ import annotations

from unittest.mock import patch

import pytest

from app.core.config import Settings
from app.services import enrich
from app.services.enrich import (
    EnrichmentResult,
    _is_public_url,
    enrich_with_web_sources,
    extract_urls,
)
from app.services.tavily import ExtractedPage


@pytest.fixture
def tavily_settings(tmp_path) -> Settings:
    return Settings(
        data_dir=tmp_path / "data",
        output_dir=tmp_path / "output",
        wiki_dir=tmp_path / "wiki",
        normalize_dir=tmp_path / "normalize",
        llm_provider="fake",
        tavily_api_key="tvly-test",
        enrich_urls=True,
        enrich_max_urls=5,
    )


def test_extract_urls_finds_unique_public_urls() -> None:
    text = (
        "See https://example.com/quote/abc and https://example.com/quote/abc again. "
        "Also https://www.gesetze-im-internet.de/bgb/__535.html."
    )
    urls = extract_urls(text, limit=5)
    assert urls == [
        "https://example.com/quote/abc",
        "https://www.gesetze-im-internet.de/bgb/__535.html",
    ]


def test_extract_urls_respects_limit() -> None:
    text = " ".join(f"https://site{i}.example.com/" for i in range(10))
    urls = extract_urls(text, limit=3)
    assert len(urls) == 3


def test_extract_urls_strips_trailing_punctuation() -> None:
    text = "Visit https://example.com/page, then continue."
    assert extract_urls(text, limit=5) == ["https://example.com/page"]


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost/foo",
        "http://127.0.0.1/foo",
        "http://10.0.0.1/foo",
        "http://192.168.1.1/foo",
        "http://server.local/foo",
        "http://intranet.internal/x",
        "http://nodot/foo",
    ],
)
def test_is_public_url_rejects_private(url: str) -> None:
    assert _is_public_url(url) is False


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/page",
        "https://www.gesetze-im-internet.de/bgb/__535.html",
        "http://93.184.216.34/path",
    ],
)
def test_is_public_url_accepts_public(url: str) -> None:
    assert _is_public_url(url) is True


async def test_enrich_disabled_when_no_key(tmp_path) -> None:
    settings = Settings(
        data_dir=tmp_path / "data",
        output_dir=tmp_path / "output",
        wiki_dir=tmp_path / "wiki",
        normalize_dir=tmp_path / "normalize",
        llm_provider="fake",
        tavily_api_key=None,
    )
    text = "See https://example.com/page"
    result = await enrich_with_web_sources(normalized_text=text, settings=settings)
    assert result == EnrichmentResult(enriched_text=text, pages=[], skipped=[])


async def test_enrich_appends_extracted_pages(tavily_settings: Settings) -> None:
    text = "Quote at https://vendor.example.com/quote/123 and notice https://localhost/secret"

    async def fake_extract(
        url: str, *, settings: Settings, extract_depth: str = "basic"
    ) -> ExtractedPage | None:
        return ExtractedPage(url=url, raw_content=f"# Page for {url}\n\nBody.")

    with patch.object(enrich, "extract_url", side_effect=fake_extract):
        result = await enrich_with_web_sources(normalized_text=text, settings=tavily_settings)

    assert [p.url for p in result.pages] == ["https://vendor.example.com/quote/123"]
    assert result.skipped == []
    assert "## Linked web sources" in result.enriched_text
    assert "Body." in result.enriched_text


async def test_enrich_records_skipped_failures(tavily_settings: Settings) -> None:
    text = "See https://broken.example.com/x"

    async def fake_extract(
        url: str, *, settings: Settings, extract_depth: str = "basic"
    ) -> ExtractedPage | None:
        return None

    with patch.object(enrich, "extract_url", side_effect=fake_extract):
        result = await enrich_with_web_sources(normalized_text=text, settings=tavily_settings)

    assert result.pages == []
    assert result.skipped == ["https://broken.example.com/x"]
    assert result.enriched_text == text


async def test_enrich_emits_tool_call_events(tavily_settings: Settings) -> None:
    text = "See https://vendor.example.com/quote/123 and https://broken.example.com/x"
    events: list[tuple[str, dict]] = []

    async def emit(name: str, data: dict) -> None:
        events.append((name, data))

    async def fake_extract(
        url: str, *, settings: Settings, extract_depth: str = "basic"
    ) -> ExtractedPage | None:
        if "broken" in url:
            return None
        return ExtractedPage(url=url, raw_content="body")

    with patch.object(enrich, "extract_url", side_effect=fake_extract):
        await enrich_with_web_sources(
            normalized_text=text, settings=tavily_settings, on_tool_call=emit
        )

    assert all(name == "enrich.tool" for name, _ in events)
    starts = [d for name, d in events if d["status"] == "start"]
    finals = [d for name, d in events if d["status"] in {"ok", "fail"}]
    assert len(starts) == 2
    assert len(finals) == 2
    ok = next(d for d in finals if d["status"] == "ok")
    fail = next(d for d in finals if d["status"] == "fail")
    assert ok["tool"] == "tavily_extract"
    assert ok["url"] == "https://vendor.example.com/quote/123"
    assert ok["chars"] == 4
    assert fail["url"] == "https://broken.example.com/x"
    assert fail["chars"] == 0
