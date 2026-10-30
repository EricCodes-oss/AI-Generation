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


def test_news_script_contract_rejects_viewer_prompting_fillers():
    script_rules = "\n".join(
        load_contracts(Path("skills/contracts"))[SkillKind.NEWS_SCRIPT_WRITER].safety_constraints
    )
    assert "近日在平台上引发关注" in script_rules
    assert "我们先看画面" in script_rules
    assert "让我们先看画面" in script_rules


def test_news_script_contract_requires_observation_meaning_and_takeaway():
    script_rules = "\n".join(
        load_contracts(Path("skills/contracts"))[SkillKind.NEWS_SCRIPT_WRITER].safety_constraints
    )
    assert "表述现象" in script_rules
    assert "说明本质" in script_rules
    assert "给出启发" in script_rules


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


def test_reference_remix_lessons_are_locked_into_contracts():
    """五星红旗一期返工教训：插播来源、画幅、主持人分工、OCR自检与例外记录不得丢失。"""
    contracts = load_contracts(Path("skills/contracts"))

    clipper_rules = "\n".join(contracts[SkillKind.FOOTAGE_CLIPPER].safety_constraints)
    assert "插播用参考视频" in clipper_rules
    assert "BVID" in clipper_rules
    assert "最小条带" in clipper_rules
    assert "片尾卡" in clipper_rules

    compositor_rules = "\n".join(contracts[SkillKind.COMPOSITOR].safety_constraints)
    assert "撑满1080宽度" in compositor_rules and "禁止左右黑边" in compositor_rules
    assert "不得由主持人口播复述" in compositor_rules

    quality_rules = "\n".join(contracts[SkillKind.QUALITY_CONTROL].safety_constraints)
    assert "正样本自检" in quality_rules and "Vision" in quality_rules
    assert "override" in quality_rules


def test_verbatim_replica_lessons_are_locked_into_contracts():
    """BV1Gknm6kE78 一期教训：先估时长再配音、结构改动须问用户、镜头标签先验、静态源标记、分辨率与逐句ASR。"""
    contracts = load_contracts(Path("skills/contracts"))

    script_rules = "\n".join(contracts[SkillKind.NEWS_SCRIPT_WRITER].safety_constraints)
    assert "先按默认音色估算朗读时长" in script_rules
    assert "4字每秒" in script_rules
    assert "必须先征求用户意见" in script_rules and "atempo" in script_rules

    clipper_rules = "\n".join(contracts[SkillKind.FOOTAGE_CLIPPER].safety_constraints)
    assert "首帧、中帧、末帧" in clipper_rules
    assert "static_source=true" in clipper_rules

    avatar_rules = "\n".join(contracts[SkillKind.AVATAR].safety_constraints)
    assert "核对分辨率" in avatar_rules and "1080" in avatar_rules

    quality_rules = "\n".join(contracts[SkillKind.QUALITY_CONTROL].safety_constraints)
    assert "逐句复核" in quality_rules
    assert "static_source=true" in quality_rules and "freezedetect" in quality_rules
    assert "fact_flags" in quality_rules
    assert "不构成授权凭证" in quality_rules


def test_verbatim_replica_lessons_are_in_agents_and_skill_reference():
    agents = Path("AGENTS.md").read_text()
    assert "Verbatim replica: plan timing before paid generation" in agents
    assert "static_source=true" in agents
    assert "sentence by sentence" in agents

    reference = Path(
        "/Users/liuweidong/.codex/skills/video-generator/references/news-editorial-quality.md"
    )
    if reference.exists():
        text = reference.read_text()
        assert "## 6. 逐字复刻：先定时长与镜头，再付费生成" in text
        assert "必须先征求用户意见" in text
        assert "static_source=true" in text


def test_generated_insert_tiny_mark_regression_rule():
    quality_rules = "\n".join(
        load_contracts(Path("skills/contracts"))[SkillKind.QUALITY_CONTROL].safety_constraints
    )
    assert "源分辨率检查细小生成标记" in quality_rules
    assert "OCR零命中" in quality_rules
    assert "局部修复后" in quality_rules
    agents = Path("AGENTS.md").read_text()
    assert "garment and prop regions at source resolution" in agents
    assert "OCR misses tiny synthetic glyphs" in agents
