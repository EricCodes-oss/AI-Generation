"""Auditable contracts for cross-platform viral hotspot discovery."""

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import Field, model_validator

from avatar_pipeline.models import DomainModel, NewsPillarSlug, SourceEvidence, utc_now


class CollectionStatus(StrEnum):
    SUCCESS = "success"
    RESTRICTED = "restricted"
    FAILED = "failed"


class ContentNature(StrEnum):
    NATURAL = "natural"
    ADVERTISEMENT = "advertisement"
    PLATFORM_ACTIVITY = "platform_activity"
    COMMERCIAL_PROMOTION = "commercial_promotion"
    PINNED = "pinned"
    UNKNOWN = "unknown"


class PlatformTrendLabel(StrEnum):
    SURGING = "surging"
    RISING = "rising"
    STABLE = "stable"
    FALLING = "falling"
    UNKNOWN = "unknown"


class TrendLabel(StrEnum):
    INITIAL_SCREEN = "initial_screen"
    SURGING = "surging"
    RISING = "rising"
    STABLE = "stable"
    FALLING = "falling"
    VOLATILE = "volatile"


class DirectorAction(StrEnum):
    DO_NOW = "do_now"
    WATCH = "watch"
    DROP = "drop"


class ViralityBand(StrEnum):
    DIRECTOR_FIRST = "director_first"
    STRONG_CANDIDATE = "strong_candidate"
    BACKUP = "backup"


class HotspotRecord(DomainModel):
    record_id: str = Field(min_length=1)
    platform: str = Field(min_length=1)
    board_name: str = Field(min_length=1)
    captured_at: datetime
    timezone: str = Field(min_length=1)
    rank: int = Field(ge=1)
    title: str = Field(min_length=1)
    heat_raw: str | None = None
    heat_value: float | None = Field(default=None, ge=0)
    url_or_reference: str = Field(min_length=1)
    raw_snapshot_path: str = Field(min_length=1)
    collection_status: CollectionStatus = CollectionStatus.SUCCESS
    content_nature: ContentNature = ContentNature.UNKNOWN
    is_top: bool = False
    published_at: datetime | None = None
    aliases: list[str] = Field(default_factory=list)


class HotspotFailure(DomainModel):
    platform: str = Field(min_length=1)
    captured_at: datetime
    reason: str = Field(min_length=1)
    raw_snapshot_path: str = Field(min_length=1)
    status: CollectionStatus = CollectionStatus.FAILED


class HotspotSnapshot(DomainModel):
    snapshot_id: str = Field(min_length=1)
    captured_at: datetime
    timezone: str = Field(min_length=1)
    records: list[HotspotRecord] = Field(default_factory=list)
    failures: list[HotspotFailure] = Field(default_factory=list)
    imported_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_capture_identity(self) -> "HotspotSnapshot":
        if any(item.captured_at != self.captured_at for item in self.records):
            raise ValueError("record captured_at must equal snapshot captured_at")
        if any(item.captured_at != self.captured_at for item in self.failures):
            raise ValueError("failure captured_at must equal snapshot captured_at")
        ids = [item.record_id for item in self.records]
        if len(ids) != len(set(ids)):
            raise ValueError("record ids must be unique inside a snapshot")
        return self

    @property
    def successful_platforms(self) -> set[str]:
        return {item.platform for item in self.records}

    @property
    def failed_platforms(self) -> set[str]:
        return {item.platform for item in self.failures}


class EventCluster(DomainModel):
    event_id: str = Field(min_length=1)
    representative_title: str = Field(min_length=1)
    aliases: list[str] = Field(default_factory=list)
    record_ids: list[str] = Field(min_length=1)
    platforms: set[str] = Field(min_length=1)
    first_seen_at: datetime
    last_seen_at: datetime
    cluster_confidence: float = Field(ge=0, le=1)
    needs_manual_review: bool = False


class TrendObservation(DomainModel):
    snapshot_id: str = Field(min_length=1)
    captured_at: datetime
    platform_ranks: dict[str, int] = Field(default_factory=dict)
    platform_heat_values: dict[str, float] = Field(default_factory=dict)


