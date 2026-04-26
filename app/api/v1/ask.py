from __future__ import annotations

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.ask import AskRequest, AskResponse
from app.services.ask import AskService, get_ask_service

log = structlog.get_logger(__name__)

router = APIRouter()


@router.post("", response_model=AskResponse)
async def ask(
    payload: AskRequest,
    service: Annotated[AskService, Depends(get_ask_service)],
) -> AskResponse:
    try:
        result = await service.answer(
            property_id=payload.lie, question=payload.question, pin=payload.pin
        )
    except Exception as exc:
        log.exception("ask_failed", lie=payload.lie)
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "ask failed") from exc
    return AskResponse(answer=result.answer, path=result.path, pinned_path=result.pinned_path)
