"""Validated interface contracts for external news-production Skills."""

from enum import StrEnum
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class SkillKind(StrEnum):
    OPINIONS_CRAWLER = "opinions_crawler"
    NEWS_SCRIPT_WRITER = "news_script_writer"
    NEWS_MEDIA_PLANNER = "news_media_planner"
    TTS = "tts"
    HOST_IMAGE = "host_image"
    AVATAR = "avatar"
    FOOTAGE_CLIPPER = "footage_clipper"
    SEEDANCE = "seedance"
    COMPOSITOR = "compositor"
    QUALITY_CONTROL = "quality_control"


class SkillManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: SkillKind
    contract_version: Literal["1.0"]
    display_name: str = Field(min_length=1)
    provider: str | None = Field(default=None, min_length=1)
    name: str | None = Field(default=None, min_length=1)
    required_inputs: list[str] | dict[str, str] = Field(min_length=1)
    optional_inputs: list[str] = Field(default_factory=list)
    required_outputs: list[str] = Field(min_length=1)
    supported_aspect_ratios: list[str] = Field(min_length=1)
    max_duration_seconds: int = Field(gt=0)
    real_generation_enabled: Literal[False]
    negative_prompt: str | None = Field(default=None, min_length=1)
    primary_mode: str | None = None
    fallback_mode: str | None = None
    recommended_audio_format: str | None = None
    timestamps_supported: bool | None = None
    safety_constraints: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_kind_specific_fields(self) -> "SkillManifest":
        if isinstance(self.required_inputs, dict):
            if any(not key or not value for key, value in self.required_inputs.items()):
                raise ValueError("required input names and constraints must be non-empty")
            self._validate_content_first_inputs()
        if self.kind is SkillKind.AVATAR:
            if not self.primary_mode or not self.fallback_mode:
                raise ValueError("avatar contract requires primary_mode and fallback_mode")
        elif self.primary_mode is not None or self.fallback_mode is not None:
            raise ValueError("generation modes are only valid for the avatar contract")
        if self.kind is SkillKind.TTS:
            if self.recommended_audio_format != "wav" or self.timestamps_supported is not True:
                raise ValueError("tts contract must recommend wav and support timestamps")
        elif self.recommended_audio_format is not None or self.timestamps_supported is not None:
            raise ValueError("audio fields are only valid for the tts contract")
        return self

    def _validate_content_first_inputs(self) -> None:
        inputs = self.required_inputs
        if self.kind is SkillKind.HOST_IMAGE:
            expected = {
                "prompt": "string",
                "negative_prompt": "string",
                "layout": "seated_studio_anchor",
                "aspect_ratio": "9:16",
                "shot": "waist_up_seated",
            }
            if inputs != expected:
                raise ValueError("host image contract must require the seated content-first inputs")
            if not self.negative_prompt:
                raise ValueError("host image contract requires negative_prompt")
            required_terms = {
                "police uniform",
                "police badge",
                "military uniform",
                "government emblem",
                "real media logo",
                "seductive pose",
                "revealing clothing",
                "readable text",
                "extra people",
            }
            terms = {term.strip().lower() for term in self.negative_prompt.split(",")}
            if not required_terms <= terms:
                raise ValueError("host image negative_prompt is missing required safety terms")
        elif self.kind is SkillKind.AVATAR:
            if (
                inputs.get("audio_path") != "string"
                or inputs.get("layout") != "seated_studio_anchor"
            ):
                raise ValueError("avatar contract must require audio_path and seated layout")
            if inputs.get("image_path") != "string" and inputs.get("reference_image") != "string":
                raise ValueError("avatar contract must require image_path or reference_image")


def load_skill_manifest(path: Path) -> SkillManifest:
    with Path(path).open("r", encoding="utf-8") as handle:
        return SkillManifest.model_validate(yaml.safe_load(handle))


def load_contracts(directory: Path) -> dict[SkillKind, SkillManifest]:
    manifests: dict[SkillKind, SkillManifest] = {}
    for path in sorted(Path(directory).glob("*.yaml")):
        manifest = load_skill_manifest(path)
        if manifest.kind in manifests:
            raise ValueError(f"duplicate skill contract: {manifest.kind.value}")
        manifests[manifest.kind] = manifest
    missing = set(SkillKind).difference(manifests)
    if missing:
        names = ", ".join(sorted(kind.value for kind in missing))
        raise ValueError(f"missing skill contracts: {names}")
    return manifests
