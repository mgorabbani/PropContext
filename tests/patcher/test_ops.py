from __future__ import annotations

from app.services.patcher.ops import (
    HUMAN_NOTES_HEADING,
    append_section,
    create_page,
    parse_frontmatter,
    prepend_log,
    render_page,
    upsert_section,
)


def test_render_page_emits_frontmatter_and_body() -> None:
    out = render_page(
        frontmatter={"name": "x", "description": "y"},
        body="Hello",
    )
    assert out.startswith("---\n")
    assert "name: x" in out
    assert "description: y" in out
    assert out.rstrip().endswith("Hello")


def test_parse_frontmatter_roundtrip() -> None:
    rendered = render_page(frontmatter={"name": "a", "description": "b"}, body="body")
    fm, body = parse_frontmatter(rendered)
    assert fm == {"name": "a", "description": "b"}
    assert body.strip() == "body"


def test_create_page_is_idempotent() -> None:
    rendered = render_page(frontmatter={"name": "x", "description": "y"}, body="initial")
    out = create_page(path_exists=True, existing=rendered, frontmatter=None, body="new")
    assert out == rendered


def test_upsert_section_replaces_existing_body() -> None:
    content = "## Status\n\nold\n\n## Other\n\nkeep me\n"
    out = upsert_section(content, heading="Status", body="new")
    assert "new" in out
    assert "old" not in out
    assert "keep me" in out


def test_upsert_section_appends_when_missing() -> None:
    content = "## Status\n\nfoo\n"
    out = upsert_section(content, heading="Aliases", body="- alt-name")
    assert "## Aliases" in out
    assert "alt-name" in out
    assert "foo" in out


def test_append_section_creates_then_appends() -> None:
    after_create = append_section("", heading="Timeline", line="- 2026-04-25 a")
    assert "## Timeline" in after_create
    after_append = append_section(after_create, heading="Timeline", line="- 2026-04-26 b")
    assert "- 2026-04-25 a" in after_append
    assert "- 2026-04-26 b" in after_append
    assert after_append.index("- 2026-04-25 a") < after_append.index("- 2026-04-26 b")


def test_prepend_log_inserts_below_h1() -> None:
    log = "# Log\n\n- earlier\n"
    out = prepend_log(log, line="- newer")
    assert out.index("- newer") < out.index("- earlier")
    assert out.startswith("# Log")


def test_upsert_section_respects_human_notes_boundary() -> None:
    content = f"## Status\n\nfoo\n\n{HUMAN_NOTES_HEADING}\n\nhuman-only stuff\n"
    out = upsert_section(content, heading="Status", body="bar")
    assert "bar" in out
    assert "human-only stuff" in out
    assert out.index("bar") < out.index(HUMAN_NOTES_HEADING)
