from datetime import UTC, datetime, timedelta

from avatar_pipeline.hotspot_ranking import (
    HotspotRankingResult,
    cluster_sources,
    rank_hotspots,
)
from avatar_pipeline.models import ContentPillarSlug
from avatar_pipeline.research_models import (
    AuthorityEvidence,
    CollectorMethod,
    EngagementMetrics,
    FactVerificationStatus,
    MetricVisibility,
    PlatformEvidenceRecord,
    ResearchPlatform,
    TimeWindow,
)

NOW = datetime(2026, 8, 7, 10, 0, tzinfo=UTC)


def source(
    source_id: str,
    event_key: str,
    platform: ResearchPlatform,
    *,
    hours_ago: int = 12,
    likes: int | None = 100,
    comments: int | None = 10,
) -> PlatformEvidenceRecord:
    published = NOW - timedelta(hours=hours_ago)
    visibility = {}
    if likes is not None:
        visibility["likes"] = MetricVisibility.VISIBLE_EXACT
    if comments is not None:
        visibility["comments"] = MetricVisibility.VISIBLE_EXACT
    return PlatformEvidenceRecord(
        source_id=source_id,
        event_key=event_key,
        platform=platform,
        content_id=source_id,
        canonical_url=f"https://example.test/{source_id}",
        title_or_caption=f"热点 {event_key}",
        published_at=published,
        collected_at=NOW,
        query="热点",
        visible_metrics=EngagementMetrics(likes=likes, comments=comments),
        metric_visibility=visibility,
        collector_method=CollectorMethod.CHROME_AUTHENTICATED,
        raw_evidence_reference=f"raw/{source_id}.json",
    )


def authority(event_key: str, *, verifies: bool = True, conflicts: bool = False):
    return AuthorityEvidence(
        source_id=f"authority-{event_key}",
        publisher="官方机构",
        title=f"事实说明 {event_key}",
        url_or_reference=f"https://authority.example/{event_key}",
        published_at=NOW,
        authority_type="official",
        verifies_fact=verifies,
        conflicts=conflicts,
        summary="核心事实说明",
    )


def metadata(events):
    return {
        key: {
            "pillar": ContentPillarSlug.CAREER_PRESSURE,
            "fact_status": FactVerificationStatus.VERIFIED,
            "verification_summary": "核心事实已由权威来源确认。",
            "authority_evidence": [authority(key)],
        }
        for key in events
    }


def test_cluster_sources_dedupes_same_platform_identity_and_preserves_cross_platform_provenance():
    sources = [
        source("dy-1", "event-1", ResearchPlatform.DOUYIN),
        source("dy-1", "event-1", ResearchPlatform.DOUYIN),
        source("xhs-1", "event-1", ResearchPlatform.XIAOHONGSHU),
    ]
    clusters = cluster_sources(sources, metadata=metadata({"event-1"}))

    assert len(clusters) == 1
    assert [item.source_id for item in clusters[0].platform_evidence] == ["dy-1", "xhs-1"]
    assert {item.platform for item in clusters[0].platform_evidence} == {
        ResearchPlatform.DOUYIN,
        ResearchPlatform.XIAOHONGSHU,
    }


def test_rank_accepts_dual_platform_verified_hotspot():
    sources = [
        source("dy-1", "event-1", ResearchPlatform.DOUYIN, likes=10_000, comments=500),
        source("xhs-1", "event-1", ResearchPlatform.XIAOHONGSHU, likes=8_000, comments=300),
    ]
    result = rank_hotspots(sources, metadata=metadata({"event-1"}), now=NOW)

    assert isinstance(result, HotspotRankingResult)
    assert result.selected_window is TimeWindow.LAST_72_HOURS
    assert len(result.cards) == 1
    assert result.cards[0].total_score > 0


def test_rank_accepts_single_platform_high_heat_only_with_authority():
    sources = [
        source("dy-1", "event-1", ResearchPlatform.DOUYIN, likes=100_000, comments=5_000),
        source("dy-2", "event-2", ResearchPlatform.DOUYIN, likes=10, comments=1),
    ]
    metadata_by_event = metadata({"event-1", "event-2"})
    metadata_by_event["event-2"]["authority_evidence"] = []
    result = rank_hotspots(sources, metadata=metadata_by_event, now=NOW)

    assert [card.cluster_id for card in result.cards] == ["event-1"]


def test_rank_skips_unverified_conflicting_and_risky_topics():
    sources = [
        source("dy-1", "pending", ResearchPlatform.DOUYIN, likes=100_000),
        source("dy-2", "conflict", ResearchPlatform.DOUYIN, likes=90_000),
        source("dy-3", "risk", ResearchPlatform.DOUYIN, likes=80_000),
    ]
    metadata_by_event = metadata({"pending", "conflict", "risk"})
    metadata_by_event["pending"]["fact_status"] = FactVerificationStatus.PENDING
    metadata_by_event["conflict"]["authority_evidence"] = [authority("conflict", conflicts=True)]
    metadata_by_event["risk"]["risk_flags"] = ["malicious_rumor"]

    result = rank_hotspots(sources, metadata=metadata_by_event, now=NOW)

    assert result.cards == []
    assert {cluster.event_key for cluster in result.excluded_clusters} == {
        "pending",
        "conflict",
        "risk",
    }


def test_rank_expands_to_seven_days_only_when_72_hour_pool_has_fewer_than_three():
    sources = [
        source("dy-1", "recent-1", ResearchPlatform.DOUYIN, hours_ago=12, likes=100),
        source("xhs-1", "recent-1", ResearchPlatform.XIAOHONGSHU, hours_ago=12, likes=100),
        source("dy-2", "recent-2", ResearchPlatform.DOUYIN, hours_ago=12, likes=90),
        source("xhs-2", "recent-2", ResearchPlatform.XIAOHONGSHU, hours_ago=12, likes=90),
        source("dy-3", "recent-3", ResearchPlatform.DOUYIN, hours_ago=12, likes=80),
        source("xhs-3", "recent-3", ResearchPlatform.XIAOHONGSHU, hours_ago=12, likes=80),
        source("dy-4", "older", ResearchPlatform.DOUYIN, hours_ago=100, likes=1_000),
        source("xhs-4", "older", ResearchPlatform.XIAOHONGSHU, hours_ago=100, likes=1_000),
    ]
    result = rank_hotspots(
        sources, metadata=metadata({"recent-1", "recent-2", "recent-3", "older"}), now=NOW
    )

    assert result.selected_window is TimeWindow.LAST_72_HOURS
    assert len(result.cards) == 3


def test_rank_uses_seven_day_fallback_when_recent_pool_is_too_small():
    sources = [
        source("dy-1", "recent-1", ResearchPlatform.DOUYIN, hours_ago=12, likes=100),
        source("xhs-1", "recent-1", ResearchPlatform.XIAOHONGSHU, hours_ago=12, likes=100),
        source("dy-2", "older", ResearchPlatform.DOUYIN, hours_ago=100, likes=90),
        source("xhs-2", "older", ResearchPlatform.XIAOHONGSHU, hours_ago=100, likes=90),
    ]
    result = rank_hotspots(sources, metadata=metadata({"recent-1", "older"}), now=NOW)

    assert result.selected_window is TimeWindow.LAST_7_DAYS
    assert {card.cluster_id for card in result.cards} == {"recent-1", "older"}
