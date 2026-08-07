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


def candidate(topic_id="t1", score=94, *, verified=True):
    return TopicCandidate(
        id=topic_id,
        title="已核实热点",
        pillar="social_phenomena",
        score=score,
        fact_status=FactStatus.VERIFIED if verified else FactStatus.PENDING,
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
        verification_summary="两个独立来源确认核心事实" if verified else None,
        publishable=verified,
    )


def script_and_plan(host_id):
    script = NewsScript(
        title="热点解读",
        spoken_segments=[ScriptSegment(id="seg1", kind="fact", text="事实内容", source_ids=["s1"])],
        source_ids=["s1", "s2"],
    )
    plan = MediaPlan(
        duration_seconds=10,
        host_id=host_id,
        segments=[
            MediaSegment(
                id="a1",
                kind=MediaKind.ANCHOR,
                start_seconds=0,
                end_seconds=3,
                script_segment_id="seg1",
                host_id=host_id,
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
                host_id=host_id,
            ),
        ],
    )
    return script, plan


def fixed_host(host_id="h1"):
    return HostProfile(
        id=host_id,
        display_name="林知遥",
        reference_image="host.png",
        is_new=False,
    )


def stage_manual_script_review(service, day, *, host=None):
    task = service.start_day(day, mode=RunMode.MANUAL)
    task.host_profile = host or fixed_host()
    task.avatar_source = AvatarSource.SAVED_HOST
    service.repository.save(task)
    service.record_research(day, [candidate("t1", 94), candidate("t2", 90), candidate("t3", 85)])
    service.approve_hotspot(day, topic_id="t1", actor="owner")
    script, plan = script_and_plan(task.host_profile.id)
    return service.record_script_and_media_plan(day, "t1", script, plan)


def test_manual_mode_has_exactly_hotspot_script_and_final_gates(tmp_path):
    service = DailyWorkflowService(DailyTaskRepository(tmp_path))
    day = date(2026, 8, 7)
    staged = stage_manual_script_review(service, day)
    assert staged.status is TaskStatus.SCRIPT_REVIEW

    approved = service.approve_script(day, actor="owner")
    assert approved.status is TaskStatus.GENERATING_TTS

    service.mark_tts_ready(day, artifact_path="audio/main.wav")
    service.mark_anchor_ready(day, artifact_path="video/anchor.mp4")
    service.mark_media_ready(day, artifact_path="media/insert.mp4")
    service.mark_compositing(day, artifact_path="video/master.mp4")
    service.record_qc(day, passed=True, report_path="qc/report.json")
    task = service.approve_final_video(day, actor="owner")

    assert task.status is TaskStatus.READY_TO_PUBLISH
    assert [approval.gate for approval in task.approvals] == [
        "hotspot",
        "script",
        "final_video",
    ]


def test_manual_research_keeps_only_top_three_verified_candidates(tmp_path):
    service = DailyWorkflowService(DailyTaskRepository(tmp_path))
    day = date(2026, 8, 7)
    service.start_day(day, mode=RunMode.MANUAL)
    result = service.record_research(
        day,
        [
            candidate("fourth", 70),
            candidate("first", 99),
            candidate("third", 80),
            candidate("second", 90),
            candidate("pending", 100, verified=False),
        ],
    )

    assert result.status is TaskStatus.HOTSPOT_REVIEW
    assert [item.id for item in result.candidates] == ["first", "second", "third"]
    assert {item.id for item in result.skipped_candidates} == {"fourth", "pending"}


def test_unverified_candidates_stop_before_any_confirmation(tmp_path):
    service = DailyWorkflowService(DailyTaskRepository(tmp_path))
    day = date(2026, 8, 7)
    service.start_day(day)
    result = service.record_research(day, [candidate("pending", 99, verified=False)])

    assert result.status is TaskStatus.STOPPED
    assert result.stop_reason == "no verified hotspot"


def test_manual_script_must_match_approved_hotspot(tmp_path):
    service = DailyWorkflowService(DailyTaskRepository(tmp_path))
    day = date(2026, 8, 7)
    task = service.start_day(day)
    task.host_profile = fixed_host()
    service.repository.save(task)
    service.record_research(day, [candidate("t1", 90), candidate("t2", 80)])
    service.approve_hotspot(day, topic_id="t1", actor="owner")
    script, plan = script_and_plan("h1")

    with pytest.raises(WorkflowPreconditionError, match="approved hotspot"):
        service.record_script_and_media_plan(day, "t2", script, plan)


def test_user_host_is_used_without_adding_an_extra_confirmation_gate(tmp_path):
    service = DailyWorkflowService(DailyTaskRepository(tmp_path))
    day = date(2026, 8, 7)
    user_host = HostProfile(
        id="user-host",
        display_name="用户主持人",
        reference_image="uploaded.png",
        is_new=True,
    )
    staged = stage_manual_script_review(service, day, host=user_host)

    approved = service.approve_script(day, actor="owner")

    assert staged.status is TaskStatus.SCRIPT_REVIEW
    assert approved.status is TaskStatus.GENERATING_TTS
    assert approved.host_profile is not None
    assert approved.host_profile.is_new is False
    assert [record.gate for record in approved.approvals] == ["hotspot", "script"]


def test_managed_mode_runs_without_user_approval_records(tmp_path):
    service = DailyWorkflowService(DailyTaskRepository(tmp_path))
    day = date(2026, 8, 7)
    service.start_day(day, mode=RunMode.MANAGED)
    researched = service.record_research(day, [candidate()])
    assert researched.status is TaskStatus.SCRIPTING
    script, plan = script_and_plan("h1")
    planned = service.record_script_and_media_plan(day, "t1", script, plan)
    assert planned.status is TaskStatus.MEDIA_PLANNING
    generated = service.set_host(
        day,
        fixed_host(),
        avatar_source=AvatarSource.SAVED_HOST,
    )
    assert generated.status is TaskStatus.GENERATING_TTS
    assert generated.approvals == []


def test_record_script_rejects_media_plan_for_existing_different_host(tmp_path):
    service = DailyWorkflowService(DailyTaskRepository(tmp_path))
    day = date(2026, 8, 7)
    service.start_day(day, mode=RunMode.MANAGED)
    service.record_research(day, [candidate()])
    task = service.get(day)
    task.host_profile = fixed_host("actual-host")
    service.repository.save(task)
    script, plan = script_and_plan("planned-host")

    with pytest.raises(WorkflowPreconditionError, match="media plan host_id must match"):
        service.record_script_and_media_plan(day, "t1", script, plan)


def test_set_host_rejects_host_that_does_not_match_media_plan(tmp_path):
    service = DailyWorkflowService(DailyTaskRepository(tmp_path))
    day = date(2026, 8, 7)
    service.start_day(day, mode=RunMode.MANAGED)
    service.record_research(day, [candidate()])
    script, plan = script_and_plan("planned-host")
    service.record_script_and_media_plan(day, "t1", script, plan)

    with pytest.raises(WorkflowPreconditionError, match="media plan host_id must match"):
        service.set_host(day, fixed_host("different-host"))
