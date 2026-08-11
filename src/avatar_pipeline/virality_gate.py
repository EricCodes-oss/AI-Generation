"""Non-negotiable eligibility gates applied before virality scoring."""

from collections.abc import Sequence

from avatar_pipeline.config import HotspotConfig
from avatar_pipeline.hotspot_models import (
    ContentNature,
    EventCluster,
    EventTrend,
    GateDecision,
    HotspotRecord,
    VerificationDecision,
)


def evaluate_virality_gate(
    cluster: EventCluster,
    trend: EventTrend,
    records: Sequence[HotspotRecord],
    verification: VerificationDecision,
    config: HotspotConfig,
) -> GateDecision:
    member_ids = set(cluster.record_ids)
    members = [item for item in records if item.record_id in member_ids]
    platforms = {
        item.platform
        for item in members
        if item.content_nature is ContentNature.NATURAL
    }
    best_rank_by_platform = {
        platform: min(item.rank for item in members if item.platform == platform)
        for platform in platforms
    }
    has_top_five = any(
        rank <= config.top_rank_single for rank in best_rank_by_platform.values()
    )
    top_ten_count = sum(
        rank <= config.top_rank_multi for rank in best_rank_by_platform.values()
    )
    checks = {
        "three_independent_platforms": len(platforms) >= config.min_platforms,
        "core_rank": (
            has_top_five or top_ten_count >= config.min_top_rank_multi_platforms
        ),
        "within_24_hours": verification.checks.get("within_24_hours", False),
        "two_consecutive_snapshots": (
            trend.consecutive_snapshot_count >= config.min_consecutive_snapshots
        ),
        "natural_heat": bool(members)
        and all(item.content_nature is ContentNature.NATURAL for item in members),
        "two_independent_reliable_sources": verification.checks.get(
            "two_independent_reliable_sources", False
        ),
        "production_visuals": verification.checks.get("production_visuals", False),
    }
    reasons = [name for name, passed in checks.items() if not passed]
    reasons.extend(reason for reason in verification.reasons if reason not in reasons)
    return GateDecision(
        event_id=cluster.event_id,
        passed=not reasons,
        checks=checks,
        reasons=reasons,
    )
