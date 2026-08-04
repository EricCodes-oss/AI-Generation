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
