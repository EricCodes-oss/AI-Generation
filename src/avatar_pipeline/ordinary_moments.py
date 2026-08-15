"""Contracts for auditing spontaneous ordinary-life human-interest footage."""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from avatar_pipeline.models import DomainModel


class RecordingOrigin(StrEnum):
    """How a spontaneous ordinary-life moment was captured."""

    FAMILY_PHONE = "family_phone"
    PASSERBY_PHONE = "passerby_phone"
    DASHCAM = "dashcam"
    CCTV = "cctv"
    SHOP_CAMERA = "shop_camera"
    PUBLIC_SCENE = "public_scene"
    OTHER_NATURAL_RECORDING = "other_natural_recording"


class OrdinaryMomentAssessment(DomainModel):
    """Evidence used to decide whether a moment is natural rather than creator-led."""

    recording_origin: RecordingOrigin
    creator_is_professional_influencer: bool
    account_is_personal_daily_recorder: bool
    ordinary_people_are_primary_subjects: bool
    event_was_creator_initiated: bool
    event_preexisted_filming: bool
    event_is_daily_life_context: bool
    natural_reaction_evidence: list[str] = Field(min_length=1)
    human_warmth_evidence: list[str] = Field(min_length=1)
    original_recorder_available: bool
    ambient_audio_available: bool
    continuous_scene_available: bool
    staging_risk: float = Field(ge=0, le=1)

    @property
    def rejection_reasons(self) -> list[str]:
        reasons: list[str] = []
        if self.creator_is_professional_influencer:
            reasons.append("professional influencer content is ineligible")
        if not self.account_is_personal_daily_recorder:
            reasons.append("account must be a personal daily recorder")
        if not self.ordinary_people_are_primary_subjects:
            reasons.append("ordinary people must be the primary subjects")
        if self.event_was_creator_initiated:
            reasons.append("creator-initiated event is ineligible")
        if not self.event_preexisted_filming:
            reasons.append("event must preexist filming")
        if not self.event_is_daily_life_context:
            reasons.append("event must occur in a real daily-life context")
        if not self.original_recorder_available:
            reasons.append("original recorder must be available")
        if not self.continuous_scene_available:
            reasons.append("continuous scene must be available")
        if self.staging_risk > 0.35:
            reasons.append("staging risk exceeds 0.35")
        return reasons

    @property
    def eligible(self) -> bool:
        return not self.rejection_reasons
