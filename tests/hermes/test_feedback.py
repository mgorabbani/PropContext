from __future__ import annotations

import json
from pathlib import Path

from app.services.hermes.feedback import (
    FEEDBACK_FILENAME,
    append_feedback,
    feedback_path,
    iter_feedback,
)


def test_append_writes_jsonl_line(tmp_path: Path) -> None:
    root = tmp_path / "LIE-001"
    written = append_feedback(
        root,
        event_id="EVT-1",
        event_type="email",
        property_id="LIE-001",
        summary="heating outage",
        applied_ops=4,
        deferred_ops=0,
        touched=["02_buildings/HAUS-12/index.md", "entities/EH-014.md"],
        op_shapes=[
            {"op": "create_page", "path": "sources/EMAIL-<id>.md"},
            {
                "op": "upsert_section",
                "path": "02_buildings/HAUS-<id>/index.md",
                "heading": "Open Issues",
            },
        ],
    )
    assert written is True

    path = feedback_path(root)
    assert path.name == FEEDBACK_FILENAME
    assert path.is_file()

    [line] = path.read_text(encoding="utf-8").splitlines()
    row = json.loads(line)
    assert row["kind"] == "ingest"
    assert row["event_id"] == "EVT-1"
    assert row["event_type"] == "email"
    assert row["property_id"] == "LIE-001"
    assert row["summary"] == "heating outage"
    assert row["applied_ops"] == 4
    assert row["deferred_ops"] == 0
    assert row["touched"] == ["02_buildings/HAUS-12/index.md", "entities/EH-014.md"]
    assert row["op_shapes"][0]["op"] == "create_page"
    assert row["op_shapes"][1]["heading"] == "Open Issues"
    assert "T" in row["ts"]


def test_append_is_idempotent_on_event_id(tmp_path: Path) -> None:
    root = tmp_path / "LIE-001"
    assert append_feedback(
        root,
        event_id="EVT-1",
        event_type="email",
        property_id="LIE-001",
        summary="first",
        applied_ops=1,
    )
    assert not append_feedback(
        root,
        event_id="EVT-1",
        event_type="email",
        property_id="LIE-001",
        summary="duplicate",
        applied_ops=99,
    )
    lines = feedback_path(root).read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["summary"] == "first"


def test_append_appends_distinct_events(tmp_path: Path) -> None:
    root = tmp_path / "LIE-001"
    for i in range(3):
        append_feedback(
            root,
            event_id=f"EVT-{i}",
            event_type="email",
            property_id="LIE-001",
            summary=f"summary {i}",
            applied_ops=i,
        )
    lines = feedback_path(root).read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3
    ids = [json.loads(line)["event_id"] for line in lines]
    assert ids == ["EVT-0", "EVT-1", "EVT-2"]


def test_iter_feedback_skips_corrupt_lines(tmp_path: Path) -> None:
    root = tmp_path / "LIE-001"
    root.mkdir(parents=True, exist_ok=True)
    path = feedback_path(root)
    path.write_text(
        '{"kind":"ingest","event_id":"EVT-1","event_type":"email","property_id":"LIE-001",'
        '"summary":"ok","applied_ops":1,"deferred_ops":0,"touched":[]}\n'
        "<<not-json>>\n"
        "\n"
        '{"kind":"ingest","event_id":"EVT-2","event_type":"email","property_id":"LIE-001",'
        '"summary":"also ok","applied_ops":2,"deferred_ops":0,"touched":["a.md"]}\n',
        encoding="utf-8",
    )
    records = list(iter_feedback(root))
    assert [r.event_id for r in records] == ["EVT-1", "EVT-2"]
    assert records[1].touched == ("a.md",)


def test_iter_feedback_returns_empty_when_missing(tmp_path: Path) -> None:
    root = tmp_path / "LIE-001"
    assert list(iter_feedback(root)) == []
