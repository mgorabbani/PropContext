from __future__ import annotations

import csv
import json
import subprocess
import tempfile
import time
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Annotated, Any, Literal

import anyio
import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.config import REPO_ROOT, Settings, get_settings
from app.schemas.webhook import IngestEvent
from app.services.classify import Classification
from app.services.llm.client import get_llm_client
from app.services.supervisor import Supervisor

router = APIRouter()
log = structlog.get_logger(__name__)

INCREMENTAL_DIR = REPO_ROOT / "data" / "incremental"


class SimItem(BaseModel):
    id: str
    kind: Literal["email", "invoice", "bank"]
    label: str
    detail: str
    source_path: str | None = None
    month: str | None = None


class SimDay(BaseModel):
    day: int
    content_date: str | None
    emails: list[SimItem]
    invoices: list[SimItem]
    bank: list[SimItem]


class SimIngestRequest(BaseModel):
    day: int = Field(ge=1, le=99)
    kind: Literal["email", "invoice", "bank"]
    id: str
    mode: Literal["isolated", "live"] = "isolated"
    property_id: str = "LIE-001"


class TouchedFile(BaseModel):
    path: str
    content: str
    previous: str = ""


class SimIngestResponse(BaseModel):
    status: str
    workspace: str
    wiki_dir: str
    provider: str
    fast_model: str
    smart_model: str
    duration_ms: int
    classification: dict | None
    applied_ops: int
    commit_sha: str | None
    idempotent: bool
    touched: list[str]
    files: list[TouchedFile]
    normalized_text: str | None
    git_log: list[str]


@router.get("/incremental", response_model=list[SimDay])
def list_incremental() -> list[SimDay]:
    if not INCREMENTAL_DIR.is_dir():
        return []
    days: list[SimDay] = []
    for entry in sorted(INCREMENTAL_DIR.iterdir()):
        if not entry.is_dir() or not entry.name.startswith("day-"):
            continue
        try:
            day_idx = int(entry.name.split("-", 1)[1])
        except ValueError:
            continue
        days.append(_describe_day(entry, day_idx))
    return days


@router.post("/ingest/stream")
async def sim_ingest_stream(
    body: SimIngestRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> StreamingResponse:
    return StreamingResponse(
        _sim_ingest_event_stream(body, settings),
        media_type="text/event-stream",
        headers={
            "cache-control": "no-cache",
            "connection": "keep-alive",
            "x-accel-buffering": "no",
        },
    )


async def _sim_ingest_event_stream(
    body: SimIngestRequest, settings: Settings
) -> AsyncGenerator[str]:
    send, recv = anyio.create_memory_object_stream[tuple[str, dict[str, Any]]](64)

    async def emit(name: str, data: dict[str, Any]) -> None:
        await send.send((name, data))

    async def runner() -> None:
        try:
            payload = await _run_sim_ingest(body, settings, on_stage=emit)
            await send.send(("response", payload))
        except HTTPException as exc:
            await send.send(("error", {"status": exc.status_code, "detail": str(exc.detail)}))
        except Exception as exc:
            log.exception("sim_ingest_stream_failed", event_id=body.id)
            await send.send(("error", {"status": 500, "detail": str(exc)}))
        finally:
            await send.aclose()

    async with anyio.create_task_group() as tg:
        tg.start_soon(runner)
        async with recv:
            async for name, data in recv:
                msg = json.dumps({"stage": name, "data": data}, separators=(",", ":"), default=str)
                yield f"event: stage\ndata: {msg}\n\n"


@router.post("/ingest", response_model=SimIngestResponse)
async def sim_ingest(
    body: SimIngestRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> SimIngestResponse:
    payload = await _run_sim_ingest(body, settings, on_stage=None)
    return SimIngestResponse(**payload)


async def _run_sim_ingest(
    body: SimIngestRequest,
    settings: Settings,
    *,
    on_stage: Any | None,
) -> dict:
    day_dir = INCREMENTAL_DIR / f"day-{body.day:02d}"
    if not day_dir.is_dir():
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"day-{body.day:02d} missing")

    item, source_path, payload = _resolve_item(day_dir, kind=body.kind, item_id=body.id)
    sim_settings, workspace = _build_sim_settings(settings, mode=body.mode)
    baseline_ref = _git_head_ref(sim_settings.wiki_dir)
    llm = get_llm_client(sim_settings)
    sup = Supervisor(settings=sim_settings, llm=llm)

    event = IngestEvent(
        event_id=item.id,
        event_type=body.kind,
        property_id=body.property_id,
        source_path=source_path,
        payload=payload,
    )

    t0 = time.time()
    try:
        result = await sup.handle(event, on_stage=on_stage)
    except Exception as exc:
        log.exception("sim_ingest_failed", event_id=item.id)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"ingest failed: {exc}") from exc
    dt = int((time.time() - t0) * 1000)

    root = sim_settings.wiki_dir / body.property_id
    touched = list(result.patch.touched) if result.patch else []
    files: list[TouchedFile] = []
    for rel in touched:
        f = root / rel
        content = f.read_text(encoding="utf-8") if f.is_file() else ""
        prev = _git_show_at(sim_settings.wiki_dir, baseline_ref, f"{body.property_id}/{rel}")
        files.append(TouchedFile(path=rel, content=content, previous=prev))

    git_lines = await anyio.to_thread.run_sync(_git_log_lines, sim_settings.wiki_dir)  # ty: ignore[unresolved-attribute]

    classification: dict | None = None
    if result.classification is not None:
        classification = _classification_dict(result.classification)

    normalized_text: str | None = None
    handler_result = getattr(sup, "_last_normalized", None)
    if handler_result and isinstance(handler_result, str):
        normalized_text = handler_result

    return {
        "status": result.status,
        "workspace": str(workspace),
        "wiki_dir": str(sim_settings.wiki_dir),
        "provider": sim_settings.llm_provider,
        "fast_model": sim_settings.fast_model,
        "smart_model": sim_settings.smart_model,
        "duration_ms": dt,
        "classification": classification,
        "applied_ops": result.patch.applied_ops if result.patch else 0,
        "commit_sha": result.patch.commit_sha if result.patch else None,
        "idempotent": result.patch.idempotent if result.patch else False,
        "touched": touched,
        "files": [f.model_dump() for f in files],
        "normalized_text": normalized_text,
        "git_log": git_lines,
    }


