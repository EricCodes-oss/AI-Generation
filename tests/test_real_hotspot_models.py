from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from avatar_pipeline.models import ContentPillarSlug
from avatar_pipeline.research_models import (
    AuthorityEvidence,
    CollectorMethod,
    EngagementMetrics,
    FactVerificationStatus,
    HotspotCluster,
    HotspotReviewCard,
    HotspotScoreBreakdown,
    MediaClearanceStatus,
    MetricVisibility,
    PlatformEvidenceRecord,
    ResearchPlatform,
    TimeWindow,
)

NOW = datetime(2026, 8, 7, 10, 0, tzinfo=UTC)


def platform_source(
    source_id: str = "dy-1",
    platform: ResearchPlatform = ResearchPlatform.DOUYIN,
) -> PlatformEvidenceRecord:
    return PlatformEvidenceRecord(
        source_id=source_id,
        event_key="event-1",
        platform=platform,
        content_id=f"content-{source_id}",
        canonical_url=f"https://example.test/{source_id}",
        account_name="公开账号",
        title_or_caption="年轻人开始重新讨论下班后的边界感",
        published_at=NOW,
        collected_at=NOW,
        query="职场边界",
        visible_metrics=EngagementMetrics(likes=12_000, comments=380),
        metric_visibility={
            "likes": MetricVisibility.VISIBLE_EXACT,
            "comments": MetricVisibility.VISIBLE_EXACT,
            "views": MetricVisibility.NOT_VISIBLE,
        },
        collector_method=CollectorMethod.CHROME_AUTHENTICATED,
        raw_evidence_reference="raw/douyin/event-1.json",
    )


def authority() -> AuthorityEvidence:
    return AuthorityEvidence(
        source_id="authority-1",
        publisher="权威机构",
        title="权威机构公开说明",
        url_or_reference="https://authority.example/notice",
        published_at=NOW,
        authority_type="official",
        verifies_fact=True,
        conflicts=False,
        summary="确认核心事实，未确认网传延伸说法。",
    )


def score() -> HotspotScoreBreakdown:
    return HotspotScoreBreakdown(
        platform_relative_heat=80,
        cross_platform_resonance=60,
        recency=100,
        comment_quality=70,
        audience_fit=90,
        source_completeness=80,
    )


def test_platform_evidence_keeps_unknown_metrics_null_and_tracks_visibility():
    source = platform_source()

    assert source.visible_metrics.views is None
    assert source.metric_visibility["views"] is MetricVisibility.NOT_VISIBLE
    assert source.collector_method is CollectorMethod.CHROME_AUTHENTICATED


def test_platform_evidence_accepts_only_target_video_platforms():
    with pytest.raises(ValidationError, match="target video platform"):
        platform_source(platform=ResearchPlatform.WECHAT_OFFICIAL_ACCOUNTS)


def test_platform_evidence_requires_identity_and_rejects_unknown_or_credential_fields():
    payload = platform_source().model_dump()
    payload["cookie"] = "secret"
    with pytest.raises(ValidationError, match="Extra inputs"):
        PlatformEvidenceRecord.model_validate(payload)

    payload = platform_source().model_dump()
    payload["content_id"] = None
    payload["canonical_url"] = None
    with pytest.raises(ValidationError, match="content id or canonical URL"):
        PlatformEvidenceRecord.model_validate(payload)


def test_cluster_requires_unique_sources_and_consistent_event_keys():
    first = platform_source("dy-1", ResearchPlatform.DOUYIN)
    duplicate = first.model_copy()
    with pytest.raises(ValidationError, match="source ids must be unique"):
        HotspotCluster(
            id="cluster-1",
            event_key="event-1",
            title="职场边界讨论",
            pillar=ContentPillarSlug.CAREER_PRESSURE,
            platform_evidence=[first, duplicate],
            authority_evidence=[authority()],
            fact_status=FactVerificationStatus.VERIFIED,
            verification_summary="核心事实已核验。",
            first_seen_at=NOW,
            last_seen_at=NOW,
        )

    wrong_event = platform_source("xhs-1", ResearchPlatform.XIAOHONGSHU).model_copy(
        update={"event_key": "event-2"}
    )
    with pytest.raises(ValidationError, match="event key"):
        HotspotCluster(
            id="cluster-1",
            event_key="event-1",
            title="职场边界讨论",
            pillar=ContentPillarSlug.CAREER_PRESSURE,
            platform_evidence=[first, wrong_event],
            authority_evidence=[authority()],
            fact_status=FactVerificationStatus.VERIFIED,
            verification_summary="核心事实已核验。",
            first_seen_at=NOW,
            last_seen_at=NOW,
        )


def test_score_uses_documented_weights_and_is_bounded():
    breakdown = score()
    assert breakdown.total_score == pytest.approx(78.0)

    with pytest.raises(ValidationError, match="less than or equal to 100"):
        HotspotScoreBreakdown(
            platform_relative_heat=101,
            cross_platform_resonance=60,
            recency=100,
            comment_quality=70,
            audience_fit=90,
            source_completeness=80,
        )


def test_review_card_separates_research_evidence_from_production_media_clearance():
    card = HotspotReviewCard(
        id="candidate-1",
        cluster_id="cluster-1",
        title="职场边界讨论升温",
        fact_summary="多个平台正在讨论下班后的工作边界，核心事实已核验。",
        pillar=ContentPillarSlug.CAREER_PRESSURE,
        time_window=TimeWindow.LAST_72_HOURS,
        score=score(),
        platform_evidence=[
            platform_source("dy-1", ResearchPlatform.DOUYIN),
            platform_source("xhs-1", ResearchPlatform.XIAOHONGSHU),
        ],
        authority_evidence=[authority()],
        verification_summary="双平台出现，并由权威来源确认核心事实。",
        audience_insight="用户关注工作与生活边界。",
        speaking_angle="讨论如何在不激化矛盾的情况下建立边界。",
        production_media_clearance=MediaClearanceStatus.AI_ILLUSTRATIVE,
        production_media_plan="使用 Seedance 2.0 生成非复刻式职场示意画面。",
    )

    assert card.production_media_clearance is MediaClearanceStatus.AI_ILLUSTRATIVE
    assert len(card.platform_evidence) == 2
    assert all(item.raw_evidence_reference for item in card.platform_evidence)


def test_verified_cluster_requires_summary_and_non_conflicting_authority():
    with pytest.raises(ValidationError, match="verification summary"):
        HotspotCluster(
            id="cluster-1",
            event_key="event-1",
            title="职场边界讨论",
            pillar=ContentPillarSlug.CAREER_PRESSURE,
            platform_evidence=[platform_source()],
            authority_evidence=[authority()],
            fact_status=FactVerificationStatus.VERIFIED,
            first_seen_at=NOW,
            last_seen_at=NOW,
        )

    conflicting = authority().model_copy(update={"conflicts": True})
    with pytest.raises(ValidationError, match="conflicting authority"):
        HotspotCluster(
            id="cluster-1",
            event_key="event-1",
            title="职场边界讨论",
            pillar=ContentPillarSlug.CAREER_PRESSURE,
            platform_evidence=[platform_source()],
            authority_evidence=[conflicting],
            fact_status=FactVerificationStatus.VERIFIED,
            verification_summary="错误地声称已经核验。",
            first_seen_at=NOW,
            last_seen_at=NOW,
        )
