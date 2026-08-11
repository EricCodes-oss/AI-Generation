"""Time-series analysis that never compares heat values across platforms."""

from collections.abc import Sequence

from avatar_pipeline.hotspot_models import (
    EventCluster,
    EventTrend,
    HotspotSnapshot,
    PlatformTrendLabel,
    TrendLabel,
    TrendObservation,
)


def _longest_consecutive_presence(presence: list[bool]) -> int:
    longest = current = 0
    for present in presence:
        current = current + 1 if present else 0
        longest = max(longest, current)
    return longest


def _platform_label(
    *, observation_count: int, rank_delta: int | None, heat_growth: float | None
) -> PlatformTrendLabel:
    if observation_count < 2:
        return PlatformTrendLabel.UNKNOWN
    movements = [value for value in (rank_delta, heat_growth) if value is not None]
    if (rank_delta is not None and rank_delta >= 5) or (
        heat_growth is not None and heat_growth >= 0.5
    ):
        return PlatformTrendLabel.SURGING
    if any(value > 0 for value in movements):
        return PlatformTrendLabel.RISING
    if any(value < 0 for value in movements):
        return PlatformTrendLabel.FALLING
    return PlatformTrendLabel.STABLE


def _event_label(
    *,
    observation_count: int,
    platform_labels: dict[str, PlatformTrendLabel],
    observation_count_by_platform: dict[str, int],
    new_platform_count: int,
) -> TrendLabel:
    if observation_count == 1:
        return TrendLabel.INITIAL_SCREEN
    points = {
        PlatformTrendLabel.SURGING: 2.0,
        PlatformTrendLabel.RISING: 1.0,
        PlatformTrendLabel.STABLE: 0.0,
        PlatformTrendLabel.FALLING: -1.0,
        PlatformTrendLabel.UNKNOWN: 0.0,
    }
    known = {
        platform: label
        for platform, label in platform_labels.items()
        if label is not PlatformTrendLabel.UNKNOWN
    }
    has_positive = (
        any(points[label] > 0 for label in known.values()) or new_platform_count > 0
    )
    has_negative = any(points[label] < 0 for label in known.values())
    if has_positive and has_negative:
        return TrendLabel.VOLATILE
    total_weight = sum(observation_count_by_platform[item] for item in known)
    weighted = (
        sum(
            points[label] * observation_count_by_platform[platform]
            for platform, label in known.items()
        )
        / total_weight
        if total_weight
        else 0.0
    )
    if new_platform_count > 0:
        weighted += min(0.5, 0.25 * new_platform_count)
    if weighted >= 1.5:
        return TrendLabel.SURGING
    if weighted > 0:
        return TrendLabel.RISING
    if weighted < 0:
        return TrendLabel.FALLING
    return TrendLabel.STABLE


def analyze_event_trend(
    cluster: EventCluster,
    snapshots: Sequence[HotspotSnapshot],
    *,
    related_subtopic_ids: Sequence[str] = (),
) -> EventTrend:
    member_ids = set(cluster.record_ids)
    ordered = sorted(snapshots, key=lambda item: item.captured_at)
    observations: list[TrendObservation] = []
    presence: list[bool] = []
    for item in ordered:
        members = [record for record in item.records if record.record_id in member_ids]
        presence.append(bool(members))
        if not members:
            continue
        best_by_platform = {}
        for record in members:
            previous = best_by_platform.get(record.platform)
            if previous is None or record.rank < previous.rank:
                best_by_platform[record.platform] = record
        observations.append(
            TrendObservation(
                snapshot_id=item.snapshot_id,
                captured_at=item.captured_at,
                platform_ranks={
                    platform: record.rank
                    for platform, record in sorted(best_by_platform.items())
                },
                platform_heat_values={
                    platform: record.heat_value
                    for platform, record in sorted(best_by_platform.items())
                    if record.heat_value is not None
                },
            )
        )
    if not observations:
        raise ValueError(f"event {cluster.event_id} is absent from all snapshots")

    first_seen: dict[str, tuple[int, float | None]] = {}
    last_seen: dict[str, tuple[int, float | None]] = {}
    observation_count_by_platform: dict[str, int] = {}
    for observation in observations:
        for platform, rank in observation.platform_ranks.items():
            heat = observation.platform_heat_values.get(platform)
            first_seen.setdefault(platform, (rank, heat))
            last_seen[platform] = (rank, heat)
            observation_count_by_platform[platform] = (
                observation_count_by_platform.get(platform, 0) + 1
            )

    rank_delta = {
        platform: first_seen[platform][0] - last_seen[platform][0]
        for platform in sorted(first_seen)
        if observation_count_by_platform[platform] >= 2
        and first_seen[platform][0] != last_seen[platform][0]
    }
    heat_growth = {}
    for platform in sorted(first_seen):
        first_heat, last_heat = first_seen[platform][1], last_seen[platform][1]
        if (
            observation_count_by_platform[platform] >= 2
            and first_heat is not None
            and first_heat > 0
            and last_heat is not None
        ):
            heat_growth[platform] = round((last_heat - first_heat) / first_heat, 4)

    platform_labels = {
        platform: _platform_label(
            observation_count=observation_count_by_platform[platform],
            rank_delta=rank_delta.get(platform),
            heat_growth=heat_growth.get(platform),
        )
        for platform in sorted(first_seen)
    }
    first_platforms = set(observations[0].platform_ranks)
    later_platforms = set().union(
        *(set(item.platform_ranks) for item in observations[1:])
    )
    new_platform_count = len(later_platforms - first_platforms)

    return EventTrend(
        event_id=cluster.event_id,
        observations=observations,
        label=_event_label(
            observation_count=len(observations),
            platform_labels=platform_labels,
            observation_count_by_platform=observation_count_by_platform,
            new_platform_count=new_platform_count,
        ),
        platform_trend_labels=platform_labels,
        consecutive_snapshot_count=max(1, _longest_consecutive_presence(presence)),
        new_platform_count=new_platform_count,
        related_subtopic_count=len(
            {item.strip() for item in related_subtopic_ids if item.strip()}
        ),
        rank_delta_by_platform=rank_delta,
        heat_growth_by_platform=heat_growth,
    )
