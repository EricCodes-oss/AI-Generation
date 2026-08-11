from avatar_pipeline.hotspot_models import (
    CollectionStatus,
    HotspotFailure,
    PlatformTrendLabel,
    TrendLabel,
)
from avatar_pipeline.trend_analyzer import analyze_event_trend
from tests.hotspot_factories import cluster, record, snapshot


def test_one_observation_is_initial_screen_and_platform_unknown():
    item = record("w0", "weibo", 5, "白海豚路径变化", heat_value=100)
    result = analyze_event_trend(
        cluster([item]),
        [snapshot("t0", "2026-08-10T19:40:00+08:00", records=[item])],
    )
    assert result.label is TrendLabel.INITIAL_SCREEN
    assert result.platform_trend_labels == {
        "weibo": PlatformTrendLabel.UNKNOWN,
    }
    assert result.consecutive_snapshot_count == 1
    assert result.rank_delta_by_platform == {}
    assert result.heat_growth_by_platform == {}


def test_three_snapshots_measure_only_within_platform_changes_and_subtopics():
    t0_records = [
        record("w0", "weibo", 5, "白海豚路径变化", heat_value=100),
        record("b0", "baidu", 9, "白海豚路径变化", heat_value=1_000),
    ]
    t1_records = [
        record("w1", "weibo", 3, "白海豚路径变化", heat_value=150),
        record("b1", "baidu", 7, "白海豚路径变化", heat_value=900),
        record("z1", "zhihu", 10, "白海豚路径变化", heat_value=20_000),
    ]
    t2_records = [
        record("w2", "weibo", 1, "白海豚路径变化", heat_value=200),
        record("b2", "baidu", 8, "白海豚路径变化", heat_value=1_100),
        record("z2", "zhihu", 4, "白海豚路径变化", heat_value=25_000),
    ]
    all_records = t0_records + t1_records + t2_records
    result = analyze_event_trend(
        cluster(all_records),
        [
            snapshot("t0", "2026-08-10T19:40:00+08:00", records=t0_records),
            snapshot("t1", "2026-08-10T19:50:00+08:00", records=t1_records),
            snapshot("t2", "2026-08-10T20:00:00+08:00", records=t2_records),
        ],
        related_subtopic_ids=["路径影响", "停航影响", "路径影响"],
    )
    assert result.consecutive_snapshot_count == 3
    assert result.new_platform_count == 1
    assert result.related_subtopic_count == 2
    assert result.rank_delta_by_platform == {"baidu": 1, "weibo": 4, "zhihu": 6}
    assert result.heat_growth_by_platform == {"baidu": 0.1, "weibo": 1.0, "zhihu": 0.25}
    assert result.platform_trend_labels == {
        "baidu": PlatformTrendLabel.RISING,
        "weibo": PlatformTrendLabel.SURGING,
        "zhihu": PlatformTrendLabel.SURGING,
    }
    assert result.label is TrendLabel.SURGING


def test_failed_platform_is_omitted_instead_of_becoming_zero_heat():
    first = record("w0", "weibo", 2, "事件", heat_value=100)
    second = record("w1", "weibo", 2, "事件", heat_value=100)
    failure = HotspotFailure(
        platform="baidu",
        captured_at=first.captured_at,
        reason="login required",
        raw_snapshot_path="tmp/baidu.json",
        status=CollectionStatus.RESTRICTED,
    )
    result = analyze_event_trend(
        cluster([first, second]),
        [
            snapshot("t0", "2026-08-10T19:40:00+08:00", records=[first]),
            snapshot(
                "t1", "2026-08-10T19:50:00+08:00", records=[second], failures=[failure]
            ),
        ],
    )
    assert "baidu" not in result.platform_trend_labels
    assert "baidu" not in result.rank_delta_by_platform
    assert "baidu" not in result.heat_growth_by_platform
    assert result.platform_trend_labels["weibo"] is PlatformTrendLabel.STABLE
    assert result.label is TrendLabel.STABLE


def test_mixed_platform_directions_are_volatile():
    t0_records = [
        record("w0", "weibo", 8, "事件", heat_value=100),
        record("b0", "baidu", 1, "事件", heat_value=200),
    ]
    t1_records = [
        record("w1", "weibo", 2, "事件", heat_value=180),
        record("b1", "baidu", 7, "事件", heat_value=100),
    ]
    result = analyze_event_trend(
        cluster(t0_records + t1_records),
        [
            snapshot("t0", "2026-08-10T19:40:00+08:00", records=t0_records),
            snapshot("t1", "2026-08-10T19:50:00+08:00", records=t1_records),
        ],
    )
    assert result.platform_trend_labels == {
        "baidu": PlatformTrendLabel.FALLING,
        "weibo": PlatformTrendLabel.SURGING,
    }
    assert result.label is TrendLabel.VOLATILE


def test_two_snapshots_can_report_a_falling_event():
    first = record("w0", "weibo", 1, "事件", heat_value=200)
    second = record("w1", "weibo", 5, "事件", heat_value=100)
    result = analyze_event_trend(
        cluster([first, second]),
        [
            snapshot("t0", "2026-08-10T19:40:00+08:00", records=[first]),
            snapshot("t1", "2026-08-10T19:50:00+08:00", records=[second]),
        ],
    )
    assert result.rank_delta_by_platform == {"weibo": -4}
    assert result.heat_growth_by_platform == {"weibo": -0.5}
    assert result.platform_trend_labels["weibo"] is PlatformTrendLabel.FALLING
    assert result.label is TrendLabel.FALLING
