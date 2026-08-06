"""Build one reusable master-video publication package for all platforms."""

from pydantic import BaseModel, ConfigDict, Field

from avatar_pipeline.media import _has_explicit_ai_generation_disclosure
from avatar_pipeline.models import (
    DailyTask,
    FactStatus,
    MediaKind,
    SourceEvidence,
    TaskStatus,
)

_REQUIRED_PLATFORMS = ("douyin", "wechat_channels", "xiaohongshu")


class PlatformPackage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    master_video_path: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)
    source_note: str = Field(min_length=1)
    ai_demo_note: str | None = None


class AIDisclosureRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    segment_id: str = Field(min_length=1)
    disclosure: str = Field(min_length=1)


class PublicationPackage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    master_video_path: str = Field(min_length=1)
    source_record_paths: list[str] = Field(min_length=1)
    sources: list[SourceEvidence] = Field(min_length=2)
    ai_disclosures: list[AIDisclosureRecord] = Field(default_factory=list)
    platforms: dict[str, PlatformPackage]


def _master_video_path(task: DailyTask) -> str:
    master_index = next(
        (
            index
            for index in range(len(task.artifacts) - 1, -1, -1)
            if task.artifacts[index].kind == "master_video" and task.artifacts[index].path.strip()
        ),
        None,
    )
    if master_index is None:
        raise ValueError("master video artifact is required")

    qc_index = next(
        (
            index
            for index in range(len(task.artifacts) - 1, -1, -1)
            if task.artifacts[index].kind == "qc_report"
        ),
        None,
    )
    if (
        qc_index is None
        or qc_index < master_index
        or task.artifacts[qc_index].metadata.get("passed") is not True
    ):
        raise ValueError("latest master video requires a final passed QC report")
    return task.artifacts[master_index].path


def _source_metadata(task: DailyTask) -> tuple[list[str], list[SourceEvidence]]:
    source_record_paths = [
        item.path for item in task.artifacts if item.kind == "source_record" and item.path.strip()
    ]
    if not source_record_paths:
        raise ValueError("source record artifact is required")

    selected = next(
        (candidate for candidate in task.candidates if candidate.id == task.selected_topic_id),
        None,
    )
    if (
        selected is None
        or selected.fact_status is not FactStatus.VERIFIED
        or not selected.publishable
        or not selected.verification_summary
    ):
        raise ValueError("complete verified source metadata is required")

    source_ids = {
        source.source_id.strip() for source in selected.source_evidence if source.source_id.strip()
    }
    if len(source_ids) < 2:
        raise ValueError(
            "complete source metadata requires at least two distinct verified source IDs"
        )
    if task.news_script is None or not task.news_script.source_ids:
        raise ValueError("complete verified source metadata is required")
    script_source_ids = {source_id.strip() for source_id in task.news_script.source_ids}
    if "" in script_source_ids or not script_source_ids.issubset(source_ids):
        raise ValueError("script source metadata is incomplete")
    for segment in task.news_script.spoken_segments:
        segment_source_ids = {source_id.strip() for source_id in segment.source_ids}
        if segment.kind == "fact" and not segment_source_ids:
            raise ValueError(f"fact segment {segment.id} requires a verified source")
        if "" in segment_source_ids or not segment_source_ids.issubset(source_ids):
            raise ValueError(f"script segment {segment.id} contains unverified source metadata")
    return source_record_paths, selected.source_evidence


def _media_disclosures(task: DailyTask, source_ids: set[str]) -> list[AIDisclosureRecord]:
    if task.media_plan is None:
        raise ValueError("media plan is required")

    disclosures: list[AIDisclosureRecord] = []
    for segment in task.media_plan.segments:
        if segment.kind is MediaKind.ORIGINAL_NEWS:
            if not segment.source_id or segment.source_id not in source_ids:
                raise ValueError("original news source metadata is incomplete")
            if not segment.provenance or not segment.provenance.strip():
                raise ValueError("original news provenance is required")
        elif segment.kind is MediaKind.AI_DEMO:
            if not _has_explicit_ai_generation_disclosure(segment.disclosure):
                raise ValueError("AI disclosure is required for AI demo media")
            disclosures.append(
                AIDisclosureRecord(
                    segment_id=segment.id,
                    disclosure=segment.disclosure,
                )
            )

    script_requires_disclosure = bool(
        task.news_script is not None and task.news_script.ai_disclosure_required
    )
    if bool(disclosures) != script_requires_disclosure:
        raise ValueError("AI disclosure records must match the news script")
    return disclosures


def build_publication_package(task: DailyTask) -> PublicationPackage:
    """Validate publication records and prepare three wrappers around one master video."""

    if task.status is not TaskStatus.READY_TO_PUBLISH:
        raise ValueError("task must be ready_to_publish")
    if set(task.platforms) != set(_REQUIRED_PLATFORMS):
        raise ValueError("publication requires douyin, wechat_channels, and xiaohongshu")

    master = _master_video_path(task)
    source_record_paths, sources = _source_metadata(task)
    disclosures = _media_disclosures(task, {source.source_id for source in sources})
    source_note = "来源：" + "；".join(f"{item.platform}《{item.title}》" for item in sources)
    ai_note = "；".join(item.disclosure for item in disclosures) or None
    packages = {
        platform: PlatformPackage(
            master_video_path=master,
            title=task.news_script.title,
            description="固定演播室坐播主持人解读，穿插经核验的竖屏新闻画面。",
            tags=["热点解读", "新闻观察", "理性表达"],
            source_note=source_note,
            ai_demo_note=ai_note,
        )
        for platform in _REQUIRED_PLATFORMS
    }
    return PublicationPackage(
        master_video_path=master,
        source_record_paths=source_record_paths,
        sources=sources,
        ai_disclosures=disclosures,
        platforms=packages,
    )
