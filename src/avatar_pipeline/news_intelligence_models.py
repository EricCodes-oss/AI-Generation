"""Auditable contracts for the editorial-opportunity v2 news intelligence funnel."""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum

from pydantic import Field, computed_field, model_validator

from avatar_pipeline.models import DomainModel, utc_now
from avatar_pipeline.ordinary_moments import OrdinaryMomentAssessment


class EvidenceRole(StrEnum):
    ATTENTION_SIGNAL = "attention_signal"
    FACT_EVIDENCE = "fact_evidence"
    FOOTAGE_CANDIDATE = "footage_candidate"


class AttentionSourceKind(StrEnum):
    DOMESTIC_BOARD = "domestic_boards"
    AUTHORITATIVE_MEDIA = "authoritative_media"
    SEARCH_DEMAND = "search_demand"
    SOCIAL_DISCUSSION = "social_discussion"
    VIDEO_PROPAGATION = "video_propagation"
    VERTICAL_COMMUNITY = "vertical_communities"


class FactSourceTier(StrEnum):
    FIRST_PARTY = "first_party"
    OFFICIAL = "official"
    REPUTABLE_MEDIA = "reputable_media"
    SPECIALIST = "specialist"
    OTHER = "other"


class FactEvidenceStatus(StrEnum):
    SUPPORTED = "supported"
    PARTIALLY_SUPPORTED = "partially_supported"
    UNSUPPORTED = "unsupported"
    UNCERTAIN = "uncertain"


class EditorialGrade(StrEnum):
    S = "S"
    A = "A"
    B = "B"
    DROP = "DROP"


class PoolQualityStatus(StrEnum):
    HAS_S_TIER = "has_s_tier"
    NO_S_TIER = "no_s_tier"


class RejectionCode(StrEnum):
    SINGLE_PLATFORM_ONLY = "single_platform_only"
    NO_RELIABLE_CORE_FACT = "no_reliable_core_fact"
    RECYCLED_OLD_NEWS = "recycled_old_news"
    EMPTY_CONTENT = "hot_title_empty_content"
    PURE_OUTRAGE_NO_PAYOFF = "pure_outrage_no_explanatory_value"
    NO_RELEVANT_FOOTAGE = "no_relevant_footage"
    UNRESOLVED_CORE_FACT_CONFLICT = "unresolved_core_fact_conflict"
    UNSAFE_HIGH_STAKES_CLAIM = "unsafe_high_stakes_claim"
    MARKETING_ONLY_PROPAGATION = "marketing_only_propagation"
    REQUIRES_EXAGGERATED_HEADLINE = "requires_exaggerated_headline"
    MISSING_ORDINARY_MOMENT_ASSESSMENT = "missing_ordinary_moment_assessment"
    PROFESSIONAL_CREATOR_CONTENT = "professional_creator_content"
    NOT_PERSONAL_DAILY_RECORDER = "not_personal_daily_recorder"
    ORDINARY_PEOPLE_NOT_PRIMARY_SUBJECTS = "ordinary_people_not_primary_subjects"
    CREATOR_INITIATED_EVENT = "creator_initiated_event"
    EVENT_DID_NOT_PREEXIST_FILMING = "event_did_not_preexist_filming"
    NOT_DAILY_LIFE_CONTEXT = "not_daily_life_context"
    ORIGINAL_RECORDER_UNAVAILABLE = "original_recorder_unavailable"
    NO_CONTINUOUS_SCENE = "no_continuous_scene"
    STAGING_RISK_TOO_HIGH = "staging_risk_too_high"


