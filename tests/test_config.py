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


def test_default_config_declares_seated_anchor_visual_spec():
    config = load_config(Path("configs/default.yaml"))

    assert config.avatar_layout == "seated_studio_anchor"
    assert config.host_visual.model_dump() == {
        "visual_style": "mature_professional_news_anchor",
        "age_range": "30-36",
        "outfit": "deep_navy_blazer_ivory_blouse",
        "aspect_ratio": "9:16",
        "shot": "waist_up_seated",
        "background": "fictional_quiet_news_studio",
        "subtitle_default": False,
    }


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("visual_style", ""),
        ("age_range", ""),
        ("outfit", ""),
        ("background", ""),
    ],
)
def test_config_rejects_empty_host_visual_fields(field, value):
    config = load_config(Path("configs/default.yaml")).model_dump()
    config["host_visual"][field] = value

    with pytest.raises(ValidationError):
        type(load_config(Path("configs/default.yaml"))).model_validate(config)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("avatar_layout", "standing_studio_anchor"),
        ("host_visual.aspect_ratio", "16:9"),
        ("host_visual.shot", "head_and_shoulders"),
        ("host_visual.subtitle_default", True),
    ],
)
def test_config_rejects_non_v1_host_visual_values(field, value):
    config = load_config(Path("configs/default.yaml")).model_dump()
    target = config
    field_parts = field.split(".")
    for part in field_parts[:-1]:
        target = target[part]
    target[field_parts[-1]] = value

    with pytest.raises(ValidationError):
        type(load_config(Path("configs/default.yaml"))).model_validate(config)


@pytest.mark.parametrize("field", ["visual_style", "age_range", "outfit", "background"])
def test_config_rejects_whitespace_only_host_visual_fields(field):
    config = load_config(Path("configs/default.yaml")).model_dump()
    config["host_visual"][field] = " \t\n "

    with pytest.raises(ValidationError):
        type(load_config(Path("configs/default.yaml"))).model_validate(config)


@pytest.mark.parametrize("field", ["subtitle", "host_visual.subtitle_default"])
@pytest.mark.parametrize("value", [True, 0, 1, "false"])
def test_config_rejects_non_boolean_false_subtitle_values(field, value):
    config = load_config(Path("configs/default.yaml")).model_dump()
    target = config
    field_parts = field.split(".")
    for part in field_parts[:-1]:
        target = target[part]
    target[field_parts[-1]] = value

    with pytest.raises(ValidationError):
        type(load_config(Path("configs/default.yaml"))).model_validate(config)


def test_default_config_uses_selected_presenter_voice():
    config = load_config(Path("configs/default.yaml"))

    assert config.tts.voice_id == "宣传女生Pro:clone_20260806_114837_980375"


def test_config_rejects_other_presenter_voice():
    config = load_config(Path("configs/default.yaml")).model_dump()
    config["tts"]["voice_id"] = "another-voice"

    with pytest.raises(ValidationError, match="selected presenter voice"):
        type(load_config(Path("configs/default.yaml"))).model_validate(config)
