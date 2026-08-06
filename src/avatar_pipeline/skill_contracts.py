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
        if isinstance(self.required_inputs, dict) and any(
            not key or not value for key, value in self.required_inputs.items()
        ):
            raise ValueError("required input names and constraints must be non-empty")
        if self.kind is SkillKind.HOST_IMAGE:
            self._validate_host_image_contract()
        elif self.kind is SkillKind.AVATAR:
            self._validate_avatar_contract()
        elif self.primary_mode is not None or self.fallback_mode is not None:
            raise ValueError("generation modes are only valid for the avatar contract")
        if self.kind is SkillKind.TTS:
            self._validate_tts_contract()
        elif self.recommended_audio_format is not None or self.timestamps_supported is not None:
            raise ValueError("audio fields are only valid for the tts contract")
        return self

    def _validate_tts_contract(self) -> None:
        expected_skill = "giggle-generation-speech"
        if self.provider != expected_skill or self.name != expected_skill:
            raise ValueError("tts contract requires the giggle-generation-speech skill")
        if self.recommended_audio_format != "wav" or self.timestamps_supported is not True:
            raise ValueError("tts contract must recommend wav and support timestamps")

    def _validate_host_image_contract(self) -> None:
        if self.provider != "giggle-gpt-image-2" or self.name != "giggle-gpt-image-2":
            raise ValueError("host image contract requires the giggle-gpt-image-2 skill")
        required_outputs = {"image_path", "identity_notes", "safety_check"}
        if not required_outputs <= set(self.required_outputs):
            raise ValueError("host image contract is missing required outputs")
        if not isinstance(self.required_inputs, dict):
            raise ValueError("host image contract requires constrained input definitions")

        inputs = self.required_inputs
        expected = {
            "prompt": "string",
            "negative_prompt": "string",
            "layout": "seated_studio_anchor",
            "aspect_ratio": "9:16",
            "shot": "waist_up_seated",
        }
        if inputs != expected:
            raise ValueError("host image contract must require the seated content-first inputs")
        if self.optional_inputs != ["reference_image"]:
            raise ValueError(
                "host image contract must allow only reference_image as optional input"
            )
        if self.supported_aspect_ratios != ["9:16"]:
            raise ValueError("host image contract must support only the 9:16 aspect ratio")
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
            "interrogation room",
            "police station",
            "prison bars",
            "wanted poster",
            "missing person poster",
            "real public figure resemblance",
        }
        terms = {term.strip().lower() for term in self.negative_prompt.split(",")}
        if not required_terms <= terms:
            raise ValueError("host image negative_prompt is missing required safety terms")

    def _validate_avatar_contract(self) -> None:
        expected_skill = "giggle-generation-tv-avatar-video"
        if self.provider != expected_skill or self.name != expected_skill:
            raise ValueError("avatar contract requires the giggle-generation-tv-avatar-video skill")
        if self.primary_mode != "image_plus_audio" or self.fallback_mode != "image_plus_text":
            raise ValueError(
                "avatar contract requires image_plus_audio primary mode and "
                "image_plus_text fallback mode"
            )
        required_outputs = {"video_path", "task_id"}
        if not required_outputs <= set(self.required_outputs):
            raise ValueError("avatar contract is missing required outputs")
        if not isinstance(self.required_inputs, dict):
            raise ValueError("avatar contract requires constrained input definitions")

        inputs = self.required_inputs
        expected = {
            "image_path": "string",
            "audio_path": "string",
            "layout": "seated_studio_anchor",
        }
        if inputs != expected:
            raise ValueError(
                "avatar contract must require image_path, audio_path, and seated layout"
            )
        if self.optional_inputs != ["text"]:
            raise ValueError("avatar contract must allow only text as optional input")
        if self.supported_aspect_ratios != ["9:16"]:
            raise ValueError("avatar contract must support only the 9:16 aspect ratio")


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
