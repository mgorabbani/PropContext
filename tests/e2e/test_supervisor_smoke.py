from __future__ import annotations

import json
import subprocess
from pathlib import Path

from app.core.config import Settings
from app.schemas.webhook import IngestEvent
from app.services.llm.client import FakeLLMClient
from app.services.supervisor import Supervisor


def _git_init(wiki_dir: Path) -> None:
    wiki_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init"], cwd=wiki_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.test"],
        cwd=wiki_dir,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "test"],
        cwd=wiki_dir,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "commit.gpgsign", "false"],
        cwd=wiki_dir,
        check=True,
        capture_output=True,
    )


async def test_one_event_creates_pages_log_and_index(tmp_path: Path) -> None:
    wiki_dir = tmp_path / "wiki"
    _git_init(wiki_dir)
    settings = Settings(
        wiki_dir=wiki_dir,
        normalize_dir=tmp_path / "normalize",
        output_dir=tmp_path / "output",
        data_dir=tmp_path / "data",
        env="dev",
        llm_provider="fake",
    )

    classify_response = json.dumps(
        {"signal": True, "category": "manual/leak", "priority": "high", "confidence": 0.9}
    )
    extract_response = json.dumps(
        {
            "summary": "EH-014 leak reported",
            "ops": [
                {
                    "op": "create_page",
                    "path": "sources/EVT-1.md",
                    "frontmatter": {
                        "name": "source-evt-1",
                        "description": "Leak reported in EH-014 by tenant.",
                    },
                    "body": "Tenant reports water leak under sink in EH-014.",
                },
                {
                    "op": "create_page",
                    "path": "entities/EH-014.md",
                    "frontmatter": {
                        "name": "unit-eh-014",
                        "description": "Apartment EH-014, currently has an open leak issue.",
                    },
                    "body": "## Status\n\nLeak reported [[sources/EVT-1.md]]\n",
                },
                {
                    "op": "append_section",
                    "path": "entities/EH-014.md",
                    "heading": "Timeline",
                    "line": "- 2026-04-25 leak reported [[sources/EVT-1.md]]",
                },
                {
                    "op": "prepend_log",
                    "line": "## [2026-04-25] manual | EH-014 leak reported",
                },
            ],
        }
    )
    llm = FakeLLMClient(
        {
            settings.fast_model: classify_response,
            settings.smart_model: extract_response,
        }
    )

    supervisor = Supervisor(settings=settings, llm=llm)
    result = await supervisor.handle(
        IngestEvent(
            event_id="EVT-1",
            event_type="manual",
            property_id="LIE-001",
            payload={"text": "Leak reported in EH-014"},
        )
    )

    assert result.status == "applied"
    assert result.patch is not None
    assert result.patch.applied_ops >= 4

    root = wiki_dir / "LIE-001"
    assert (root / "sources/EVT-1.md").is_file()
    assert (root / "entities/EH-014.md").is_file()
    assert (root / "log.md").is_file()
    assert (root / "index.md").is_file()

    eh014 = (root / "entities/EH-014.md").read_text(encoding="utf-8")
    assert "name: unit-eh-014" in eh014
    assert "## Timeline" in eh014
    assert "leak reported" in eh014.lower()

    log = (root / "log.md").read_text(encoding="utf-8")
    assert "EH-014 leak reported" in log

    index = (root / "index.md").read_text(encoding="utf-8")
    assert "entities/EH-014.md" in index
    assert "sources/EVT-1.md" in index
