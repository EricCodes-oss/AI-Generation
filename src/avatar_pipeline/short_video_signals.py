"""Evaluate Douyin and Xiaohongshu evidence without inventing missing heat."""

from avatar_pipeline.config import HotspotConfig
from avatar_pipeline.hotspot_models import (
    CollectionStatus,
    EventShortVideoEvidence,
    ShortVideoAssessment,
    ShortVideoPlatformEvidence,
)


def _platform_score(
    evidence: ShortVideoPlatformEvidence,
    config: HotspotConfig,
) -> float | None:
    if evidence.collection_status is not CollectionStatus.SUCCESS:
        return None
    engagement_rate = evidence.engagement_rate
    observed_interactions = sum(
        value or 0
        for value in (evidence.likes, evidence.comments, evidence.shares, evidence.saves)
    )
    engagement_score = (
        min(1.0, engagement_rate / config.min_short_video_engagement_rate)
        if engagement_rate is not None
        else min(
            1.0,
            observed_interactions / config.min_short_video_observed_interactions,
        )
    )
    source_score = min(1.0, evidence.source_count / config.min_short_video_sources_per_platform)
    comment_score = min(
        1.0,
        evidence.comment_sample_count / config.min_short_video_comment_samples_per_platform,
    )
    suitability_score = evidence.suitability_score or 0.0
    return round(
        0.2 * source_score
        + 0.2 * comment_score
        + 0.3 * engagement_score
        + 0.3 * suitability_score,
        4,
    )


def assess_short_video_evidence(
    evidence: EventShortVideoEvidence | None,
    config: HotspotConfig,
    *,
    event_id: str | None = None,
) -> ShortVideoAssessment:
    """Require positive evidence on every configured short-video platform."""

    resolved_event_id = evidence.event_id if evidence else event_id
    if not resolved_event_id:
        raise ValueError("event_id is required when short-video evidence is absent")

    required = list(config.required_short_video_platforms)
    platform_scores: dict[str, float | None] = {}
    missing: list[str] = []
    restricted: list[str] = []
    strong: list[str] = []
    checks: dict[str, bool] = {}
    reasons: list[str] = []

    for platform in required:
        item = evidence.platforms.get(platform) if evidence else None
        if item is None:
            missing.append(platform)
            platform_scores[platform] = None
            checks[f"short_video_evidence:{platform}"] = False
            reasons.append(f"missing_short_video_evidence:{platform}")
            continue
        if item.collection_status is not CollectionStatus.SUCCESS:
            restricted.append(platform)
            platform_scores[platform] = None
            checks[f"short_video_evidence:{platform}"] = False
            reasons.append(f"restricted_short_video_evidence:{platform}")
            if item.failure_reason and item.failure_reason not in reasons:
                reasons.append(item.failure_reason)
            continue

        score = _platform_score(item, config)
        platform_scores[platform] = score
        source_ok = item.source_count >= config.min_short_video_sources_per_platform
        comments_ok = (
            item.comment_sample_count
            >= config.min_short_video_comment_samples_per_platform
        )
        observed_interactions = sum(
            value or 0
            for value in (item.likes, item.comments, item.shares, item.saves)
        )
        engagement_ok = (
            item.engagement_rate is not None
            and item.engagement_rate >= config.min_short_video_engagement_rate
        ) or (
            item.views is None
            and observed_interactions >= config.min_short_video_observed_interactions
        )
        suitability_ok = (
            item.suitability_score is not None
            and item.suitability_score >= config.min_short_video_platform_score
        )
        platform_ok = (
            source_ok
            and comments_ok
            and engagement_ok
            and suitability_ok
            and score is not None
            and score >= config.min_short_video_platform_score
        )
        checks[f"short_video_evidence:{platform}"] = platform_ok
        if not source_ok:
            reasons.append(f"insufficient_short_video_sources:{platform}")
        if not comments_ok:
            reasons.append(f"insufficient_comment_samples:{platform}")
        if not engagement_ok:
            reasons.append(f"low_short_video_engagement:{platform}")
        if not suitability_ok:
            reasons.append(f"low_short_video_suitability:{platform}")
        if platform_ok:
            strong.append(platform)

    return ShortVideoAssessment(
        event_id=resolved_event_id,
        passed=len(strong) == len(required),
        required_platforms=required,
        missing_platforms=missing,
        restricted_platforms=restricted,
        strong_platforms=strong,
        platform_scores=platform_scores,
        checks=checks,
        reasons=reasons,
    )
