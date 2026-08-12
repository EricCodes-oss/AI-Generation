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
    footage_audio: Literal[False]


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


class BrollConfig(StrictModel):
    min_clip_seconds: float = Field(gt=0)
    preferred_clip_seconds: float = Field(gt=0)
    max_clip_seconds: float = Field(gt=0)
    target_ratio_min: float = Field(gt=0, lt=1)
    target_ratio_max: float = Field(gt=0, lt=1)
    prohibit_reverse: Literal[True]
    prohibit_loop: Literal[True]
    prohibit_ping_pong: Literal[True]
    require_semantic_mapping: Literal[True]

    @model_validator(mode="after")
    def validate_ranges(self) -> BrollConfig:
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
    broll: BrollConfig
    ending: EndingConfig
    quality: QualityConfig


def load_news_quality_config(path: Path | str) -> NewsVideoQualityConfig:
    """Load a V5 quality profile from YAML and reject unknown or unsafe values."""

    with Path(path).open("r", encoding="utf-8") as handle:
        return NewsVideoQualityConfig.model_validate(yaml.safe_load(handle))
