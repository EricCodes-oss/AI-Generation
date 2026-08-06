from datetime import UTC, date, datetime

import pytest

from avatar_pipeline.models import (
    ArtifactRecord,
    DailyTask,
    FactStatus,
    MediaKind,
    MediaPlan,
    MediaSegment,
    NewsScript,
    ScriptSegment,
    SourceEvidence,
    TaskStatus,
    TopicCandidate,
)
from avatar_pipeline.publication import build_publication_package


def source(source_id: str, platform: str) -> SourceEvidence:
    return SourceEvidence(
        source_id=source_id,
        platform=platform,
        title=f"{platform}来源",
        url_or_reference=f"https://example.test/{source_id}",
        evidence_type="official" if platform == "official" else "reputable_media",
        published_at=datetime(2026, 8, 6, 1, tzinfo=UTC),
        reliability_note="已核对核心事实",
    )


def ready_task(*, use_ai_demo: bool = False, ai_disclosure: str | None = None) -> DailyTask:
    sources = [source("s1", "official"), source("s2", "media")]
    candidate = TopicCandidate(
        id="topic-1",
        title="已核实热点",
        pillar="social_phenomena",
        score=95,
        fact_status=FactStatus.VERIFIED,
        source_evidence=sources,
        verification_summary="官方信息与独立媒体交叉核验",
        publishable=True,
    )
    insert = MediaSegment(
        id="insert-1",
        kind=MediaKind.AI_DEMO if use_ai_demo else MediaKind.ORIGINAL_NEWS,
        start_seconds=3,
        end_seconds=7,
        script_segment_id="seg-1",
        source_id=None if use_ai_demo else "s1",
        provenance=None if use_ai_demo else "官方公开视频片段",
        disclosure=ai_disclosure,
        asset_path="media/insert.mp4",
    )
    return DailyTask(
        day=date(2026, 8, 6),
        status=TaskStatus.READY_TO_PUBLISH,
        candidates=[candidate],
        selected_topic_id=candidate.id,
        news_script=NewsScript(
            title="热点解读",
            spoken_segments=[
                ScriptSegment(id="seg-1", kind="fact", text="事实内容", source_ids=["s1"])
            ],
            source_ids=["s1", "s2"],
            ai_disclosure_required=use_ai_demo,
        ),
        media_plan=MediaPlan(
            duration_seconds=10,
            host_id="fixed-seated-anchor",
            segments=[
                MediaSegment(
                    id="anchor-1",
                    kind=MediaKind.ANCHOR,
                    start_seconds=0,
                    end_seconds=3,
                    script_segment_id="seg-1",
                ),
                insert,
                MediaSegment(
                    id="anchor-2",
                    kind=MediaKind.ANCHOR,
                    start_seconds=7,
                    end_seconds=10,
                    script_segment_id="seg-1",
                ),
            ],
        ),
        artifacts=[
            ArtifactRecord(kind="master_video", path="video/master.mp4"),
            ArtifactRecord(kind="qc_report", path="qc/passed.json", metadata={"passed": True}),
            ArtifactRecord(kind="source_record", path="audit/sources.json"),
        ],
    )


def test_publication_package_reuses_one_master_for_three_platforms():
    package = build_publication_package(ready_task())
    assert package.master_video_path == "video/master.mp4"
    assert set(package.platforms) == {"douyin", "wechat_channels", "xiaohongshu"}
    assert {item.master_video_path for item in package.platforms.values()} == {"video/master.mp4"}


def test_publication_uses_latest_master_after_qc_retry():
    task = ready_task()
    task.artifacts = [
        ArtifactRecord(kind="master_video", path="video/failed.mp4"),
        ArtifactRecord(kind="qc_report", path="qc/failed.json", metadata={"passed": False}),
        ArtifactRecord(kind="master_video", path="video/final.mp4"),
        ArtifactRecord(kind="qc_report", path="qc/passed.json", metadata={"passed": True}),
        ArtifactRecord(kind="source_record", path="audit/sources.json"),
    ]

    package = build_publication_package(task)

    assert package.master_video_path == "video/final.mp4"


