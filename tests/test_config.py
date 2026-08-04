from pathlib import Path

from avatar_pipeline.config import load_config


def test_default_config_locks_v1_video_and_content_constraints():
    config = load_config(Path("configs/default.yaml"))

    assert config.video.width == 1080
    assert config.video.height == 1920
    assert config.video.min_duration_seconds == 35
    assert config.video.max_duration_seconds == 50
    assert config.video.avatar_ratio_min == 0.55
    assert config.video.avatar_ratio_max == 0.65
    assert [pillar.slug for pillar in config.content.pillars] == [
        "career_pressure",
        "parent_child_communication",
        "self_growth",
    ]
    assert sum(pillar.monthly_count for pillar in config.content.pillars) == 30
    assert config.approvals.required == ["topic", "script", "video"]


def test_default_config_locks_research_sampling_and_cooldown_constraints():
    config = load_config(Path("configs/default.yaml"))

    assert config.research.query.core_group_count == 9
    assert config.research.query.groups_per_pillar == 3
    assert config.research.query.expansion_cap == 3
    assert config.research.query.exact_query_cooldown_days == 7
    assert config.research.query.scene_cooldown_days == 3
    assert config.research.query.history_days == 30
    assert config.research.query.empty_result_threshold == 2
    assert config.research.query.empty_result_cooldown_days == 14
    assert config.research.time_window_shares.last_72_hours == 0.5
    assert config.research.time_window_shares.last_7_days == 0.35
    assert config.research.time_window_shares.last_30_days == 0.15
    assert config.research.platform_targets.douyin.min_sources == 8
    assert config.research.platform_targets.douyin.max_sources == 10
    assert config.research.platform_targets.wechat_channels.min_sources == 6
    assert config.research.platform_targets.xiaohongshu.max_sources == 10
    assert config.research.comments.a_grade_sources_min == 5
    assert config.research.comments.a_grade_sources_max == 8
    assert config.research.comments.per_source_min == 20
    assert config.research.comments.per_source_max == 40
    assert "父母养老与照护压力" in config.research.excluded_topics