class AttentionSignal(DomainModel):
    signal_id: str = Field(min_length=1)
    source_kind: AttentionSourceKind
    platform: str = Field(min_length=1)
    captured_at: datetime
    url_or_reference: str = Field(min_length=1)
    roles: list[EvidenceRole] = Field(default_factory=lambda: [EvidenceRole.ATTENTION_SIGNAL])
    raw_snapshot_path: str = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)
    rank: int | None = Field(default=None, ge=1)
    engagement: int | None = Field(default=None, ge=0)
    velocity_score: float = Field(default=0, ge=0, le=1)
    account_baseline_ratio: float | None = Field(default=None, ge=0)
    search_growth_score: float = Field(default=0, ge=0, le=1)
    outlier_score: float = Field(default=0, ge=0, le=1)
    persistence_score: float = Field(default=0, ge=0, le=1)
    repeated_questions: list[str] = Field(default_factory=list)
    first_party_breaking: bool = False
    marketing_origin: bool = False

    @model_validator(mode="after")
    def validate_attention_role(self) -> AttentionSignal:
        if EvidenceRole.FACT_EVIDENCE in self.roles:
            raise ValueError("attention signals cannot be fact evidence")
        if EvidenceRole.ATTENTION_SIGNAL not in self.roles:
            raise ValueError("attention signal requires the attention_signal role")
        return self


class FactEvidence(DomainModel):
    evidence_id: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)
    claim_text: str = Field(min_length=1)
    source_name: str = Field(min_length=1)
    source_tier: FactSourceTier
    published_at: datetime | None = None
    url_or_reference: str = Field(min_length=1)
    status: FactEvidenceStatus
    is_first_party: bool = False
    independent_source_group: str = Field(min_length=1)
    unresolved_conflict: bool = False
    is_core_claim: bool = False

    @model_validator(mode="after")
    def validate_first_party_tier(self) -> FactEvidence:
        if self.is_first_party and self.source_tier not in {
            FactSourceTier.FIRST_PARTY,
            FactSourceTier.OFFICIAL,
        }:
            raise ValueError("first-party evidence must use a first_party or official tier")
        return self


class FootageAssessment(DomainModel):
    has_factual_relevant_footage: bool
    coherent_narrative_score: float = Field(ge=0, le=1)
    quality_era_match_score: float = Field(ge=0, le=1)
    acquisition_feasibility_score: float = Field(ge=0, le=1)
    assets: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    acquisition_notes: list[str] = Field(default_factory=list)
    rights_notes: list[str] = Field(default_factory=list)
    usable_continuous_seconds: float = Field(default=0, ge=0)


class EditorialValueSignals(DomainModel):
    curiosity_gap: float = Field(ge=0, le=1)
    conflict_contrast_suspense: float = Field(ge=0, le=1)
    human_stakes: float = Field(ge=0, le=1)
    emotional_intensity: float = Field(ge=0, le=1)
    explanatory_payoff: float = Field(ge=0, le=1)
    ordinary_people_proximity: float = Field(ge=0, le=1)


class ScoreComponent(DomainModel):
    score: float = Field(ge=0)
    maximum: float = Field(gt=0)
    reasons: list[str] = Field(min_length=1)
    breakdown: dict[str, float] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_score_bound(self) -> ScoreComponent:
        if self.score > self.maximum:
            raise ValueError("component score cannot exceed maximum")
        if self.breakdown and abs(sum(self.breakdown.values()) - self.score) > 0.011:
            raise ValueError("component breakdown must sum to score")
        return self


class EditorialOpportunityScore(DomainModel):
    real_heat: ScoreComponent
    content_attractiveness: ScoreComponent
    fact_reliability: ScoreComponent
    video_potential: ScoreComponent

    @computed_field
    @property
    def total(self) -> float:
        return round(
            self.real_heat.score
            + self.content_attractiveness.score
            + self.fact_reliability.score
            + self.video_potential.score,
            2,
        )

    @computed_field
    @property
    def maximum(self) -> float:
        return round(
            self.real_heat.maximum
            + self.content_attractiveness.maximum
            + self.fact_reliability.maximum
            + self.video_potential.maximum,
            2,
        )

    @model_validator(mode="after")
    def validate_total_maximum(self) -> EditorialOpportunityScore:
        if abs(self.maximum - 100) > 1e-9:
            raise ValueError("editorial opportunity score maximum must equal 100")
        return self


