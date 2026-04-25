from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest

from app.tools.bootstrap_wiki import bootstrap

REPO_ROOT = Path(__file__).resolve().parents[2]
STAMMDATEN = REPO_ROOT / "data" / "stammdaten" / "stammdaten.json"

LIE_REQUIRED_SECTIONS = [
    "Buildings",
    "Bank Accounts",
    "Open Issues",
    "Recent Events",
    "Procedural Memory",
    "Provenance",
]
HAUS_REQUIRED_SECTIONS = [
    "Summary",
    "Units",
    "Open Issues",
    "Recent Events",
    "Contractors Active",
    "Provenance",
]
UNIT_REQUIRED_SECTIONS = [
    "Unit Facts",
    "Current Tenant",
    "Current Owner",
    "History",
    "Provenance",
]
EIG_REQUIRED_SECTIONS = [
    "Contact",
    "Units Owned",
    "Roles",
    "Payment History",
    "Correspondence Summary",
    "Provenance",
]
MIE_REQUIRED_SECTIONS = [
    "Contact",
    "Tenancy",
    "Payment History",
    "Contact History",
    "Provenance",
]
DL_REQUIRED_SECTIONS = [
    "Services",
    "Contracts",
    "Recent Invoices",
    "Performance Notes",
    "Provenance",
]

FRONTMATTER_RE = re.compile(
    r"\A---\nname: [a-z0-9-]{1,64}\ndescription: .{1,1024}\n---\n",
    re.DOTALL,
)


@pytest.fixture
def bootstrapped(tmp_path: Path) -> Path:
    return bootstrap(STAMMDATEN, tmp_path / "wiki")


def _all_md_files(root: Path) -> list[Path]:
    return sorted(
        p for p in root.rglob("*.md") if not any(part.startswith(".") for part in p.parts)
    )


def _assert_sections(content: str, sections: list[str]) -> None:
    for s in sections:
        assert f"## {s}" in content, f"missing section ## {s}"


def test_bootstrap_creates_required_files(bootstrapped: Path) -> None:
    root = bootstrapped
    assert root.name == "LIE-001"
    assert (root / "index.md").is_file()
    assert (root / "_state.json").is_file()
    assert (root / "log.md").is_file()
    assert (root / "_pending_review.md").is_file()
    assert (root / "06_skills.md").is_file()
    assert (root / "07_timeline.md").is_file()
    assert (root / "05_finances" / "overview.md").is_file()
    assert (root / "05_finances" / "reconciliation.md").is_file()
    for haus_id in ("HAUS-12", "HAUS-14", "HAUS-16"):
        assert (root / "02_buildings" / haus_id / "index.md").is_file()
    assert (root / "02_buildings" / "HAUS-12" / "units" / "EH-001.md").is_file()
    assert (root / "03_people" / "eigentuemer" / "EIG-001.md").is_file()
    assert (root / "03_people" / "mieter" / "MIE-001.md").is_file()
    assert (root / "04_dienstleister" / "DL-001.md").is_file()


def test_unit_count_matches_stammdaten(bootstrapped: Path) -> None:
    units = list((bootstrapped / "02_buildings").rglob("EH-*.md"))
    assert len(units) == 52


def test_owner_and_tenant_counts(bootstrapped: Path) -> None:
    eigs = list((bootstrapped / "03_people" / "eigentuemer").glob("EIG-*.md"))
    miers = list((bootstrapped / "03_people" / "mieter").glob("MIE-*.md"))
    dls = list((bootstrapped / "04_dienstleister").glob("DL-*.md"))
    assert len(eigs) == 35
    assert len(miers) == 26
    assert len(dls) == 16


def test_every_md_file_has_frontmatter(bootstrapped: Path) -> None:
    for md in _all_md_files(bootstrapped):
        text = md.read_text(encoding="utf-8")
        assert FRONTMATTER_RE.match(text), f"bad frontmatter in {md.relative_to(bootstrapped)}"


def test_every_md_file_has_human_notes_boundary(bootstrapped: Path) -> None:
    for md in _all_md_files(bootstrapped):
        text = md.read_text(encoding="utf-8")
        assert text.rstrip().endswith("# Human Notes"), (
            f"missing # Human Notes boundary in {md.relative_to(bootstrapped)}"
        )


