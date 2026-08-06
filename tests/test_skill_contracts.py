from pathlib import Path

import pytest
from pydantic import ValidationError

from avatar_pipeline.skill_contracts import SkillKind, SkillManifest, load_contracts


def test_news_pipeline_skill_contracts_are_declared():
    contracts = load_contracts(Path("skills/contracts"))
    assert set(contracts) == {
        SkillKind.OPINIONS_CRAWLER,
        SkillKind.NEWS_SCRIPT_WRITER,
        SkillKind.NEWS_MEDIA_PLANNER,
        SkillKind.TTS,
        SkillKind.HOST_IMAGE,
        SkillKind.AVATAR,
        SkillKind.FOOTAGE_CLIPPER,
        SkillKind.SEEDANCE,
        SkillKind.COMPOSITOR,
        SkillKind.QUALITY_CONTROL,
    }
    assert contracts[SkillKind.AVATAR].primary_mode == "image_plus_audio"
    assert contracts[SkillKind.TTS].recommended_audio_format == "wav"
    assert contracts[SkillKind.SEEDANCE].required_outputs == ["video_path", "task_id"]
    assert contracts[SkillKind.COMPOSITOR].required_outputs == [
        "master_video_path",
        "timeline_report",
    ]
    assert contracts[SkillKind.QUALITY_CONTROL].required_outputs == [
        "passed",
        "report_path",
        "issues",
    ]


def test_target_skill_contracts_expose_provider_and_content_first_fields():
    contracts = load_contracts(Path("skills/contracts"))

    assert contracts[SkillKind.TTS].provider == "giggle-generation-speech"
    assert contracts[SkillKind.TTS].name == "giggle-generation-speech"
    assert contracts[SkillKind.HOST_IMAGE].provider == "giggle-gpt-image-2"
    assert contracts[SkillKind.HOST_IMAGE].required_inputs["prompt"] == "string"
    assert contracts[SkillKind.AVATAR].provider == "giggle-generation-tv-avatar-video"
    assert contracts[SkillKind.AVATAR].required_inputs["audio_path"] == "string"


def test_other_skill_contracts_keep_legacy_required_input_lists():
    contracts = load_contracts(Path("skills/contracts"))

    for kind, contract in contracts.items():
        if kind not in {SkillKind.HOST_IMAGE, SkillKind.AVATAR}:
            assert isinstance(contract.required_inputs, list)


@pytest.mark.parametrize("field", ["provider", "name"])
def test_tts_contract_rejects_missing_skill_identity(field):
    contract = load_contracts(Path("skills/contracts"))[SkillKind.TTS]
    payload = contract.model_dump()
    del payload[field]

    with pytest.raises(ValidationError):
        SkillManifest.model_validate(payload)


@pytest.mark.parametrize("field", ["provider", "name"])
def test_tts_contract_rejects_wrong_skill_identity(field):
    contract = load_contracts(Path("skills/contracts"))[SkillKind.TTS]
    payload = contract.model_dump()
    payload[field] = "other-speech-skill"

    with pytest.raises(ValidationError):
        SkillManifest.model_validate(payload)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("recommended_audio_format", "mp3"),
        ("timestamps_supported", False),
    ],
)
def test_tts_contract_keeps_wav_and_timestamps_constraints(field, value):
    contract = load_contracts(Path("skills/contracts"))[SkillKind.TTS]
    payload = contract.model_dump()
    payload[field] = value

    with pytest.raises(ValidationError):
        SkillManifest.model_validate(payload)


@pytest.mark.parametrize(
    "required_output",
    ["audio_path", "timestamps"],
)
def test_tts_contract_rejects_missing_required_outputs(required_output):
    contract = load_contracts(Path("skills/contracts"))[SkillKind.TTS]
    payload = contract.model_dump()
    payload["required_outputs"].remove(required_output)

    with pytest.raises(ValidationError):
        SkillManifest.model_validate(payload)


@pytest.mark.parametrize(
    "kind",
    [SkillKind.HOST_IMAGE, SkillKind.AVATAR, SkillKind.TTS],
)
def test_target_contracts_reject_duplicate_required_outputs(kind):
    contract = load_contracts(Path("skills/contracts"))[kind]
    payload = contract.model_dump()
    payload["required_outputs"].extend(["future_output", "future_output"])

    with pytest.raises(ValidationError):
        SkillManifest.model_validate(payload)


@pytest.mark.parametrize(
    "kind",
    [SkillKind.HOST_IMAGE, SkillKind.AVATAR, SkillKind.TTS],
)
def test_target_contracts_allow_additional_non_conflicting_outputs(kind):
    contract = load_contracts(Path("skills/contracts"))[kind]
    payload = contract.model_dump()
    payload["required_outputs"].append("future_output")

    validated = SkillManifest.model_validate(payload)

    assert "future_output" in validated.required_outputs


def test_tts_contract_locks_selected_presenter_voice():
    contract = load_contracts(Path("skills/contracts"))[SkillKind.TTS]

    assert contract.default_voice_id == "宣传女生Pro:clone_20260806_114837_980375"