def _git_head_ref(wiki_dir: Path) -> str | None:
    proc = subprocess.run(
        ["git", "rev-parse", "--verify", "HEAD"],  # noqa: S607
        cwd=wiki_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() or None


def _git_show_at(wiki_dir: Path, ref: str | None, rel_from_repo_root: str) -> str:
    if ref is None:
        return ""
    proc = subprocess.run(  # noqa: S603
        ["git", "show", f"{ref}:{rel_from_repo_root}"],  # noqa: S607
        cwd=wiki_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return ""
    return proc.stdout


def _git_log_lines(wiki_dir: Path) -> list[str]:
    proc = subprocess.run(
        ["git", "log", "--oneline", "-n", "10"],  # noqa: S607
        cwd=wiki_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return []
    return [ln for ln in proc.stdout.splitlines() if ln.strip()]


def _classification_dict(c: Classification) -> dict:
    return {
        "signal": c.signal,
        "category": c.category,
        "priority": c.priority,
        "confidence": c.confidence,
    }


def _describe_day(day_dir: Path, day_idx: int) -> SimDay:
    manifest = day_dir / "incremental_manifest.json"
    content_date: str | None = None
    if manifest.is_file():
        try:
            content_date = json.loads(manifest.read_text(encoding="utf-8")).get("content_date")
        except (ValueError, OSError):
            content_date = None

    emails: list[SimItem] = []
    emails_index = day_dir / "emails_index.csv"
    if emails_index.is_file():
        for row in _read_csv(emails_index):
            emails.append(
                SimItem(
                    id=row["id"],
                    kind="email",
                    label=row.get("subject") or row["id"],
                    detail=" · ".join(
                        [
                            f"{row.get('from_email', '?')} → {row.get('to_email', '?')}",
                            row.get("datetime", ""),
                            row.get("category", ""),
                        ]
                    ),
                    source_path=str(
                        Path("emails") / (row.get("month_dir") or "") / (row.get("filename") or "")
                    ),
                    month=row.get("month_dir"),
                )
            )

    invoices: list[SimItem] = []
    inv_index = day_dir / "rechnungen_index.csv"
    if inv_index.is_file():
        for row in _read_csv(inv_index):
            invoices.append(
                SimItem(
                    id=row["id"],
                    kind="invoice",
                    label=" — ".join(
                        [
                            row.get("rechnungsnr", row["id"]),
                            row.get("dienstleister_firma", ""),
                        ]
                    ),
                    detail=" · ".join(
                        [
                            row.get("datum", ""),
                            f"brutto {row.get('brutto', '?')} EUR",
                            row.get("iban", ""),
                        ]
                    ),
                    source_path=str(
                        Path("rechnungen")
                        / (row.get("month_dir") or "")
                        / (row.get("filename") or "")
                    ),
                    month=row.get("month_dir"),
                )
            )

    bank: list[SimItem] = []
    bank_index = day_dir / "bank" / "bank_index.csv"
    if bank_index.is_file():
        for row in _read_csv(bank_index):
            bank.append(
                SimItem(
                    id=row["id"],
                    kind="bank",
                    label=(
                        f"{row.get('typ', '?')} {row.get('betrag', '?')} EUR"
                        f" — {row.get('gegen_name', '')}"
                    ),
                    detail=" · ".join(
                        [
                            row.get("datum", ""),
                            row.get("kategorie", ""),
                            row.get("verwendungszweck", ""),
                        ]
                    ),
                    source_path=None,
                    month=None,
                )
            )

    return SimDay(
        day=day_idx,
        content_date=content_date,
        emails=emails,
        invoices=invoices,
        bank=bank,
    )


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as fp:
        reader = csv.DictReader(fp)
        return [{k: (v or "") for k, v in row.items()} for row in reader]


def _resolve_item(day_dir: Path, *, kind: str, item_id: str) -> tuple[SimItem, Path | None, dict]:
    day_summary = _describe_day(day_dir, int(day_dir.name.split("-")[1]))
    items = {
        "email": day_summary.emails,
        "invoice": day_summary.invoices,
        "bank": day_summary.bank,
    }[kind]
    match = next((i for i in items if i.id == item_id), None)
    if match is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, f"item {kind}/{item_id} not found in {day_dir.name}"
        )

    payload: dict = {}
    source_path: Path | None = None
    if kind in {"email", "invoice"} and match.source_path:
        source_path = (day_dir / match.source_path).resolve()
        if not source_path.is_file():
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, f"source file missing: {match.source_path}"
            )
    if kind == "bank":
        bank_index = day_dir / "bank" / "bank_index.csv"
        row = next((r for r in _read_csv(bank_index) if r["id"] == item_id), None)
        if row is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"bank row {item_id} missing")
        payload = {"row": row, "month": row.get("datum", "")[:7]}
    return match, source_path, payload


