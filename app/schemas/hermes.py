from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class SubstrateStats(BaseModel):
    model_config = ConfigDict(extra="forbid")
    exists: bool
    total_events: int = 0
    applied_events: int = 0
    miss_events: int = 0
    conflict_events: int = 0
    error_events: int = 0
    last_event_id: str | None = None
    last_ts: str | None = None


class SkillItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    slug: str
    event_type: str
    occurrences: int
    last_event_id: str
    path_templates: list[str] = Field(default_factory=list)
    sample_summaries: list[str] = Field(default_factory=list)


class SkillsBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")
    promoted_count: int = 0
    candidates: list[SkillItem] = Field(default_factory=list)
    buckets: list[SkillItem] = Field(default_factory=list)
    registry_event_types: list[str] = Field(default_factory=list)
    registry_briefings: dict[str, int] = Field(default_factory=dict)
    promotion_threshold: int = 5
    registry_threshold: int = 3


class ProposalItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: str
    target: str
    rationale: str
    evidence_count: int
    evidence_event_ids: list[str] = Field(default_factory=list)


class ProposalsBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")
    total: int = 0
    by_kind: dict[str, int] = Field(default_factory=dict)
    items: list[ProposalItem] = Field(default_factory=list)


class ArtifactPaths(BaseModel):
    model_config = ConfigDict(extra="forbid")
    skills_md: str | None = None
    proposals_md: str | None = None
    feedback_jsonl: str | None = None


class HermesDashboard(BaseModel):
    model_config = ConfigDict(extra="forbid")
    property_id: str
    substrate: SubstrateStats
    skills: SkillsBlock
    proposals: ProposalsBlock
    artifacts: ArtifactPaths
