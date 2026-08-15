"""Scoring and hard-gate logic for the editorial-opportunity v2 funnel."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import Field

from avatar_pipeline.models import DomainModel, utc_now
from avatar_pipeline.news_intelligence_models import (
    DirectorTopicCard,
    EditorialGrade,
    EditorialOpportunity,
    EditorialOpportunityPool,
    EditorialOpportunityScore,
    FactEvidenceStatus,
    FactSourceTier,
    PoolQualityStatus,
    RejectionCode,
    ScoreComponent,
)


class EditorialOpportunityPolicy(DomainModel):
    s_score_min: float = Field(default=85, ge=0, le=100)
    a_score_min: float = Field(default=78, ge=0, le=100)
    max_user_candidates: int = Field(default=8, ge=1, le=8)
    min_cross_platforms: int = Field(default=2, ge=2)
    max_fact_age_hours: float = Field(default=72, gt=0)


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _round_breakdown(values: dict[str, float]) -> dict[str, float]:
    return {key: round(value, 2) for key, value in values.items()}


def evaluate_rejections(
    opportunity: EditorialOpportunity,
    policy: EditorialOpportunityPolicy,
) -> list[RejectionCode]:
    """Return deterministic hard-rejection reasons without using score thresholds."""

    rejections: list[RejectionCode] = []
    platforms = {item.platform for item in opportunity.attention_signals}
    has_breaking_exception = any(
        item.first_party_breaking for item in opportunity.attention_signals
    )
    if len(platforms) < policy.min_cross_platforms:
        if has_breaking_exception:
            opportunity.watch_only_reason = "first_party_breaking_signal_not_yet_cross_platform"
        else:
            rejections.append(RejectionCode.SINGLE_PLATFORM_ONLY)

    core_supported = any(
        item.is_core_claim
        and item.status in {FactEvidenceStatus.SUPPORTED, FactEvidenceStatus.PARTIALLY_SUPPORTED}
        and item.source_tier
        in {
            FactSourceTier.FIRST_PARTY,
            FactSourceTier.OFFICIAL,
            FactSourceTier.REPUTABLE_MEDIA,
            FactSourceTier.SPECIALIST,
        }
        for item in opportunity.fact_evidence
    )
    if not core_supported:
        rejections.append(RejectionCode.NO_RELIABLE_CORE_FACT)
    if any(item.is_core_claim and item.unresolved_conflict for item in opportunity.fact_evidence):
        rejections.append(RejectionCode.UNRESOLVED_CORE_FACT_CONFLICT)
    if opportunity.recycled_old_news:
        rejections.append(RejectionCode.RECYCLED_OLD_NEWS)
    if opportunity.empty_content:
        rejections.append(RejectionCode.EMPTY_CONTENT)
    if opportunity.pure_outrage_without_payoff:
        rejections.append(RejectionCode.PURE_OUTRAGE_NO_PAYOFF)
    if not opportunity.footage.has_factual_relevant_footage:
        rejections.append(RejectionCode.NO_RELEVANT_FOOTAGE)
    if opportunity.marketing_only_propagation or (
        opportunity.attention_signals
        and all(item.marketing_origin for item in opportunity.attention_signals)
    ):
        rejections.append(RejectionCode.MARKETING_ONLY_PROPAGATION)
    if opportunity.requires_exaggerated_headline:
        rejections.append(RejectionCode.REQUIRES_EXAGGERATED_HEADLINE)
    if opportunity.category == "ordinary_life_moment":
        assessment = opportunity.ordinary_moment_assessment
        if assessment is None:
            rejections.append(RejectionCode.MISSING_ORDINARY_MOMENT_ASSESSMENT)
        else:
            if assessment.creator_is_professional_influencer:
                rejections.append(RejectionCode.PROFESSIONAL_CREATOR_CONTENT)
            if not assessment.account_is_personal_daily_recorder:
                rejections.append(RejectionCode.NOT_PERSONAL_DAILY_RECORDER)
            if not assessment.ordinary_people_are_primary_subjects:
                rejections.append(RejectionCode.ORDINARY_PEOPLE_NOT_PRIMARY_SUBJECTS)
            if assessment.event_was_creator_initiated:
                rejections.append(RejectionCode.CREATOR_INITIATED_EVENT)
            if not assessment.event_preexisted_filming:
                rejections.append(RejectionCode.EVENT_DID_NOT_PREEXIST_FILMING)
            if not assessment.event_is_daily_life_context:
                rejections.append(RejectionCode.NOT_DAILY_LIFE_CONTEXT)
            if not assessment.original_recorder_available:
                rejections.append(RejectionCode.ORIGINAL_RECORDER_UNAVAILABLE)
            if not assessment.continuous_scene_available:
                rejections.append(RejectionCode.NO_CONTINUOUS_SCENE)
            if assessment.staging_risk > 0.35:
                rejections.append(RejectionCode.STAGING_RISK_TOO_HIGH)
    if opportunity.high_stakes_claim:
        has_first_party = any(
            item.is_core_claim
            and item.is_first_party
            and item.status is FactEvidenceStatus.SUPPORTED
            for item in opportunity.fact_evidence
        )
        independent_groups = {
            item.independent_source_group
            for item in opportunity.fact_evidence
            if item.is_core_claim and item.status is FactEvidenceStatus.SUPPORTED
        }
        if not has_first_party or len(independent_groups) < 2:
            rejections.append(RejectionCode.UNSAFE_HIGH_STAKES_CLAIM)
    return rejections


def score_opportunity(
    opportunity: EditorialOpportunity,
    *,
    as_of: datetime | None = None,
) -> EditorialOpportunityScore:
    """Calculate the exact 30/35/20/15 auditable score."""

    as_of = as_of or utc_now()
    signals = opportunity.attention_signals
    platforms = {item.platform for item in signals}
    heat_breakdown = _round_breakdown(
        {
            "cross_platform_resonance": min(len(platforms) / 3, 1) * 8,
            "rank_engagement_velocity": _mean([item.velocity_score for item in signals]) * 8,
            "search_demand_growth": max(
                (item.search_growth_score for item in signals), default=0
            )
            * 5,
            "outlier_content": _mean([item.outlier_score for item in signals]) * 5,
            "persistence": _mean([item.persistence_score for item in signals]) * 4,
        }
    )

    values = opportunity.editorial_values
    attraction_breakdown = _round_breakdown(
        {
            "curiosity_gap": values.curiosity_gap * 8,
            "conflict_contrast_suspense": values.conflict_contrast_suspense * 7,
            "human_stakes": values.human_stakes * 6,
            "emotional_intensity": values.emotional_intensity * 5,
            "explanatory_payoff": values.explanatory_payoff * 5,
            "ordinary_people_proximity": values.ordinary_people_proximity * 4,
        }
    )

    supported_core = [
        item
        for item in opportunity.fact_evidence
        if item.is_core_claim and item.status is FactEvidenceStatus.SUPPORTED
    ]
    has_primary = any(
        item.source_tier in {FactSourceTier.FIRST_PARTY, FactSourceTier.OFFICIAL}
        for item in supported_core
    )
    independent_groups = {item.independent_source_group for item in supported_core}
    dated = [item.published_at for item in supported_core if item.published_at is not None]
    newest_age_hours = min(
        (max((as_of - published_at).total_seconds() / 3600, 0) for published_at in dated),
        default=None,
    )
    if newest_age_hours is None:
        recency_score = 0.0
    elif newest_age_hours <= 24:
        recency_score = 3.0
    elif newest_age_hours <= 72:
        recency_score = 2.0
    else:
        recency_score = 0.5
    unresolved = any(
        item.is_core_claim
        and (
            item.unresolved_conflict
            or item.status in {FactEvidenceStatus.UNSUPPORTED, FactEvidenceStatus.UNCERTAIN}
        )
        for item in opportunity.fact_evidence
    )
    fact_breakdown = _round_breakdown(
        {
            "first_party_official": 8.0 if has_primary else 0.0,
            "independent_corroboration": min(len(independent_groups) / 2, 1) * 5,
            "recency": recency_score,
            "unresolved_claim_control": 0.0 if unresolved else 4.0,
        }
    )

    footage = opportunity.footage
    video_breakdown = _round_breakdown(
        {
            "factual_relevant_footage": 6.0 if footage.has_factual_relevant_footage else 0.0,
            "coherent_visual_narrative": footage.coherent_narrative_score * 4,
            "quality_era_match": footage.quality_era_match_score * 3,
            "acquisition_feasibility": footage.acquisition_feasibility_score * 2,
        }
    )

    return EditorialOpportunityScore(
        real_heat=ScoreComponent(
            score=round(sum(heat_breakdown.values()), 2),
            maximum=30,
            reasons=[f"{len(platforms)}个平台形成注意力信号"],
            breakdown=heat_breakdown,
        ),
        content_attractiveness=ScoreComponent(
            score=round(sum(attraction_breakdown.values()), 2),
            maximum=35,
            reasons=[opportunity.strongest_tension, opportunity.viewer_payoff],
            breakdown=attraction_breakdown,
        ),
        fact_reliability=ScoreComponent(
            score=round(sum(fact_breakdown.values()), 2),
            maximum=20,
            reasons=[f"{len(independent_groups)}组独立事实来源"],
            breakdown=fact_breakdown,
        ),
        video_potential=ScoreComponent(
            score=round(sum(video_breakdown.values()), 2),
            maximum=15,
            reasons=[
                f"可用连续画面约{footage.usable_continuous_seconds:g}秒",
                *footage.risks,
            ],
            breakdown=video_breakdown,
        ),
    )


def grade_opportunity(
    score: EditorialOpportunityScore,
    rejections: list[RejectionCode],
    policy: EditorialOpportunityPolicy,
    *,
    watch_only: bool = False,
) -> EditorialGrade:
    if rejections:
        return EditorialGrade.DROP
    if watch_only:
        return EditorialGrade.B
    if score.total >= policy.s_score_min:
        return EditorialGrade.S
    if score.total >= policy.a_score_min:
        return EditorialGrade.A
    return EditorialGrade.B


def _heat_evidence(opportunity: EditorialOpportunity) -> list[str]:
    evidence: list[str] = []
    for signal in opportunity.attention_signals:
        details = [signal.platform, signal.source_kind.value]
        if signal.velocity_score:
            details.append(f"增速{signal.velocity_score:.0%}")
        if signal.search_growth_score:
            details.append(f"搜索增长{signal.search_growth_score:.0%}")
        if signal.outlier_score:
            details.append(f"异常传播{signal.outlier_score:.0%}")
        evidence.append(" / ".join(details))
    return evidence


def _fact_sources(opportunity: EditorialOpportunity) -> list[str]:
    return [
        f"{item.source_name}：{item.claim_text}（{item.status.value}）"
        for item in opportunity.fact_evidence
        if item.status in {FactEvidenceStatus.SUPPORTED, FactEvidenceStatus.PARTIALLY_SUPPORTED}
    ]


def build_opportunity_pool(
    day: date,
    opportunities: list[EditorialOpportunity],
    *,
    policy: EditorialOpportunityPolicy | None = None,
    as_of: datetime | None = None,
) -> EditorialOpportunityPool:
    """Return only qualified S/A cards; never pad the list with weak candidates."""

    policy = policy or EditorialOpportunityPolicy()
    as_of = as_of or utc_now()
    cards: list[DirectorTopicCard] = []
    rejected: dict[str, list[str]] = {}
    for opportunity in opportunities:
        rejections = evaluate_rejections(opportunity, policy)
        score = score_opportunity(opportunity, as_of=as_of)
        grade = grade_opportunity(
            score,
            rejections,
            policy,
            watch_only=opportunity.watch_only_reason is not None,
        )
        if grade not in {EditorialGrade.S, EditorialGrade.A}:
            reasons = [item.value for item in rejections]
            if opportunity.watch_only_reason:
                reasons.append(opportunity.watch_only_reason)
            if not reasons:
                reasons.append(f"score_below_a_threshold:{score.total:g}")
            rejected[opportunity.opportunity_id] = reasons
            continue
        cards.append(
            DirectorTopicCard(
                opportunity_id=opportunity.opportunity_id,
                candidate_title=opportunity.title,
                category=opportunity.category,
                latest_development=opportunity.latest_development,
                why_today=opportunity.why_today,
                heat_evidence=_heat_evidence(opportunity),
                strongest_tension=opportunity.strongest_tension,
                ordinary_people_relevance=opportunity.ordinary_people_relevance,
                viewer_payoff=opportunity.viewer_payoff,
                three_second_hook=opportunity.three_second_hook,
                reliable_fact_sources=_fact_sources(opportunity),
                footage_candidates=opportunity.footage.assets,
                footage_risks=opportunity.footage.risks,
                expected_heat_lifetime=opportunity.expected_heat_lifetime,
                grade=grade,
                score=score.total,
                score_breakdown=score,
                ordinary_moment_assessment=opportunity.ordinary_moment_assessment,
            )
        )
    cards.sort(key=lambda item: (item.grade is EditorialGrade.S, item.score), reverse=True)
    cards = cards[: policy.max_user_candidates]
    quality = (
        PoolQualityStatus.HAS_S_TIER
        if any(item.grade is EditorialGrade.S for item in cards)
        else PoolQualityStatus.NO_S_TIER
    )
    return EditorialOpportunityPool(
        day=day,
        candidates=cards,
        quality_status=quality,
        generated_at=as_of,
        reviewed_count=len(opportunities),
        rejected_reasons=rejected,
    )
