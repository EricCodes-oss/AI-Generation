import hashlib
import json
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from avatar_pipeline.news_production import (
    NewsProductionGateError,
    initialize_news_run,
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
    return initialize_news_run(
        tmp_path,
        day=date(2026, 8, 12),
        slug="storm",
        topic="台风新闻",
        version=1,
        quality_config_path=root / CONFIG,
    )


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


def test_broll_guidance_depends_on_duration():
    config = load_news_quality_config(CONFIG)
    assert recommend_broll(52.128, config).recommended_count == 3
    assert recommend_broll(60, config).minimum_count == 3
    assert recommend_broll(80, config).maximum_count == 4
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
