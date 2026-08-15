"""Stage gates and version-safe workspace operations for V5 news runs."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import tempfile
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from avatar_pipeline.hotspot_selection import TopicSelectionApproval
from avatar_pipeline.news_production_models import (
    FactEvidence,
    FootageLedger,
    NewsRunManifest,
    NewsRunStatus,
    NewsTimeline,
    ProgramTranscript,
    ScriptReview,
    ShotSelection,
)
from avatar_pipeline.news_quality_config import (
    NewsVideoQualityConfig,
    load_news_quality_config,
)

T = TypeVar("T", bound=BaseModel)


class NewsProductionGateError(ValueError):
    """Raised when a hard V5 production requirement is not satisfied."""

    def __init__(self, stage: str, failures: list[str]) -> None:
        self.stage = stage
        self.failures = failures
        super().__init__(f"{stage} preflight failed: {', '.join(failures)}")


@dataclass(frozen=True)
class BrollGuidance:
    selection_mode: str
    count_fixed: bool
    minimum_count: int
    maximum_count: int
    minimum_clip_seconds: float
    preferred_clip_seconds: float
    maximum_clip_seconds: float
    minimum_ratio: float
    maximum_ratio: float
    prefer_coherent_blocks: bool
    avoid_frequent_short_cuts: bool

    @property
    def recommended_count(self) -> int | None:
        """Do not turn a broad editorial range into a fixed insert quota."""

        return None if not self.count_fixed else self.minimum_count


@dataclass(frozen=True)
class StageValidationResult:
    stage: str
    status: NewsRunStatus
    hard_failures: list[str]
    advisories: list[str]


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_json(path: Path, model: BaseModel) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            json.dump(model.model_dump(mode="json"), handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            temporary = Path(handle.name)
        temporary.replace(path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(text)
            temporary = Path(handle.name)
        temporary.replace(path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def load_run_record(run_dir: Path, relative_path: str, model_type: type[T]) -> T:
    path = Path(run_dir) / relative_path
    if not path.is_file():
        raise NewsProductionGateError("record", [f"missing:{relative_path}"])
    try:
        return model_type.model_validate_json(path.read_text(encoding="utf-8"))
    except (ValidationError, ValueError) as error:
        raise NewsProductionGateError("record", [f"invalid:{relative_path}:{error}"]) from error


def save_manifest(run_dir: Path, manifest: NewsRunManifest) -> None:
    manifest.updated_at = _utc_now()
    _write_json(Path(run_dir) / "production/run-manifest.json", manifest)


def initialize_news_run(
    output_root: Path,
    *,
    day: date,
    slug: str,
    topic: str,
    version: int,
    quality_config_path: Path,
    parent_run_id: str | None = None,
    topic_selection_path: Path | None = None,
) -> Path:
    """Create one immutable-version run directory and its locked manifest."""

    if version < 1:
        raise ValueError("version must be at least 1")
    safe_slug = slug.strip().replace(" ", "-")
    if not safe_slug or not re.fullmatch(r"[\w\-\u4e00-\u9fff]+", safe_slug):
        raise ValueError(
            "slug must contain only letters, numbers, CJK characters, underscores, or hyphens"
        )
    config_path = Path(quality_config_path)
    config = load_news_quality_config(config_path)
    selection = None
    if topic_selection_path is not None:
        selection_path = Path(topic_selection_path)
        selection = TopicSelectionApproval.model_validate_json(
            selection_path.read_text(encoding="utf-8")
        )
        if not selection.approved:
            raise ValueError("topic selection must be approved")
        if selection.day != day:
            raise ValueError("topic selection date does not match run date")
        if selection.title != topic:
            raise ValueError("topic selection title does not match run topic")
    run_id = f"manual-news-{day.isoformat()}-{safe_slug}-v{version:02d}"
    run_dir = Path(output_root) / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    try:
        for name in ("video", "audio", "copy", "production", "qc"):
            (run_dir / name).mkdir()
        shutil.copy2(config_path, run_dir / "production/quality-profile.yaml")
        manifest = NewsRunManifest(
            run_id=run_id,
            quality_profile=config.profile.id,
            quality_profile_version=config.profile.version,
            topic=topic,
            topic_selection_id=selection.candidate_id if selection else None,
            target_duration_seconds=60,
            host_id=config.host.id,
            host_reference_image=config.host.reference_image,
            host_sha256=config.host.sha256,
            voice_id=config.voice.voice_id,
            clean_master=True,
            status=NewsRunStatus.INITIALIZED,
            parent_run_id=parent_run_id,
            final_video_path="video/final-clean.mp4",
            created_at=_utc_now(),
        )
        _write_json(run_dir / "production/run-manifest.json", manifest)
        if topic_selection_path is not None:
            shutil.copy2(topic_selection_path, run_dir / "production/topic-selection.json")
    except Exception:
        shutil.rmtree(run_dir)
        raise
    return run_dir


def recommend_broll(duration_seconds: float, config: NewsVideoQualityConfig) -> BrollGuidance:
    """Return broad director guidance, never a duration-derived insert quota."""

    minimum = config.profile.min_duration_seconds
    maximum = config.profile.max_duration_seconds
    if not minimum <= duration_seconds <= maximum:
        raise ValueError("V5 duration must stay within 45-90 seconds")
    broll = config.broll
    return BrollGuidance(
        selection_mode=broll.selection_mode,
        count_fixed=broll.count_fixed,
        minimum_count=broll.guidance_min_count,
        maximum_count=broll.guidance_max_count,
        minimum_clip_seconds=broll.min_clip_seconds,
        preferred_clip_seconds=broll.preferred_clip_seconds,
        maximum_clip_seconds=broll.max_clip_seconds,
        minimum_ratio=broll.target_ratio_min,
        maximum_ratio=broll.target_ratio_max,
        prefer_coherent_blocks=broll.prefer_coherent_blocks,
        avoid_frequent_short_cuts=broll.avoid_frequent_short_cuts,
    )


def _load_context(run_dir: Path) -> tuple[NewsRunManifest, NewsVideoQualityConfig]:
    manifest = load_run_record(run_dir, "production/run-manifest.json", NewsRunManifest)
    config = load_news_quality_config(Path(run_dir) / "production/quality-profile.yaml")
    return manifest, config


def _require_same_run(run_id: str, *records: BaseModel) -> list[str]:
    failures = []
    for record in records:
        if getattr(record, "run_id", None) != run_id:
            failures.append(f"run_id:{record.__class__.__name__}")
    return failures


def _format_timestamp(seconds: float) -> str:
    total_milliseconds = round(seconds * 1000)
    minutes, remainder = divmod(total_milliseconds, 60_000)
    whole_seconds, milliseconds = divmod(remainder, 1000)
    return f"{minutes:02d}:{whole_seconds:02d}.{milliseconds:03d}"


def render_full_program_transcript(run_dir: Path) -> str:
    """Render every audible programme segment, including approved source dialogue."""

    run_dir = Path(run_dir)
    manifest = load_run_record(run_dir, "production/run-manifest.json", NewsRunManifest)
    timeline = load_run_record(run_dir, "production/timeline.json", NewsTimeline)
    transcript = load_run_record(
        run_dir, "production/program-transcript.json", ProgramTranscript
    )
    failures = _require_same_run(manifest.run_id, timeline, transcript)
    if not transcript.director_approved:
        failures.append("director_approval")

    if len(transcript.segments) != len(timeline.segments):
        failures.append("segment_coverage")
    else:
        for index, (timeline_segment, transcript_segment) in enumerate(
            zip(timeline.segments, transcript.segments, strict=True), start=1
        ):
            if transcript_segment.script_segment_id != timeline_segment.script_segment_id:
                failures.append(f"segment_id:{index}")
            if transcript_segment.visual_type != timeline_segment.type:
                failures.append(f"visual_type:{index}")
            if abs(transcript_segment.start - timeline_segment.start) > 0.01:
                failures.append(f"segment_start:{index}")
            if abs(transcript_segment.end - timeline_segment.end) > 0.01:
                failures.append(f"segment_end:{index}")
    if failures:
        raise NewsProductionGateError("program_transcript", failures)

    title_path = run_dir / transcript.title_path
    if not title_path.is_file() or not title_path.read_text(encoding="utf-8").strip():
        raise NewsProductionGateError("program_transcript", ["title:missing_or_empty"])
    title = title_path.read_text(encoding="utf-8").strip().splitlines()[0].strip()
    if not (title.startswith("《") and title.endswith("》")):
        title = f"《{title}》"

    blocks = [title]
    for segment in transcript.segments:
        role = "主持人口播" if segment.audio_role == "presenter" else "现场原声"
        heading = (
            f"【{_format_timestamp(segment.start)}—{_format_timestamp(segment.end)}｜{role}】"
        )
        lines = [f"{line.speaker}：{line.text}" for line in segment.lines]
        blocks.append("\n".join([heading, *lines]))
    return "\n\n".join(blocks) + "\n"


def build_full_program_transcript(run_dir: Path) -> Path:
    """Generate the canonical complete programme transcript as a delivery artifact."""

    run_dir = Path(run_dir)
    record = load_run_record(
        run_dir, "production/program-transcript.json", ProgramTranscript
    )
    output_path = run_dir / record.output_path
    _write_text(output_path, render_full_program_transcript(run_dir))
    return output_path


def validate_full_program_transcript(run_dir: Path) -> None:
    """Reject missing, incomplete, or stale programme transcript deliverables."""

    run_dir = Path(run_dir)
    record = load_run_record(
        run_dir, "production/program-transcript.json", ProgramTranscript
    )
    output_path = run_dir / record.output_path
    if not output_path.is_file() or output_path.stat().st_size == 0:
        raise NewsProductionGateError("program_transcript", ["output:missing_or_empty"])
    expected = render_full_program_transcript(run_dir)
    if output_path.read_text(encoding="utf-8") != expected:
        raise NewsProductionGateError("program_transcript", ["output:stale_or_incomplete"])


def validate_generation_preflight(run_dir: Path, project_root: Path) -> StageValidationResult:
    """Validate facts, copy, voice, and the actual locked host before generation."""

    run_dir = Path(run_dir)
    manifest, config = _load_context(run_dir)
    failures: list[str] = []
    if manifest.quality_profile != config.profile.id:
        failures.append("quality_profile")
    if manifest.host_id != config.host.id:
        failures.append("host_id")
    if manifest.host_reference_image != config.host.reference_image:
        failures.append("host_reference_image")
    if manifest.host_sha256 != config.host.sha256:
        failures.append("host_sha256:manifest")
    host_path = Path(project_root) / config.host.reference_image
    if not host_path.is_file():
        failures.append("host_reference_image:missing")
    elif _sha256(host_path) != config.host.sha256:
        failures.append("host_sha256:actual")
    if manifest.voice_id != config.voice.voice_id:
        failures.append("voice_id")

    try:
        facts = load_run_record(run_dir, "production/fact-evidence.json", FactEvidence)
        review = load_run_record(run_dir, "production/script-review.json", ScriptReview)
        failures.extend(_require_same_run(manifest.run_id, facts, review))
        if not review.director_approved:
            failures.append("script_review:director_approval")
        for label, relative_path in (
            ("voiceover", review.script_path),
            ("title", review.title_path),
            ("master_audio", "audio/master-voiceover.wav"),
        ):
            path = run_dir / relative_path
            if not path.is_file() or path.stat().st_size == 0:
                failures.append(f"{label}:missing_or_empty")
    except NewsProductionGateError as error:
        failures.extend(error.failures)

    if failures:
        raise NewsProductionGateError("generation", failures)
    manifest.status = NewsRunStatus.GENERATION_READY
    save_manifest(run_dir, manifest)
    return StageValidationResult("generation", manifest.status, [], [])


def validate_timeline_preflight(run_dir: Path) -> StageValidationResult:
    """Join footage, shot, and timeline records and enforce V5 structural rules."""

    run_dir = Path(run_dir)
    manifest, config = _load_context(run_dir)
    failures: list[str] = []
    advisories: list[str] = []
    if manifest.status not in {NewsRunStatus.GENERATION_READY, NewsRunStatus.TIMELINE_READY}:
        failures.append(f"status:{manifest.status.value}")
    try:
        ledger = load_run_record(run_dir, "production/footage-ledger.json", FootageLedger)
        selection = load_run_record(run_dir, "production/shot-selection.json", ShotSelection)
        timeline = load_run_record(run_dir, "production/timeline.json", NewsTimeline)
        failures.extend(_require_same_run(manifest.run_id, ledger, selection, timeline))
    except NewsProductionGateError as error:
        raise NewsProductionGateError("timeline", error.failures) from error

    assets = {item.asset_id: item for item in ledger.assets}
    shots = {item.shot_id: item for item in selection.shots}
    for asset in ledger.assets:
        if not asset.user_usage_rule_passed:
            failures.append(f"asset_usage_rule:{asset.asset_id}")
        asset_path = run_dir / asset.local_path
        if not asset_path.is_file():
            failures.append(f"asset_missing:{asset.asset_id}")
        elif _sha256(asset_path) != asset.sha256:
            failures.append(f"asset_sha256:{asset.asset_id}")
    for shot in selection.shots:
        if shot.asset_id not in assets:
            failures.append(f"unknown_asset:{shot.asset_id}")
        if not shot.director_approved:
            failures.append(f"shot_approval:{shot.shot_id}")
    broll_segments = [item for item in timeline.segments if item.type == "broll"]
    for segment in broll_segments:
        shot = shots.get(segment.shot_id or "")
        if shot is None:
            failures.append(f"unknown_shot:{segment.shot_id}")
            continue
        if shot.script_segment_id != segment.script_segment_id:
            failures.append(f"semantic_mapping:{shot.shot_id}")
        if abs((segment.end - segment.start) - shot.target_duration_seconds) > 0.01:
            failures.append(f"shot_duration:{shot.shot_id}")
    tail = timeline.segments[-1].end - timeline.segments[-1].start
    required_tail = timeline.audio_duration_seconds * config.ending.min_anchor_ratio
    if tail + 0.01 < required_tail:
        failures.append(f"anchor_tail:{tail:.3f}<{required_tail:.3f}")

    guidance = recommend_broll(timeline.audio_duration_seconds, config)
    broll_total = sum(item.end - item.start for item in broll_segments)
    ratio = broll_total / timeline.audio_duration_seconds
    if not guidance.minimum_count <= len(broll_segments) <= guidance.maximum_count:
        advisories.append(f"broll_count:{len(broll_segments)}")
    for segment in broll_segments:
        duration = segment.end - segment.start
        if not guidance.minimum_clip_seconds <= duration <= guidance.maximum_clip_seconds:
            advisories.append(f"broll_duration:{duration:.3f}")
    if not guidance.minimum_ratio <= ratio <= guidance.maximum_ratio:
        advisories.append(f"broll_ratio:{ratio:.4f}")

    if failures:
        raise NewsProductionGateError("timeline", failures)
    manifest.status = NewsRunStatus.TIMELINE_READY
    save_manifest(run_dir, manifest)
    return StageValidationResult("timeline", manifest.status, [], advisories)


def validate_render_preflight(run_dir: Path) -> StageValidationResult:
    """Reject unsafe filters, source-audio maps, missing inputs, and output overwrite."""

    run_dir = Path(run_dir)
    manifest, _ = _load_context(run_dir)
    failures: list[str] = []
    if manifest.status not in {NewsRunStatus.TIMELINE_READY, NewsRunStatus.RENDER_READY}:
        failures.append(f"status:{manifest.status.value}")
    script_path = run_dir / "production/render.sh"
    if not script_path.is_file() or script_path.stat().st_size == 0:
        failures.append("render_script:missing_or_empty")
        text = ""
    else:
        text = script_path.read_text(encoding="utf-8")
    lowered = text.casefold()
    forbidden_patterns = {
        "reverse": r"\breverse\b",
        "loop": r"(?:\bloop\b|stream_loop)",
        "pingpong": r"ping[-_ ]?pong|pingpong",
    }
    for label, pattern in forbidden_patterns.items():
        if re.search(pattern, lowered):
            failures.append(f"forbidden_filter:{label}")
    input_paths = re.findall(r"(?:^|\s)-i\s+[\"']?([^\"'\s]+)", text)
    for match in re.finditer(r"-map\s+[\"']?(?P<index>[0-9]+):a", text):
        index = int(match.group("index"))
        input_path = input_paths[index] if index < len(input_paths) else ""
        if not input_path.endswith("/audio/master-voiceover.wav"):
            failures.append("source_audio_map")
            break
    for match in re.finditer(r"\[(?P<index>[0-9]+):a(?::[0-9]+)?\]", text):
        index = int(match.group("index"))
        input_path = input_paths[index] if index < len(input_paths) else ""
        if not input_path.endswith("/audio/master-voiceover.wav"):
            failures.append("source_audio_filter")
            break
    for relative in re.findall(r"\$ROOT/([^\"'\s]+)", text):
        if relative == (manifest.final_video_path or "video/final-clean.mp4"):
            continue
        if not (run_dir / relative).exists():
            failures.append(f"render_input_missing:{relative}")
    final_path = run_dir / (manifest.final_video_path or "video/final-clean.mp4")
    if final_path.exists():
        failures.append("overwrite:final_video_exists")
    if failures:
        raise NewsProductionGateError("render", failures)
    manifest.status = NewsRunStatus.RENDER_READY
    save_manifest(run_dir, manifest)
    return StageValidationResult("render", manifest.status, [], [])


def mark_rendered(run_dir: Path) -> NewsRunManifest:
    """Record a successful render without claiming that QC has passed."""

    run_dir = Path(run_dir)
    manifest, _ = _load_context(run_dir)
    failures = []
    if manifest.status is not NewsRunStatus.RENDER_READY:
        failures.append(f"status:{manifest.status.value}")
    final_path = run_dir / (manifest.final_video_path or "video/final-clean.mp4")
    if not final_path.is_file() or final_path.stat().st_size == 0:
        failures.append("final_video:missing_or_empty")
    if failures:
        raise NewsProductionGateError("mark_rendered", failures)
    manifest.status = NewsRunStatus.RENDERED_PENDING_QC
    manifest.final_video_sha256 = _sha256(final_path)
    save_manifest(run_dir, manifest)
    return manifest
