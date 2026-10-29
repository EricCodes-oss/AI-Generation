"""Strict configuration for the approved V5 manual news-video profile."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProfileConfig(StrictModel):
    id: Literal["v5_vertical_anchor_news"]
    version: str = Field(min_length=1)
    production_mode: Literal["manual_directed"]
    min_duration_seconds: Literal[45]
    max_duration_seconds: Literal[90]


class OutputConfig(StrictModel):
    width: Literal[1080]
    height: Literal[1920]
    fps: Literal[25]
    video_codec: Literal["h264"]
    audio_codec: Literal["aac"]
    audio_sample_rate: Literal[48000]
    audio_channels: Literal[1]


class CleanMasterConfig(StrictModel):
    subtitles: Literal[False]
    title_overlay: Literal[False]
    source_overlay: Literal[False]
    logo: Literal[False]
    background_music: Literal[False]
    footage_audio: Literal["director_selected"]


class HostLockConfig(StrictModel):
    id: Literal["host-c2-pro-candidate-2-final"]
    display_name: str = Field(min_length=1)
    reference_image: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    identity_lock: Literal["strict"]


class VoiceLockConfig(StrictModel):
    display_name: str = Field(min_length=1)
    voice_id: str = Field(min_length=1)
    identity_lock: Literal["strict"]


class StructureConfig(StrictModel):
    """Three-part programme: presenter opening, one insert body, presenter closing."""

    mode: Literal["three_part"] = "three_part"
    opening_seconds_min: float = Field(default=5, gt=0)
    opening_seconds_max: float = Field(default=15, gt=0)
    closing_seconds_min: float = Field(default=8, gt=0)
    closing_seconds_max: float = Field(default=20, gt=0)
    max_presenter_insert_alternations: Literal[1] = 1

    @model_validator(mode="after")
    def validate_ranges(self) -> StructureConfig:
        if self.opening_seconds_min > self.opening_seconds_max:
            raise ValueError("Opening duration range must be ordered")
        if self.closing_seconds_min > self.closing_seconds_max:
            raise ValueError("Closing duration range must be ordered")
        return self


class BrollConfig(StrictModel):
    selection_mode: Literal["director_dynamic"]
    # 插播规格统一硬门：同片插播比例与画布尺寸一致，源素材不低于 1080p。
    insert_format: Literal["landscape_16x9_on_portrait_canvas"] = "landscape_16x9_on_portrait_canvas"
    require_uniform_insert_format: Literal[True] = True
    require_uniform_display_size: Literal[True] = True
    min_source_height: int = Field(default=1080, ge=1080)
    allow_below_1080p_only_when_justified: Literal[True] = True
    prefer_source_fps: list[int] = Field(default_factory=lambda: [25, 50])
    background_fill: Literal["black"] = "black"
    # 有参考视频时镜头时长跟随参考节奏，下方数值只作无参考时的指引。
    clip_duration_policy: Literal["follow_reference_pacing", "guidance"] = "guidance"
    # Regional and identity hard gates are part of the V5 YAML profile.  Keep
    # defaults for legacy test fixtures and older local profiles.
    china_context_required: Literal[True] = True
    require_chinese_people_when_people_visible: Literal[True] = True
    prohibit_foreign_people: Literal[True] = True
    prohibit_unverified_people_identity: Literal[True] = True
    prohibit_unverified_overseas_context: Literal[True] = True
    identity_review: Literal["frame_by_frame"] = "frame_by_frame"
    count_fixed: Literal[False]
    guidance_min_count: int = Field(ge=1)
    guidance_max_count: int = Field(ge=1)
    min_clip_seconds: float = Field(gt=0)
    preferred_clip_seconds: float = Field(gt=0)
    max_clip_seconds: float = Field(gt=0)
    target_ratio_min: float = Field(gt=0, lt=1)
    target_ratio_max: float = Field(gt=0, lt=1)
    prefer_coherent_blocks: Literal[True]
    avoid_frequent_short_cuts: Literal[True]
    prohibit_reverse: Literal[True]
    prohibit_loop: Literal[True]
    prohibit_ping_pong: Literal[True]
    require_semantic_mapping: Literal[True]

    @model_validator(mode="after")
    def validate_ranges(self) -> BrollConfig:
        if self.guidance_min_count > self.guidance_max_count:
            raise ValueError("B-roll guidance counts must be ordered")
        if not self.min_clip_seconds <= self.preferred_clip_seconds <= self.max_clip_seconds:
            raise ValueError("B-roll clip durations must be ordered")
        if self.target_ratio_min > self.target_ratio_max:
            raise ValueError("B-roll target ratios must be ordered")
        return self


class EndingConfig(StrictModel):
    min_anchor_ratio: float = Field(gt=0, lt=1)
    preferred_anchor_seconds: float = Field(gt=0)
    require_complete_sentence: Literal[True]


class QualityConfig(StrictModel):
    prohibit_black_frames: Literal[True]
    max_unexpected_silence_seconds: float = Field(gt=0)
    require_decode_clean: Literal[True]
    require_audio_master_match: Literal[True]
    audio_correlation_min: float = Field(gt=0, le=1)
    require_director_review: Literal[True]


class NewsVideoQualityConfig(StrictModel):
    profile: ProfileConfig
    output: OutputConfig
    clean_master: CleanMasterConfig
    host: HostLockConfig
    voice: VoiceLockConfig
    structure: StructureConfig = Field(default_factory=StructureConfig)
    broll: BrollConfig
    ending: EndingConfig
    quality: QualityConfig


def load_news_quality_config(path: Path | str) -> NewsVideoQualityConfig:
    """Load a V5 quality profile from YAML and reject unknown or unsafe values."""

    with Path(path).open("r", encoding="utf-8") as handle:
        return NewsVideoQualityConfig.model_validate(yaml.safe_load(handle))
