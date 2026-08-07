"""Deterministic clustering, verification gates, and ranking for daily hotspots.

The module deliberately keeps event clustering conservative: callers must provide an
``event_key`` from the collection/verification step.  It does not infer that two
similar captions describe the same real-world event.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from math import exp, log1p
from typing import Any

from avatar_pipeline.models import ContentPillarSlug
from avatar_pipeline.research_models import (
    AuthorityEvidence,
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

_TARGET_PLATFORMS = {
    ResearchPlatform.DOUYIN,
    ResearchPlatform.WECHAT_CHANNELS,
    ResearchPlatform.XIAOHONGSHU,
}
_SINGLE_PLATFORM_HIGH_HEAT_THRESHOLD = 80.0


@dataclass(frozen=True)
class HotspotRankingResult:
    """Result shown to the manual hotspot confirmation gate."""

    cards: list[HotspotReviewCard]
    excluded_clusters: list[HotspotCluster]
    selected_window: TimeWindow


def cluster_sources(
    sources: Sequence[PlatformEvidenceRecord],
    *,
    metadata: Mapping[str, Mapping[str, Any]],
) -> list[HotspotCluster]:
    """Deduplicate evidence and assemble conservative event clusters.

    ``event_key`` is intentionally the only cross-platform grouping key.  This
    prevents the ranking layer from merging merely similar topics or emotional
    language into one purported event.
    """

    unique_sources = _deduplicate_sources(sources)
    grouped: dict[str, list[PlatformEvidenceRecord]] = {}
    for item in unique_sources:
        grouped.setdefault(item.event_key, []).append(item)

    clusters: list[HotspotCluster] = []
    for event_key, evidence in grouped.items():
        event_metadata = metadata.get(event_key, {})
        authority_evidence = _authority_evidence(event_metadata.get("authority_evidence", []))
        requested_status = _enum_value(
            event_metadata.get("fact_status", FactVerificationStatus.PENDING),
            FactVerificationStatus,
        )
        fact_status = _safe_fact_status(requested_status, authority_evidence)
        published_times = [item.published_at for item in evidence if item.published_at is not None]
        observed_times = published_times or [item.collected_at for item in evidence]
        title = str(event_metadata.get("title") or evidence[0].title_or_caption).strip()
        pillar = _enum_value(
            event_metadata.get("pillar", ContentPillarSlug.CAREER_PRESSURE),
            ContentPillarSlug,
        )
        clusters.append(
            HotspotCluster(
                id=event_key,
                event_key=event_key,
                title=title,
                pillar=pillar,
                platform_evidence=evidence,
                authority_evidence=authority_evidence,
                fact_status=fact_status,
                verification_summary=_text_or_none(event_metadata.get("verification_summary")),
                first_seen_at=min(observed_times),
                last_seen_at=max(observed_times),
                risk_flags=_string_list(event_metadata.get("risk_flags", [])),
            )
        )
    return clusters


def rank_hotspots(
    sources: Sequence[PlatformEvidenceRecord],
    *,
    metadata: Mapping[str, Mapping[str, Any]],
    now: datetime,
    limit: int = 3,
) -> HotspotRankingResult:
    """Apply hard safety gates, then rank eligible clusters for review."""

    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    if limit < 1:
        raise ValueError("limit must be at least 1")

    clusters = cluster_sources(sources, metadata=metadata)
    recent_sources = _sources_in_window(sources, now=now, duration=timedelta(hours=72))
    recent_ids = {item.source_id for item in recent_sources}
    recent_clusters = [
        cluster
        for cluster in clusters
        if any(item.source_id in recent_ids for item in cluster.platform_evidence)
    ]

    eligible_recent, excluded = _eligible_clusters(recent_clusters, metadata=metadata, now=now)
    selected_window = TimeWindow.LAST_72_HOURS
    selected = eligible_recent

    if len(selected) < limit:
        week_sources = _sources_in_window(sources, now=now, duration=timedelta(days=7))
        week_ids = {item.source_id for item in week_sources}
        week_clusters = [
            cluster
            for cluster in clusters
            if any(item.source_id in week_ids for item in cluster.platform_evidence)
        ]
        eligible_week, week_excluded = _eligible_clusters(week_clusters, metadata=metadata, now=now)
        # Keep the 72-hour label when the wider window adds no candidate. This
        # avoids claiming an expansion occurred merely because fewer than three
        # total candidates existed.
        if len(eligible_week) > len(selected):
            selected = eligible_week
            selected_window = TimeWindow.LAST_7_DAYS
        excluded = _merge_excluded(excluded, week_excluded)

    score_maxima = _platform_maxima(clusters)
    ranked = sorted(
        selected,
        key=lambda cluster: _cluster_sort_key(cluster, now=now, platform_maxima=score_maxima),
        reverse=True,
    )[:limit]
    cards = [
        _review_card(
            cluster,
            metadata=metadata.get(cluster.event_key, {}),
            now=now,
            time_window=selected_window,
            platform_maxima=_platform_maxima(clusters),
        )
        for cluster in ranked
    ]
    return HotspotRankingResult(
        cards=cards,
        excluded_clusters=excluded,
        selected_window=selected_window,
    )


def _deduplicate_sources(sources: Sequence[PlatformEvidenceRecord]) -> list[PlatformEvidenceRecord]:
    seen: set[tuple[ResearchPlatform, str]] = set()
    result: list[PlatformEvidenceRecord] = []
    for item in sources:
        identity = item.content_id or item.canonical_url or item.source_id
        key = (item.platform, identity)
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def _sources_in_window(
    sources: Sequence[PlatformEvidenceRecord],
    *,
    now: datetime,
    duration: timedelta,
) -> list[PlatformEvidenceRecord]:
    start = now - duration
    return [
        item
        for item in sources
        if item.published_at is not None and start <= item.published_at <= now
    ]


def _eligible_clusters(
    clusters: Sequence[HotspotCluster],
    *,
    metadata: Mapping[str, Mapping[str, Any]],
    now: datetime,
) -> tuple[list[HotspotCluster], list[HotspotCluster]]:
    maxima = _platform_maxima(clusters)
    eligible: list[HotspotCluster] = []
    excluded: list[HotspotCluster] = []
    for cluster in clusters:
        reason = _exclusion_reason(cluster, maxima=maxima, metadata=metadata, now=now)
        if reason is None:
            eligible.append(cluster)
        else:
            excluded.append(cluster.model_copy(update={"excluded_reason": reason}))
    return eligible, excluded


def _exclusion_reason(
    cluster: HotspotCluster,
    *,
    maxima: Mapping[ResearchPlatform, float],
    metadata: Mapping[str, Mapping[str, Any]],
    now: datetime,
) -> str | None:
    if cluster.fact_status is not FactVerificationStatus.VERIFIED:
        return f"fact_status:{cluster.fact_status.value}"
    if cluster.risk_flags:
        return "risk_flags:" + ",".join(cluster.risk_flags)
    if any(item.event_key != cluster.event_key for item in cluster.platform_evidence):
        return "event_key_mismatch"
    if any(evidence.conflicts for evidence in cluster.authority_evidence):
        return "conflicting_authority_evidence"
    if not any(evidence.verifies_fact for evidence in cluster.authority_evidence):
        return "missing_authority_verification"
    if not cluster.verification_summary or not cluster.verification_summary.strip():
        return "missing_verification_summary"

    platforms = {item.platform for item in cluster.platform_evidence}
    if len(platforms) >= 2:
        return None
    relative_heat = _cluster_relative_heat(cluster, maxima)
    if relative_heat < _SINGLE_PLATFORM_HIGH_HEAT_THRESHOLD:
        return f"single_platform_heat_below:{_SINGLE_PLATFORM_HIGH_HEAT_THRESHOLD:g}"
    return None


def _review_card(
    cluster: HotspotCluster,
    *,
    metadata: Mapping[str, Any],
    now: datetime,
    time_window: TimeWindow,
    platform_maxima: Mapping[ResearchPlatform, float],
) -> HotspotReviewCard:
    score = _score_cluster(cluster, metadata=metadata, now=now, platform_maxima=platform_maxima)
    speaking_angle = _text_or_none(metadata.get("speaking_angle")) or (
        "从事实出发，解释它与普通人生活的关系。"
    )
    audience_insight = _text_or_none(metadata.get("audience_insight"))
    return HotspotReviewCard(
        id=f"hotspot-{cluster.id}",
        cluster_id=cluster.id,
        title=cluster.title,
        fact_summary=cluster.verification_summary or "已核验事实，详见权威来源。",
        pillar=cluster.pillar,
        time_window=time_window,
        score=score,
        platform_evidence=cluster.platform_evidence,
        authority_evidence=cluster.authority_evidence,
        verification_summary=cluster.verification_summary or "已完成事实核验。",
        audience_insight=audience_insight,
        speaking_angle=speaking_angle,
        risk_flags=cluster.risk_flags,
        production_media_clearance=MediaClearanceStatus.AI_ILLUSTRATIVE,
        production_media_plan=(
            "使用 Seedance 2.0 生成不复刻原视频人物、构图或品牌视觉的 AI 示意画面，"
            "不直接使用平台热点视频。"
        ),
    )


def _score_cluster(
    cluster: HotspotCluster,
    *,
    metadata: Mapping[str, Any],
    now: datetime,
    platform_maxima: Mapping[ResearchPlatform, float],
) -> HotspotScoreBreakdown:
    evidence = cluster.platform_evidence
    relative_heat = sum(_relative_heat(item, platform_maxima) for item in evidence) / len(evidence)
    platform_count = len({item.platform for item in evidence})
    resonance = min(100.0, platform_count / len(_TARGET_PLATFORMS) * 100.0)
    latest = max(
        (item.published_at for item in evidence if item.published_at),
        default=cluster.last_seen_at,
    )
    age_hours = max(0.0, (now - latest).total_seconds() / 3600)
    recency = max(0.0, min(100.0, 100.0 * exp(-age_hours / 72.0)))
    comment_quality = sum(_comment_quality(item) for item in evidence) / len(evidence)
    audience_fit = _bounded_number(metadata.get("audience_fit", 70.0), default=70.0)
    source_completeness = sum(_source_completeness(item) for item in evidence) / len(evidence)
    return HotspotScoreBreakdown(
        platform_relative_heat=relative_heat,
        cross_platform_resonance=resonance,
        recency=recency,
        comment_quality=comment_quality,
        audience_fit=audience_fit,
        source_completeness=source_completeness,
    )


def _cluster_sort_key(
    cluster: HotspotCluster,
    *,
    now: datetime,
    platform_maxima: Mapping[ResearchPlatform, float],
) -> tuple[float, str]:
    score = _score_cluster(
        cluster,
        metadata={},
        now=now,
        platform_maxima=platform_maxima,
    ).total_score
    return score, cluster.id


def _platform_maxima(clusters: Sequence[HotspotCluster]) -> dict[ResearchPlatform, float]:
    maxima: dict[ResearchPlatform, float] = {}
    for cluster in clusters:
        for item in cluster.platform_evidence:
            maxima[item.platform] = max(maxima.get(item.platform, 0.0), _raw_heat(item))
    return maxima


def _cluster_relative_heat(
    cluster: HotspotCluster,
    maxima: Mapping[ResearchPlatform, float],
) -> float:
    values = [_relative_heat(item, maxima) for item in cluster.platform_evidence]
    return max(values, default=0.0)


def _relative_heat(
    item: PlatformEvidenceRecord,
    maxima: Mapping[ResearchPlatform, float],
) -> float:
    maximum = maxima.get(item.platform, 0.0)
    if maximum <= 0:
        return 0.0
    return max(0.0, min(100.0, _raw_heat(item) / maximum * 100.0))


def _raw_heat(item: PlatformEvidenceRecord) -> float:
    metrics = item.visible_metrics
    # Absolute counts are not compared between platforms; this value is used
    # only to normalize records within their own platform.
    return (
        log1p(metrics.views or 0) * 1.0
        + log1p(metrics.likes or 0) * 0.8
        + log1p(metrics.comments or 0) * 1.2
        + log1p(metrics.shares or 0) * 1.0
        + log1p(metrics.saves or 0) * 0.8
        + (metrics.platform_heat or 0.0) * 0.5
    )


def _comment_quality(item: PlatformEvidenceRecord) -> float:
    comments = item.visible_metrics.comments
    likes = item.visible_metrics.likes
    if comments is None or likes is None:
        return 25.0
    if likes == 0:
        return 0.0
    return max(0.0, min(100.0, comments / likes * 1000.0))


def _source_completeness(item: PlatformEvidenceRecord) -> float:
    checks = [
        item.content_id is not None,
        item.canonical_url is not None,
        item.published_at is not None,
        bool(item.title_or_caption.strip()),
        bool(item.raw_evidence_reference.strip()),
    ]
    visible = [
        visibility
        for visibility in item.metric_visibility.values()
        if visibility in {MetricVisibility.VISIBLE_EXACT, MetricVisibility.VISIBLE_APPROXIMATE}
    ]
    return (sum(checks) / len(checks) * 80.0) + min(20.0, len(visible) / 5.0 * 20.0)


def _safe_fact_status(
    requested: FactVerificationStatus,
    authority_evidence: Sequence[AuthorityEvidence],
) -> FactVerificationStatus:
    if requested is not FactVerificationStatus.VERIFIED:
        return requested
    if any(evidence.conflicts for evidence in authority_evidence):
        return FactVerificationStatus.CONFLICTING
    if not any(evidence.verifies_fact for evidence in authority_evidence):
        return FactVerificationStatus.PENDING
    return requested


def _authority_evidence(values: Any) -> list[AuthorityEvidence]:
    if values is None:
        return []
    return [
        value if isinstance(value, AuthorityEvidence) else AuthorityEvidence.model_validate(value)
        for value in values
    ]


def _enum_value(value: Any, enum_type: type[Any]) -> Any:
    if isinstance(value, enum_type):
        return value
    return enum_type(value)


def _text_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _bounded_number(value: Any, *, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = default
    return max(0.0, min(100.0, number))


def _merge_excluded(*groups: Sequence[HotspotCluster]) -> list[HotspotCluster]:
    seen: set[str] = set()
    merged: list[HotspotCluster] = []
    for group in groups:
        for cluster in group:
            if cluster.id not in seen:
                merged.append(cluster)
                seen.add(cluster.id)
    return merged
