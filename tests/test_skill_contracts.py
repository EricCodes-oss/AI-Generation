from pathlib import Path

from avatar_pipeline.skill_contracts import SkillKind, load_contracts


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

    assert contracts[SkillKind.HOST_IMAGE].provider == "giggle-gpt-image-2"
    assert contracts[SkillKind.HOST_IMAGE].required_inputs["prompt"] == "string"
    assert contracts[SkillKind.AVATAR].provider == "giggle-generation-tv-avatar-video"
    assert contracts[SkillKind.AVATAR].required_inputs["audio_path"] == "string"