def test_lie_index_required_sections(bootstrapped: Path) -> None:
    text = (bootstrapped / "index.md").read_text(encoding="utf-8")
    _assert_sections(text, LIE_REQUIRED_SECTIONS)


def test_haus_index_required_sections(bootstrapped: Path) -> None:
    text = (bootstrapped / "02_buildings" / "HAUS-12" / "index.md").read_text(encoding="utf-8")
    _assert_sections(text, HAUS_REQUIRED_SECTIONS)


def test_unit_required_sections(bootstrapped: Path) -> None:
    text = (bootstrapped / "02_buildings" / "HAUS-12" / "units" / "EH-001.md").read_text(
        encoding="utf-8"
    )
    _assert_sections(text, UNIT_REQUIRED_SECTIONS)


def test_owner_required_sections(bootstrapped: Path) -> None:
    text = (bootstrapped / "03_people" / "eigentuemer" / "EIG-001.md").read_text(encoding="utf-8")
    _assert_sections(text, EIG_REQUIRED_SECTIONS)


def test_tenant_required_sections(bootstrapped: Path) -> None:
    text = (bootstrapped / "03_people" / "mieter" / "MIE-001.md").read_text(encoding="utf-8")
    _assert_sections(text, MIE_REQUIRED_SECTIONS)


def test_dienstleister_required_sections(bootstrapped: Path) -> None:
    text = (bootstrapped / "04_dienstleister" / "DL-001.md").read_text(encoding="utf-8")
    _assert_sections(text, DL_REQUIRED_SECTIONS)


def test_state_json_shape(bootstrapped: Path) -> None:
    state = json.loads((bootstrapped / "_state.json").read_text(encoding="utf-8"))
    assert state["schema_version"] == 1
    assert state["property_id"] == "LIE-001"
    assert state["last_patched"] is None
    assert state["counts"] == {
        "buildings": 3,
        "units": 52,
        "owners": 35,
        "tenants": 26,
        "dienstleister": 16,
        "open_issues": 0,
    }


def test_git_log_shows_one_commit(bootstrapped: Path) -> None:
    wiki_dir = bootstrapped.parent
    result = subprocess.run(
        ["git", "log", "--oneline"],
        cwd=wiki_dir,
        check=True,
        capture_output=True,
        text=True,
    )
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    assert len(lines) == 1
    assert "bootstrap(LIE-001)" in lines[0]


def test_bootstrap_idempotent_no_new_commit(tmp_path: Path) -> None:
    wiki_dir = tmp_path / "wiki"
    bootstrap(STAMMDATEN, wiki_dir)
    bootstrap(STAMMDATEN, wiki_dir)

    result = subprocess.run(
        ["git", "log", "--oneline"],
        cwd=wiki_dir,
        check=True,
        capture_output=True,
        text=True,
    )
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    assert len(lines) == 1


def test_bootstrap_no_git_flag(tmp_path: Path) -> None:
    wiki_dir = tmp_path / "wiki"
    bootstrap(STAMMDATEN, wiki_dir, run_git_init=False)
    assert not (wiki_dir / ".git").exists()


def test_haus_index_lists_units_in_table(bootstrapped: Path) -> None:
    text = (bootstrapped / "02_buildings" / "HAUS-12" / "index.md").read_text(encoding="utf-8")
    assert "| ID | WE-Nr | Lage | Typ | qm | Zimmer | MEA |" in text
    assert "| EH-001 |" in text


def test_lie_index_lists_buildings_in_table(bootstrapped: Path) -> None:
    text = (bootstrapped / "index.md").read_text(encoding="utf-8")
    assert "| ID | Hausnr | Units | Stories | Elevator |" in text
    for haus_id in ("HAUS-12", "HAUS-14", "HAUS-16"):
        assert f"| {haus_id} |" in text


def test_owner_units_owned_links_resolve(bootstrapped: Path) -> None:
    text = (bootstrapped / "03_people" / "eigentuemer" / "EIG-001.md").read_text(encoding="utf-8")
    assert "[EH-037](" in text
    assert "[EH-032](" in text


def test_pending_review_is_empty_with_section(bootstrapped: Path) -> None:
    text = (bootstrapped / "_pending_review.md").read_text(encoding="utf-8")
    assert "## Open Conflicts" in text
