from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class CreatePageOp(BaseModel):
    model_config = ConfigDict(extra="forbid")
    op: Literal["create_page"] = "create_page"
    path: str
    frontmatter: dict[str, Any] | None = None
    body: str = ""


class UpsertSectionOp(BaseModel):
    model_config = ConfigDict(extra="forbid")
    op: Literal["upsert_section"] = "upsert_section"
    path: str
    heading: str
    body: str = ""


class AppendSectionOp(BaseModel):
    model_config = ConfigDict(extra="forbid")
    op: Literal["append_section"] = "append_section"
    path: str
    heading: str
    line: str


class PrependLogOp(BaseModel):
    model_config = ConfigDict(extra="forbid")
    op: Literal["prepend_log"] = "prepend_log"
    line: str


PatchOp = CreatePageOp | UpsertSectionOp | AppendSectionOp | PrependLogOp


class PatchPlan(BaseModel):
    model_config = ConfigDict(extra="ignore")

    event_id: str
    property_id: str
    summary: str = ""
    event_type: str = "unknown"
    source_ids: list[str] = Field(default_factory=list)
    ops: list[PatchOp] = Field(default_factory=list)
