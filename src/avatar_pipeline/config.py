"""Application configuration loading and validation."""

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    """Base model that rejects unknown configuration keys."""

    model_config = ConfigDict(extra="forbid")


class VideoConfig(StrictModel):
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    min_duration_seconds: int = Field(ge=1)
    max_duration_seconds: int = Field(ge=1)
    target_audio_min_seconds: int = Field(ge=1)
    target_audio_max_seconds: int = Field(ge=1)
    avatar_ratio_min: float = Field(ge=0, le=1)
    avatar_ratio_max: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def validate_ranges(self) -> "VideoConfig":
        if self.min_duration_seconds > self.max_duration_seconds:
            raise ValueError("minimum duration must not exceed maximum duration")
        if self.target_audio_min_seconds > self.target_audio_max_seconds:
            raise ValueError("minimum target audio duration must not exceed maximum")
        if self.avatar_ratio_min > self.avatar_ratio_max:
            raise ValueError("minimum avatar ratio must not exceed maximum")
        return self


class ContentPillar(StrictModel):
    slug: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    monthly_count: int = Field(gt=0)


class ContentConfig(StrictModel):
    pillars: list[ContentPillar] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_pillars(self) -> "ContentConfig":
        slugs = [pillar.slug for pillar in self.pillars]
        if len(slugs) != len(set(slugs)):
            raise ValueError("content pillar slugs must be unique")
        return self


class ApprovalConfig(StrictModel):
    required: list[str] = Field(min_length=1)


class StorageConfig(StrictModel):
    workspace: Path
    contracts_directory: Path


class AppConfig(StrictModel):
    video: VideoConfig
    content: ContentConfig
    approvals: ApprovalConfig
    storage: StorageConfig


def load_config(path: Path) -> AppConfig:
    """Load and validate application configuration from a YAML file."""

    with path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    return AppConfig.model_validate(raw)
