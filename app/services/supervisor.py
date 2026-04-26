from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any

import structlog
from fastapi import Depends

from app.core.config import Settings, get_settings
from app.schemas.webhook import IngestEvent
from app.services.classify import Classification, classify_document
from app.services.enrich import enrich_with_web_sources
from app.services.extract import extract_patch_plan
from app.services.handlers import get_event_handler
from app.services.llm.client import LLMClient, get_llm_client
from app.services.locate import locate_sections
from app.services.patcher.apply import PatchApplyResult, apply_patch_plan
from app.services.patcher.git import commit_all, head_sha
from app.services.reindex import reindex_files, reindex_property
from app.services.resolve import resolve_context
from app.services.wiki_index import regenerate_index
from app.storage.stammdaten import StammdatenStore, open_stammdaten
from app.storage.wiki_chunks import open_wiki_chunks

log = structlog.get_logger(__name__)

StageCallback = Callable[[str, dict[str, Any]], Awaitable[None]]


async def _noop_stage(_name: str, _data: dict[str, Any]) -> None:
    return None


@dataclass(frozen=True)
class SupervisorResult:
    event_id: str
    status: str
    classification: Classification | None
    patch: PatchApplyResult | None


class Supervisor:
    def __init__(self, *, settings: Settings, llm: LLMClient) -> None:
        self._settings = settings
        self._llm = llm

    async def handle(  # noqa: PLR0915  # supervisor pipeline orchestrates 9 sequential stages
        self,
        event: IngestEvent,
        *,
        on_stage: StageCallback | None = None,
    ) -> SupervisorResult:
        emit = on_stage or _noop_stage
        await emit(
            "normalize",
            {"event_id": event.event_id, "event_type": event.event_type},
        )
        handler = get_event_handler(event.event_type)
        normalized = await handler.handle(event, self._settings)
        await emit(
            "normalize.done",
            {
                "normalized_path": str(normalized.normalized_path),
                "chars": len(normalized.normalized_text),
                "preview": normalized.normalized_text[:280],
            },
        )

        await emit("enrich", {})
        enrichment = await enrich_with_web_sources(
            normalized_text=normalized.normalized_text,
            settings=self._settings,
            on_tool_call=emit,
        )
        enriched_text = enrichment.enriched_text
        await emit(
            "enrich.done",
            {
                "fetched": [p.url for p in enrichment.pages],
                "skipped": enrichment.skipped,
                "chars": len(enriched_text),
            },
        )

        await emit("classify", {})
        classification = await classify_document(
            normalized_text=enriched_text,
            llm=self._llm,
            settings=self._settings,
        )
        await emit(
            "classify.done",
            {
                "signal": classification.signal,
                "category": classification.category,
                "priority": classification.priority,
                "confidence": classification.confidence,
            },
        )
        if not classification.signal:
            log.info(
                "ingest_short_circuit",
                event_id=event.event_id,
                event_type=event.event_type,
                category=classification.category,
            )
            await emit("done", {"status": "no_signal"})
            return SupervisorResult(event.event_id, "no_signal", classification, None)

        await emit("resolve", {})
        stammdaten = self._open_stammdaten(property_id=event.property_id)
        resolution = resolve_context(
            normalized_text=enriched_text,
            stammdaten=stammdaten,
            property_id=event.property_id,
        )
        await emit(
            "resolve.done",
            {"entity_ids": list(resolution.entity_ids)},
        )

        await emit("locate", {})
        wiki_chunks_db = self._wiki_chunks_db_path()
        property_root = self._settings.wiki_dir / event.property_id
        if property_root.is_dir():
            wiki_chunks = open_wiki_chunks(wiki_chunks_db)
            if not wiki_chunks.has_property(event.property_id):
                reindex_property(
                    wiki_dir=self._settings.wiki_dir,
                    property_id=event.property_id,
                    db_path=wiki_chunks_db,
                )
                wiki_chunks = open_wiki_chunks(wiki_chunks_db)
            sections = locate_sections(
                wiki_chunks=wiki_chunks,
                property_id=event.property_id,
                entity_ids=resolution.entity_ids,
                query_text=enriched_text,
            )
        else:
            sections = []
        await emit(
            "locate.done",
            {"sections": [getattr(s, "path", str(s)) for s in sections][:10]},
        )

        existing_pages = _list_existing_pages(property_root)

        await emit("extract", {})
        plan = await extract_patch_plan(
            event_id=event.event_id,
            event_type=event.event_type,
            property_id=event.property_id,
            normalized_text=enriched_text,
            resolution=resolution,
            sections=sections,
            existing_pages=existing_pages,
            llm=self._llm,
            settings=self._settings,
        )
        await emit(
            "extract.done",
            {
                "ops": len(plan.ops),
                "summary": plan.summary,
                "op_kinds": [type(op).__name__ for op in plan.ops],
            },
        )

        await emit("patch", {})
        patch = apply_patch_plan(plan, wiki_dir=self._settings.wiki_dir)
        await emit(
            "patch.done",
            {
                "applied_ops": patch.applied_ops,
                "touched": list(patch.touched),
                "commit": patch.commit_sha[:10] if patch.commit_sha else None,
            },
        )

        await emit("index", {})
        index_path = regenerate_index(self._settings.wiki_dir / event.property_id)
        if index_path is not None:
            commit_all(
                self._settings.wiki_dir,
                message=f"index({event.property_id}): regen after {event.event_id}",
            )
            index_rel = index_path.relative_to(property_root).as_posix()
            new_touched = (
                patch.touched if index_rel in patch.touched else (*patch.touched, index_rel)
            )
            patch = PatchApplyResult(
                event_id=patch.event_id,
                applied_ops=patch.applied_ops,
                commit_sha=head_sha(self._settings.wiki_dir),
                touched=new_touched,
                idempotent=patch.idempotent,
            )

        await emit(
            "index.done",
            {"index_regenerated": index_path is not None},
        )

        files_to_reindex = [t for t in patch.touched if t.endswith(".md")]
        await emit("reindex", {"files": files_to_reindex})
        if files_to_reindex:
            reindex_files(
                wiki_dir=self._settings.wiki_dir,
                property_id=event.property_id,
                files=files_to_reindex,
                db_path=wiki_chunks_db,
            )
        await emit("reindex.done", {"count": len(files_to_reindex)})

        await emit("done", {"status": "applied"})
        return SupervisorResult(event.event_id, "applied", classification, patch)

    def record_failed_event(self, event: IngestEvent, reason: str) -> None:
        log.warning(
            "ingest_failed",
            event_id=event.event_id,
            property_id=event.property_id,
            event_type=event.event_type,
            reason=reason,
        )

    def _open_stammdaten(self, *, property_id: str) -> StammdatenStore:
        db_path = self._settings.output_dir / "stammdaten.duckdb"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        store = open_stammdaten(db_path)
        if store.find_entity_by_id(property_id) is None:
            source = self._settings.data_dir / "stammdaten" / "stammdaten.json"
            if source.is_file():
                store.load_from_json(source)
        return store

    def _wiki_chunks_db_path(self) -> Path:
        self._settings.output_dir.mkdir(parents=True, exist_ok=True)
        return self._settings.output_dir / "wiki_chunks.duckdb"


def _list_existing_pages(property_root: Path) -> list[str]:
    if not property_root.is_dir():
        return []
    pages: list[str] = []
    for path in sorted(property_root.rglob("*.md")):
        rel = path.relative_to(property_root)
        if any(part.startswith("_") for part in rel.parts):
            continue
        pages.append(rel.as_posix())
    return pages


def get_supervisor(
    settings: Annotated[Settings, Depends(get_settings)],
    llm: Annotated[LLMClient, Depends(get_llm_client)],
) -> Supervisor:
    return Supervisor(settings=settings, llm=llm)
