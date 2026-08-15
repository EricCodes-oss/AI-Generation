from datetime import date, datetime, timedelta

from avatar_pipeline.editorial_opportunity import (
    EditorialOpportunityPolicy,
    build_opportunity_pool,
    evaluate_rejections,
    score_opportunity,
)
from avatar_pipeline.news_intelligence_models import (
    AttentionSignal,
    AttentionSourceKind,
    EditorialGrade,
    EditorialOpportunity,
    EditorialValueSignals,
    FactEvidence,
    FactEvidenceStatus,
    FactSourceTier,
    FootageAssessment,
    RejectionCode,
)

NOW = datetime.fromisoformat("2026-08-13T10:00:00+08:00")


def attention(
    signal_id: str,
    platform: str,
    *,
    velocity: float = 0.8,
    search_growth: float = 0.0,
    outlier: float = 0.7,
    persistence: float = 0.8,
    first_party_breaking: bool = False,
    marketing: bool = False,
) -> AttentionSignal:
    return AttentionSignal(
        signal_id=signal_id,
        source_kind=(
            AttentionSourceKind.SEARCH_DEMAND
            if search_growth
            else AttentionSourceKind.DOMESTIC_BOARD
        ),
        platform=platform,
        captured_at=NOW,
        url_or_reference=f"{platform}:{signal_id}",
        roles=["attention_signal"],
        raw_snapshot_path=f"raw/{signal_id}.json",
        confidence=0.9,
        velocity_score=velocity,
        search_growth_score=search_growth,
        outlier_score=outlier,
        persistence_score=persistence,
        first_party_breaking=first_party_breaking,
        marketing_origin=marketing,
    )


def fact(
    evidence_id: str = "fact-1",
    *,
    first_party: bool = True,
    group: str = "official",
    conflict: bool = False,
) -> FactEvidence:
    return FactEvidence(
        evidence_id=evidence_id,
        claim_id="core-claim",
        claim_text="核心事实",
        source_name="第一方公告" if first_party else "权威媒体",
        source_tier=(FactSourceTier.FIRST_PARTY if first_party else FactSourceTier.REPUTABLE_MEDIA),
        published_at=NOW - timedelta(hours=2),
        url_or_reference=f"https://example.test/{evidence_id}",
        status=FactEvidenceStatus.SUPPORTED,
        is_first_party=first_party,
        independent_source_group=group,
        unresolved_conflict=conflict,
        is_core_claim=True,
    )


def opportunity(
    opportunity_id: str = "topic-1",
    *,
    attentions: list[AttentionSignal] | None = None,
    facts: list[FactEvidence] | None = None,
    footage: FootageAssessment | None = None,
    recycled: bool = False,
    marketing_only: bool = False,
    high_stakes: bool = False,
) -> EditorialOpportunity:
    return EditorialOpportunity(
        opportunity_id=opportunity_id,
        title="高关注事件为什么突然反转",
        category="social_livelihood",
        latest_development="今天公布最新结果",
        why_today="多平台传播和搜索需求在今天同步抬升",
        strongest_tension="结果与公众此前预期相反",
        ordinary_people_relevance="影响普通人的消费判断",
        viewer_payoff="看懂事件因果和真实影响",
        three_second_hook="一家仍在盈利的门店，为什么突然关闭？",
        expected_heat_lifetime="24-48小时",
        attention_signals=attentions
        or [attention("s1", "baidu"), attention("s2", "toutiao"), attention("s3", "x")],
        fact_evidence=(
            [fact(), fact("fact-2", first_party=False, group="media-a")]
            if facts is None
            else facts
        ),
        footage=footage
        or FootageAssessment(
            has_factual_relevant_footage=True,
            coherent_narrative_score=0.9,
            quality_era_match_score=0.9,
            acquisition_feasibility_score=0.8,
            assets=["真实连续画面"],
            usable_continuous_seconds=35,
        ),
        editorial_values=EditorialValueSignals(
            curiosity_gap=0.95,
            conflict_contrast_suspense=0.9,
            human_stakes=0.8,
            emotional_intensity=0.7,
            explanatory_payoff=0.9,
            ordinary_people_proximity=0.8,
        ),
        recycled_old_news=recycled,
        marketing_only_propagation=marketing_only,
        high_stakes_claim=high_stakes,
    )


def test_single_platform_only_is_rejected():
    item = opportunity(attentions=[attention("s1", "baidu")])
    assert RejectionCode.SINGLE_PLATFORM_ONLY in evaluate_rejections(
        item, EditorialOpportunityPolicy()
    )


def test_first_party_breaking_single_platform_is_watch_only_not_recommended():
    item = opportunity(
        attentions=[attention("s1", "official", first_party_breaking=True)]
    )
    assert RejectionCode.SINGLE_PLATFORM_ONLY not in evaluate_rejections(
        item, EditorialOpportunityPolicy()
    )
    pool = build_opportunity_pool(date(2026, 8, 13), [item], as_of=NOW)
    assert pool.candidates == []
    assert item.watch_only_reason == "first_party_breaking_signal_not_yet_cross_platform"


def test_missing_reliable_core_fact_and_unresolved_conflict_are_rejected():
    unsupported = opportunity(facts=[])
    conflicted = opportunity(facts=[fact(conflict=True)])
    assert RejectionCode.NO_RELIABLE_CORE_FACT in evaluate_rejections(
        unsupported, EditorialOpportunityPolicy()
    )
    assert RejectionCode.UNRESOLVED_CORE_FACT_CONFLICT in evaluate_rejections(
        conflicted, EditorialOpportunityPolicy()
    )


