from __future__ import annotations

from pathlib import Path

from httpx import AsyncClient

from app.services.hermes.feedback import append_feedback


def _seed(root: Path) -> None:
    for i in range(5):
        append_feedback(
            root,
            event_id=f"EMAIL-{i:03d}",
            event_type="email",
            property_id="LIE-001",
            summary=f"heating in EH-0{i:02d}",
            applied_ops=3,
            touched=[
                f"02_buildings/HAUS-{12 + i % 2}/index.md",
                f"entities/EH-0{i:02d}.md",
                f"sources/EMAIL-{i:03d}.md",
            ],
            op_shapes=[
                {"op": "create_page", "path": "sources/EMAIL-<id>.md"},
                {
                    "op": "upsert_section",
                    "path": "02_buildings/HAUS-<id>/index.md",
                    "heading": "Open Issues",
                },
                {"op": "prepend_log"},
            ],
        )
    for i in range(2):
        append_feedback(
            root,
            event_id=f"VOICE-{i}",
            event_type="voicenote",
            property_id="LIE-001",
            summary="recorded note",
            applied_ops=0,
        )


async def test_hermes_dashboard_404_when_property_missing(client: AsyncClient) -> None:
    r = await client.get("/api/v1/properties/LIE-001/hermes")
    assert r.status_code == 404


async def test_hermes_dashboard_returns_empty_substrate_for_bare_property(
    client: AsyncClient, wiki_dir: Path
) -> None:
    (wiki_dir / "LIE-001").mkdir()
    r = await client.get("/api/v1/properties/LIE-001/hermes")
    assert r.status_code == 200
    body = r.json()
    assert body["property_id"] == "LIE-001"
    assert body["substrate"]["exists"] is False
    assert body["substrate"]["total_events"] == 0
    assert body["skills"]["promoted_count"] == 0
    assert body["proposals"]["total"] == 0
    assert body["artifacts"]["feedback_jsonl"] is None


async def test_hermes_dashboard_reports_skills_and_proposals(
    client: AsyncClient, wiki_dir: Path
) -> None:
    property_root = wiki_dir / "LIE-001"
    property_root.mkdir()
    _seed(property_root)

    r = await client.get("/api/v1/properties/LIE-001/hermes")
    assert r.status_code == 200
    body = r.json()

    sub = body["substrate"]
    assert sub["exists"] is True
    assert sub["total_events"] == 7
    assert sub["applied_events"] == 5
    assert sub["miss_events"] == 2
    assert sub["last_event_id"] == "VOICE-1"

    skills = body["skills"]
    assert skills["promoted_count"] == 1
    assert skills["candidates"][0]["event_type"] == "email"
    assert skills["candidates"][0]["occurrences"] == 5
    assert "email" in skills["registry_event_types"]

    proposals = body["proposals"]
    assert proposals["total"] >= 1
    kinds = {p["kind"] for p in proposals["items"]}
    assert "schema-gap" in kinds
    schema_gap = next(p for p in proposals["items"] if p["kind"] == "schema-gap")
    assert schema_gap["evidence_count"] == 2
    assert "VOICE-0" in schema_gap["evidence_event_ids"]

    assert body["artifacts"]["feedback_jsonl"] == "_hermes_feedback.jsonl"


async def test_hermes_dashboard_rejects_bad_property_id(client: AsyncClient) -> None:
    r = await client.get("/api/v1/properties/HAUS-12/hermes")
    assert r.status_code == 422
