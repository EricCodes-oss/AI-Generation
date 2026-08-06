"""Domain models for the hotspot news-anchor production pipeline."""

from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from avatar_pipeline.voice import DEFAULT_TTS_VOICE_ID


def utc_now() -> datetime:
    return datetime.now(UTC)


class DomainModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class RunMode(StrEnum):
    MANAGED = "managed"
    MANUAL = "manual"


class TopicSource(StrEnum):
    USER_TOPIC = "user_topic"
    AUTO_HOT = "auto_hot"


class AvatarSource(StrEnum):
    USER_PROVIDED = "user_provided"
    SAVED_HOST = "saved_host"
    AGENT_DESIGNED = "agent_designed"


class AvatarLayout(StrEnum):
    SEATED_STUDIO_ANCHOR = "seated_studio_anchor"


class FactStatus(StrEnum):
    VERIFIED = "verified"
    PENDING = "pending"
    UNVERIFIED = "unverified"
    HIGH_RISK = "high_risk"
    MALICIOUS = "malicious"


class ContentPillarSlug(StrEnum):
    """Three research pillars retained for the gated research workflow."""

    CAREER_PRESSURE = "career_pressure"
    PARENT_CHILD_COMMUNICATION = "parent_child_communication"
    SELF_GROWTH = "self_growth"


class NewsPillarSlug(StrEnum):
    """Production pillars for the hotspot news-anchor workflow."""

    SOCIAL_PHENOMENA = "social_phenomena"
    WORKPLACE_LIFE = "workplace_life"
    EDUCATION = "education"
    CONSUMER_LIFE = "consumer_life"
    TECHNOLOGY_LIFE = "technology_life"
    FAMILY_RELATIONSHIPS = "family_relationships"
    YOUTH_LIFESTYLE = "youth_lifestyle"


class MediaKind(StrEnum):
    ANCHOR = "anchor"
    ORIGINAL_NEWS = "original_news"
    AI_DEMO = "ai_demo"


class TaskStatus(StrEnum):
    INPUT_RECEIVED = "input_received"
    RESEARCHING = "researching"
    FACT_SCREENED = "fact_screened"
    TOPIC_SCRIPT_REVIEW = "topic_script_review"
    HOST_REVIEW = "host_review"
    MEDIA_PLANNING = "media_planning"
    GENERATING_TTS = "generating_tts"
    GENERATING_ANCHOR = "generating_anchor"
    ACQUIRING_OR_GENERATING_MEDIA = "acquiring_or_generating_media"
    COMPOSITING = "compositing"
    QUALITY_CHECK = "quality_check"
    FINAL_REVIEW = "final_review"
    READY_TO_PUBLISH = "ready_to_publish"
    STOPPED = "stopped"


class SourceEvidence(DomainModel):
    source_id: str = Field(min_length=1)
    platform: str = Field(min_length=1)
    title: str = Field(min_length=1)
    url_or_reference: str = Field(min_length=1)
    evidence_type: Literal["primary", "corroboration", "official", "reputable_media", "other"]
    published_at: datetime | None = None
    reliability_note: str | None = None


class TopicCandidate(DomainModel):
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    pillar: NewsPillarSlug
    score: float = Field(ge=0, le=100)
    fact_status: FactStatus = FactStatus.PENDING
    target_audience: str | None = None
    situation: str | None = None
    recommendation_reason: str | None = None
    opening_hook: str | None = None
    trend_evidence: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    source_evidence: list[SourceEvidence] = Field(default_factory=list)
    dedupe_key: str | None = None
    cluster_id: str | None = None
    verified_at: datetime | None = None
    verification_summary: str | None = None
    publishable: bool = False

    @model_validator(mode="after")
    def validate_publishability(self) -> "TopicCandidate":
        if self.publishable and self.fact_status is not FactStatus.VERIFIED:
            raise ValueError("publishable candidate must be verified")
        return self


class HostProfile(DomainModel):
    id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    reference_image: str = Field(min_length=1)
    studio_reference: str | None = None
    voice_id: str = Field(default=DEFAULT_TTS_VOICE_ID, min_length=1)
    visual_style: str = "成熟陪伴型新闻主持人"
    is_new: bool = False
    version: int = Field(default=1, ge=1)
    layout: AvatarLayout = AvatarLayout.SEATED_STUDIO_ANCHOR
    age_range: str = "30-36"
    outfit: str = "deep_navy_blazer_ivory_blouse"
    mouth_unobstructed: bool = True

    @model_validator(mode="after")
    def validate_seated_anchor_profile(self) -> "HostProfile":
        if self.layout is not AvatarLayout.SEATED_STUDIO_ANCHOR:
            raise ValueError("host profile layout must be seated_studio_anchor")
        if not self.mouth_unobstructed:
            raise ValueError("mouth_unobstructed must be true for lip sync")
        return self