def test_publication_refuses_master_without_final_passed_qc():
    task = ready_task()
    task.artifacts = [
        ArtifactRecord(kind="master_video", path="video/master.mp4"),
        ArtifactRecord(kind="qc_report", path="qc/failed.json", metadata={"passed": False}),
        ArtifactRecord(kind="source_record", path="audit/sources.json"),
    ]

    with pytest.raises(ValueError, match="passed QC"):
        build_publication_package(task)


def test_publication_package_contains_structured_source_metadata():
    package = build_publication_package(ready_task())
    assert package.source_record_paths == ["audit/sources.json"]
    assert {item.source_id for item in package.sources} == {"s1", "s2"}
    assert {item.platform for item in package.sources} == {"official", "media"}
    assert all(item.source_note for item in package.platforms.values())


def test_publication_package_contains_ai_disclosure_metadata_when_ai_demo_is_used():
    task = ready_task(use_ai_demo=True, ai_disclosure="AI生成示意画面，非新闻现场实拍")
    package = build_publication_package(task)
    assert [item.segment_id for item in package.ai_disclosures] == ["insert-1"]
    assert package.ai_disclosures[0].disclosure == "AI生成示意画面，非新闻现场实拍"
    assert all(item.ai_demo_note for item in package.platforms.values())


def test_unfinished_task_cannot_be_packaged():
    with pytest.raises(ValueError, match="ready_to_publish"):
        build_publication_package(DailyTask(day=date(2026, 8, 6)))


def test_publication_refuses_missing_source_record_artifact():
    task = ready_task()
    task.artifacts = [item for item in task.artifacts if item.kind != "source_record"]
    with pytest.raises(ValueError, match="source record"):
        build_publication_package(task)


def test_publication_refuses_incomplete_verified_source_metadata():
    task = ready_task()
    task.candidates[0].source_evidence = task.candidates[0].source_evidence[:1]
    with pytest.raises(ValueError, match="source metadata"):
        build_publication_package(task)


def test_publication_refuses_duplicate_source_evidence():
    task = ready_task()
    task.candidates[0].source_evidence[1] = source("s1", "media")

    with pytest.raises(ValueError, match="distinct"):
        build_publication_package(task)


def test_publication_refuses_unknown_spoken_segment_source():
    task = ready_task()
    task.news_script.spoken_segments[0].source_ids = ["unknown-source"]

    with pytest.raises(ValueError, match="script segment"):
        build_publication_package(task)


def test_publication_refuses_fact_segment_without_source():
    task = ready_task()
    task.news_script.spoken_segments[0].source_ids = []

    with pytest.raises(ValueError, match="fact segment"):
        build_publication_package(task)


def test_publication_refuses_original_news_without_provenance():
    task = ready_task()
    task.media_plan.segments[1].provenance = None
    with pytest.raises(ValueError, match="provenance"):
        build_publication_package(task)


def test_publication_accepts_explicit_chinese_ai_generation_disclosure():
    task = ready_task(use_ai_demo=True, ai_disclosure="人工智能生成示意画面，非新闻现场实拍")

    package = build_publication_package(task)

    assert package.ai_disclosures[0].disclosure.startswith("人工智能生成")


def test_publication_refuses_vague_ai_label_without_generation_disclosure():
    task = ready_task(use_ai_demo=True, ai_disclosure="AI相关素材")

    with pytest.raises(ValueError, match="AI disclosure"):
        build_publication_package(task)


def test_publication_refuses_script_required_ai_disclosure_without_ai_record():
    task = ready_task()
    task.news_script.ai_disclosure_required = True

    with pytest.raises(ValueError, match="AI disclosure"):
        build_publication_package(task)


def test_publication_refuses_ai_demo_without_explicit_disclosure():
    task = ready_task(use_ai_demo=True)
    with pytest.raises(ValueError, match="AI disclosure"):
        build_publication_package(task)


@pytest.mark.parametrize(
    "disclosure",
    [
        "本画面并非AI生成，为新闻现场实拍",
        "不是AI生成画面",
        "非人工智能生成画面",
        "not AI-generated footage",
        "not generated by AI",
        "non-AI-generated archival footage",
    ],
)
def test_publication_refuses_negated_ai_disclosure(disclosure):
    task = ready_task(use_ai_demo=True, ai_disclosure=disclosure)

    with pytest.raises(ValueError, match="AI disclosure"):
        build_publication_package(task)
