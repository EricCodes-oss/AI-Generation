"""Domain models for one daily avatar-video production task."""

from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


def utc_now() -> datetime:
    """Return an aware UTC timestamp."""

    return datetime.now(UTC)


class DomainModel(BaseModel):
    """Strict base model for persisted workflow data."""

    model_config = ConfigDict(extra="forbid")


class ContentPillarSlug(StrEnum):
    CAREER_PRESSURE = "career_pressure"
    PARENT_CHILD_COMMUNICATION = "parent_child_communication"
    SELF_GROWTH = "self_growth"


class TaskStatus(StrEnum):
    CREATED = "created"
    RESEARCHED = "researched"
    TOPIC_APPROVED = "topic_approved"
    SCRIPT_DRAFT = "script_draft"
    SCRIPT_APPROVED = "script_approved"
    AUDIO_READY = "audio_ready"
    ASSETS_GENERATING = "assets_generating"
    COMPOSITING = "compositing"
    QC_FAILED = "qc_failed"
    QC_PASSED = "qc_passed"
    VIDEO_APPROVED = "video_approved"
    PUBLISHED = "published"
    ANALYZED = "analyzed"


class TopicCandidate(DomainModel):
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    pillar: ContentPillarSlug
    score: float = Field(ge=0, le=100)
    target_audience: str | None = None
    situation: str | None = None
    pain_point: str | None = None
    trend_evidence: list[str] = Field(default_factory=list)
    recommendation_reason: str | None = None
    opening_hook: str | None = None
    emotion: str | None = None
    risks: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)


class ApprovalRecord(DomainModel):
    gate: str = Field(pattern=r"^(topic|script|video)$")
    actor: str = Field(min_length=1)
    approved_at: datetime = Field(default_factory=utc_now)


class ArtifactRecord(DomainModel):
    kind: str = Field(min_length=1)
    path: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class DailyTask(DomainModel):
    day: date
    status: TaskStatus = TaskStatus.CREATED
    candidates: list[TopicCandidate] = Field(default_factory=list)
    selected_topic_id: str | None = None
    script_text: str | None = None
    approvals: list[ApprovalRecord] = Field(default_factory=list)
    artifacts: list[ArtifactRecord] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_candidates(self) -> "DailyTask":
        if self.candidates and len(self.candidates) != 3:
            raise ValueError("a researched task must contain exactly three candidates")
        candidate_ids = [candidate.id for candidate in self.candidates]
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError("candidate ids must be unique")
        if self.selected_topic_id and self.selected_topic_id not in set(candidate_ids):
            raise ValueError("selected topic must be one of the candidates")
        return self
