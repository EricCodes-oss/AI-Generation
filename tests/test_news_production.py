import hashlib
import json
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from avatar_pipeline.news_production import (
    NewsProductionGateError,
    build_full_program_transcript,
    initialize_news_run,
    lock_creative_brief,
    mark_rendered,
    recommend_broll,
    validate_generation_preflight,
    validate_render_preflight,
    validate_timeline_preflight,
)
from avatar_pipeline.news_production_models import NewsRunManifest, NewsRunStatus
from avatar_pipeline.news_quality_config import load_news_quality_config

NOW = datetime(2026, 8, 12, 12, 0, tzinfo=UTC)
CONFIG = Path("configs/news-video-quality-v5.yaml")


def write_json(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def initialized_run(tmp_path: Path, project_root: Path | None = None) -> Path:
    root = project_root or Path.cwd()
    run_dir = initialize_news_run(
        tmp_path,
        day=date(2026, 8, 12),
        slug="storm",
        topic="台风新闻",
        version=1,
        quality_config_path=root / CONFIG,
    )
    manifest = NewsRunManifest.model_validate_json(
        (run_dir / "production/run-manifest.json").read_text(encoding="utf-8")
    )
    write_json(
        run_dir / "production/creative-lock.json",
        {
            "run_id": manifest.run_id,
            "status": "locked",
            "core_subject": "台风新闻",
            "narrative_promise": "让观众快速理解强风影响。",
            "required_visual_tags": ["weather-impact"],
            "non_negotiables": ["必须展示强风影响。"],
            "replaceable_elements": ["城市远景"],
            "prohibited_substitutions": ["不得用无关风景代替天气影响。"],
            "uncertainty_policy": "不确定地点不写入口播，只描述可见影响。",
            "approval_basis": "director_confirmed",
            "locked_by": "test-director",
            "locked_at": NOW.isoformat(),
        },
    )
    return run_dir


def add_generation_records(run_dir: Path):
    manifest = NewsRunManifest.model_validate_json(
        (run_dir / "production/run-manifest.json").read_text(encoding="utf-8")
    )
    (run_dir / "copy/voiceover.txt").write_text("权威新闻口播。完整收束。\n", encoding="utf-8")
    (run_dir / "copy/title.txt").write_text("台风最新变化\n强降雨仍在持续\n", encoding="utf-8")
    (run_dir / "audio/master-voiceover.wav").write_bytes(b"RIFF" + b"0" * 32)
    write_json(
        run_dir / "production/fact-evidence.json",
        {
            "run_id": manifest.run_id,
            "authoritative_sources": [
                {
                    "source_id": "official-1",
                    "platform": "official",
                    "title": "权威通报",
                    "url": "https://example.com/official",
                    "published_at": NOW.isoformat(),
                }
            ],
            "verified_facts": ["台风强度减弱，降雨仍在持续"],
        },
    )
    write_json(
        run_dir / "production/script-review.json",
        {
            "run_id": manifest.run_id,
            "script_path": "copy/voiceover.txt",
            "title_path": "copy/title.txt",
            "target_duration_seconds": 52.0,
            "actual_audio_duration_seconds": 52.0,
            "authoritative_tone_passed": True,
            "sentence_clarity_passed": True,
            "information_density_passed": True,
            "ending_complete": True,
            "facts_traceable": True,
            "director_approved": True,
        },
    )


def add_timeline_records(run_dir: Path):
    manifest = NewsRunManifest.model_validate_json(
        (run_dir / "production/run-manifest.json").read_text(encoding="utf-8")
    )
    media = run_dir / "media"
    media.mkdir(exist_ok=True)
    asset = media / "storm.mp4"
    asset.write_bytes(b"forward storm footage")
    write_json(
        run_dir / "production/footage-ledger.json",
        {
            "run_id": manifest.run_id,
            "assets": [
                {
                    "asset_id": "asset-1",
                    "source_platform": "bilibili",
                    "source_url": "https://example.com/video",
                    "downloaded_at": NOW.isoformat(),
                    "local_path": "media/storm.mp4",
                    "sha256": sha(asset),
                    "watermark_free": True,
                    "platform_logo_free": True,
                    "account_mark_free": True,
                    "burned_caption_free": True,
                    "visual_relevance": "strong_wind",
                    "user_usage_rule_passed": True,
                }
            ],
        },
    )
    write_json(
        run_dir / "production/shot-selection.json",
        {
            "run_id": manifest.run_id,
            "shots": [
                {
                    "shot_id": "shot-1",
                    "asset_id": "asset-1",
                    "script_segment_id": "script-2",
                    "semantic_role": "展示强风影响",
                    "source_in": 2.0,
                    "source_out": 7.5,
                    "target_duration_seconds": 5.5,
                    "continuous_action": True,
                    "forward_playback": True,
                    "visual_quality_passed": True,
                    "director_approved": True,
                    "creative_tags": ["weather-impact"],
                }
            ],
        },
    )
    write_json(
        run_dir / "production/timeline.json",
        {
            "run_id": manifest.run_id,
            "audio_duration_seconds": 52.0,
            "segments": [
                {"type": "anchor", "start": 0, "end": 7, "script_segment_id": "script-1"},
                {
                    "type": "broll",
                    "start": 7,
                    "end": 12.5,
                    "script_segment_id": "script-2",
                    "shot_id": "shot-1",
                },
                {
                    "type": "anchor",
                    "start": 12.5,
                    "end": 52.0,
                    "script_segment_id": "script-3",
                },
            ],
        },
    )


def advance_generation(run_dir: Path, project_root: Path):
    add_generation_records(run_dir)
    validate_generation_preflight(run_dir, project_root)


def test_initialize_run_is_version_safe_and_copies_profile(tmp_path):
    run_dir = initialized_run(tmp_path)
    assert run_dir.name == "manual-news-2026-08-12-storm-v01"
    expected_directories = {"video", "audio", "copy", "production", "qc"}
    assert {item.name for item in run_dir.iterdir()} == expected_directories
    assert (run_dir / "production/quality-profile.yaml").exists()
    manifest = NewsRunManifest.model_validate_json(
        (run_dir / "production/run-manifest.json").read_text(encoding="utf-8")
    )
    assert manifest.status is NewsRunStatus.INITIALIZED
    assert manifest.parent_run_id is None
    with pytest.raises(FileExistsError):
        initialized_run(tmp_path)


def test_generation_preflight_blocks_unlocked_creative_brief(tmp_path):
    run_dir = initialized_run(tmp_path)
    lock = json.loads((run_dir / "production/creative-lock.json").read_text(encoding="utf-8"))
    lock["status"] = "draft"
    lock["locked_by"] = None
    lock["locked_at"] = None
    write_json(run_dir / "production/creative-lock.json", lock)
    add_generation_records(run_dir)

    with pytest.raises(NewsProductionGateError, match="creative_lock:not_locked"):
        validate_generation_preflight(run_dir, Path.cwd())


def test_lock_creative_brief_requires_locked_director_contract(tmp_path):
    run_dir = initialize_news_run(
        tmp_path,
        day=date(2026, 8, 12),
        slug="lock-test",
        topic="台风新闻",
        version=1,
        quality_config_path=Path.cwd() / CONFIG,
    )
    brief = tmp_path / "creative-lock.json"
    write_json(
        brief,
        {
            "run_id": run_dir.name,
            "status": "locked",
            "core_subject": "台风新闻",
            "narrative_promise": "让观众快速理解强风影响。",
            "required_visual_tags": ["weather-impact"],
            "non_negotiables": ["必须展示强风影响。"],
            "replaceable_elements": [],
            "prohibited_substitutions": ["不得用无关风景代替天气影响。"],
            "uncertainty_policy": "不确定地点不写入口播，只描述可见影响。",
            "approval_basis": "user_confirmed",
            "locked_by": "user",
            "locked_at": NOW.isoformat(),
        },
    )

    result = lock_creative_brief(run_dir, brief)

    assert result.status == "locked"
    installed = json.loads(
        (run_dir / "production/creative-lock.json").read_text(encoding="utf-8")
    )
    assert installed["required_visual_tags"] == ["weather-impact"]


def test_broll_guidance_is_director_dynamic_instead_of_count_fixed():
    config = load_news_quality_config(CONFIG)
    for duration in (52.128, 60, 80):
        guidance = recommend_broll(duration, config)
        assert guidance.selection_mode == "director_dynamic"
        assert guidance.count_fixed is False
        assert guidance.recommended_count is None
        assert guidance.minimum_count == 1
        assert guidance.maximum_count == 5
        assert guidance.minimum_clip_seconds == 4.5
        assert guidance.maximum_clip_seconds == 12.0
        assert guidance.maximum_ratio == 0.80
    with pytest.raises(ValueError, match="45-90"):
        recommend_broll(40, config)


def test_generation_preflight_locks_identity_and_approvals(tmp_path):
    project_root = Path.cwd()
    run_dir = initialized_run(tmp_path)
    add_generation_records(run_dir)
    result = validate_generation_preflight(run_dir, project_root)
    assert result.hard_failures == []
    manifest = NewsRunManifest.model_validate_json(
        (run_dir / "production/run-manifest.json").read_text(encoding="utf-8")
    )
    assert manifest.status is NewsRunStatus.GENERATION_READY

    payload = json.loads((run_dir / "production/run-manifest.json").read_text(encoding="utf-8"))
    payload["voice_id"] = "wrong"
    payload["status"] = "initialized"
    write_json(run_dir / "production/run-manifest.json", payload)
    with pytest.raises(NewsProductionGateError, match="voice_id"):
        validate_generation_preflight(run_dir, project_root)


def test_generation_preflight_recomputes_host_hash(tmp_path):
    project_root = tmp_path / "project"
    project_root.mkdir()
    config_raw = (Path.cwd() / CONFIG).read_text(encoding="utf-8")
    config_path = project_root / CONFIG
    config_path.parent.mkdir(parents=True)
    config_path.write_text(config_raw, encoding="utf-8")
    host = project_root / "output/host-v12-c2-pro/GPT-Image-2-Pro-C2-Pro-主持人最终选定.png"
    host.parent.mkdir(parents=True)
    host.write_bytes(b"wrong-host")
    run_dir = initialized_run(tmp_path / "runs", project_root)
    add_generation_records(run_dir)
    with pytest.raises(NewsProductionGateError, match="host_sha256"):
        validate_generation_preflight(run_dir, project_root)


def test_timeline_preflight_joins_assets_shots_and_semantics(tmp_path):
    run_dir = initialized_run(tmp_path)
    advance_generation(run_dir, Path.cwd())
    add_timeline_records(run_dir)
    result = validate_timeline_preflight(run_dir)
    assert result.hard_failures == []
    assert result.advisories
    manifest = NewsRunManifest.model_validate_json(
        (run_dir / "production/run-manifest.json").read_text(encoding="utf-8")
    )
    assert manifest.status is NewsRunStatus.TIMELINE_READY


def test_timeline_preflight_accepts_three_part_programme_without_advisory(tmp_path):
    run_dir = initialized_run(tmp_path)
    advance_generation(run_dir, Path.cwd())
    add_timeline_records(run_dir)
    selection = json.loads((run_dir / "production/shot-selection.json").read_text(encoding="utf-8"))
    selection["shots"] = [
        {
            "shot_id": f"shot-{index}",
            "asset_id": "asset-1",
            "script_segment_id": f"script-broll-{index}",
            "semantic_role": f"连贯叙事块{index}",
            "source_in": float((index - 1) * 11),
            "source_out": float(index * 11),
            "target_duration_seconds": 11.0,
            "continuous_action": True,
            "forward_playback": True,
            "visual_quality_passed": True,
            "director_approved": True,
            "creative_tags": ["weather-impact"],
        }
        for index in range(1, 4)
    ]
    write_json(run_dir / "production/shot-selection.json", selection)
    write_json(
        run_dir / "production/timeline.json",
        {
            "run_id": run_dir.name,
            "audio_duration_seconds": 55.0,
            "segments": [
                {"type": "anchor", "start": 0, "end": 10, "script_segment_id": "script-a1"},
                *[
                    {
                        "type": "broll",
                        "start": 10 + (index - 1) * 11,
                        "end": 10 + index * 11,
                        "script_segment_id": f"script-broll-{index}",
                        "shot_id": f"shot-{index}",
                    }
                    for index in range(1, 4)
                ],
                {"type": "anchor", "start": 43, "end": 55, "script_segment_id": "script-ending"},
            ],
        },
    )
    result = validate_timeline_preflight(run_dir)
    assert result.advisories == []


def test_timeline_preflight_rejects_alternating_presenter_and_inserts(tmp_path):
    run_dir = initialized_run(tmp_path)
    advance_generation(run_dir, Path.cwd())
    add_timeline_records(run_dir)
    timeline = json.loads((run_dir / "production/timeline.json").read_text(encoding="utf-8"))
    timeline["segments"] = [
        {"type": "anchor", "start": 0, "end": 7, "script_segment_id": "script-1"},
        {"type": "broll", "start": 7, "end": 12.5, "script_segment_id": "script-2", "shot_id": "shot-1"},
        {"type": "anchor", "start": 12.5, "end": 30, "script_segment_id": "script-3"},
        {"type": "broll", "start": 30, "end": 35.5, "script_segment_id": "script-2", "shot_id": "shot-1"},
        {"type": "anchor", "start": 35.5, "end": 52, "script_segment_id": "script-3"},
    ]
    write_json(run_dir / "production/timeline.json", timeline)
    with pytest.raises(NewsProductionGateError, match="structure_not_three_part"):
        validate_timeline_preflight(run_dir)


def test_timeline_preflight_rejects_asset_hash_and_unknown_shot(tmp_path):
    run_dir = initialized_run(tmp_path)
    advance_generation(run_dir, Path.cwd())
    add_timeline_records(run_dir)
    (run_dir / "media/storm.mp4").write_bytes(b"changed")
    with pytest.raises(NewsProductionGateError, match="asset_sha256"):
        validate_timeline_preflight(run_dir)

    add_timeline_records(run_dir)
    timeline = json.loads((run_dir / "production/timeline.json").read_text(encoding="utf-8"))
    timeline["segments"][1]["shot_id"] = "missing"
    write_json(run_dir / "production/timeline.json", timeline)
    with pytest.raises(NewsProductionGateError, match="unknown_shot"):
        validate_timeline_preflight(run_dir)


def test_timeline_preflight_rejects_short_anchor_tail(tmp_path):
    run_dir = initialized_run(tmp_path)
    advance_generation(run_dir, Path.cwd())
    add_timeline_records(run_dir)
    timeline = json.loads((run_dir / "production/timeline.json").read_text(encoding="utf-8"))
    timeline["segments"] = [
        {"type": "anchor", "start": 0, "end": 41, "script_segment_id": "script-1"},
        {
            "type": "broll",
            "start": 41,
            "end": 46.5,
            "script_segment_id": "script-2",
            "shot_id": "shot-1",
        },
        {"type": "anchor", "start": 46.5, "end": 52, "script_segment_id": "script-3"},
    ]
    write_json(run_dir / "production/timeline.json", timeline)
    with pytest.raises(NewsProductionGateError, match="anchor_tail"):
        validate_timeline_preflight(run_dir)


def test_render_preflight_rejects_forbidden_processing_and_overwrite(tmp_path):
    run_dir = initialized_run(tmp_path)
    advance_generation(run_dir, Path.cwd())
    add_timeline_records(run_dir)
    validate_timeline_preflight(run_dir)
    (run_dir / "video/anchor.mp4").write_bytes(b"anchor")
    script = run_dir / "production/render.sh"
    script.write_text(
        '#!/bin/sh\nffmpeg -i "$ROOT/video/anchor.mp4" -filter_complex reverse '
        '-map "[v]" -map "[a]" "$ROOT/video/final-clean.mp4"\n',
        encoding="utf-8",
    )
    with pytest.raises(NewsProductionGateError, match="forbidden_filter"):
        validate_render_preflight(run_dir)

    script.write_text(
        '#!/bin/sh\nffmpeg -i "$ROOT/video/anchor.mp4" -map "[v]" -map "[a]" '
        '"$ROOT/video/final-clean.mp4"\n',
        encoding="utf-8",
    )
    validate_render_preflight(run_dir)
    (run_dir / "video/final-clean.mp4").write_bytes(b"existing")
    with pytest.raises(NewsProductionGateError, match="overwrite"):
        validate_render_preflight(run_dir)


def test_render_preflight_allows_only_prebuilt_mixed_master_audio(tmp_path):
    run_dir = initialized_run(tmp_path)
    advance_generation(run_dir, Path.cwd())
    add_timeline_records(run_dir)
    validate_timeline_preflight(run_dir)
    (run_dir / "video/anchor.mp4").write_bytes(b"anchor")
    script = run_dir / "production/render.sh"

    script.write_text(
        '#!/bin/sh\nffmpeg -i "$ROOT/video/anchor.mp4" -i "$ROOT/media/storm.mp4" '
        '-map 0:v -map 1:a "$ROOT/video/final-clean.mp4"\n',
        encoding="utf-8",
    )
    with pytest.raises(NewsProductionGateError, match="source_audio_map"):
        validate_render_preflight(run_dir)

    script.write_text(
        '#!/bin/sh\nffmpeg -i "$ROOT/video/anchor.mp4" -i "$ROOT/media/storm.mp4" '
        '-filter_complex "[1:a]anull[src]" -map 0:v -map "[src]" '
        '"$ROOT/video/final-clean.mp4"\n',
        encoding="utf-8",
    )
    with pytest.raises(NewsProductionGateError, match="source_audio_filter"):
        validate_render_preflight(run_dir)

    script.write_text(
        '#!/bin/sh\nffmpeg -i "$ROOT/video/anchor.mp4" '
        '-i "$ROOT/audio/master-voiceover.wav" -map 0:v -map 1:a '
        '"$ROOT/video/final-clean.mp4"\n',
        encoding="utf-8",
    )
    result = validate_render_preflight(run_dir)
    assert result.hard_failures == []


def test_mark_rendered_requires_render_ready_nonempty_video(tmp_path):
    run_dir = initialized_run(tmp_path)
    advance_generation(run_dir, Path.cwd())
    add_timeline_records(run_dir)
    validate_timeline_preflight(run_dir)
    (run_dir / "video/anchor.mp4").write_bytes(b"anchor")
    (run_dir / "production/render.sh").write_text(
        '#!/bin/sh\nffmpeg -map "[v]" -map "[a]" "$ROOT/video/final-clean.mp4"\n',
        encoding="utf-8",
    )
    validate_render_preflight(run_dir)
    (run_dir / "video/final-clean.mp4").write_bytes(b"final video")
    manifest = mark_rendered(run_dir)
    assert manifest.status is NewsRunStatus.RENDERED_PENDING_QC


def test_build_full_program_transcript_includes_presenter_and_source_dialogue(tmp_path):
    run_dir = initialized_run(tmp_path)
    timeline = {
        "run_id": run_dir.name,
        "audio_duration_seconds": 52.0,
        "segments": [
            {"type": "anchor", "start": 0, "end": 7, "script_segment_id": "opening"},
            {
                "type": "broll",
                "start": 7,
                "end": 12.5,
                "script_segment_id": "source-dialogue",
                "shot_id": "shot-1",
            },
            {"type": "anchor", "start": 12.5, "end": 52, "script_segment_id": "ending"},
        ],
    }
    write_json(run_dir / "production/timeline.json", timeline)
    (run_dir / "copy/title.txt").write_text("孩子们说：老板要挺住\n", encoding="utf-8")
    write_json(
        run_dir / "production/program-transcript.json",
        {
            "run_id": run_dir.name,
            "title_path": "copy/title.txt",
            "director_approved": True,
            "segments": [
                {
                    "script_segment_id": "opening",
                    "visual_type": "anchor",
                    "audio_role": "presenter",
                    "start": 0,
                    "end": 7,
                    "lines": [{"speaker": "主持人", "text": "近日，小店里发生暖心一幕。"}],
                },
                {
                    "script_segment_id": "source-dialogue",
                    "visual_type": "broll",
                    "audio_role": "source_audio",
                    "start": 7,
                    "end": 12.5,
                    "lines": [
                        {"speaker": "孩子", "text": "老板要挺住啊！"},
                        {"speaker": "店主", "text": "你们留着自己花。"},
                    ],
                },
                {
                    "script_segment_id": "ending",
                    "visual_type": "anchor",
                    "audio_role": "presenter",
                    "start": 12.5,
                    "end": 52,
                    "lines": [{"speaker": "主持人", "text": "善意让低谷中的人感到温暖。"}],
                },
            ],
        },
    )

    transcript_path = build_full_program_transcript(run_dir)

    transcript = transcript_path.read_text(encoding="utf-8")
    assert transcript.startswith("《孩子们说：老板要挺住》")
    assert "【00:00.000—00:07.000｜主持人口播】" in transcript
    assert "【00:07.000—00:12.500｜现场原声】" in transcript
    assert "孩子：老板要挺住啊！" in transcript
    assert "店主：你们留着自己花。" in transcript
    assert transcript.rstrip().endswith("主持人：善意让低谷中的人感到温暖。")


def test_build_full_program_transcript_rejects_missing_timeline_segment(tmp_path):
    run_dir = initialized_run(tmp_path)
    write_json(
        run_dir / "production/timeline.json",
        {
            "run_id": run_dir.name,
            "audio_duration_seconds": 52.0,
            "segments": [
                {"type": "anchor", "start": 0, "end": 52, "script_segment_id": "opening"}
            ],
        },
    )
    (run_dir / "copy/title.txt").write_text("完整台词测试\n", encoding="utf-8")
    write_json(
        run_dir / "production/program-transcript.json",
        {
            "run_id": run_dir.name,
            "title_path": "copy/title.txt",
            "director_approved": True,
            "segments": [],
        },
    )

    with pytest.raises(NewsProductionGateError, match="segment_coverage"):
        build_full_program_transcript(run_dir)
