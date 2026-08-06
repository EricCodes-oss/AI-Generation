import json
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from avatar_pipeline.models import ContentPillarSlug
from avatar_pipeline.research_adapters import CollectionBatch, RawCollectionItem
from avatar_pipeline.research_models import (
    CommentInsightCard,
    CommentSampleType,
    ConfidenceLevel,
    DailyResearchPlan,
    ImplicitNeed,
    QueryGroup,
    ResearchPlatform,
    ResearchReviewAction,
    ResearchRunStatus,
    TimeWindow,
)
from avatar_pipeline.research_repository import ResearchRunRepository
from avatar_pipeline.research_service import ResearchService, ResearchWorkflowError

DAY = date(2026, 8, 4)
NOW = datetime(2026, 8, 4, 1, 0, tzinfo=UTC)
PILLARS = tuple(ContentPillarSlug)


def make_plan() -> DailyResearchPlan:
    groups = [
        QueryGroup(
            id=f"q-{index}",
            pillar=PILLARS[index // 3],
            intent=f"intent-{index}",
            scene=f"scene-{index}",
            natural_query=f"natural-query-{index}",
            platform_expressions={ResearchPlatform.XIAOHONGSHU: [f"query-{index}"]},
            time_window=TimeWindow.LAST_72_HOURS,
        )
        for index in range(9)
    ]
    return DailyResearchPlan(
        day=DAY,
        core_groups=groups,
        time_window_shares={
            TimeWindow.LAST_72_HOURS: 0.5,
            TimeWindow.LAST_7_DAYS: 0.35,
            TimeWindow.LAST_30_DAYS: 0.15,
        },
        created_at=NOW,
    )


def make_batch(tmp_path: Path, count: int = 30, a_grade_count: int = 5) -> CollectionBatch:
    raw_path = tmp_path / "fixture-source.json"
    raw_path.write_text('{"fixture": true}', encoding="utf-8")
    platforms = (
        ResearchPlatform.DOUYIN,
        ResearchPlatform.WECHAT_CHANNELS,
        ResearchPlatform.XIAOHONGSHU,
    )
    return CollectionBatch(
        raw_items=[
            RawCollectionItem(
                platform=platforms[index % len(platforms)],
                query_group_id=f"q-{index % 9}",
                payload={
                    "title": f"热点来源 {index}",
                    "url": f"https://example.com/{index}",
                    "content_id": f"content-{index}",
                    "grade": "A" if index < a_grade_count else "B",
                    "published_at": "2026-08-04T08:00:00+08:00",
                    "likes": index * 100,
                },
                raw_artifact_path=str(raw_path),
            )
            for index in range(count)
        ],
        collector_name="fixture",
        started_at=NOW,
        completed_at=NOW,
        raw_artifact_paths=[str(raw_path)],
    )


def make_cards(source_ids: list[str]) -> list[CommentInsightCard]:
    return [
        CommentInsightCard(
            source_id=source_id,
            sample_count=20,
            sample_type_counts={sample_type: 4 for sample_type in CommentSampleType},
            scenes=["下班后仍在回复消息"],
            emotions=["疲惫"],
            inner_conflicts=["想休息又怕落后"],
            explicit_questions=["怎样停止内耗"],
            implicit_needs=[ImplicitNeed.BEING_SEEN],
            disagreement_signals=["少数人认为应先改变工作方式"],
            representative_paraphrases=["停下来时反而更不安"],
            comment_refs=[f"{source_id}-comment-{index}" for index in range(20)],
            privacy_notes=["已匿名化"],
            confidence=ConfidenceLevel.HIGH,
            created_at=NOW,
        )
        for source_id in source_ids
    ]


def prepare_ready_run(service: ResearchService, tmp_path: Path, *, count=30, a_count=5):
    service.start(DAY)
    service.record_plan(DAY, make_plan())
    collected = service.import_collection(DAY, make_batch(tmp_path, count, a_count))
    a_ids = [source.id for source in collected.sources if source.grade.value == "A"]
    service.record_insights(DAY, make_cards(a_ids))
    service.render_report(DAY)
    return service.status(DAY)


def test_legal_progression_report_gate_approval_and_save_resume(tmp_path):
    repo = ResearchRunRepository(tmp_path)
    service = ResearchService(repo)

    started = service.start(DAY)
    assert started.status is ResearchRunStatus.DRAFT
    with pytest.raises(ResearchWorkflowError, match="ready_for_review"):
        service.approve(DAY, actor="用户")

    planned = service.record_plan(DAY, make_plan())
    assert planned.status is ResearchRunStatus.COLLECTING
    collected = service.import_collection(DAY, make_batch(tmp_path))
    assert collected.status is ResearchRunStatus.COLLECTING
    assert len(collected.sources) == 30

    a_ids = [source.id for source in collected.sources if source.grade.value == "A"]
    ready = service.record_insights(DAY, make_cards(a_ids))
    assert ready.status is ResearchRunStatus.READY_FOR_REVIEW
    assert ready.summary.valid_source_count == 30
    assert ready.summary.insight_card_count == 5

    with pytest.raises(ResearchWorkflowError, match="rendered report"):
        service.approve(DAY, actor="用户")

    report_path = service.render_report(DAY)
    assert report_path.is_file()
    assert "每日热点内容检索报告" in report_path.read_text(encoding="utf-8")

    approved = service.approve(DAY, actor="用户")
    assert approved.status is ResearchRunStatus.APPROVED
    assert approved.review_action is ResearchReviewAction.APPROVE
    assert approved.approvals[-1].actor == "用户"
    assert approved.approvals[-1].accepted_gaps == []
    revision_path = tmp_path / "days" / DAY.isoformat() / "research/revisions/revision-1.json"
    assert revision_path.is_file()

    resumed = ResearchService(ResearchRunRepository(tmp_path)).status(DAY)
    assert resumed.status is ResearchRunStatus.APPROVED
    payload = resumed.model_dump()
    assert "topic_candidates" not in payload
    assert "candidates" not in payload
    assert "script_text" not in payload


def test_actor_is_required_and_shortfalls_need_explicit_accepted_gaps(tmp_path):
    service = ResearchService(ResearchRunRepository(tmp_path))
    ready = prepare_ready_run(service, tmp_path, count=3, a_count=1)
    assert ready.is_approvable() is False

    with pytest.raises(ValueError, match="actor"):
        service.approve(DAY, actor="   ", accepted_gaps=["样本量不足"])
    with pytest.raises(ResearchWorkflowError, match="accepted gaps"):
        service.approve(DAY, actor="用户")

    approved = service.approve(
        DAY,
        actor="用户",
        accepted_gaps=["当前仅 3 条夹具来源，用于离线流程验收", "仅 1 张评论洞察卡"],
    )
    assert approved.status is ResearchRunStatus.APPROVED
    assert approved.approvals[-1].accepted_gaps == [
        "当前仅 3 条夹具来源，用于离线流程验收",
        "仅 1 张评论洞察卡",
    ]


@pytest.mark.parametrize(
    "action, feedback",
    [
        (ResearchReviewAction.SUPPLEMENT_PLATFORM, "补充视频号来源"),
        (ResearchReviewAction.SUPPLEMENT_TOPIC, "补充职场被否定话题"),
        (ResearchReviewAction.RECOLLECT_COMMENTS, "重新采集 source-1 评论"),
    ],
)
def test_revision_actions_create_new_revision_without_overwriting_approved_snapshot(
    tmp_path, action, feedback
):
    repo = ResearchRunRepository(tmp_path)
    service = ResearchService(repo)
    prepare_ready_run(service, tmp_path, count=3, a_count=1)
    service.approve(DAY, actor="用户", accepted_gaps=["离线验收样本量不足"])
    approved_path = tmp_path / "days" / DAY.isoformat() / "research/revisions/revision-1.json"
    approved_payload = approved_path.read_text(encoding="utf-8")

    revised = service.request_revision(DAY, feedback=feedback, action=action)

    assert revised.status is ResearchRunStatus.REVISION_REQUESTED
    assert revised.revision == 2
    assert revised.parent_revision == 1
    assert revised.review_action is action
    assert revised.review_feedback == feedback
    assert revised.report_artifact_path is None
    assert approved_path.read_text(encoding="utf-8") == approved_payload
    assert json.loads(approved_payload)["status"] == "approved"


def test_redo_hold_and_return_actions_are_explicit(tmp_path):
    service = ResearchService(ResearchRunRepository(tmp_path))
    prepare_ready_run(service, tmp_path, count=3, a_count=1)

    held = service.request_revision(DAY, feedback="稍后再看", action=ResearchReviewAction.HOLD)
    assert held.status is ResearchRunStatus.HELD

    returned = service.request_revision(
        DAY, feedback="回到检索计划", action=ResearchReviewAction.RETURN
    )
    assert returned.status is ResearchRunStatus.REVISION_REQUESTED

    redone = service.request_revision(DAY, feedback="全部重做", action=ResearchReviewAction.REDO)
    assert redone.status is ResearchRunStatus.DRAFT
    assert redone.plan is None
    assert redone.sources == []
    assert redone.insight_cards == []
