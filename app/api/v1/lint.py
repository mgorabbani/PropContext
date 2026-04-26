from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.schemas.properties import PropertyId
from app.services.lint import LintService, get_lint_service

router = APIRouter()


class LintFindingOut(BaseModel):
    kind: str
    path: str
    detail: str = ""


class LintResponse(BaseModel):
    property_id: str
    findings: list[LintFindingOut]
    report_path: str | None
    commit_sha: str | None


@router.post("/{property_id}")
async def run_lint(
    property_id: PropertyId,
    service: Annotated[LintService, Depends(get_lint_service)],
) -> LintResponse:
    result = service.lint(property_id)
    return LintResponse(
        property_id=result.property_id,
        findings=[
            LintFindingOut(kind=f.kind, path=f.path, detail=f.detail) for f in result.findings
        ],
        report_path=str(result.report_path) if result.report_path else None,
        commit_sha=result.commit_sha,
    )
