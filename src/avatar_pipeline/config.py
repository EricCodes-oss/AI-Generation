"""Application configuration loading and validation."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal

import yaml
from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict, Field, model_validator

from avatar_pipeline.voice import DEFAULT_TTS_VOICE_ID


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def validate_non_blank_string(value: str) -> str:
    """Reject strings that contain no non-whitespace characters."""

    if not value.strip():
        raise ValueError("must not be blank")
    return value


NonBlankStr = Annotated[str, AfterValidator(validate_non_blank_string)]


def validate_strict_false(value: object) -> bool:
    """Accept only the literal boolean value False."""

    if type(value) is not bool or value is not False:
        raise ValueError("must be the boolean value false")
    return value


StrictFalse = Annotated[Literal[False], BeforeValidator(validate_strict_false)]


class VideoConfig(StrictModel):
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    min_duration_seconds: int = Field(ge=1)
    max_duration_seconds: int = Field(ge=1)
    target_audio_min_seconds: int = Field(default=40, ge=1)
    target_audio_max_seconds: int = Field(default=46, ge=1)
    avatar_ratio_min: float = Field(default=0.55, ge=0, le=1)
    avatar_ratio_max: float = Field(default=0.65, ge=0, le=1)

    @model_validator(mode="after")
    def validate_v1(self) -> VideoConfig:
        if self.width != 1080 or self.height != 1920:
            raise ValueError("V1 video output must be 1080x1920")
        if self.min_duration_seconds > self.max_duration_seconds:
            raise ValueError("minimum duration must not exceed maximum duration")
        if self.min_duration_seconds < 45 or self.max_duration_seconds > 75:
            raise ValueError("V1 duration range must stay within 45-75 seconds")
        if self.target_audio_min_seconds > self.target_audio_max_seconds:
            raise ValueError("minimum target audio duration must not exceed maximum")
        if self.avatar_ratio_min > self.avatar_ratio_max:
            raise ValueError("minimum avatar ratio must not exceed maximum")
        return self


class ContentPillar(StrictModel):
    slug: str = Field(min_length=1)
    display_name: str = Field(min_length=1)


class ContentConfig(StrictModel):
    pillars: list[ContentPillar] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_pillars(self) -> ContentConfig:
        slugs = [pillar.slug for pillar in self.pillars]
        if len(slugs) != len(set(slugs)):
            raise ValueError("content pillar slugs must be unique")
        return self


class ApprovalPolicy(StrictModel):
    topic_script: Literal["auto", "user_confirm"]
    avatar: Literal["auto", "confirm_if_new_or_changed"]
    final_video: Literal["final_only", "user_confirm"]


class ApprovalConfig(StrictModel):
    managed: ApprovalPolicy
    manual: ApprovalPolicy


class StorageConfig(StrictModel):
    workspace: Path
    contracts_directory: Path


class SourceRangeConfig(StrictModel):
    min_sources: int = Field(ge=0)
    max_sources: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_range(self) -> SourceRangeConfig:
        if self.min_sources > self.max_sources:
            raise ValueError("minimum source target must not exceed maximum")
        return self


class PlatformTargetsConfig(StrictModel):
    douyin: SourceRangeConfig
    wechat_channels: SourceRangeConfig
    xiaohongshu: SourceRangeConfig
    supplementary: SourceRangeConfig
    wechat_official_accounts: SourceRangeConfig


class TimeWindowSharesConfig(StrictModel):
    last_72_hours: float = Field(ge=0, le=1)
    last_7_days: float = Field(ge=0, le=1)
    last_30_days: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def validate_total(self) -> TimeWindowSharesConfig:
        total = self.last_72_hours + self.last_7_days + self.last_30_days
        if abs(total - 1.0) > 1e-9:
            raise ValueError("research time-window shares must sum to 1.0")
        return self


class ResearchQueryConfig(StrictModel):
    core_group_count: int = Field(gt=0)
    groups_per_pillar: int = Field(gt=0)
    expansion_cap: int = Field(ge=0)
    exact_query_cooldown_days: int = Field(gt=0)
    scene_cooldown_days: int = Field(gt=0)
    history_days: int = Field(gt=0)
    empty_result_threshold: int = Field(gt=0)
    empty_result_cooldown_days: int = Field(gt=0)


class CommentTargetsConfig(StrictModel):
    a_grade_sources_min: int = Field(gt=0)
    a_grade_sources_max: int = Field(gt=0)
    per_source_min: int = Field(gt=0)
    per_source_max: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_ranges(self) -> CommentTargetsConfig:
        if self.a_grade_sources_min > self.a_grade_sources_max:
            raise ValueError("minimum A-grade source target must not exceed maximum")
        if self.per_source_min > self.per_source_max:
            raise ValueError("minimum comment target must not exceed maximum")
        return self


class ResearchConfig(StrictModel):
    query: ResearchQueryConfig
    time_window_shares: TimeWindowSharesConfig
    platform_targets: PlatformTargetsConfig
    comments: CommentTargetsConfig
    excluded_topics: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_query_shape(self) -> ResearchConfig:
        if self.query.core_group_count != self.query.groups_per_pillar * 3:
            raise ValueError("core query count must equal groups per pillar times 3")
        if any(not topic.strip() for topic in self.excluded_topics):
            raise ValueError("excluded research topics must not be blank")
        return self


class TTSConfig(StrictModel):
    voice_id: NonBlankStr
    emotion: Literal["neutral"]
    speaking_rate: float = Field(gt=0, le=2)

    @model_validator(mode="after")
    def validate_selected_voice(self) -> TTSConfig:
        if self.voice_id != DEFAULT_TTS_VOICE_ID:
            raise ValueError("tts must use the selected presenter voice")
        return self


class HostVisualConfig(StrictModel):
    visual_style: NonBlankStr
    age_range: NonBlankStr
    outfit: NonBlankStr
    aspect_ratio: Literal["9:16"]
    shot: Literal["waist_up_seated"]
    background: NonBlankStr
    subtitle_default: StrictFalse


class HostIdentityConfig(StrictModel):
    id: Literal["fixed-seated-anchor"]
    display_name: Literal["林知遥"]
    reference_image: Path
    voice_id: NonBlankStr
    layout: Literal["seated_studio_anchor"]
    mouth_unobstructed: Literal[True]

    @model_validator(mode="after")
    def validate_selected_voice(self) -> HostIdentityConfig:
        if self.voice_id != DEFAULT_TTS_VOICE_ID:
            raise ValueError("host identity must use the selected presenter voice")
        return self


class AppConfig(StrictModel):
    mode: Literal["managed", "manual"]
    avatar_layout: Literal["seated_studio_anchor"]
    topic_source: Literal["user_topic", "auto_hot"]
    avatar_source: Literal["user_provided", "saved_host", "agent_designed"]
    tts: TTSConfig
    host_visual: HostVisualConfig
    host_identity: HostIdentityConfig
    subtitle: StrictFalse
    video_structure: Literal["studio_anchor_plus_vertical_news_insert"]
    media_policy: Literal["reliable_original_first_ai_demo_fallback"]
    platforms: list[Literal["douyin", "wechat_channels", "xiaohongshu"]] = Field(min_length=1)
    video: VideoConfig
    content: ContentConfig
    approval_policy: ApprovalConfig
    storage: StorageConfig
    research: ResearchConfig


def load_config(path: Path | str) -> AppConfig:
    """Load and validate application configuration from a YAML file."""

    with Path(path).open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    return AppConfig.model_validate(raw)
