from copy import deepcopy
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from avatar_pipeline.news_quality_config import NewsVideoQualityConfig, load_news_quality_config

CONFIG_PATH = Path("configs/news-video-quality-v5.yaml")


def test_canonical_v5_quality_config_is_locked():
    config = load_news_quality_config(CONFIG_PATH)
    assert config.profile.id == "v5_vertical_anchor_news"
    assert config.profile.min_duration_seconds == 45
    assert config.profile.max_duration_seconds == 90
    assert (config.output.width, config.output.height, config.output.fps) == (1080, 1920, 25)
    assert config.host.sha256 == (
        "939324593eb718cd2a39be4c171f74178a6a48442f7e0d61afe8a875011e8a47"
    )
    assert config.voice.voice_id == "cobra_design_20250717_162347_664524"
    clean_master = config.clean_master.model_dump()
    assert clean_master.pop("footage_audio") == "director_selected"
    assert not any(clean_master.values())
    assert config.broll.selection_mode == "director_dynamic"
    assert config.broll.count_fixed is False
    assert config.broll.prefer_coherent_blocks is True
    assert config.broll.avoid_frequent_short_cuts is True
    assert config.broll.max_clip_seconds == 12.0
    assert config.broll.target_ratio_max == 0.80


def test_quality_config_rejects_non_v5_duration_output_and_clean_master():
    raw = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    cases = []
    changed = deepcopy(raw)
    changed["profile"]["min_duration_seconds"] = 44
    cases.append(changed)
    changed = deepcopy(raw)
    changed["profile"]["max_duration_seconds"] = 91
    cases.append(changed)
    changed = deepcopy(raw)
    changed["output"]["fps"] = 30
    cases.append(changed)
    changed = deepcopy(raw)
    changed["clean_master"]["subtitles"] = True
    cases.append(changed)
    for payload in cases:
        with pytest.raises(ValidationError):
            NewsVideoQualityConfig.model_validate(payload)


def test_quality_config_rejects_blank_locked_identity():
    raw = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    for section, field in (("host", "sha256"), ("voice", "voice_id")):
        changed = deepcopy(raw)
        changed[section][field] = ""
        with pytest.raises(ValidationError):
            NewsVideoQualityConfig.model_validate(changed)


def test_v5_profile_locks_three_part_structure_and_uniform_inserts():
    config = load_news_quality_config(Path("configs/news-video-quality-v5.yaml"))

    assert config.structure.mode == "three_part"
    assert config.structure.max_presenter_insert_alternations == 1
    assert config.broll.insert_format == "landscape_16x9_on_portrait_canvas"
    assert config.broll.require_uniform_insert_format is True
    assert config.broll.min_source_height >= 1080
    assert config.broll.background_fill == "black"
    assert config.broll.clip_duration_policy == "follow_reference_pacing"
