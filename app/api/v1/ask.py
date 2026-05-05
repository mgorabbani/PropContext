from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from typing import Annotated

import anyio
import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.schemas.ask import AskRequest, AskResponse, AskStepOut, AskUsageOut
from app.services.ask import AskService, AskStep, get_ask_service

log = structlog.get_logger(__name__)

router = APIRouter()


@router.post("", response_model=AskResponse)
async def ask(
    payload: AskRequest,
    service: Annotated[AskService, Depends(get_ask_service)],
) -> AskResponse:
    try:
        result = await service.answer(
            property_id=payload.lie,
            question=payload.question,
            pin=payload.pin,
            history=[(t.question, t.answer) for t in payload.history],
        )
    except Exception as exc:
        log.exception("ask_failed", lie=payload.lie)
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "ask failed") from exc
    return _serialize(result)


def _serialize(result) -> AskResponse:  # type: ignore[no-untyped-def]
    return AskResponse(
        answer=result.answer,
        path=result.path,
        pinned_path=result.pinned_path,
        usage=(
            AskUsageOut(
                input_tokens=result.usage.input_tokens,
                output_tokens=result.usage.output_tokens,
                cache_read_input_tokens=result.usage.cache_read_input_tokens,
                cache_creation_input_tokens=result.usage.cache_creation_input_tokens,
                sections=result.usage.sections,
            )
            if result.usage
            else None
        ),
        steps=[
            AskStepOut(label=s.label, detail=s.detail, paths=s.paths)
            for s in (result.steps or [])
        ],
    )


@router.post("/stream")
async def ask_stream(
    payload: AskRequest,
    service: Annotated[AskService, Depends(get_ask_service)],
) -> StreamingResponse:
    return StreamingResponse(
        _ask_event_stream(payload, service),
        media_type="text/event-stream",
        headers={
            "cache-control": "no-cache",
            "connection": "keep-alive",
            "x-accel-buffering": "no",
        },
    )


async def _ask_event_stream(
    payload: AskRequest, service: AskService
) -> AsyncGenerator[str]:
    send, recv = anyio.create_memory_object_stream[tuple[str, dict]](64)

    async def emit_step(step: AskStep) -> None:
        await send.send(
            (
                "step",
                {"label": step.label, "detail": step.detail, "paths": step.paths},
            )
        )

    async def runner() -> None:
        try:
            result = await service.answer(
                property_id=payload.lie,
                question=payload.question,
                pin=payload.pin,
                history=[(t.question, t.answer) for t in payload.history],
                on_step=emit_step,
            )
            response = _serialize(result)
            await send.send(("response", json.loads(response.model_dump_json())))
        except HTTPException as exc:
            await send.send(("error", {"status": exc.status_code, "detail": str(exc.detail)}))
        except Exception as exc:
            log.exception("ask_stream_failed", lie=payload.lie)
            await send.send(("error", {"status": 500, "detail": str(exc)}))
        finally:
            await send.aclose()

    async with anyio.create_task_group() as tg:
        tg.start_soon(runner)
        async with recv:
            async for name, data in recv:
                msg = json.dumps(
                    {"stage": name, "data": data}, separators=(",", ":"), default=str
                )
                yield f"event: stage\ndata: {msg}\n\n"