def test_old_news_marketing_only_and_missing_footage_are_rejected():
    no_footage = FootageAssessment(
        has_factual_relevant_footage=False,
        coherent_narrative_score=0,
        quality_era_match_score=0,
        acquisition_feasibility_score=0,
    )
    item = opportunity(recycled=True, marketing_only=True, footage=no_footage)
    rejected = evaluate_rejections(item, EditorialOpportunityPolicy())
    assert RejectionCode.RECYCLED_OLD_NEWS in rejected
    assert RejectionCode.MARKETING_ONLY_PROPAGATION in rejected
    assert RejectionCode.NO_RELEVANT_FOOTAGE in rejected


def test_score_is_100_point_auditable_and_rewards_velocity_search_and_outliers():
    strong = opportunity(
        attentions=[
            attention("s1", "baidu", velocity=1, search_growth=1, outlier=1, persistence=1),
            attention("s2", "toutiao", velocity=1, outlier=1, persistence=1),
            attention("s3", "x", velocity=1, outlier=1, persistence=1),
        ]
    )
    weak = opportunity(
        opportunity_id="weak",
        attentions=[
            attention("w1", "baidu", velocity=0.1, outlier=0.1, persistence=0.1),
            attention("w2", "toutiao", velocity=0.1, outlier=0.1, persistence=0.1),
        ],
    )
    strong_score = score_opportunity(strong, as_of=NOW)
    weak_score = score_opportunity(weak, as_of=NOW)
    assert strong_score.maximum == 100
    assert 0 <= strong_score.total <= 100
    assert strong_score.real_heat.score > weak_score.real_heat.score


def test_pool_ranks_qualified_candidates_and_does_not_pad_weak_ones():
    strong = opportunity("strong")
    weak = opportunity(
        "weak",
        attentions=[attention("w1", "baidu"), attention("w2", "toutiao")],
    )
    weak.editorial_values = EditorialValueSignals(
        curiosity_gap=0.1,
        conflict_contrast_suspense=0.1,
        human_stakes=0.1,
        emotional_intensity=0.1,
        explanatory_payoff=0.1,
        ordinary_people_proximity=0.1,
    )
    pool = build_opportunity_pool(date(2026, 8, 13), [weak, strong], as_of=NOW)
    assert [item.opportunity_id for item in pool.candidates] == ["strong"]
    assert pool.candidates[0].grade in {EditorialGrade.S, EditorialGrade.A}


def test_ordinary_life_moment_requires_natural_event_audit_before_candidate_pool():
    from avatar_pipeline.ordinary_moments import OrdinaryMomentAssessment, RecordingOrigin

    missing = opportunity("ordinary-missing")
    missing.category = "ordinary_life_moment"
    assert RejectionCode.MISSING_ORDINARY_MOMENT_ASSESSMENT in evaluate_rejections(
        missing, EditorialOpportunityPolicy()
    )

    creator_led = opportunity("ordinary-creator")
    creator_led.category = "ordinary_life_moment"
    creator_led.ordinary_moment_assessment = OrdinaryMomentAssessment(
        recording_origin=RecordingOrigin.PASSERBY_PHONE,
        creator_is_professional_influencer=True,
        account_is_personal_daily_recorder=False,
        ordinary_people_are_primary_subjects=False,
        event_was_creator_initiated=True,
        event_preexisted_filming=False,
        event_is_daily_life_context=False,
        natural_reaction_evidence=["镜头前有固定栏目话术"],
        human_warmth_evidence=["只有策划话术，没有自然流露"],
        original_recorder_available=True,
        ambient_audio_available=True,
        continuous_scene_available=True,
        staging_risk=0.8,
    )
    rejected = evaluate_rejections(creator_led, EditorialOpportunityPolicy())
    assert RejectionCode.PROFESSIONAL_CREATOR_CONTENT in rejected
    assert RejectionCode.NOT_PERSONAL_DAILY_RECORDER in rejected
    assert RejectionCode.ORDINARY_PEOPLE_NOT_PRIMARY_SUBJECTS in rejected
    assert RejectionCode.NOT_DAILY_LIFE_CONTEXT in rejected
    assert RejectionCode.CREATOR_INITIATED_EVENT in rejected
    assert RejectionCode.EVENT_DID_NOT_PREEXIST_FILMING in rejected
    assert RejectionCode.STAGING_RISK_TOO_HIGH in rejected


def test_ordinary_life_moment_audit_survives_director_card_conversion():
    from avatar_pipeline.ordinary_moments import OrdinaryMomentAssessment, RecordingOrigin

    item = opportunity("ordinary-natural")
    item.category = "ordinary_life_moment"
    item.ordinary_moment_assessment = OrdinaryMomentAssessment(
        recording_origin=RecordingOrigin.CCTV,
        creator_is_professional_influencer=False,
        account_is_personal_daily_recorder=True,
        ordinary_people_are_primary_subjects=True,
        event_was_creator_initiated=False,
        event_preexisted_filming=True,
        event_is_daily_life_context=True,
        natural_reaction_evidence=["监控连续记录，当事人未面向镜头表演"],
        human_warmth_evidence=["家人之间的关心在日常动作中自然流露"],
        original_recorder_available=True,
        ambient_audio_available=False,
        continuous_scene_available=True,
        staging_risk=0.05,
    )
    pool = build_opportunity_pool(date(2026, 8, 15), [item], as_of=NOW)
    assert len(pool.candidates) == 1
    assert pool.candidates[0].ordinary_moment_assessment == item.ordinary_moment_assessment