class EventTrend(DomainModel):
    event_id: str = Field(min_length=1)
    observations: list[TrendObservation] = Field(min_length=1)
    label: TrendLabel
    platform_trend_labels: dict[str, PlatformTrendLabel] = Field(default_factory=dict)
    consecutive_snapshot_count: int = Field(ge=1)
    new_platform_count: int = Field(ge=0)
    related_subtopic_count: int = Field(default=0, ge=0)
    rank_delta_by_platform: dict[str, int] = Field(default_factory=dict)
    heat_growth_by_platform: dict[str, float] = Field(default_factory=dict)


class VisualPlan(DomainModel):
    has_usable_factual_visuals: bool = False
    ai_demo_available: bool = False
    ai_disclosure: str | None = None
    assets: list[str] = Field(default_factory=list)
    copyright_notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_ai_disclosure(self) -> "VisualPlan":
        if self.ai_demo_available and not self.ai_disclosure:
            raise ValueError("AI demo requires an explicit disclosure")
        return self


class CandidateVerification(DomainModel):
    event_id: str = Field(min_length=1)
    occurred_at: datetime
    core_fact: str = Field(min_length=1)
    sources: list[SourceEvidence] = Field(default_factory=list)
    primary_source_ids: list[str] = Field(default_factory=list)
    unresolved_claims: list[str] = Field(default_factory=list)
    old_news_rehash: bool = False
    major_fact_conflict: bool = False
    exploitative_harm: bool = False
    high_stakes_unresolved: bool = False
    wording_to_avoid: list[str] = Field(default_factory=list)
    cluster_review_approved: bool = False
    related_subtopic_ids: list[str] = Field(default_factory=list)
    visual_plan: VisualPlan
    verified_at: datetime = Field(default_factory=utc_now)


class VerificationDecision(DomainModel):
    event_id: str = Field(min_length=1)
    passed: bool
    age_hours: float = Field(ge=0)
    independent_reliable_source_count: int = Field(ge=0)
    checks: dict[str, bool]
    reasons: list[str] = Field(default_factory=list)


class EditorialSignals(DomainModel):
    event_id: str = Field(min_length=1)
    pillar: NewsPillarSlug
    click_title: str = Field(min_length=1)
    why_click: str = Field(min_length=1)
    opening_hook: str = Field(min_length=1)
    audience_relevance: str = Field(min_length=1)
    expected_lifetime: str = Field(min_length=1)
    conflict_suspense: float = Field(ge=0, le=1)
    public_interest: float = Field(ge=0, le=1)
    curiosity_gap: float = Field(ge=0, le=1)
    visual_impact: float = Field(ge=0, le=1)
    explanatory_depth: float = Field(ge=0, le=1)


class ShortVideoPlatformEvidence(DomainModel):
    platform: str = Field(min_length=1)
    collection_status: CollectionStatus = CollectionStatus.SUCCESS
    failure_reason: str | None = None
    source_count: int = Field(default=0, ge=0)
    comment_sample_count: int = Field(default=0, ge=0)
    views: int | None = Field(default=None, ge=0)
    likes: int | None = Field(default=None, ge=0)
    comments: int | None = Field(default=None, ge=0)
    shares: int | None = Field(default=None, ge=0)
    saves: int | None = Field(default=None, ge=0)
    emotional_signals: list[str] = Field(default_factory=list)
    conflict_signals: list[str] = Field(default_factory=list)
    hook_patterns: list[str] = Field(default_factory=list)
    visual_materials: list[str] = Field(default_factory=list)
    suitability_score: float | None = Field(default=None, ge=0, le=1)
    raw_evidence_paths: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_collection_result(self) -> "ShortVideoPlatformEvidence":
        if self.collection_status is not CollectionStatus.SUCCESS and not self.failure_reason:
            raise ValueError("failed or restricted short-video evidence requires failure_reason")
        if self.collection_status is CollectionStatus.SUCCESS and self.failure_reason:
            raise ValueError("successful short-video evidence cannot declare failure_reason")
        return self

    @property
    def engagement_rate(self) -> float | None:
        if not self.views:
            return None
        interactions = sum(
            value or 0 for value in (self.likes, self.comments, self.shares, self.saves)
        )
        return interactions / self.views


