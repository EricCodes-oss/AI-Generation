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


def test_default_config_keeps_viral_collection_rules_as_compatible_funnel_one():
    config = load_config(Path("configs/default.yaml"))
    assert config.hotspot.rule_version == "viral-v1.1"
    assert config.hotspot.core_platforms == [
        "weibo",
        "douyin",
        "xiaohongshu",
        "baidu",
        "toutiao",
        "kuaishou",
        "zhihu",
        "bilibili",
        "wechat",
    ]
    assert config.hotspot.required_short_video_platforms == ["douyin", "xiaohongshu"]
    assert config.hotspot.platform_aliases["小红书"] == "xiaohongshu"
    assert config.hotspot.platform_categories["xiaohongshu"] == "short_video"
    assert config.hotspot.platform_categories["weibo"] == "social"
    assert config.hotspot.platform_categories["baidu"] == "search"
    assert config.hotspot.event_aliases["台风白海豚"] == [
        "白海豚",
        "台风“白海豚”",
        "台风「白海豚」",
    ]
    assert config.hotspot.snapshot_interval_minutes == 10
    assert config.hotspot.snapshot_count == 3
    assert config.hotspot.min_platforms == 3
    assert config.hotspot.min_consecutive_snapshots == 2
    assert config.hotspot.display_score_min == 75
    assert sum(config.hotspot.score_weights.model_dump().values()) == 100


def test_default_config_requires_dynamic_user_gated_hotspot_pool():
    config = load_config(Path("configs/default.yaml"))
    selection = config.hotspot_selection
    assert selection.target_min_candidates == 3
    assert selection.max_candidates == 8
    assert selection.allow_fewer_than_target is True
    assert selection.pad_weak_candidates is False
    assert selection.require_user_selection is True
    assert "education" in selection.categories
    assert "influencer" in selection.categories
    assert "ordinary_people" in selection.categories
    media = {item.name: item for item in selection.preferred_authoritative_media}
    assert media["新华网"].roles == ["fact_source", "hotspot_signal", "footage_candidate"]
    assert media["人民日报"].platform == "bilibili"
    assert media["人民日报"].account_name == "人民日报"
    assert media["中国青年报"].account_name == "中国青年报"


def test_default_config_locks_editorial_opportunity_v2_weights_and_sources():
    config = load_config(Path("configs/default.yaml"))
    editorial = config.editorial_opportunity
    assert editorial.rule_version == "editorial-opportunity-v2.0"
    assert editorial.score_weights.model_dump() == {
        "real_heat": 30,
        "content_attractiveness": 35,
        "fact_reliability": 20,
        "video_potential": 15,
    }
    assert sum(editorial.score_weights.model_dump().values()) == 100
    assert editorial.s_score_min == 85
    assert editorial.a_score_min == 78
    assert editorial.no_s_tier_message == "暂无S级选题"
    assert set(editorial.source_signal_classes) == {
        "domestic_boards",
        "authoritative_media",
        "search_demand",
        "social_discussion",
        "video_propagation",
        "vertical_communities",
    }


def test_legacy_v1_hotspot_and_selection_config_remain_parseable():
    config = load_config(Path("configs/default.yaml"))
    payload = config.model_dump(mode="python")
    payload.pop("editorial_opportunity")
    payload["hotspot_selection"] = {
        "min_candidates": 8,
        "max_candidates": 12,
        "min_categories": 5,
        "require_user_selection": True,
        "categories": config.hotspot_selection.categories,
        "preferred_authoritative_media": [
            item.model_dump(mode="python")
            for item in config.hotspot_selection.preferred_authoritative_media
        ],
    }
    legacy = type(config).model_validate(payload)
    assert legacy.editorial_opportunity is None
    assert legacy.hotspot_selection.max_candidates == 12


def test_default_config_locks_ordinary_life_moment_hard_gate():
    selection = load_config(Path("configs/default.yaml")).hotspot_selection
    assert "ordinary_life_moment" in selection.categories
    gate = selection.ordinary_life_moment_gate
    assert gate.enabled is True
    assert gate.reject_professional_influencers is True
    assert gate.require_personal_daily_recorder is True
    assert gate.require_ordinary_people_as_primary_subjects is True
    assert gate.reject_creator_initiated_events is True
    assert gate.require_event_preexisted_filming is True
    assert gate.require_daily_life_context is True
    assert gate.require_human_warmth_evidence is True
    assert gate.max_staging_risk == 0.35
    assert gate.require_original_recorder is True
    assert gate.require_continuous_scene is True