class EditorialOpportunity(DomainModel):
    opportunity_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    category: str = Field(min_length=1)
    latest_development: str = Field(min_length=1)
    why_today: str = Field(min_length=1)
    strongest_tension: str = Field(min_length=1)
    ordinary_people_relevance: str = Field(min_length=1)
    viewer_payoff: str = Field(min_length=1)
    three_second_hook: str = Field(min_length=1)
    expected_heat_lifetime: str = Field(min_length=1)
    attention_signals: list[AttentionSignal] = Field(default_factory=list)
    fact_evidence: list[FactEvidence] = Field(default_factory=list)
    footage: FootageAssessment
    editorial_values: EditorialValueSignals
    recycled_old_news: bool = False
    marketing_only_propagation: bool = False
    high_stakes_claim: bool = False
    empty_content: bool = False
    pure_outrage_without_payoff: bool = False
    requires_exaggerated_headline: bool = False
    watch_only_reason: str | None = None
    ordinary_moment_assessment: OrdinaryMomentAssessment | None = None

    @model_validator(mode="after")
    def validate_unique_evidence_ids(self) -> EditorialOpportunity:
        signal_ids = [item.signal_id for item in self.attention_signals]
        fact_ids = [item.evidence_id for item in self.fact_evidence]
        if len(signal_ids) != len(set(signal_ids)):
            raise ValueError("attention signal IDs must be unique")
        if len(fact_ids) != len(set(fact_ids)):
            raise ValueError("fact evidence IDs must be unique")
        return self


class DirectorTopicCard(DomainModel):
    opportunity_id: str = Field(min_length=1)
    candidate_title: str = Field(min_length=1)
    category: str = Field(min_length=1)
    latest_development: str = Field(min_length=1)
    why_today: str = Field(min_length=1)
    heat_evidence: list[str] = Field(min_length=1)
    strongest_tension: str = Field(min_length=1)
    ordinary_people_relevance: str = Field(min_length=1)
    viewer_payoff: str = Field(min_length=1)
    three_second_hook: str = Field(min_length=1)
    reliable_fact_sources: list[str] = Field(min_length=1)
    footage_candidates: list[str] = Field(min_length=1)
    footage_risks: list[str] = Field(default_factory=list)
    expected_heat_lifetime: str = Field(min_length=1)
    grade: EditorialGrade
    score: float = Field(ge=0, le=100)
    score_breakdown: EditorialOpportunityScore | None = None
    do_not_produce_reasons: list[str] = Field(default_factory=list)
    ordinary_moment_assessment: OrdinaryMomentAssessment | None = None

    @model_validator(mode="after")
    def validate_recommended_grade(self) -> DirectorTopicCard:
        if self.grade not in {EditorialGrade.S, EditorialGrade.A}:
            raise ValueError("user-visible director cards must be S or A grade")
        return self


class EditorialOpportunityPool(DomainModel):
    day: date
    candidates: list[DirectorTopicCard] = Field(default_factory=list, max_length=8)
    quality_status: PoolQualityStatus
    generated_at: datetime = Field(default_factory=utc_now)
    rule_version: str = "editorial-opportunity-v2.0"
    requires_user_selection: bool = True
    reviewed_count: int = Field(default=0, ge=0)
    rejected_reasons: dict[str, list[str]] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_pool_consistency(self) -> EditorialOpportunityPool:
        ids = [item.opportunity_id for item in self.candidates]
        if len(ids) != len(set(ids)):
            raise ValueError("candidate IDs must be unique")
        has_s = any(item.grade is EditorialGrade.S for item in self.candidates)
        if has_s != (self.quality_status is PoolQualityStatus.HAS_S_TIER):
            raise ValueError("pool quality status must match S-tier candidates")
        if not self.requires_user_selection:
            raise ValueError("editorial opportunity pools require user selection")
        return self