class EventShortVideoEvidence(DomainModel):
    event_id: str = Field(min_length=1)
    captured_at: datetime
    platforms: dict[str, ShortVideoPlatformEvidence] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_platform_keys(self) -> "EventShortVideoEvidence":
        if any(key != item.platform for key, item in self.platforms.items()):
            raise ValueError("short-video platform keys must match evidence platform")
        return self


class ShortVideoAssessment(DomainModel):
    event_id: str = Field(min_length=1)
    passed: bool
    required_platforms: list[str] = Field(default_factory=list)
    missing_platforms: list[str] = Field(default_factory=list)
    restricted_platforms: list[str] = Field(default_factory=list)
    strong_platforms: list[str] = Field(default_factory=list)
    platform_scores: dict[str, float | None] = Field(default_factory=dict)
    checks: dict[str, bool] = Field(default_factory=dict)
    reasons: list[str] = Field(default_factory=list)


class GateDecision(DomainModel):
    event_id: str = Field(min_length=1)
    passed: bool
    checks: dict[str, bool]
    reasons: list[str] = Field(default_factory=list)


class ViralityScore(DomainModel):
    event_id: str = Field(min_length=1)
    rule_version: str = Field(min_length=1)
    cross_platform_resonance: float = Field(ge=0, le=25)
    trend_velocity: float = Field(ge=0, le=20)
    conflict_suspense: float = Field(ge=0, le=15)
    public_interest: float = Field(ge=0, le=10)
    curiosity_gap: float = Field(ge=0, le=10)
    visual_impact: float = Field(ge=0, le=10)
    explanatory_depth: float = Field(ge=0, le=5)
    fact_safety: float = Field(ge=0, le=5)
    total: float = Field(ge=0, le=100)

    @model_validator(mode="after")
    def validate_total(self) -> "ViralityScore":
        components = (
            self.cross_platform_resonance,
            self.trend_velocity,
            self.conflict_suspense,
            self.public_interest,
            self.curiosity_gap,
            self.visual_impact,
            self.explanatory_depth,
            self.fact_safety,
        )
        if abs(self.total - sum(components)) > 0.01:
            raise ValueError("virality total must equal component sum")
        return self


class HotspotCandidateReport(DomainModel):
    event_id: str
    representative_title: str
    click_title: str
    collected_from: datetime
    collected_to: datetime
    platform_evidence: list[str]
    trend_label: TrendLabel
    platform_trend_labels: dict[str, PlatformTrendLabel] = Field(default_factory=dict)
    related_subtopic_count: int = Field(default=0, ge=0)
    score: ViralityScore
    score_band: ViralityBand
    why_click: str
    opening_hook: str
    audience_relevance: str
    visual_assets: list[str]
    copyright_notes: list[str]
    expected_lifetime: str
    risks: list[str]
    wording_to_avoid: list[str]
    director_action: DirectorAction
    pillar: NewsPillarSlug
    source_evidence: list[SourceEvidence]
    verification_summary: str
    short_video_assessment: ShortVideoAssessment


class EvaluatedHotspot(DomainModel):
    cluster: EventCluster
    trend: EventTrend
    gate: GateDecision
    score: ViralityScore | None = None
    verification: CandidateVerification | None = None
    editorial_signals: EditorialSignals | None = None
    short_video_evidence: EventShortVideoEvidence | None = None
    short_video_assessment: ShortVideoAssessment | None = None


class HotspotRejectedEvent(DomainModel):
    event_id: str
    representative_title: str
    reasons: list[str] = Field(min_length=1)


class HotspotReport(DomainModel):
    day: str
    rule_version: str
    generated_at: datetime = Field(default_factory=utc_now)
    snapshot_ids: list[str]
    collection_failures: list[HotspotFailure]
    rejected_events: list[HotspotRejectedEvent] = Field(default_factory=list)
    candidates: list[HotspotCandidateReport] = Field(max_length=3)
    director_recommendation_event_id: str | None = None
    outcome: Literal["qualified_candidates", "no_qualified_hotspot"]
