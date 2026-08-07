"""Strict domain models for the user-gated daily hotspot research step."""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime
from enum import StrEnum
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator

from avatar_pipeline.models import ContentPillarSlug, utc_now


def _aware_timestamp(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return value


AwareTimestamp = Annotated[datetime, AfterValidator(_aware_timestamp)]


class ResearchModel(BaseModel):
    """Base class for persisted research data."""

    model_config = ConfigDict(extra="forbid")


class ResearchRunStatus(StrEnum):
    DRAFT = "draft"
    COLLECTING = "collecting"
    READY_FOR_REVIEW = "ready_for_review"
    REVISION_REQUESTED = "revision_requested"
    APPROVED = "approved"
    HELD = "held"


class ResearchReviewAction(StrEnum):
    APPROVE = "approve"
    REVISE = "revise"
    REDO = "redo"
    RETURN = "return"
    HOLD = "hold"
    SUPPLEMENT_PLATFORM = "supplement_platform"
    SUPPLEMENT_TOPIC = "supplement_topic"
    RECOLLECT_COMMENTS = "recollect_comments"


class ResearchGrade(StrEnum):
    A = "A"
    B = "B"
    C = "C"


class ResearchPlatform(StrEnum):
    DOUYIN = "douyin"
    WECHAT_CHANNELS = "wechat_channels"
    XIAOHONGSHU = "xiaohongshu"
    ZHIHU = "zhihu"
    WEIBO = "weibo"
    BILIBILI = "bilibili"
    TOUTIAO = "toutiao"
    JIKE = "jike"
    WECHAT_OFFICIAL_ACCOUNTS = "wechat_official_accounts"
    YOUTUBE = "youtube"
    REDDIT = "reddit"
    MANUAL_IMPORT = "manual_import"
    OTHER = "other"


class TimeWindow(StrEnum):
    LAST_72_HOURS = "last_72_hours"
    LAST_7_DAYS = "last_7_days"
    LAST_30_DAYS = "last_30_days"


class ConfidenceLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class CommentSampleType(StrEnum):
    HIGH_LIKE = "high_like"
    LIVED_EXPERIENCE = "lived_experience"
    HELP_SEEKING = "help_seeking"
    DISAGREEMENT = "disagreement"
    LATEST = "latest"


class ImplicitNeed(StrEnum):
    BEING_SEEN = "being_seen"
    BEING_ACCEPTED = "being_accepted"
    BEING_COMFORTED = "being_comforted"
    BEING_EXPLAINED = "being_explained"
    BEING_GUIDED = "being_guided"
    BEING_ACCOMPANIED = "being_accompanied"


class QueryGroup(ResearchModel):
    id: str = Field(min_length=1)
    pillar: ContentPillarSlug
    intent: str = Field(min_length=1)
    scene: str = Field(min_length=1)
    natural_query: str = Field(min_length=1)
    platform_expressions: dict[ResearchPlatform, list[str]] = Field(min_length=1)
    time_window: TimeWindow
    target_count: int | None = Field(default=None, ge=1)
    result_count: int | None = Field(default=None, ge=0)
    is_expansion: bool = False
    parent_query_id: str | None = None
    expansion_reason: str | None = None
    history_notes: list[str] = Field(default_factory=list)
    exclusions: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_group(self) -> QueryGroup:
        for platform, expressions in self.platform_expressions.items():
            if not expressions or any(not expression.strip() for expression in expressions):
                raise ValueError(f"{platform.value} must have non-empty query expressions")
        if self.is_expansion:
            if not self.parent_query_id or not self.expansion_reason:
                raise ValueError("expansion groups require parent_query_id and expansion_reason")
        elif self.parent_query_id is not None or self.expansion_reason is not None:
            raise ValueError("core groups cannot declare expansion metadata")
        return self


class DailyResearchPlan(ResearchModel):
    day: date
    core_groups: list[QueryGroup]
    expansion_groups: list[QueryGroup] = Field(default_factory=list)
    time_window_shares: dict[TimeWindow, float]
    user_directive: str | None = None
    produced_topic_terms: list[str] = Field(default_factory=list)
    planning_notes: list[str] = Field(default_factory=list)
    created_at: AwareTimestamp = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_plan(self) -> DailyResearchPlan:
        if len(self.core_groups) != 9:
            raise ValueError("daily plan requires exactly 9 core query groups")
        if len(self.expansion_groups) > 3:
            raise ValueError("daily plan allows at most 3 expansion groups")
        if any(group.is_expansion for group in self.core_groups):
            raise ValueError("core_groups cannot contain expansion groups")
        if any(not group.is_expansion for group in self.expansion_groups):
            raise ValueError("expansion_groups must contain only expansion groups")

        counts = Counter(group.pillar for group in self.core_groups)
        expected = set(ContentPillarSlug)
        if set(counts) != expected or any(counts[pillar] != 3 for pillar in expected):
            raise ValueError("daily plan requires 3 core query groups per pillar")

        all_ids = [group.id for group in [*self.core_groups, *self.expansion_groups]]
        if len(all_ids) != len(set(all_ids)):
            raise ValueError("query group ids must be unique")
        core_ids = {group.id for group in self.core_groups}
        if any(group.parent_query_id not in core_ids for group in self.expansion_groups):
            raise ValueError("expansion parent_query_id must reference a core query group")

        if set(self.time_window_shares) != set(TimeWindow):
            raise ValueError("time_window_shares must define all supported windows")
        if any(share < 0 or share > 1 for share in self.time_window_shares.values()):
            raise ValueError("time-window shares must be between 0 and 1")
        if abs(sum(self.time_window_shares.values()) - 1.0) > 1e-9:
            raise ValueError("time-window shares must sum to 1.0")
        return self


class EngagementMetrics(ResearchModel):
    views: int | None = Field(default=None, ge=0)
    likes: int | None = Field(default=None, ge=0)
    comments: int | None = Field(default=None, ge=0)
    shares: int | None = Field(default=None, ge=0)
    saves: int | None = Field(default=None, ge=0)
    followers: int | None = Field(default=None, ge=0)
    platform_heat: float | None = Field(default=None, ge=0)


class CollectorMethod(StrEnum):
    """How a source was observed without persisting platform credentials."""

    CHROME_AUTHENTICATED = "chrome_authenticated"
    OPENCLI_BROWSER_BRIDGE = "opencli_browser_bridge"
    BROWSER_ASSISTED = "browser_assisted"
    MANUAL_IMPORT = "manual_import"


class MetricVisibility(StrEnum):
    """Visibility and precision of a platform interaction metric."""

    VISIBLE_EXACT = "visible_exact"
    VISIBLE_APPROXIMATE = "visible_approximate"
    NOT_VISIBLE = "not_visible"
    UNAVAILABLE = "unavailable"


class FactVerificationStatus(StrEnum):
    """Fact state after separating platform discussion from verified facts."""

    VERIFIED = "verified"
    PENDING = "pending"
    CONFLICTING = "conflicting"
    REJECTED = "rejected"


class MediaClearanceStatus(StrEnum):
    """Whether an asset may be used as production media."""

    AUTHORIZED_OFFICIAL = "authorized_official"
    AUTHORIZED_ORIGINAL = "authorized_original"
    AI_ILLUSTRATIVE = "ai_illustrative"
    REJECTED_WATERMARK = "rejected_watermark"
    REJECTED_UNCLEARED = "rejected_uncleared"
    UNKNOWN = "unknown"


_TARGET_VIDEO_PLATFORMS = {
    ResearchPlatform.DOUYIN,
    ResearchPlatform.WECHAT_CHANNELS,
    ResearchPlatform.XIAOHONGSHU,
}


class PlatformEvidenceRecord(ResearchModel):
    """A minimal, credential-free record captured from a target platform."""

    source_id: str = Field(min_length=1)
    event_key: str = Field(min_length=1)
    platform: ResearchPlatform
    content_id: str | None = Field(default=None, min_length=1)
    canonical_url: str | None = Field(default=None, min_length=1)
    account_name: str | None = Field(default=None, min_length=1)
    account_id: str | None = Field(default=None, min_length=1)
    title_or_caption: str = Field(min_length=1)
    published_at: AwareTimestamp | None = None
    collected_at: AwareTimestamp
    query: str = Field(min_length=1)
    visible_metrics: EngagementMetrics = Field(default_factory=EngagementMetrics)
    metric_visibility: dict[str, MetricVisibility] = Field(default_factory=dict)
    collector_method: CollectorMethod
    raw_evidence_reference: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_evidence(self) -> PlatformEvidenceRecord:
        if self.platform not in _TARGET_VIDEO_PLATFORMS:
            raise ValueError("platform must be a target video platform")
        if not self.content_id and not self.canonical_url:
            raise ValueError("source requires a content id or canonical URL")
        for field_name, visibility in self.metric_visibility.items():
            if field_name not in EngagementMetrics.model_fields:
                raise ValueError(f"unknown engagement metric: {field_name}")
            value = getattr(self.visible_metrics, field_name)
            if (
                visibility
                in {
                    MetricVisibility.VISIBLE_EXACT,
                    MetricVisibility.VISIBLE_APPROXIMATE,
                }
                and value is None
            ):
                raise ValueError(f"visible metric {field_name} must have a value")
            if visibility in {MetricVisibility.NOT_VISIBLE, MetricVisibility.UNAVAILABLE} and value:
                raise ValueError(f"unavailable metric {field_name} must remain null")
        return self


class AuthorityEvidence(ResearchModel):
    """An independent public source used for fact verification."""

    source_id: str = Field(min_length=1)
    publisher: str = Field(min_length=1)
    title: str = Field(min_length=1)
    url_or_reference: str = Field(min_length=1)
    published_at: AwareTimestamp | None = None
    authority_type: str = Field(min_length=1)
    verifies_fact: bool
    conflicts: bool = False
    summary: str = Field(min_length=1)


class HotspotScoreBreakdown(ResearchModel):
    """Normalized score components; weights are fixed by the product spec."""

    platform_relative_heat: float = Field(ge=0, le=100)
    cross_platform_resonance: float = Field(ge=0, le=100)
    recency: float = Field(ge=0, le=100)
    comment_quality: float = Field(ge=0, le=100)
    audience_fit: float = Field(ge=0, le=100)
    source_completeness: float = Field(ge=0, le=100)

    @property
    def total_score(self) -> float:
        return round(
            self.platform_relative_heat * 0.35
            + self.cross_platform_resonance * 0.25
            + self.recency * 0.15
            + self.comment_quality * 0.10
            + self.audience_fit * 0.10
            + self.source_completeness * 0.05,
            4,
        )


class HotspotCluster(ResearchModel):
    """A conservative event cluster assembled from platform evidence."""

    id: str = Field(min_length=1)
    event_key: str = Field(min_length=1)
    title: str = Field(min_length=1)
    pillar: ContentPillarSlug
    platform_evidence: list[PlatformEvidenceRecord] = Field(min_length=1)
    authority_evidence: list[AuthorityEvidence] = Field(default_factory=list)
    fact_status: FactVerificationStatus = FactVerificationStatus.PENDING
    verification_summary: str | None = None
    first_seen_at: AwareTimestamp
    last_seen_at: AwareTimestamp
    risk_flags: list[str] = Field(default_factory=list)
    excluded_reason: str | None = None

    @model_validator(mode="after")
    def validate_cluster(self) -> HotspotCluster:
        source_ids = [source.source_id for source in self.platform_evidence]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("source ids must be unique")
        if any(source.event_key != self.event_key for source in self.platform_evidence):
            raise ValueError("platform evidence event key must match cluster event key")
        if self.last_seen_at < self.first_seen_at:
            raise ValueError("last_seen_at cannot precede first_seen_at")
        if self.fact_status is FactVerificationStatus.VERIFIED:
            if not self.verification_summary or not self.verification_summary.strip():
                raise ValueError("verified cluster requires verification summary")
            if any(evidence.conflicts for evidence in self.authority_evidence):
                raise ValueError("verified cluster cannot contain conflicting authority evidence")
            if not any(evidence.verifies_fact for evidence in self.authority_evidence):
                raise ValueError("verified cluster requires authority evidence")
        return self


class HotspotReviewCard(ResearchModel):
    """The only research payload shown at the manual hotspot gate."""

    id: str = Field(min_length=1)
    cluster_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    fact_summary: str = Field(min_length=1)
    pillar: ContentPillarSlug
    time_window: TimeWindow
    score: HotspotScoreBreakdown
    platform_evidence: list[PlatformEvidenceRecord] = Field(min_length=1)
    authority_evidence: list[AuthorityEvidence] = Field(default_factory=list)
    verification_summary: str = Field(min_length=1)
    audience_insight: str | None = None
    speaking_angle: str = Field(min_length=1)
    risk_flags: list[str] = Field(default_factory=list)
    production_media_clearance: MediaClearanceStatus
    production_media_plan: str = Field(min_length=1)

    @property
    def total_score(self) -> float:
        return self.score.total_score

    @model_validator(mode="after")
    def validate_review_card(self) -> HotspotReviewCard:
        platforms = {source.platform for source in self.platform_evidence}
        has_cross_platform = len(platforms) >= 2
        has_authority = any(evidence.verifies_fact for evidence in self.authority_evidence)
        if not has_cross_platform and not has_authority:
            raise ValueError("review card requires cross-platform or authority evidence")
        if self.production_media_clearance in {
            MediaClearanceStatus.REJECTED_WATERMARK,
            MediaClearanceStatus.REJECTED_UNCLEARED,
            MediaClearanceStatus.UNKNOWN,
        }:
            raise ValueError("review card production media must have a safe fallback")
        return self


class ResearchSource(ResearchModel):
    id: str = Field(min_length=1)
    platform: ResearchPlatform
    query_group_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    excerpt: str | None = None
    url: str | None = None
    platform_content_id: str | None = None
    author_label: str | None = None
    pillar: ContentPillarSlug
    grade: ResearchGrade
    metrics: EngagementMetrics = Field(default_factory=EngagementMetrics)
    metric_notes: dict[str, str] = Field(default_factory=dict)
    published_at: AwareTimestamp | None = None
    collector: str = Field(min_length=1)
    collector_version: str = Field(min_length=1)
    raw_artifact_path: str = Field(min_length=1)
    raw_artifact_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    collected_at: AwareTimestamp
    confidence: ConfidenceLevel
    duplicate_of: str | None = None
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_identity(self) -> ResearchSource:
        if not self.url and not self.platform_content_id:
            raise ValueError("source requires a URL or platform content id")
        return self


class CommentInsightCard(ResearchModel):
    source_id: str = Field(min_length=1)
    sample_count: int = Field(ge=1)
    sample_type_counts: dict[CommentSampleType, int] = Field(default_factory=dict)
    role_or_life_stage_clues: list[str] = Field(default_factory=list)
    scenes: list[str] = Field(default_factory=list)
    emotions: list[str] = Field(default_factory=list)
    inner_conflicts: list[str] = Field(default_factory=list)
    explicit_questions: list[str] = Field(default_factory=list)
    implicit_needs: list[ImplicitNeed] = Field(default_factory=list)
    failed_attempts: list[str] = Field(default_factory=list)
    disliked_expressions: list[str] = Field(default_factory=list)
    disagreement_signals: list[str] = Field(default_factory=list)
    representative_paraphrases: list[str] = Field(default_factory=list)
    comment_refs: list[str] = Field(default_factory=list)
    privacy_notes: list[str] = Field(default_factory=list)
    confidence: ConfidenceLevel
    created_at: AwareTimestamp = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_sample(self) -> CommentInsightCard:
        if any(count < 0 for count in self.sample_type_counts.values()):
            raise ValueError("comment sample counts cannot be negative")
        if sum(self.sample_type_counts.values()) != self.sample_count:
            raise ValueError("comment sample type counts must equal sample_count")
        if len(self.comment_refs) != len(set(self.comment_refs)):
            raise ValueError("comment references must be unique")
        return self


class CollectionFailure(ResearchModel):
    platform: ResearchPlatform
    capability: str = Field(min_length=1)
    query_group_id: str | None = None
    message: str = Field(min_length=1)
    error_code: str | None = None
    retryable: bool = False
    attempted_at: AwareTimestamp
    raw_artifact_path: str | None = None


class ResearchReportSummary(ResearchModel):
    valid_source_count: int = Field(default=0, ge=0)
    a_grade_source_count: int = Field(default=0, ge=0)
    insight_card_count: int = Field(default=0, ge=0)
    platform_counts: dict[ResearchPlatform, int] = Field(default_factory=dict)
    pillar_counts: dict[ContentPillarSlug, int] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)


