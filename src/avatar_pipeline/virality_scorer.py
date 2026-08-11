"""Versioned virality scoring derived only from saved evidence and editorial inputs."""

from collections.abc import Sequence

from avatar_pipeline.config import HotspotConfig
from avatar_pipeline.hotspot_models import (
    CandidateVerification,
    EditorialSignals,
    EventCluster,
    EventTrend,
    GateDecision,
    HotspotRecord,
    VerificationDecision,
    ViralityScore,
)


def _cross_platform_score(
    cluster: EventCluster,
    records: Sequence[HotspotRecord],
    config: HotspotConfig,
) -> float:
    member_ids = set(cluster.record_ids)
    members = [item for item in records if item.record_id in member_ids]
    best_ranks = {}
    for item in members:
        best_ranks[item.platform] = min(
            best_ranks.get(item.platform, item.rank), item.rank
        )
    platform_points = min(13.0, 7.0 + 2.0 * len(best_ranks))
    categories = {
        config.platform_categories.get(platform, f"unknown:{platform}")
        for platform in best_ranks
    }
    diversity_points = min(2.0, max(0.0, float(len(categories) - 1)))
    best_rank = min(best_ranks.values())
    rank_points = 6.0 if best_rank == 1 else 5.0 if best_rank <= 5 else 3.0
    top_ten_points = min(
        4.0,
        2.0 * max(0, sum(rank <= 10 for rank in best_ranks.values()) - 1),
    )
    return min(
        25.0,
        platform_points + diversity_points + rank_points + top_ten_points,
    )


def _trend_score(trend: EventTrend) -> float:
    persistence = min(6.0, 2.0 * trend.consecutive_snapshot_count)
    new_platforms = min(4.0, 2.0 * trend.new_platform_count)
    rank_improvement = min(5.0, max([0, *trend.rank_delta_by_platform.values()]))
    best_same_platform_growth = max([0.0, *trend.heat_growth_by_platform.values()])
    heat_growth = min(5.0, 5.0 * best_same_platform_growth)
    subtopic_diffusion = min(2.0, float(trend.related_subtopic_count))
    return min(
        20.0,
        persistence
        + new_platforms
        + rank_improvement
        + heat_growth
        + subtopic_diffusion,
    )


def _fact_safety_score(
    evidence: CandidateVerification, verification: VerificationDecision
) -> float:
    source_points = (
        3.0 if verification.independent_reliable_source_count >= 2 else 0.0
    )
    primary_points = 1.0 if evidence.primary_source_ids else 0.0
    resolved_points = 1.0 if not evidence.unresolved_claims else 0.0
    return min(5.0, source_points + primary_points + resolved_points)


def score_virality(
    cluster: EventCluster,
    trend: EventTrend,
    records: Sequence[HotspotRecord],
    evidence: CandidateVerification,
    verification: VerificationDecision,
    editorial: EditorialSignals,
    gate: GateDecision,
    config: HotspotConfig,
) -> ViralityScore:
    ids = {
        cluster.event_id,
        trend.event_id,
        evidence.event_id,
        verification.event_id,
        editorial.event_id,
        gate.event_id,
    }
    if len(ids) != 1:
        raise ValueError("all score inputs must describe the same event_id")
    if not gate.passed:
        raise ValueError("virality score requires all hard gates to pass")
    components = {
        "cross_platform_resonance": _cross_platform_score(cluster, records, config),
        "trend_velocity": _trend_score(trend),
        "conflict_suspense": editorial.conflict_suspense * 15,
        "public_interest": editorial.public_interest * 10,
        "curiosity_gap": editorial.curiosity_gap * 10,
        "visual_impact": editorial.visual_impact * 10,
        "explanatory_depth": editorial.explanatory_depth * 5,
        "fact_safety": _fact_safety_score(evidence, verification),
    }
    rounded = {name: round(value, 2) for name, value in components.items()}
    return ViralityScore(
        event_id=cluster.event_id,
        rule_version=config.rule_version,
        **rounded,
        total=round(sum(rounded.values()), 2),
    )
