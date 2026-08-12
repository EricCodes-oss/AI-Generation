import json
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from avatar_pipeline.news_production import initialize_news_run
from avatar_pipeline.news_production_models import NewsRunManifest, NewsRunStatus
from avatar_pipeline.news_qc import (
    REQUIRED_DIRECTOR_CHECK_IDS,
    apply_director_review,
    build_automatic_qc_report,
)

NOW = datetime(2026, 8, 12, 12, 0, tzinfo=UTC)
CONFIG = Path("configs/news-video-quality-v5.yaml")


def write_json(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def prepared_run(tmp_path: Path) -> Path:
    run_dir = initialize_news_run(
        tmp_path,
        day=date(2026, 8, 12),
        slug="storm",
        topic="台风新闻",
        version=1,
        quality_config_path=CONFIG,
    )
    manifest_path = run_dir / "production/run-manifest.json"
    manifest = NewsRunManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    final_video = run_dir / "video/final-clean.mp4"
    final_video.write_bytes(b"final-v5-video")
    import hashlib

    manifest.status = NewsRunStatus.RENDERED_PENDING_QC
    manifest.final_video_sha256 = hashlib.sha256(final_video.read_bytes()).hexdigest()
    manifest.updated_at = NOW
    write_json(manifest_path, manifest.model_dump(mode="json"))

    for relative, text in {
        "copy/voiceover.txt": "权威新闻口播。完整收束。\n",
        "copy/title.txt": "台风最新变化\n强降雨仍在持续\n",
        "audio/master-voiceover.wav": "master",
        "production/render.sh": '#!/bin/sh\nffmpeg -map "[v]" -map "[a]" video/final-clean.mp4\n',
    }.items():
        path = run_dir / relative
        path.write_text(text, encoding="utf-8")
    for relative in (
        "production/fact-evidence.json",
        "production/script-review.json",
        "production/shot-selection.json",
        "production/footage-ledger.json",
    ):
        write_json(run_dir / relative, {"run_id": manifest.run_id, "recorded": True})
    write_json(
        run_dir / "production/timeline.json",
        {
            "run_id": manifest.run_id,
            "audio_duration_seconds": 52.128,
            "segments": [
                {"type": "anchor", "start": 0, "end": 6.5, "script_segment_id": "s1"},
                {
                    "type": "broll",
                    "start": 6.5,
                    "end": 11.5,
                    "script_segment_id": "s2",
                    "shot_id": "shot-1",
                },
                {"type": "anchor", "start": 11.5, "end": 52.128, "script_segment_id": "s3"},
            ],
        },
    )
    write_json(
        run_dir / "qc/ffprobe.json",
        {
            "streams": [
                {
                    "codec_type": "video",
                    "codec_name": "h264",
                    "width": 1080,
                    "height": 1920,
                    "r_frame_rate": "25/1",
                    "duration": "52.160",
                },
                {
                    "codec_type": "audio",
                    "codec_name": "aac",
                    "sample_rate": "48000",
                    "channels": 1,
                    "duration": "52.128",
                },
            ],
            "format": {"duration": "52.160"},
        },
    )
    (run_dir / "qc/blackdetect.log").write_text("", encoding="utf-8")
    (run_dir / "qc/silencedetect.log").write_text(
        "silence_start: 51.855 | silence_end: 52.138 | silence_duration: 0.283\n",
        encoding="utf-8",
    )
    (run_dir / "qc/decode-errors.log").write_text("", encoding="utf-8")
    write_json(
        run_dir / "qc/audio-comparison.json",
        {
            "best_lag_ms": 0.0,
            "normalized_correlation": 0.999995,
            "final_samples": 2502144,
            "master_samples": 2502144,
        },
    )
    return run_dir


def add_director_review(run_dir: Path, approved: bool = True):
    checks = [
        {
            "id": check_id,
            "description": check_id,
            "passed": approved,
            "evidence_path": "qc/contact-sheet.jpg",
        }
        for check_id in sorted(REQUIRED_DIRECTOR_CHECK_IDS)
    ]
    write_json(
        run_dir / "qc/director-review.json",
        {
            "run_id": run_dir.name,
            "approved": approved,
            "checks": checks,
            "reviewed_at": NOW.isoformat(),
            "actor": "director",
        },
    )
    for name in ("contact-sheet.jpg", "boundary-contact.jpg", "tail-contact.jpg"):
        (run_dir / "qc" / name).write_bytes(b"image")


def test_automatic_qc_builds_evidence_rich_report_and_advances_status(tmp_path):
    run_dir = prepared_run(tmp_path)
    report = build_automatic_qc_report(run_dir)
    assert report.overall_passed is False
    assert not [item for item in report.checks if item.status == "FAIL"]
    ids = {item.id for item in report.checks}
    assert {"streams", "video_spec", "audio_spec", "duration", "audio_integrity"} <= ids
    manifest = NewsRunManifest.model_validate_json(
        (run_dir / "production/run-manifest.json").read_text(encoding="utf-8")
    )
    assert manifest.status is NewsRunStatus.AUTOMATIC_QC_PASSED
    assert (run_dir / "qc/final-qc-report.json").exists()
    assert (run_dir / "qc/sha256.txt").read_text(encoding="utf-8").strip()


def test_automatic_qc_marks_changes_required_for_stream_black_silence_and_audio_failures(tmp_path):
    run_dir = prepared_run(tmp_path)
    probe = json.loads((run_dir / "qc/ffprobe.json").read_text(encoding="utf-8"))
    probe["streams"].append(dict(probe["streams"][0]))
    write_json(run_dir / "qc/ffprobe.json", probe)
    (run_dir / "qc/blackdetect.log").write_text("black_start:0 black_end:1\n", encoding="utf-8")
    (run_dir / "qc/silencedetect.log").write_text(
        "silence_start: 10 | silence_end: 12 | silence_duration: 2\n", encoding="utf-8"
    )
    write_json(
        run_dir / "qc/audio-comparison.json",
        {
            "best_lag_ms": 120,
            "normalized_correlation": 0.8,
            "final_samples": 1,
            "master_samples": 2,
        },
    )
    report = build_automatic_qc_report(run_dir)
    failed_ids = {item.id for item in report.checks if item.status == "FAIL"}
    assert {"streams", "no_black_frames", "no_long_silence", "audio_integrity"} <= failed_ids
    manifest = NewsRunManifest.model_validate_json(
        (run_dir / "production/run-manifest.json").read_text(encoding="utf-8")
    )
    assert manifest.status is NewsRunStatus.CHANGES_REQUIRED


def test_director_review_and_complete_deliverables_are_required(tmp_path):
    run_dir = prepared_run(tmp_path)
    build_automatic_qc_report(run_dir)
    add_director_review(run_dir)
    report = apply_director_review(run_dir)
    assert report.overall_passed is True
    assert report.director_review and report.director_review.approved
    manifest = NewsRunManifest.model_validate_json(
        (run_dir / "production/run-manifest.json").read_text(encoding="utf-8")
    )
    assert manifest.status is NewsRunStatus.READY_TO_DELIVER


def test_missing_director_evidence_or_deliverable_blocks_delivery(tmp_path):
    run_dir = prepared_run(tmp_path)
    build_automatic_qc_report(run_dir)
    add_director_review(run_dir)
    (run_dir / "qc/tail-contact.jpg").unlink()
    with pytest.raises(ValueError, match="tail-contact"):
        apply_director_review(run_dir)

    (run_dir / "qc/tail-contact.jpg").write_bytes(b"image")
    (run_dir / "copy/title.txt").unlink()
    with pytest.raises(ValueError, match="title"):
        apply_director_review(run_dir)