class SkillExecutionRecord(ResearchModel):
    skill_name: str = Field(min_length=1)
    skill_version: str = Field(min_length=1)
    supporting_skills: list[str] = Field(default_factory=list)
    started_at: AwareTimestamp
    completed_at: AwareTimestamp | None = None
    input_artifacts: list[str] = Field(default_factory=list)
    output_artifact: str | None = None
    issues: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_timing(self) -> SkillExecutionRecord:
        if self.completed_at is not None and self.completed_at < self.started_at:
            raise ValueError("completed_at cannot precede started_at")
        return self


class ResearchApprovalRecord(ResearchModel):
    actor: str = Field(min_length=1)
    approved_at: AwareTimestamp = Field(default_factory=utc_now)
    revision: int = Field(ge=1)
    accepted_gaps: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def normalize_approval(self) -> ResearchApprovalRecord:
        self.actor = self.actor.strip()
        if not self.actor:
            raise ValueError("actor must not be blank")
        normalized_gaps = [gap.strip() for gap in self.accepted_gaps]
        if any(not gap for gap in normalized_gaps):
            raise ValueError("accepted gaps must not contain blank entries")
        self.accepted_gaps = normalized_gaps
        return self


class ResearchRun(ResearchModel):
    day: date
    status: ResearchRunStatus = ResearchRunStatus.DRAFT
    revision: int = Field(default=1, ge=1)
    parent_revision: int | None = Field(default=None, ge=1)
    review_action: ResearchReviewAction | None = None
    review_feedback: str | None = None
    plan: DailyResearchPlan | None = None
    sources: list[ResearchSource] = Field(default_factory=list)
    insight_cards: list[CommentInsightCard] = Field(default_factory=list)
    failures: list[CollectionFailure] = Field(default_factory=list)
    summary: ResearchReportSummary = Field(default_factory=ResearchReportSummary)
    skill_executions: list[SkillExecutionRecord] = Field(default_factory=list)
    approvals: list[ResearchApprovalRecord] = Field(default_factory=list)
    report_artifact_path: str | None = None
    created_at: AwareTimestamp = Field(default_factory=utc_now)
    updated_at: AwareTimestamp = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_run(self) -> ResearchRun:
        if self.plan is not None and self.plan.day != self.day:
            raise ValueError("research plan day must match run day")
        source_ids = [source.id for source in self.sources]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("source ids must be unique")
        card_source_ids = [card.source_id for card in self.insight_cards]
        if len(card_source_ids) != len(set(card_source_ids)):
            raise ValueError("insight card source ids must be unique")
        unknown_sources = set(card_source_ids) - set(source_ids)
        if unknown_sources:
            raise ValueError("insight cards must reference sources in the run")
        if self.parent_revision is not None and self.parent_revision >= self.revision:
            raise ValueError("parent_revision must precede revision")
        if any(approval.revision > self.revision for approval in self.approvals):
            raise ValueError("approval revision cannot exceed the run revision")
        return self

    def is_approvable(self) -> bool:
        """Return whether the run meets the research gate without mutating draft data."""

        if self.status is not ResearchRunStatus.READY_FOR_REVIEW or self.plan is None:
            return False
        if not 30 <= len(self.sources) <= 40:
            return False

        sources_by_id = {source.id: source for source in self.sources}
        a_grade_sources = [source for source in self.sources if source.grade is ResearchGrade.A]
        if not 5 <= len(a_grade_sources) <= 8:
            return False
        if not 5 <= len(self.insight_cards) <= 8:
            return False
        if any(not 20 <= card.sample_count <= 40 for card in self.insight_cards):
            return False
        if any(
            sources_by_id.get(card.source_id) is None
            or sources_by_id[card.source_id].grade is not ResearchGrade.A
            for card in self.insight_cards
        ):
            return False

        expected_platform_counts = Counter(source.platform for source in self.sources)
        expected_pillar_counts = Counter(source.pillar for source in self.sources)
        return (
            self.summary.valid_source_count == len(self.sources)
            and self.summary.a_grade_source_count == len(a_grade_sources)
            and self.summary.insight_card_count == len(self.insight_cards)
            and self.summary.platform_counts == dict(expected_platform_counts)
            and (
                not self.summary.pillar_counts
                or self.summary.pillar_counts == dict(expected_pillar_counts)
            )
        )
