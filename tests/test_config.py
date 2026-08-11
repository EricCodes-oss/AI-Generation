from pathlib import Path

import pytest
from pydantic import ValidationError

from avatar_pipeline.config import load_config


def test_default_config_locks_news_anchor_v1():
    config = load_config(Path("configs/default.yaml"))
    assert config.mode == "manual"
    assert config.topic_source == "auto_hot"
    assert config.avatar_source == "saved_host"
    assert config.video.width == 1080
    assert config.video.height == 1920
    assert (config.video.min_duration_seconds, config.video.max_duration_seconds) == (45, 75)
    assert config.subtitle is False
    assert config.video_structure == "studio_anchor_plus_vertical_news_insert"
    assert config.media_policy == "reliable_original_first_ai_demo_fallback"
    assert config.platforms == ["douyin", "wechat_channels", "xiaohongshu"]
    assert config.approval_policy.manual.topic_script == "user_confirm"


def test_config_rejects_subtitles_or_unknown_video_structure():
    config = {
        "mode": "manual",
        "topic_source": "auto_hot",
        "avatar_source": "saved_host",
        "subtitle": True,
        "video_structure": "talking_head_only",
        "media_policy": "reliable_original_first_ai_demo_fallback",
        "platforms": ["douyin"],
        "video": {
            "width": 1080,
            "height": 1920,
            "min_duration_seconds": 45,
            "max_duration_seconds": 75,
        },
        "content": {"pillars": [{"slug": "workplace_life", "display_name": "职场生活"}]},
        "approval_policy": {
            "managed": {"topic_script": "auto", "avatar": "auto", "final_video": "final_only"},
            "manual": {
                "topic_script": "user_confirm",
                "avatar": "confirm_if_new_or_changed",
                "final_video": "user_confirm",
            },
        },
        "storage": {"workspace": "workspace", "contracts_directory": "skills/contracts"},
    }
    with pytest.raises(ValidationError):
        type(load_config(Path("configs/default.yaml"))).model_validate(config)


def test_default_config_locks_confirmed_hotspot_rules():
    config = load_config(Path("configs/default.yaml"))
    assert config.hotspot.rule_version == "viral-v1.0"
    assert config.hotspot.core_platforms == [
        "weibo", "douyin", "baidu", "toutiao",
        "kuaishou", "zhihu", "bilibili", "wechat",
    ]
    assert config.hotspot.platform_categories["weibo"] == "social"
    assert config.hotspot.platform_categories["baidu"] == "search"
    assert config.hotspot.snapshot_interval_minutes == 10
    assert config.hotspot.snapshot_count == 3
    assert config.hotspot.min_platforms == 3
    assert config.hotspot.min_consecutive_snapshots == 2
    assert config.hotspot.display_score_min == 75
    assert sum(config.hotspot.score_weights.model_dump().values()) == 100
