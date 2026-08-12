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
        "identity_check",
        "timeline_check",
        "ending_check",
    ]


def test_target_skill_contracts_expose_provider_and_content_first_fields():
    contracts = load_contracts(Path("skills/contracts"))

    assert contracts[SkillKind.HOST_IMAGE].provider == "giggle-gpt-image-2"
    assert contracts[SkillKind.HOST_IMAGE].required_inputs["prompt"] == "string"
    assert contracts[SkillKind.AVATAR].provider == "giggle-generation-tv-avatar-video"
    assert contracts[SkillKind.AVATAR].required_inputs["audio_path"] == "string"


def test_v5_news_contracts_lock_duration_identity_clean_master_and_quality_evidence():
    contracts = load_contracts(Path("skills/contracts"))
    v5_kinds = {
        SkillKind.NEWS_SCRIPT_WRITER,
        SkillKind.NEWS_MEDIA_PLANNER,
        SkillKind.TTS,
        SkillKind.AVATAR,
        SkillKind.FOOTAGE_CLIPPER,
        SkillKind.COMPOSITOR,
        SkillKind.QUALITY_CONTROL,
    }
    assert all(contracts[kind].max_duration_seconds == 90 for kind in v5_kinds)

    avatar = contracts[SkillKind.AVATAR]
    avatar_rules = "\n".join(avatar.safety_constraints)
    assert "host-c2-pro-candidate-2-final" in avatar_rules
    assert "939324593eb718cd2a39be4c171f74178a6a48442f7e0d61afe8a875011e8a47" in (avatar_rules)
    tts = contracts[SkillKind.TTS]
    assert "voice_id" in tts.required_inputs
    assert any("cobra_design_20250717_162347_664524" in item for item in tts.safety_constraints)

    planner = contracts[SkillKind.NEWS_MEDIA_PLANNER]
    assert {"script_segment_ids", "semantic_mapping", "source_sidecar_records"} <= set(
        planner.required_inputs
    )
    assert "source_sidecar_records" in planner.required_outputs

    clipper = contracts[SkillKind.FOOTAGE_CLIPPER]
    assert {"script_segment_id", "semantic_role"} <= set(clipper.required_inputs)
    assert any("连续正向" in item for item in clipper.safety_constraints)
    assert any("倒放" in item and "循环" in item for item in clipper.safety_constraints)

    compositor = contracts[SkillKind.COMPOSITOR]
    compositor_rules = "\n".join(compositor.safety_constraints)
    assert "无字净版" in compositor_rules
    assert "素材原声" in compositor_rules
    assert "字幕" in compositor_rules and "Logo" in compositor_rules
    assert "旁路" in compositor_rules

    quality = contracts[SkillKind.QUALITY_CONTROL]
    assert {"identity_check", "timeline_check", "ending_check"} <= set(quality.required_outputs)
    quality_rules = "\n".join(quality.safety_constraints)
    assert "主持人" in quality_rules and "音色" in quality_rules
    assert "连续主持人结尾" in quality_rules
