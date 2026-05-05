from __future__ import annotations

from pathlib import Path

from app.services.pages_filter import filter_relevant_pages


def _write(path: Path, frontmatter_desc: str = "", body: str = "body") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if frontmatter_desc:
        text = f"---\nname: page\ndescription: {frontmatter_desc}\n---\n\n{body}\n"
    else:
        text = body
    path.write_text(text, encoding="utf-8")


def _seed(root: Path) -> None:
    _write(root / "index.md", "Property root index")
    _write(root / "log.md", "Append-only log")
    _write(root / "building.md", "Synthesis overview")
    _write(root / "06_skills.md", "Hermes skills")
    _write(root / "entities/EH-014.md", "Unit EH-014 dossier — heating complaints.")
    _write(root / "entities/EH-099.md", "Unit EH-099 dossier — unrelated.")
    _write(root / "entities/EIG-009.md", "Owner EIG-009 — unrelated.")
    _write(root / "sources/EMAIL-12044.md", "Heating outage email referencing EH-014.")
    _write(
        root / "topics/heizung.md",
        "Heating outages across HAUS-12 — see EH-014 history.",
    )
    _write(root / "topics/garten.md", "Gardening notes for the courtyard.")


def test_filter_includes_essential_pages_even_without_match(tmp_path: Path) -> None:
    root = tmp_path / "LIE-001"
    _seed(root)
    pages = filter_relevant_pages(root, entity_ids=["EH-001"])
    assert "index.md" in pages
    assert "log.md" in pages
    assert "building.md" in pages
    assert "06_skills.md" in pages


def test_filter_keeps_pages_whose_path_mentions_entity(tmp_path: Path) -> None:
    root = tmp_path / "LIE-001"
    _seed(root)
    pages = filter_relevant_pages(root, entity_ids=["EH-014"])
    assert "entities/EH-014.md" in pages
    assert "entities/EH-099.md" not in pages
    assert "entities/EIG-009.md" not in pages


def test_filter_keeps_pages_whose_description_mentions_entity(tmp_path: Path) -> None:
    root = tmp_path / "LIE-001"
    _seed(root)
    pages = filter_relevant_pages(root, entity_ids=["EH-014"])
    assert "topics/heizung.md" in pages  # description mentions EH-014
    assert "topics/garten.md" not in pages


def test_filter_includes_source_pages_via_source_ids(tmp_path: Path) -> None:
    root = tmp_path / "LIE-001"
    _seed(root)
    pages = filter_relevant_pages(root, entity_ids=[], source_ids=["EMAIL-12044"])
    assert "sources/EMAIL-12044.md" in pages


def test_filter_skips_underscore_prefixed_paths(tmp_path: Path) -> None:
    root = tmp_path / "LIE-001"
    _seed(root)
    _write(root / "_hermes_proposals.md", "Proposals — references EH-014.")
    _write(root / "_state.md", "internal")
    pages = filter_relevant_pages(root, entity_ids=["EH-014"])
    assert "_hermes_proposals.md" not in pages
    assert "_state.md" not in pages


def test_filter_returns_empty_for_missing_property(tmp_path: Path) -> None:
    assert filter_relevant_pages(tmp_path / "missing", entity_ids=["EH-014"]) == []


def test_filter_caps_at_limit(tmp_path: Path) -> None:
    root = tmp_path / "LIE-001"
    _write(root / "index.md", "root")
    for i in range(60):
        _write(root / f"entities/EH-{i:03d}.md", "")
    pages = filter_relevant_pages(
        root,
        entity_ids=[f"EH-{i:03d}" for i in range(60)],
        limit=10,
    )
    assert len(pages) == 10


def test_filter_subdir_index_pages_treated_as_essential(tmp_path: Path) -> None:
    root = tmp_path / "LIE-001"
    _seed(root)
    _write(root / "02_buildings/HAUS-12/index.md", "Building HAUS-12 dossier.")
    _write(root / "02_buildings/HAUS-99/index.md", "Building HAUS-99 dossier.")
    pages = filter_relevant_pages(root, entity_ids=["EH-014"])
    assert "02_buildings/HAUS-12/index.md" in pages
    assert "02_buildings/HAUS-99/index.md" in pages
