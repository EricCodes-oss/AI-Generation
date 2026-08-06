from pathlib import Path

import pytest
from pydantic import ValidationError

from avatar_pipeline.skill_contracts import SkillKind, SkillManifest, load_contracts

CONTRACTS = Path("skills/contracts")
REQUIRED_NEGATIVE_TERMS = {
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


def test_host_image_contract_is_content_first_seated_and_negative_prompted():
    contract = load_contracts(CONTRACTS)[SkillKind.HOST_IMAGE]

    assert contract.name == "giggle-gpt-image-2"
    assert contract.provider == "giggle-gpt-image-2"
    assert contract.required_inputs == {
        "prompt": "string",
        "negative_prompt": "string",
        "layout": "seated_studio_anchor",
        "aspect_ratio": "9:16",
        "shot": "waist_up_seated",
    }
    assert "reference_image" in contract.optional_inputs
    assert set(contract.negative_prompt.lower().split(", ")) >= REQUIRED_NEGATIVE_TERMS
    assert {"image_path", "identity_notes", "safety_check"} <= set(contract.required_outputs)


def test_avatar_contract_requires_image_audio_and_seated_layout():
    contract = load_contracts(CONTRACTS)[SkillKind.AVATAR]

    assert contract.name == "giggle-generation-tv-avatar-video"
    assert contract.provider == "giggle-generation-tv-avatar-video"
    assert contract.primary_mode == "image_plus_audio"
    assert contract.required_inputs == {
        "image_path": "string",
        "audio_path": "string",
        "layout": "seated_studio_anchor",
    }
    assert {"video_path", "task_id"} <= set(contract.required_outputs)


@pytest.mark.parametrize(
    ("kind", "field", "value"),
    [
        (SkillKind.HOST_IMAGE, "layout", "standing_studio_anchor"),
        (SkillKind.HOST_IMAGE, "aspect_ratio", "16:9"),
        (SkillKind.HOST_IMAGE, "shot", "head_and_shoulders"),
        (SkillKind.AVATAR, "layout", "standing_studio_anchor"),
    ],
)
def test_seated_avatar_contracts_reject_wrong_layout_or_frame(kind, field, value):
    contract = load_contracts(CONTRACTS)[kind]
    payload = contract.model_dump()
    payload["required_inputs"][field] = value

    with pytest.raises(ValidationError):
        SkillManifest.model_validate(payload)


@pytest.mark.parametrize(
    ("kind", "field"),
    [
        (SkillKind.HOST_IMAGE, "prompt"),
        (SkillKind.HOST_IMAGE, "negative_prompt"),
        (SkillKind.AVATAR, "image_path"),
        (SkillKind.AVATAR, "audio_path"),
    ],
)
def test_seated_avatar_contracts_reject_missing_required_inputs(kind, field):
    contract = load_contracts(CONTRACTS)[kind]
    payload = contract.model_dump()
    del payload["required_inputs"][field]

    with pytest.raises(ValidationError):
        SkillManifest.model_validate(payload)
