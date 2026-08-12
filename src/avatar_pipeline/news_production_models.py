"""Stored records for the V5 manual avatar-news production workflow."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ProductionModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class NewsRunStatus(StrEnum):
    INITIALIZED = "initialized"
    GENERATION_READY = "generation_ready"
    TIMELINE_READY = "timeline_ready"
    RENDER_READY = "render_ready"
    RENDERED_PENDING_QC = "rendered_pending_qc"
    AUTOMATIC_QC_PASSED = "automatic_qc_passed"
    DIRECTOR_REVIEW = "director_review"
    READY_TO_DELIVER = "ready_to_deliver"
    CHANGES_REQUIRED = "changes_required"


class NewsRunManifest(ProductionModel):
    run_id: str = Field(min_length=1)
    quality_profile: str = Field(min_length=1)
    quality_profile_version: str = Field(min_length=1)
    production_mode: Literal["manual_directed"] = "manual_directed"
    topic: str = Field(min_length=1)
    target_duration_seconds: float = Field(ge=45, le=90)
    host_id: str = Field(min_length=1)
    host_reference_image: str = Field(min_length=1)
    host_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    voice_id: str = Field(min_length=1)
    clean_master: Literal[True] = True
    status: NewsRunStatus = NewsRunStatus.INITIALIZED
    parent_run_id: str | None = None
    final_video_path: str | None = None
    final_video_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    created_at: datetime
    updated_at: datetime | None = None


class AuthoritativeSource(ProductionModel):
    source_id: str = Field(min_length=1)
    platform: str = Field(min_length=1)
    title: str = Field(min_length=1)
    url: str = Field(min_length=1)
    published_at: datetime
    reliability_note: str | None = None


class FactEvidence(ProductionModel):
    run_id: str = Field(min_length=1)
    authoritative_sources: list[AuthoritativeSource] = Field(default_factory=list)
    event_time: datetime | None = None
    locations: list[str] = Field(default_factory=list)
    verified_facts: list[str] = Field(default_factory=list)
    verified_numbers: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    prohibited_claims: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_evidence(self) -> FactEvidence:
        if not self.authoritative_sources:
            raise ValueError("fact evidence requires an authoritative source")
        if not self.verified_facts:
            raise ValueError("fact evidence requires a verified fact")
        return self


class ScriptReview(ProductionModel):
    run_id: str = Field(min_length=1)
    script_path: str = Field(min_length=1)
    title_path: str = Field(min_length=1)
    target_duration_seconds: float = Field(ge=45, le=90)
    actual_audio_duration_seconds: float = Field(ge=45, le=90)
    authoritative_tone_passed: bool
    sentence_clarity_passed: bool
    information_density_passed: bool
    ending_complete: bool
    facts_traceable: bool
    director_approved: bool

    @model_validator(mode="after")
    def validate_approval(self) -> ScriptReview:
        checks = (
            self.authoritative_tone_passed,
            self.sentence_clarity_passed,
            self.information_density_passed,
            self.ending_complete,
            self.facts_traceable,
        )
        if self.director_approved and not all(checks):
            raise ValueError("approved script review requires every editorial check to pass")
        return self


class FootageAsset(ProductionModel):
    asset_id: str = Field(min_length=1)
    source_platform: str = Field(min_length=1)
    source_url: str = Field(min_length=1)
    downloaded_at: datetime
    local_path: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    watermark_free: bool
    platform_logo_free: bool
    account_mark_free: bool
    burned_caption_free: bool
    visual_relevance: str = Field(min_length=1)
    user_usage_rule_passed: bool

    @model_validator(mode="after")
    def validate_usage_rule(self) -> FootageAsset:
        checks = (
            self.watermark_free,
            self.platform_logo_free,
            self.account_mark_free,
            self.burned_caption_free,
        )
        if self.user_usage_rule_passed and not all(checks):
            raise ValueError("watermark and visual-text checks must pass before project use")
        return self


class FootageLedger(ProductionModel):
    run_id: str = Field(min_length=1)
    assets: list[FootageAsset] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_assets(self) -> FootageLedger:
        ids = [item.asset_id for item in self.assets]
        if len(ids) != len(set(ids)):
            raise ValueError("footage asset IDs must be unique")
        return self


class ShotSelectionRecord(ProductionModel):
    shot_id: str = Field(min_length=1)
    asset_id: str = Field(min_length=1)
    script_segment_id: str = Field(min_length=1)
    semantic_role: str = Field(min_length=1)
    source_in: float = Field(ge=0)
    source_out: float = Field(gt=0)
    target_duration_seconds: float = Field(gt=0)
    continuous_action: bool
    forward_playback: bool
    visual_quality_passed: bool
    director_approved: bool

    @model_validator(mode="after")
    def validate_shot(self) -> ShotSelectionRecord:
        if self.source_out <= self.source_in:
            raise ValueError("shot source interval must have a positive duration")
        source_duration = self.source_out - self.source_in
        if abs(source_duration - self.target_duration_seconds) > 0.01:
            raise ValueError("shot target duration must match its source interval")
        if self.director_approved and not (
            self.continuous_action and self.forward_playback and self.visual_quality_passed
        ):
            raise ValueError("approved shot must be continuous, forward, and visually qualified")
        if not self.forward_playback:
            raise ValueError("V5 footage must use forward playback")
        return self


class ShotSelection(ProductionModel):
    run_id: str = Field(min_length=1)
    shots: list[ShotSelectionRecord] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_shots(self) -> ShotSelection:
        ids = [item.shot_id for item in self.shots]
        if len(ids) != len(set(ids)):
            raise ValueError("shot IDs must be unique")
        return self


class TimelineSegment(ProductionModel):
    type: Literal["anchor", "broll"]
    start: float = Field(ge=0)
    end: float = Field(gt=0)
    script_segment_id: str = Field(min_length=1)
    shot_id: str | None = None

    @model_validator(mode="after")
    def validate_segment(self) -> TimelineSegment:
        if self.end <= self.start:
            raise ValueError("timeline segment must have a positive duration")
        if self.type == "broll" and not self.shot_id:
            raise ValueError("B-roll timeline segment requires a shot ID")
        if self.type == "anchor" and self.shot_id is not None:
            raise ValueError("anchor timeline segment cannot reference a shot")
        return self


class NewsTimeline(ProductionModel):
    run_id: str = Field(min_length=1)
    audio_duration_seconds: float = Field(ge=45, le=90)
    segments: list[TimelineSegment] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_timeline(self) -> NewsTimeline:
        if abs(self.segments[0].start) > 0.001:
            raise ValueError("timeline must start at zero")
        previous_end = 0.0
        for segment in self.segments:
            if abs(segment.start - previous_end) > 0.01:
                raise ValueError("timeline must not contain gaps or overlaps")
            previous_end = segment.end
        if abs(previous_end - self.audio_duration_seconds) > 0.01:
            raise ValueError("timeline must end at the master audio duration")
        if self.segments[-1].type != "anchor":
            raise ValueError("news timeline must close with the anchor")
        return self


class DirectorCheck(ProductionModel):
    id: str = Field(min_length=1)
    description: str = Field(min_length=1)
    passed: bool
    note: str | None = None
    evidence_path: str | None = None


class DirectorReview(ProductionModel):
    run_id: str = Field(min_length=1)
    approved: bool
    checks: list[DirectorCheck] = Field(min_length=1)
    reviewed_at: datetime
    actor: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_review(self) -> DirectorReview:
        if self.approved and not all(item.passed for item in self.checks):
            raise ValueError("approved director review cannot contain failed checks")
        return self


class QualityCheck(ProductionModel):
    id: str = Field(min_length=1)
    category: Literal[
        "technical", "identity", "timeline", "footage", "audio", "director", "deliverable"
    ]
    severity: Literal["hard_block", "advisory", "director_review"]
    expected: str = Field(min_length=1)
    actual: str = Field(min_length=1)
    status: Literal["PASS", "FAIL", "ADVISORY"]
    evidence_path: str = Field(min_length=1)
    checked_at: datetime


class FinalQualityReport(ProductionModel):
    run_id: str = Field(min_length=1)
    overall_passed: bool
    checks: list[QualityCheck] = Field(default_factory=list)
    director_review: DirectorReview | None = None
    final_video_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_outcome(self) -> FinalQualityReport:
        failed = [item for item in self.checks if item.status == "FAIL"]
        if self.overall_passed and failed:
            raise ValueError("overall-passed report cannot contain failed checks")
        if self.overall_passed and (
            self.director_review is None or not self.director_review.approved
        ):
            raise ValueError("overall-passed report requires director approval")
        return self
