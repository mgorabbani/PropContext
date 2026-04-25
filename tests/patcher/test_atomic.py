from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.services.patcher import atomic


def test_atomic_write_failure_leaves_original_intact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "doc.md"
    path.write_text("original", encoding="utf-8")

    def fail_replace(src: str | os.PathLike[str], dst: str | os.PathLike[str]) -> None:
        raise RuntimeError("simulated crash")

    monkeypatch.setattr(atomic.os, "replace", fail_replace)

    with pytest.raises(RuntimeError, match="simulated crash"):
        atomic.atomic_write_text(path, "new")

    assert path.read_text(encoding="utf-8") == "original"
    assert list(tmp_path.glob("*.tmp")) == []
