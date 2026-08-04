"""Validated interface contracts for external generation Skills."""

from enum import StrEnum
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class SkillKind(StrEnum):
    """External capability types required by the production pipeline."""

    TTS = "tts"
    AVATAR = "avatar"
    SEEDANCE = "seedance"


class SkillManifest(BaseModel):
    """Phase 1 manifest describing, but not invoking, an external Skill."""

    model_config = ConfigDict(extra="forbid")

    kind: SkillKind
    contract_version: Literal["1.0"]
    display_name: str = Field(min_length=1)
    required_inputs: list[str] = Field(min_length=1)
    optional_inputs: list[str] = Field(default_factory=list)
    required_outputs: list[str] = Field(min_length=1)
    supported_aspect_ratios: list[str] = Field(min_length=1)
    max_duration_seconds: int = Field(gt=0)
    real_generation_enabled: Literal[False]
    primary_mode: str | None = None
    fallback_mode: str | None = None
    recommended_audio_format: str | None = None
    timestamps_supported: bool | None = None

    @model_validator(mode="after")
    def validate_kind_specific_fields(self) -> "SkillManifest":
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


def load_skill_manifest(path: Path) -> SkillManifest:
    """Load one strict YAML Skill manifest."""

    with Path(path).open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    return SkillManifest.model_validate(raw)


def load_contracts(directory: Path) -> dict[SkillKind, SkillManifest]:
    """Load exactly one manifest for each external Skill kind."""

    manifests: dict[SkillKind, SkillManifest] = {}
    for path in sorted(Path(directory).glob("*.yaml")):
        manifest = load_skill_manifest(path)
        if manifest.kind in manifests:
            raise ValueError(f"duplicate skill contract: {manifest.kind.value}")
        manifests[manifest.kind] = manifest

    required = set(SkillKind)
    missing = required.difference(manifests)
    if missing:
        names = ", ".join(sorted(kind.value for kind in missing))
        raise ValueError(f"missing skill contracts: {names}")
    return manifests
