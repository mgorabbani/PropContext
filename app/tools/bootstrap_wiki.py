from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

import structlog

from app.core.config import get_settings
from app.tools.wiki_templates import (
    render_dienstleister,
    render_eigentuemer,
    render_einheit,
    render_finances_overview,
    render_finances_reconciliation,
    render_haus_index,
    render_lie_index,
    render_lie_state,
    render_log,
    render_mieter,
    render_pending_review,
    render_skills,
    render_timeline,
)

log = structlog.get_logger(__name__)


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        ["git", *args],  # noqa: S607
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )


def _has_staged_changes(wiki_dir: Path) -> bool:
    result = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],  # noqa: S607
        cwd=wiki_dir,
        check=False,
        capture_output=True,
        text=True,
    )
    # exit 0 → no staged changes; exit 1 → staged changes; other → error
    if result.returncode not in (0, 1):
        raise subprocess.CalledProcessError(
            result.returncode, result.args, result.stdout, result.stderr
        )
    return result.returncode == 1


def _preserve_bootstrap_timestamp(state: dict[str, Any], state_path: Path) -> dict[str, Any]:
    if not state_path.is_file():
        return state
    try:
        existing = json.loads(state_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return state
    if isinstance(existing.get("bootstrapped_at"), str):
        state["bootstrapped_at"] = existing["bootstrapped_at"]
    return state


def _render_property(stammdaten: dict[str, Any], property_root: Path) -> None:
    _write_text(property_root / "index.md", render_lie_index(stammdaten))
    state_path = property_root / "_state.json"
    state = _preserve_bootstrap_timestamp(render_lie_state(stammdaten), state_path)
    _write_json(state_path, state)
    _write_text(property_root / "log.md", render_log())
    _write_text(property_root / "_pending_review.md", render_pending_review())
    _write_text(property_root / "06_skills.md", render_skills())
    _write_text(property_root / "07_timeline.md", render_timeline())
    _write_text(
        property_root / "05_finances" / "overview.md",
        render_finances_overview(stammdaten),
    )
    _write_text(
        property_root / "05_finances" / "reconciliation.md",
        render_finances_reconciliation(),
    )

    for haus in stammdaten.get("gebaeude", []):
        haus_dir = property_root / "02_buildings" / haus["id"]
        _write_text(haus_dir / "index.md", render_haus_index(haus, stammdaten))

    for einheit in stammdaten.get("einheiten", []):
        unit_path = (
            property_root / "02_buildings" / einheit["haus_id"] / "units" / f"{einheit['id']}.md"
        )
        _write_text(unit_path, render_einheit(einheit, stammdaten))

    for eig in stammdaten.get("eigentuemer", []):
        _write_text(
            property_root / "03_people" / "eigentuemer" / f"{eig['id']}.md",
            render_eigentuemer(eig, stammdaten),
        )

    for mie in stammdaten.get("mieter", []):
        _write_text(
            property_root / "03_people" / "mieter" / f"{mie['id']}.md",
            render_mieter(mie, stammdaten),
        )

    for dl in stammdaten.get("dienstleister", []):
        _write_text(
            property_root / "04_dienstleister" / f"{dl['id']}.md",
            render_dienstleister(dl, stammdaten),
        )


def _git_init_and_commit(wiki_dir: Path, lie_id: str) -> None:
    git_dir = wiki_dir / ".git"
    if not git_dir.exists():
        _git(["init"], cwd=wiki_dir)
        log.info("git_init", wiki_dir=str(wiki_dir))

    # CI environments often lack global git identity; set locally so commits succeed.
    _git(["config", "user.name", "buena-bootstrap"], cwd=wiki_dir)
    _git(["config", "user.email", "bootstrap@buena.local"], cwd=wiki_dir)
    # Wiki commits are programmatic audit trail, not authored commits — disable
    # local signing so the bootstrap works on hosts without GPG/SSH signing keys.
    _git(["config", "commit.gpgsign", "false"], cwd=wiki_dir)

    _git(["add", "-A"], cwd=wiki_dir)

    if not _has_staged_changes(wiki_dir):
        log.info("git_commit_skipped_no_changes", wiki_dir=str(wiki_dir), lie_id=lie_id)
        return

    _git(
        ["commit", "-m", f"bootstrap({lie_id}): skeleton from stammdaten"],
        cwd=wiki_dir,
    )
    log.info("git_commit", wiki_dir=str(wiki_dir), lie_id=lie_id)


def bootstrap(
    stammdaten_path: Path,
    wiki_dir: Path,
    *,
    run_git_init: bool = True,
) -> Path:
    """Render wiki skeleton from stammdaten.json under <wiki_dir>/<LIE-id>/.

    Returns the property root path. Idempotent on file content (overwrites).
    """
    stammdaten = json.loads(stammdaten_path.read_text(encoding="utf-8"))
    lie_id: str = stammdaten["liegenschaft"]["id"]

    wiki_dir.mkdir(parents=True, exist_ok=True)
    property_root = wiki_dir / lie_id
    property_root.mkdir(parents=True, exist_ok=True)

    log.info(
        "bootstrap_start",
        stammdaten_path=str(stammdaten_path),
        wiki_dir=str(wiki_dir),
        lie_id=lie_id,
    )

    _render_property(stammdaten, property_root)

    log.info(
        "bootstrap_rendered",
        lie_id=lie_id,
        gebaeude=len(stammdaten.get("gebaeude", [])),
        einheiten=len(stammdaten.get("einheiten", [])),
        eigentuemer=len(stammdaten.get("eigentuemer", [])),
        mieter=len(stammdaten.get("mieter", [])),
        dienstleister=len(stammdaten.get("dienstleister", [])),
    )

    if run_git_init:
        _git_init_and_commit(wiki_dir, lie_id)

    return property_root


def main() -> None:
    """CLI entry. Parses --stammdaten and --wiki-dir args, calls bootstrap()."""
    settings = get_settings()
    default_stammdaten = settings.data_dir / "stammdaten" / "stammdaten.json"
    default_wiki_dir = settings.wiki_dir

    parser = argparse.ArgumentParser(
        prog="bootstrap_wiki",
        description="Render wiki skeleton from stammdaten.json and git-init the tree.",
    )
    parser.add_argument(
        "--stammdaten",
        type=Path,
        default=default_stammdaten,
        help=f"Path to stammdaten.json (default: {default_stammdaten})",
    )
    parser.add_argument(
        "--wiki-dir",
        type=Path,
        default=default_wiki_dir,
        help=f"Wiki output root (default: {default_wiki_dir})",
    )
    parser.add_argument(
        "--no-git",
        action="store_true",
        help="Skip git init and commit.",
    )

    args = parser.parse_args()
    property_root = bootstrap(
        args.stammdaten,
        args.wiki_dir,
        run_git_init=not args.no_git,
    )
    log.info("bootstrap_done", property_root=str(property_root))


if __name__ == "__main__":
    main()
