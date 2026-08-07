from datetime import date

import pytest

from avatar_pipeline.models import (
    AvatarSource,
    FactStatus,
    HostProfile,
    MediaKind,
    MediaPlan,
    MediaSegment,
    NewsScript,
    RunMode,
    ScriptSegment,
    SourceEvidence,
    TaskStatus,
    TopicCandidate,
)
from avatar_pipeline.repository import DailyTaskRepository
from avatar_pipeline.service import DailyWorkflowService, WorkflowPreconditionError


def candidate(topic_id: str, score: float) -> TopicCandidate:
    return TopicCandidate(
        id=topic_id,
        title=f"热点 {topic_id}",
        pillar="social_phenomena",
        score=score,
        fact_status=FactStatus.VERIFIED,
        source_evidence=[
            SourceEvidence(
                source_id=f"{topic_id}-trend",
                platform="douyin",
                title="平台热度来源",
                url_or_reference=f"https://example.test/{topic_id}/trend",
                evidence_type="other",
            ),
            SourceEvidence(
                source_id=f"{topic_id}-official",
                platform="official",
                title="事实核验来源",
                url_or_reference=f"https://example.test/{topic_id}/official",
                evidence_type="official",
            ),
        ],
        trend_evidence=["点赞 120000", "评论 8300"],
        verification_summary="热点和核心事实均已核验",
        publishable=True,
    )


def script_and_plan(host_id: str) -> tuple[NewsScript, MediaPlan]:
    script = NewsScript(
        title="热点解读",
        spoken_segments=[
            ScriptSegment(
                id="seg1",
                kind="fact",
                text="这里是已经核验的事实内容。",
                source_ids=["t2-official"],
            )
        ],
        source_ids=["t2-official"],
    )
    plan = MediaPlan(
        duration_seconds=10,
        host_id=host_id,
        segments=[
            MediaSegment(
                id="anchor-1",
                kind=MediaKind.ANCHOR,
                start_seconds=0,
                end_seconds=3,
                script_segment_id="seg1",
                host_id=host_id,
            ),
            MediaSegment(
                id="insert-1",
                kind=MediaKind.AI_DEMO,
                start_seconds=3,
                end_seconds=7,
                script_segment_id="seg1",
                disclosure="AI生成示意画面",
            ),
            MediaSegment(
                id="anchor-2",
                kind=MediaKind.ANCHOR,
                start_seconds=7,
                end_seconds=10,
                script_segment_id="seg1",
                host_id=host_id,
            ),
        ],
    )
    return script, plan


def test_manual_mode_pauses_for_hotspot_then_script_then_final_video(tmp_path):
    service = DailyWorkflowService(DailyTaskRepository(tmp_path))
    day = date(2026, 8, 7)
    task = service.start_day(day, mode=RunMode.MANUAL)
    task.host_profile = HostProfile(
        id="fixed-host",
        display_name="林知遥",
        reference_image="host.png",
        is_new=False,
    )
    task.avatar_source = AvatarSource.SAVED_HOST
    service.repository.save(task)

    researched = service.record_research(
        day,
        [candidate("t1", 90), candidate("t2", 95), candidate("t3", 85)],
    )
    assert researched.status is TaskStatus.HOTSPOT_REVIEW
    assert [item.id for item in researched.candidates] == ["t2", "t1", "t3"]
    assert researched.selected_topic_id is None

    selected = service.approve_hotspot(day, topic_id="t2", actor="owner")
    assert selected.status is TaskStatus.SCRIPTING
    assert selected.selected_topic_id == "t2"
    assert [item.gate for item in selected.approvals] == ["hotspot"]

    script, plan = script_and_plan("fixed-host")
    scripted = service.record_script_and_media_plan(day, "t2", script, plan)
    assert scripted.status is TaskStatus.SCRIPT_REVIEW

    approved = service.approve_script(day, actor="owner")
    assert approved.status is TaskStatus.GENERATING_TTS
    assert [item.gate for item in approved.approvals] == ["hotspot", "script"]

    service.mark_tts_ready(day, artifact_path="audio/main.mp3")
    service.mark_anchor_ready(day, artifact_path="video/anchor.mp4")
    service.mark_media_ready(day, artifact_path="video/insert.mp4")
    service.mark_compositing(day, artifact_path="video/master.mp4")
    reviewed = service.record_qc(day, passed=True, report_path="qc/report.json")
    assert reviewed.status is TaskStatus.FINAL_REVIEW

    completed = service.approve_final_video(day, actor="owner")
    assert completed.status is TaskStatus.READY_TO_PUBLISH
    assert [item.gate for item in completed.approvals] == ["hotspot", "script", "final_video"]


def test_manual_mode_cannot_write_script_before_hotspot_selection(tmp_path):
    service = DailyWorkflowService(DailyTaskRepository(tmp_path))
    day = date(2026, 8, 7)
    service.start_day(day, mode=RunMode.MANUAL)
    service.record_research(day, [candidate("t1", 90), candidate("t2", 80), candidate("t3", 70)])
    script, plan = script_and_plan("fixed-host")

    with pytest.raises(WorkflowPreconditionError, match="expected scripting"):
        service.record_script_and_media_plan(day, "t1", script, plan)


def test_manual_mode_cannot_generate_media_before_script_approval(tmp_path):
    service = DailyWorkflowService(DailyTaskRepository(tmp_path))
    day = date(2026, 8, 7)
    task = service.start_day(day, mode=RunMode.MANUAL)
    task.host_profile = HostProfile(
        id="fixed-host",
        display_name="林知遥",
        reference_image="host.png",
        is_new=False,
    )
    service.repository.save(task)
    service.record_research(day, [candidate("t1", 90), candidate("t2", 80), candidate("t3", 70)])
    service.approve_hotspot(day, topic_id="t1", actor="owner")
    script, plan = script_and_plan("fixed-host")
    service.record_script_and_media_plan(day, "t1", script, plan)

    with pytest.raises(WorkflowPreconditionError, match="expected generating_tts"):
        service.mark_tts_ready(day, artifact_path="audio/main.mp3")