def _build_sim_settings(
    base: Settings, *, mode: Literal["isolated", "live"]
) -> tuple[Settings, Path]:
    if mode == "live":
        wiki_dir = base.wiki_dir
        workspace = wiki_dir.parent
        _ensure_git(wiki_dir)
        return (
            Settings(
                wiki_dir=wiki_dir,
                normalize_dir=base.normalize_dir,
                output_dir=base.output_dir,
                data_dir=base.data_dir,
                env=base.env,
                llm_provider=base.llm_provider,
                gemini_api_key=base.gemini_api_key,
                anthropic_api_key=base.anthropic_api_key,
            ),
            workspace,
        )

    workspace = Path(tempfile.mkdtemp(prefix="sim_ingest_"))
    wiki_dir = workspace / "wiki"
    _ensure_git(wiki_dir)
    return (
        Settings(
            wiki_dir=wiki_dir,
            normalize_dir=workspace / "normalize",
            output_dir=workspace / "output",
            data_dir=base.data_dir,
            env="dev",
            llm_provider=base.llm_provider,
            gemini_api_key=base.gemini_api_key,
            anthropic_api_key=base.anthropic_api_key,
        ),
        workspace,
    )


def _ensure_git(wiki_dir: Path) -> None:
    wiki_dir.mkdir(parents=True, exist_ok=True)
    if (wiki_dir / ".git").is_dir():
        return
    for cmd in (
        ["git", "init", "-q"],
        ["git", "config", "user.email", "sim@example.test"],
        ["git", "config", "user.name", "sim"],
        ["git", "config", "commit.gpgsign", "false"],
    ):
        subprocess.run(cmd, cwd=wiki_dir, check=True, capture_output=True)  # noqa: S603
