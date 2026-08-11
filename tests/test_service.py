from datetime import date

import pytest

from avatar_pipeline.models import (
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


def candidate(topic_id="t1", score=94):
    return TopicCandidate(
        id=topic_id,
        title="已核实热点",
        pillar="social_phenomena",
        score=score,
        fact_status=FactStatus.VERIFIED,
        source_evidence=[
            SourceEvidence(
                source_id="s1",
                platform="official",
                title="官方",
                url_or_reference="s1",
                evidence_type="primary",
            ),
            SourceEvidence(
                source_id="s2",
                platform="media",
                title="媒体",
                url_or_reference="s2",
                evidence_type="corroboration",
            ),
        ],
        verification_summary="两个独立来源确认核心事实",
        publishable=True,
    )


def _candidate_verified(topic_id: str) -> TopicCandidate:
    return candidate(topic_id=topic_id).model_copy(
        update={"fact_status": FactStatus.VERIFIED, "publishable": True}
    )


def script_and_plan():
    script = NewsScript(
        title="热点解读",
        spoken_segments=[ScriptSegment(id="seg1", kind="fact", text="事实内容", source_ids=["s1"])],
        source_ids=["s1", "s2"],
    )
    plan = MediaPlan(
        duration_seconds=10,
        segments=[
            MediaSegment(
                id="a1",
                kind=MediaKind.ANCHOR,
                start_seconds=0,
                end_seconds=3,
                script_segment_id="seg1",
            ),
            MediaSegment(
                id="d1",
                kind=MediaKind.AI_DEMO,
                start_seconds=3,
                end_seconds=7,
                script_segment_id="seg1",
                disclosure="AI生成示意画面",
            ),
            MediaSegment(
                id="a2",
                kind=MediaKind.ANCHOR,
                start_seconds=7,
                end_seconds=10,
                script_segment_id="seg1",
            ),
        ],
    )
    return script, plan


def test_manual_mode_has_topic_script_host_and_final_gates(tmp_path):
    service = DailyWorkflowService(DailyTaskRepository(tmp_path))
    day = date(2026, 8, 6)
    service.start_day(day, mode=RunMode.MANUAL)
    service.record_research(day, [candidate()])
    script, plan = script_and_plan()
    service.record_script_and_media_plan(day, "t1", script, plan)
    service.approve_topic_script(day, actor="owner")
    service.set_host(
        day, HostProfile(id="h1", display_name="林知遥", reference_image="host.png", is_new=True)
    )
    service.approve_host(day, actor="owner")
    service.mark_tts_ready(day, artifact_path="audio/main.wav")
    service.mark_anchor_ready(day, artifact_path="video/anchor.mp4")
    service.mark_media_ready(day, artifact_path="media/insert.mp4")
    service.mark_compositing(day, artifact_path="video/master.mp4")
    service.record_qc(day, passed=True, report_path="qc/report.json")
    task = service.approve_final_video(day, actor="owner")
    assert task.status == TaskStatus.READY_TO_PUBLISH
    assert [approval.gate for approval in task.approvals] == ["topic_script", "host", "final_video"]


def test_saved_host_skips_host_gate(tmp_path):
    service = DailyWorkflowService(DailyTaskRepository(tmp_path))
    day = date(2026, 8, 6)
    service.start_day(day, mode=RunMode.MANUAL)
    service.record_research(day, [candidate()])
    script, plan = script_and_plan()
    service.record_script_and_media_plan(day, "t1", script, plan)
    service.approve_topic_script(day, actor="owner")
    service.set_host(
        day, HostProfile(id="h1", display_name="林知遥", reference_image="host.png", is_new=False)
    )
    assert service.get(day).status == TaskStatus.GENERATING_TTS


def test_managed_mode_has_no_user_approval_records(tmp_path):
    service = DailyWorkflowService(DailyTaskRepository(tmp_path))
    day = date(2026, 8, 6)
    service.start_day(day, mode=RunMode.MANAGED)
    service.record_research(day, [candidate()])
    script, plan = script_and_plan()
    service.record_script_and_media_plan(day, "t1", script, plan)
    service.set_host(
        day, HostProfile(id="h1", display_name="林知遥", reference_image="host.png", is_new=True)
    )
    assert service.get(day).status == TaskStatus.GENERATING_TTS
    assert service.get(day).approvals == []


def test_unverified_candidate_cannot_be_selected(tmp_path):
    service = DailyWorkflowService(DailyTaskRepository(tmp_path))
    day = date(2026, 8, 6)
    service.start_day(day)
    pending = candidate(topic_id="pending")
    pending = pending.model_copy(update={"fact_status": FactStatus.PENDING, "publishable": False})
    service.record_research(day, [pending])
    with pytest.raises(WorkflowPreconditionError, match="no verified hotspot"):
        service.record_script_and_media_plan(
            day, "pending", script_and_plan()[0], script_and_plan()[1]
        )


def test_service_refreshes_only_unapproved_topic_fields_and_preserves_host(tmp_path):
    service = DailyWorkflowService(DailyTaskRepository(tmp_path))
    day = date(2026, 8, 10)
    service.start_day(day, mode=RunMode.MANUAL)
    service.record_research(day, [candidate("old")])
    host = HostProfile(
        id="host-c2-pro-candidate-2-final",
        display_name="C2-Pro 新闻主持人",
        reference_image=("output/host-v12-c2-pro/GPT-Image-2-Pro-C2-Pro-主持人最终选定.png"),
        studio_reference="蓝色演播室、近景胸像、白衬衣、深藏青西装、无桌、避免手臂入镜",
        visual_style="知性亲和、专业克制、低AI感、五官清晰稳定",
        is_new=False,
        version=12,
    )
    task = service.get(day)
    task.host_profile = host
    service.repository.save(task)
    refreshed = service.refresh_unapproved_hotspots(
        day,
        [_candidate_verified("new")],
        archive_reason="旧候选传播性不足",
        confirmed_host=host,
    )
    assert refreshed.host_profile == host
    assert refreshed.status is TaskStatus.TOPIC_SCRIPT_REVIEW
    assert refreshed.selected_topic_id is None
    assert refreshed.news_script is None
    assert refreshed.media_plan is None
    assert refreshed.approvals == task.approvals
    assert refreshed.artifacts == task.artifacts