class ScriptSegment(DomainModel):
    id: str = Field(min_length=1)
    kind: Literal["fact", "context", "interpretation", "conclusion"]
    text: str = Field(min_length=1)
    source_ids: list[str] = Field(default_factory=list)


class NewsScript(DomainModel):
    title: str = Field(min_length=1)
    spoken_segments: list[ScriptSegment] = Field(min_length=1)
    source_ids: list[str] = Field(default_factory=list)
    information_bars: list[str] = Field(default_factory=list)
    ai_disclosure_required: bool = False
    target_duration_seconds: int | None = Field(default=None, ge=1)


class MediaSegment(DomainModel):
    id: str = Field(min_length=1)
    kind: MediaKind
    start_seconds: float = Field(ge=0)
    end_seconds: float = Field(gt=0)
    script_segment_id: str = Field(min_length=1)
    host_id: str | None = Field(default=None, min_length=1)
    source_id: str | None = None
    provenance: str | None = None
    disclosure: str | None = None
    asset_path: str | None = None

    @model_validator(mode="after")
    def validate_interval(self) -> "MediaSegment":
        if self.end_seconds <= self.start_seconds:
            raise ValueError("media segment end must be after start")
        return self


class MediaPlan(DomainModel):
    duration_seconds: float = Field(gt=0)
    segments: list[MediaSegment] = Field(min_length=3)
    anchor_layout: AvatarLayout = AvatarLayout.SEATED_STUDIO_ANCHOR
    host_id: str = Field(min_length=1)
    subtitle_enabled: bool = False
    aspect_ratio: Literal["9:16"] = "9:16"

    @model_validator(mode="after")
    def validate_host_id(self) -> "MediaPlan":
        if not self.host_id.strip():
            raise ValueError("host_id must not be blank")
        return self


class ApprovalRecord(DomainModel):
    gate: Literal["topic_script", "host", "final_video"]
    actor: str = Field(min_length=1)
    approved_at: datetime = Field(default_factory=utc_now)
    automatic: bool = False


class ArtifactRecord(DomainModel):
    kind: str = Field(min_length=1)
    path: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class DailyTask(DomainModel):
    schema_version: int = 2
    day: date
    mode: RunMode = RunMode.MANUAL
    topic_source: TopicSource = TopicSource.AUTO_HOT
    input_text: str | None = None
    avatar_source: AvatarSource = AvatarSource.SAVED_HOST
    status: TaskStatus = TaskStatus.INPUT_RECEIVED
    candidates: list[TopicCandidate] = Field(default_factory=list)
    skipped_candidates: list[TopicCandidate] = Field(default_factory=list)
    selected_topic_id: str | None = None
    host_profile: HostProfile | None = None
    news_script: NewsScript | None = None
    media_plan: MediaPlan | None = None
    subtitle_enabled: bool = False
    video_structure: str = "studio_anchor_plus_vertical_news_insert"
    media_policy: str = "reliable_original_first_ai_demo_fallback"
    platforms: list[str] = Field(
        default_factory=lambda: ["douyin", "wechat_channels", "xiaohongshu"]
    )
    approvals: list[ApprovalRecord] = Field(default_factory=list)
    artifacts: list[ArtifactRecord] = Field(default_factory=list)
    stop_reason: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @property
    def requires_host_approval(self) -> bool:
        return self.host_profile is not None and self.host_profile.is_new

    @model_validator(mode="after")
    def validate_task(self) -> "DailyTask":
        candidate_ids = [candidate.id for candidate in self.candidates]
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError("candidate ids must be unique")
        skipped_ids = [candidate.id for candidate in self.skipped_candidates]
        if set(candidate_ids) & set(skipped_ids):
            raise ValueError("formal and skipped candidate ids must be distinct")
        all_ids = set(candidate_ids)
        if self.selected_topic_id and self.selected_topic_id not in all_ids:
            raise ValueError("selected topic must be one of the formal candidates")
        if self.video_structure != "studio_anchor_plus_vertical_news_insert":
            raise ValueError("unsupported video structure")
        if self.subtitle_enabled:
            raise ValueError("word-for-word subtitles are disabled in V1")
        return self
