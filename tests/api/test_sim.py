from __future__ import annotations

import subprocess
from pathlib import Path

from app.api.v1.sim import _git_head_ref, _git_show_at


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def _git_init(repo: Path) -> None:
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "test@example.test")
    _git(repo, "config", "user.name", "test")
    _git(repo, "config", "commit.gpgsign", "false")


def test_git_show_at_reads_from_ingest_baseline(tmp_path: Path) -> None:
    repo = tmp_path / "wiki"
    _git_init(repo)

    root = repo / "LIE-001"
    root.mkdir()
    index = root / "index.md"
    index.write_text("# Index\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "seed")

    baseline = _git_head_ref(repo)

    source = root / "sources" / "EMAIL-06583.md"
    source.parent.mkdir()
    source.write_text("# Source\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "ingest")

    index.write_text("# Index\n\n- [source](sources/EMAIL-06583.md)\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "index")

    assert _git_show_at(repo, baseline, "LIE-001/sources/EMAIL-06583.md") == ""
    assert _git_show_at(repo, baseline, "LIE-001/index.md") == "# Index\n"
