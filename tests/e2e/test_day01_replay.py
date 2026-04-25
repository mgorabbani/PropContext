from __future__ import annotations

import csv
import json
import re
import subprocess
from pathlib import Path

from httpx import ASGITransport, AsyncClient

from app.core.config import Settings, get_settings
from app.main import app
from app.services.events import reset_event_broker
from app.services.llm.client import LLMClient, get_llm_client
from app.tools.bootstrap_wiki import bootstrap
from app.tools.replay import replay_day

REPO_ROOT = Path(__file__).resolve().parents[2]
STAMMDATEN = REPO_ROOT / "data" / "stammdaten" / "stammdaten.json"


class _SmartLLM:
    """Returns canned classification + per-event extract plan keyed by event_id."""

    def __init__(self, *, haiku_model: str, sonnet_model: str) -> None:
        self.haiku_model = haiku_model
        self.sonnet_model = sonnet_model
        self.calls: list[str] = []

    async def complete(self, *, model: str, system_prompt: str, user_prompt: str) -> str:
        self.calls.append(model)
        if model == self.haiku_model:
            return json.dumps(
                {
                    "signal": True,
                    "category": "mieter/heizung",
                    "priority": "normal",
                    "confidence": 0.9,
                }
            )
        evt = _extract_event_id(user_prompt)
        plan = {
            "summary": f"e2e {evt}",
            "ops": [
                {
                    "op": "prepend_row",
                    "file": "07_timeline.md",
                    "section": "Events",
                    "row": ["2026-01-01", evt, "e2e test row"],
                    "header": ["date", "event_id", "summary"],
                }
            ],
        }
        return json.dumps(plan)


def _extract_event_id(user_prompt: str) -> str:
    match = re.search(r'"event_id":\s*"([^"]+)"', user_prompt)
    return match.group(1) if match else "EVT-UNKNOWN"


def _build_fixture_day(tmp_path: Path) -> Path:
    day = tmp_path / "day-01"
    (day / "emails" / "2026-01").mkdir(parents=True)
    (day / "bank").mkdir(parents=True)

    (day / "emails" / "2026-01" / "20260101_080000_EMAIL-90001.eml").write_text(
        "From: mieter@example.com\nTo: pm@example.com\nSubject: Heizung defekt\n\n"
        "Die Heizung in EH-001 ist seit gestern aus.\n",
        encoding="utf-8",
    )
    (day / "emails" / "2026-01" / "20260102_080000_EMAIL-90002.eml").write_text(
        "From: mieter@example.com\nTo: pm@example.com\nSubject: Re: Heizung\n\n"
        "Update: still cold today.\n",
        encoding="utf-8",
    )

    with (day / "emails_index.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(
            ["id", "datetime", "thread_id", "from_email", "category", "filename", "month_dir"]
        )
        w.writerow(
            [
                "EMAIL-90001",
                "2026-01-01T08:00:00",
                "T1",
                "mieter@example.com",
                "mieter/heizung",
                "20260101_080000_EMAIL-90001.eml",
                "2026-01",
            ]
        )
        w.writerow(
            [
                "EMAIL-90002",
                "2026-01-02T08:00:00",
                "T1",
                "mieter@example.com",
                "mieter/heizung",
                "20260102_080000_EMAIL-90002.eml",
                "2026-01",
            ]
        )

    with (day / "bank" / "bank_index.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "datum", "typ", "betrag", "kategorie", "referenz_id", "error_types"])
        w.writerow(["TX-90001", "2026-01-06", "DEBIT", "100.00", "dienstleister", "INV-90001", ""])

    return day


def _git_log_count(wiki_dir: Path, property_root: Path) -> int:
    result = subprocess.run(
        ["git", "rev-list", "--count", "HEAD", "--", str(property_root.relative_to(wiki_dir))],
        cwd=wiki_dir,
        check=True,
        capture_output=True,
        text=True,
    )
    return int(result.stdout.strip())


async def test_day01_replay_end_to_end(tmp_path: Path) -> None:
    reset_event_broker()
    wiki_dir = tmp_path / "wiki"
    output_dir = tmp_path / "output"
    normalize_dir = tmp_path / "normalize"

    property_root = bootstrap(
        STAMMDATEN, wiki_dir, wiki_chunks_db=output_dir / "wiki_chunks.duckdb"
    )
    initial_commits = _git_log_count(wiki_dir, property_root)
    assert initial_commits >= 1

    settings = Settings(
        wiki_dir=wiki_dir,
        normalize_dir=normalize_dir,
        output_dir=output_dir,
        data_dir=REPO_ROOT / "data",
        webhook_hmac_secret="e2e-secret",
        env="dev",
    )
    fake_llm: LLMClient = _SmartLLM(
        haiku_model=settings.haiku_model,
        sonnet_model=settings.sonnet_model,
    )

    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_llm_client] = lambda: fake_llm
    transport = ASGITransport(app=app)
    try:
        day = _build_fixture_day(tmp_path)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            responses = await replay_day(client, day, secret="e2e-secret")
    finally:
        app.dependency_overrides.clear()
        reset_event_broker()

    assert [r.status_code for r in responses] == [200, 200, 200]
    bodies = [r.json() for r in responses]
    statuses = {b["status"] for b in bodies}
    assert statuses == {"applied"}

    timeline = (property_root / "07_timeline.md").read_text(encoding="utf-8")
    assert "EMAIL-90001" in timeline
    assert "EMAIL-90002" in timeline
    assert "TX-90001" in timeline

    feedback = (property_root / "_hermes_feedback.jsonl").read_text(encoding="utf-8")
    feedback_lines = [json.loads(line) for line in feedback.splitlines() if line.strip()]
    seen_ids = {entry["event_id"] for entry in feedback_lines}
    assert seen_ids == {"EMAIL-90001", "EMAIL-90002", "TX-90001"}
    assert all(entry["applied_ops"] >= 1 for entry in feedback_lines)

    final_commits = _git_log_count(wiki_dir, property_root)
    assert final_commits >= initial_commits + 1
