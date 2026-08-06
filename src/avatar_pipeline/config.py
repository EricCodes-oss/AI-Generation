"""Application configuration loading and validation."""

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class VideoConfig(StrictModel):
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    min_duration_seconds: int = Field(ge=1)
    max_duration_seconds: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_v1(self) -> "VideoConfig":
        if self.width != 1080 or self.height != 1920:
            raise ValueError("V1 video output must be 1080x1920")
        if self.min_duration_seconds > self.max_duration_seconds:
            raise ValueError("minimum duration must not exceed maximum duration")
        if self.min_duration_seconds < 45 or self.max_duration_seconds > 75:
            raise ValueError("V1 duration range must stay within 45-75 seconds")
        return self


class ContentPillar(StrictModel):
    slug: str = Field(min_length=1)
    display_name: str = Field(min_length=1)


class ContentConfig(StrictModel):
    pillars: list[ContentPillar] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_pillars(self) -> "ContentConfig":
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


class AppConfig(StrictModel):
    mode: Literal["managed", "manual"]
    topic_source: Literal["user_topic", "auto_hot"]
    avatar_source: Literal["user_provided", "saved_host", "agent_designed"]
    subtitle: Literal[False]
    video_structure: Literal["studio_anchor_plus_vertical_news_insert"]
    media_policy: Literal["reliable_original_first_ai_demo_fallback"]
    platforms: list[Literal["douyin", "wechat_channels", "xiaohongshu"]] = Field(min_length=1)
    video: VideoConfig
    content: ContentConfig
    approval_policy: ApprovalConfig
    storage: StorageConfig


def load_config(path: Path) -> AppConfig:
    with path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    return AppConfig.model_validate(raw)
