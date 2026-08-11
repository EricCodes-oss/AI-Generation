from datetime import datetime

from avatar_pipeline.config import load_config
from avatar_pipeline.hotspot_models import (
    CollectionStatus,
    EventShortVideoEvidence,
    ShortVideoPlatformEvidence,
)
from avatar_pipeline.short_video_signals import assess_short_video_evidence

CONFIG = load_config("configs/default.yaml").hotspot


def platform_evidence(
    platform: str,
    *,
    engagement_rate: float = 0.05,
    comment_sample_count: int = 20,
    suitability_score: float = 0.8,
) -> ShortVideoPlatformEvidence:
    views = 100_000
    interactions = int(views * engagement_rate)
    return ShortVideoPlatformEvidence(
        platform=platform,
        collection_status=CollectionStatus.SUCCESS,
        source_count=3,
        comment_sample_count=comment_sample_count,
        views=views,
        likes=interactions,
        comments=0,
        shares=0,
        saves=0,
        emotional_signals=["惊讶"],
        conflict_signals=["预期与现实冲突"],
        hook_patterns=["结果先行"],
        visual_materials=["现场画面"],
        suitability_score=suitability_score,
        raw_evidence_paths=[f"tmp/{platform}.json"],
    )


def test_douyin_and_xiaohongshu_strong_signals_pass_director_readiness():
    evidence = EventShortVideoEvidence(
        event_id="event-1",
        captured_at=datetime.fromisoformat("2026-08-11T11:30:00+08:00"),
        platforms={
            "douyin": platform_evidence("douyin"),
            "xiaohongshu": platform_evidence("xiaohongshu"),
        },
    )
    assessment = assess_short_video_evidence(evidence, CONFIG)
    assert assessment.passed is True
    assert assessment.missing_platforms == []
    assert assessment.strong_platforms == ["douyin", "xiaohongshu"]
    assert assessment.reasons == []


def test_missing_xiaohongshu_is_unknown_not_zero_and_cannot_pass():
    evidence = EventShortVideoEvidence(
        event_id="event-1",
        captured_at=datetime.fromisoformat("2026-08-11T11:30:00+08:00"),
        platforms={"douyin": platform_evidence("douyin")},
    )
    assessment = assess_short_video_evidence(evidence, CONFIG)
    assert assessment.passed is False
    assert assessment.platform_scores["xiaohongshu"] is None
    assert assessment.missing_platforms == ["xiaohongshu"]
    assert "missing_short_video_evidence:xiaohongshu" in assessment.reasons


def test_restricted_xiaohongshu_preserves_failure_instead_of_zero_heat():
    evidence = EventShortVideoEvidence(
        event_id="event-1",
        captured_at=datetime.fromisoformat("2026-08-11T11:30:00+08:00"),
        platforms={
            "douyin": platform_evidence("douyin"),
            "xiaohongshu": ShortVideoPlatformEvidence(
                platform="xiaohongshu",
                collection_status=CollectionStatus.RESTRICTED,
                failure_reason="login verification required",
                raw_evidence_paths=["tmp/xiaohongshu-error.json"],
            ),
        },
    )
    assessment = assess_short_video_evidence(evidence, CONFIG)
    assert assessment.passed is False
    assert assessment.platform_scores["xiaohongshu"] is None
    assert "restricted_short_video_evidence:xiaohongshu" in assessment.reasons
    assert "login verification required" in assessment.reasons


def test_low_short_video_engagement_stays_watch_only():
    evidence = EventShortVideoEvidence(
        event_id="event-1",
        captured_at=datetime.fromisoformat("2026-08-11T11:30:00+08:00"),
        platforms={
            "douyin": platform_evidence("douyin", engagement_rate=0.01),
            "xiaohongshu": platform_evidence("xiaohongshu"),
        },
    )
    assessment = assess_short_video_evidence(evidence, CONFIG)
    assert assessment.passed is False
    assert assessment.platform_scores["douyin"] is not None
    assert "low_short_video_engagement:douyin" in assessment.reasons


def test_xiaohongshu_can_use_observed_interactions_when_views_are_not_public():
    xiaohongshu = platform_evidence("xiaohongshu")
    xiaohongshu = xiaohongshu.model_copy(
        update={
            "views": None,
            "likes": 8_000,
            "comments": 800,
            "shares": 200,
            "saves": 4_000,
        }
    )
    evidence = EventShortVideoEvidence(
        event_id="event-1",
        captured_at=datetime.fromisoformat("2026-08-11T11:30:00+08:00"),
        platforms={
            "douyin": platform_evidence("douyin"),
            "xiaohongshu": xiaohongshu,
        },
    )
    assessment = assess_short_video_evidence(evidence, CONFIG)
    assert assessment.passed is True
    assert assessment.platform_scores["xiaohongshu"] is not None
    assert "unknown_short_video_engagement:xiaohongshu" not in assessment.reasons
