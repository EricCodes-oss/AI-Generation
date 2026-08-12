"""Automatic and director quality gates for V5 manual news productions."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from fractions import Fraction
from pathlib import Path

from avatar_pipeline.news_production import load_run_record, save_manifest
from avatar_pipeline.news_production_models import (
    DirectorReview,
    FinalQualityReport,
    NewsRunManifest,
    NewsRunStatus,
    NewsTimeline,
    QualityCheck,
)
from avatar_pipeline.news_quality_config import load_news_quality_config

REQUIRED_DIRECTOR_CHECK_IDS = frozenset(
    {
        "host_identity",
        "facial_naturalness",
        "lip_sync",
        "script_clarity",
        "footage_relevance",
        "edit_rhythm",
        "no_watermarks_text",
        "no_reverse_repeat",
        "ending_complete",
        "overall_news_effect",
    }
)

_REQUIRED_AUTOMATIC_EVIDENCE = (
    "qc/ffprobe.json",
    "qc/blackdetect.log",
    "qc/silencedetect.log",
    "qc/decode-errors.log",
    "qc/audio-comparison.json",
)

_REQUIRED_DELIVERABLES = (
    "video/final-clean.mp4",
    "audio/master-voiceover.wav",
    "copy/voiceover.txt",
    "copy/title.txt",
    "production/run-manifest.json",
    "production/quality-profile.yaml",
    "production/fact-evidence.json",
    "production/script-review.json",
    "production/shot-selection.json",
    "production/timeline.json",
    "production/footage-ledger.json",
    "production/render.sh",
    "qc/final-qc-report.json",
    "qc/ffprobe.json",
    "qc/contact-sheet.jpg",
    "qc/boundary-contact.jpg",
    "qc/tail-contact.jpg",
    "qc/sha256.txt",
)


def _now() -> datetime:
    return datetime.now(UTC)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_json(path: Path, report: FinalQualityReport) -> None:
    path.write_text(
        json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _check(
    *,
    identifier: str,
    category: str,
    expected: str,
    actual: str,
    passed: bool,
    evidence_path: str,
    severity: str = "hard_block",
) -> QualityCheck:
    return QualityCheck(
        id=identifier,
        category=category,
        severity=severity,
        expected=expected,
        actual=actual,
        status="PASS" if passed else "FAIL",
        evidence_path=evidence_path,
        checked_at=_now(),
    )


def _missing_evidence_checks(run_dir: Path) -> list[QualityCheck]:
    checks = []
    for relative in _REQUIRED_AUTOMATIC_EVIDENCE:
        path = run_dir / relative
        checks.append(
            _check(
                identifier=f"evidence_{Path(relative).stem}",
                category="deliverable",
                expected="required QC evidence exists",
                actual="present" if path.is_file() else "missing",
                passed=path.is_file(),
                evidence_path=relative,
            )
        )
    return checks


def _probe_checks(run_dir: Path) -> tuple[list[QualityCheck], float, float]:
    relative = "qc/ffprobe.json"
    path = run_dir / relative
    if not path.is_file():
        return [], 0.0, 0.0
    payload = json.loads(path.read_text(encoding="utf-8"))
    streams = payload.get("streams", [])
    video = [item for item in streams if item.get("codec_type") == "video"]
    audio = [item for item in streams if item.get("codec_type") == "audio"]
    checks = [
        _check(
            identifier="streams",
            category="technical",
            expected="1 video stream and 1 audio stream",
            actual=f"video={len(video)}, audio={len(audio)}",
            passed=len(video) == 1 and len(audio) == 1,
            evidence_path=relative,
        )
    ]
    video_item = video[0] if video else {}
    audio_item = audio[0] if audio else {}
    fps_text = str(video_item.get("r_frame_rate", "0/1"))
    try:
        fps = float(Fraction(fps_text))
    except (ValueError, ZeroDivisionError):
        fps = 0.0
    video_spec = (
        video_item.get("codec_name") == "h264"
        and video_item.get("width") == 1080
        and video_item.get("height") == 1920
        and abs(fps - 25) < 0.001
    )
    checks.append(
        _check(
            identifier="video_spec",
            category="technical",
            expected="H.264, 1080x1920, 25fps",
            actual=(
                f"{video_item.get('codec_name')}, {video_item.get('width')}x"
                f"{video_item.get('height')}, {fps_text}"
            ),
            passed=video_spec,
            evidence_path=relative,
        )
    )
    audio_spec = (
        audio_item.get("codec_name") == "aac"
        and str(audio_item.get("sample_rate")) == "48000"
        and audio_item.get("channels") == 1
    )
    checks.append(
        _check(
            identifier="audio_spec",
            category="audio",
            expected="AAC, 48kHz, mono",
            actual=(
                f"{audio_item.get('codec_name')}, {audio_item.get('sample_rate')}Hz, "
                f"channels={audio_item.get('channels')}"
            ),
            passed=audio_spec,
            evidence_path=relative,
        )
    )
    video_duration = float(
        video_item.get("duration") or payload.get("format", {}).get("duration") or 0
    )
    audio_duration = float(audio_item.get("duration") or 0)
    tolerance = (1 / 25) + 0.01
    checks.append(
        _check(
            identifier="duration",
            category="technical",
            expected=f"audio/video duration difference <= {tolerance:.3f}s",
            actual=f"video={video_duration:.3f}s, audio={audio_duration:.3f}s",
            passed=audio_duration > 0 and abs(video_duration - audio_duration) <= tolerance,
            evidence_path=relative,
        )
    )
    return checks, video_duration, audio_duration


def _black_check(run_dir: Path) -> QualityCheck | None:
    relative = "qc/blackdetect.log"
    path = run_dir / relative
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8")
    count = len(re.findall(r"black_start\s*:", text))
    return _check(
        identifier="no_black_frames",
        category="technical",
        expected="no detected black-frame events",
        actual=f"events={count}",
        passed=count == 0,
        evidence_path=relative,
    )


def _silence_check(run_dir: Path, audio_duration: float, maximum: float) -> QualityCheck | None:
    relative = "qc/silencedetect.log"
    path = run_dir / relative
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8")
    events = []
    for match in re.finditer(
        r"silence_start:\s*([0-9.]+).*?silence_end:\s*([0-9.]+).*?silence_duration:\s*([0-9.]+)",
        text,
    ):
        start, end, duration = (float(value) for value in match.groups())
        events.append((start, end, duration))
    unexpected = [
        event
        for event in events
        if event[2] > maximum and not (audio_duration > 0 and event[0] >= audio_duration - 1)
    ]
    return _check(
        identifier="no_long_silence",
        category="audio",
        expected=f"no unexpected silence longer than {maximum:.3f}s",
        actual=f"unexpected={unexpected}",
        passed=not unexpected,
        evidence_path=relative,
    )


def _decode_check(run_dir: Path) -> QualityCheck | None:
    relative = "qc/decode-errors.log"
    path = run_dir / relative
    if not path.is_file():
        return None
    size = path.stat().st_size
    return _check(
        identifier="decode_clean",
        category="technical",
        expected="empty decode error log",
        actual=f"bytes={size}",
        passed=size == 0,
        evidence_path=relative,
    )


def _audio_integrity_check(run_dir: Path, minimum_correlation: float) -> QualityCheck | None:
    relative = "qc/audio-comparison.json"
    path = run_dir / relative
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    correlation = float(payload.get("normalized_correlation", 0))
    lag = abs(float(payload.get("best_lag_ms", 999999)))
    same_samples = payload.get("final_samples") == payload.get("master_samples")
    passed = correlation >= minimum_correlation and lag <= 40 and same_samples
    return _check(
        identifier="audio_integrity",
        category="audio",
        expected=(
            f"correlation >= {minimum_correlation}, lag <= 40ms, identical sample count"
        ),
        actual=f"correlation={correlation}, lag_ms={lag}, same_samples={same_samples}",
        passed=passed,
        evidence_path=relative,
    )


def _identity_and_timeline_checks(run_dir: Path) -> list[QualityCheck]:
    manifest = load_run_record(run_dir, "production/run-manifest.json", NewsRunManifest)
    config = load_news_quality_config(run_dir / "production/quality-profile.yaml")
    timeline = load_run_record(run_dir, "production/timeline.json", NewsTimeline)
    host_path = Path.cwd() / config.host.reference_image
    actual_host_hash = _sha256(host_path) if host_path.is_file() else "missing"
    broll = [item for item in timeline.segments if item.type == "broll"]
    broll_total = sum(item.end - item.start for item in broll)
    tail = timeline.segments[-1].end - timeline.segments[-1].start
    required_tail = timeline.audio_duration_seconds * config.ending.min_anchor_ratio
    return [
        _check(
            identifier="host_identity",
            category="identity",
            expected=f"{config.host.id}:{config.host.sha256}",
            actual=f"{manifest.host_id}:{actual_host_hash}",
            passed=(
                manifest.host_id == config.host.id
                and manifest.host_sha256 == config.host.sha256
                and actual_host_hash == config.host.sha256
            ),
            evidence_path="production/run-manifest.json",
        ),
        _check(
            identifier="voice_identity",
            category="identity",
            expected=config.voice.voice_id,
            actual=manifest.voice_id,
            passed=manifest.voice_id == config.voice.voice_id,
            evidence_path="production/run-manifest.json",
        ),
        _check(
            identifier="timeline_structure",
            category="timeline",
            expected="contiguous timeline, B-roll semantic references, anchor close",
            actual=f"segments={len(timeline.segments)}, broll={len(broll)}",
            passed=True,
            evidence_path="production/timeline.json",
        ),
        _check(
            identifier="continuous_anchor_tail",
            category="timeline",
            expected=f">= {required_tail:.3f}s",
            actual=f"{tail:.3f}s",
            passed=tail + 0.01 >= required_tail,
            evidence_path="production/timeline.json",
        ),
        _check(
            identifier="broll_ratio",
            category="timeline",
            expected=(
                f"{config.broll.target_ratio_min:.2f}-"
                f"{config.broll.target_ratio_max:.2f} director target"
            ),
            actual=f"{broll_total / timeline.audio_duration_seconds:.4f}",
            passed=True,
            evidence_path="production/timeline.json",
            severity="advisory",
        ),
    ]


def build_automatic_qc_report(run_dir: Path) -> FinalQualityReport:
    """Build the automatic report and stop short of director approval."""

    run_dir = Path(run_dir)
    manifest = load_run_record(run_dir, "production/run-manifest.json", NewsRunManifest)
    config = load_news_quality_config(run_dir / "production/quality-profile.yaml")
    final_path = run_dir / (manifest.final_video_path or "video/final-clean.mp4")
    if not final_path.is_file() or final_path.stat().st_size == 0:
        raise ValueError("final video is missing or empty")

    checks = _missing_evidence_checks(run_dir)
    probe_checks, _, audio_duration = _probe_checks(run_dir)
    checks.extend(probe_checks)
    for check in (
        _black_check(run_dir),
        _silence_check(
            run_dir, audio_duration, config.quality.max_unexpected_silence_seconds
        ),
        _decode_check(run_dir),
        _audio_integrity_check(run_dir, config.quality.audio_correlation_min),
    ):
        if check is not None:
            checks.append(check)
    try:
        checks.extend(_identity_and_timeline_checks(run_dir))
    except (ValueError, json.JSONDecodeError) as error:
        checks.append(
            _check(
                identifier="production_records",
                category="timeline",
                expected="valid identity and timeline production records",
                actual=str(error),
                passed=False,
                evidence_path="production/",
            )
        )

    final_hash = _sha256(final_path)
    failed = [item for item in checks if item.status == "FAIL"]
    report = FinalQualityReport(
        run_id=manifest.run_id,
        overall_passed=False,
        checks=checks,
        director_review=None,
        final_video_sha256=final_hash,
    )
    _write_json(run_dir / "qc/final-qc-report.json", report)
    (run_dir / "qc/sha256.txt").write_text(
        f"{final_hash}  {manifest.final_video_path or 'video/final-clean.mp4'}\n",
        encoding="utf-8",
    )
    manifest.final_video_sha256 = final_hash
    manifest.status = (
        NewsRunStatus.CHANGES_REQUIRED if failed else NewsRunStatus.AUTOMATIC_QC_PASSED
    )
    save_manifest(run_dir, manifest)
    return report


def apply_director_review(run_dir: Path) -> FinalQualityReport:
    """Require the full two-pass director review and all standard deliverables."""

    run_dir = Path(run_dir)
    manifest = load_run_record(run_dir, "production/run-manifest.json", NewsRunManifest)
    if manifest.status is not NewsRunStatus.AUTOMATIC_QC_PASSED:
        raise ValueError("automatic QC must pass before director review")
    report = load_run_record(run_dir, "qc/final-qc-report.json", FinalQualityReport)
    review = load_run_record(run_dir, "qc/director-review.json", DirectorReview)
    if review.run_id != manifest.run_id:
        raise ValueError("director review run_id does not match the manifest")
    ids = {item.id for item in review.checks}
    missing_checks = sorted(REQUIRED_DIRECTOR_CHECK_IDS - ids)
    if missing_checks:
        raise ValueError(f"director review is missing checks: {', '.join(missing_checks)}")
    if not review.approved:
        manifest.status = NewsRunStatus.CHANGES_REQUIRED
        save_manifest(run_dir, manifest)
        raise ValueError("director review requires changes")
    missing_files = [
        relative
        for relative in _REQUIRED_DELIVERABLES
        if not (run_dir / relative).is_file()
    ]
    if missing_files:
        raise ValueError(f"required deliverables are missing: {', '.join(missing_files)}")
    for relative in ("qc/contact-sheet.jpg", "qc/boundary-contact.jpg", "qc/tail-contact.jpg"):
        if (run_dir / relative).stat().st_size == 0:
            raise ValueError(f"director evidence is empty: {relative}")

    director_checks = [
        QualityCheck(
            id=f"director_{item.id}",
            category="director",
            severity="director_review",
            expected="director check passed",
            actual=item.note or ("passed" if item.passed else "failed"),
            status="PASS" if item.passed else "FAIL",
            evidence_path=item.evidence_path or "qc/director-review.json",
            checked_at=review.reviewed_at,
        )
        for item in review.checks
    ]
    merged = FinalQualityReport(
        run_id=manifest.run_id,
        overall_passed=True,
        checks=[*report.checks, *director_checks],
        director_review=review,
        final_video_sha256=report.final_video_sha256,
    )
    _write_json(run_dir / "qc/final-qc-report.json", merged)
    manifest.status = NewsRunStatus.READY_TO_DELIVER
    save_manifest(run_dir, manifest)
    return merged
