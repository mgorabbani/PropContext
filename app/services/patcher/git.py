from __future__ import annotations

import subprocess
from pathlib import Path


def run_git(args: list[str], cwd: Path, *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        ["git", *args],  # noqa: S607
        cwd=cwd,
        check=check,
        capture_output=True,
        text=True,
    )


def commit_all(wiki_dir: Path, *, message: str) -> str | None:
    run_git(["add", "-A"], cwd=wiki_dir)
    diff = run_git(["diff", "--cached", "--quiet"], cwd=wiki_dir, check=False)
    if diff.returncode == 0:
        return head_sha(wiki_dir)
    if diff.returncode != 1:
        raise subprocess.CalledProcessError(diff.returncode, diff.args, diff.stdout, diff.stderr)
    run_git(["commit", "-m", message], cwd=wiki_dir)
    return head_sha(wiki_dir)


def head_sha(wiki_dir: Path) -> str | None:
    result = run_git(["rev-parse", "HEAD"], cwd=wiki_dir, check=False)
    if result.returncode != 0:
        return None
    return result.stdout.strip()
