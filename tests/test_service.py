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


def test_manual_new_host_stays_in_review_when_updated(tmp_path):
    service = DailyWorkflowService(DailyTaskRepository(tmp_path))
    day = date(2026, 8, 6)
    service.start_day(day, mode=RunMode.MANUAL)
    service.record_research(day, [candidate()])
    script, plan = script_and_plan()
    service.record_script_and_media_plan(day, "t1", script, plan)
    service.approve_topic_script(day, actor="owner")
    service.set_host(
        day,
        HostProfile(id="h1", display_name="林知遥", reference_image="host-v1.png", is_new=True),
    )

    updated = service.set_host(
        day,
        HostProfile(id="h1", display_name="林知遥", reference_image="host-v1.png", is_new=True),
    )

    assert updated.status is TaskStatus.HOST_REVIEW
    assert updated.requires_host_approval is True


def test_manual_changed_host_requires_host_review(tmp_path):
    service = DailyWorkflowService(DailyTaskRepository(tmp_path))
    day = date(2026, 8, 6)
    service.start_day(day, mode=RunMode.MANUAL)
    service.record_research(day, [candidate()])
    script, plan = script_and_plan()
    service.record_script_and_media_plan(day, "t1", script, plan)
    service.approve_topic_script(day, actor="owner")
    service.set_host(
        day,
        HostProfile(id="h1", display_name="林知遥", reference_image="host-v1.png", is_new=True),
    )

    changed = service.set_host(
        day,
        HostProfile(id="h1", display_name="林知遥", reference_image="host-v2.png", is_new=False),
    )

    assert changed.status is TaskStatus.HOST_REVIEW
    assert changed.requires_host_approval is True


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


def stage_manual_host_selection(service, day):
    service.start_day(day, mode=RunMode.MANUAL)
    service.record_research(day, [candidate()])
    script, plan = script_and_plan()
    service.record_script_and_media_plan(day, "t1", script, plan)
    service.approve_topic_script(day, actor="owner")


@pytest.mark.parametrize(
    "avatar_source",
    [AvatarSource.USER_PROVIDED, AvatarSource.AGENT_DESIGNED],
)
def test_manual_new_source_requires_host_review_even_when_marked_not_new(tmp_path, avatar_source):
    service = DailyWorkflowService(DailyTaskRepository(tmp_path))
    day = date(2026, 8, 6)
    stage_manual_host_selection(service, day)

    task = service.set_host(
        day,
        HostProfile(
            id="h1",
            display_name="林知遥",
            reference_image="host.png",
            is_new=False,
        ),
        avatar_source=avatar_source,
    )

    assert task.status is TaskStatus.HOST_REVIEW
    assert task.avatar_source is avatar_source
    assert task.host_profile is not None
    assert task.host_profile.is_new is True
    assert task.requires_host_approval is True


def test_manual_saved_host_marked_not_new_is_the_only_direct_reuse_path(tmp_path):
    service = DailyWorkflowService(DailyTaskRepository(tmp_path))
    day = date(2026, 8, 6)
    stage_manual_host_selection(service, day)

    task = service.set_host(
        day,
        HostProfile(
            id="saved",
            display_name="林知遥",
            reference_image="saved.png",
            is_new=False,
        ),
        avatar_source=AvatarSource.SAVED_HOST,
    )

    assert task.status is TaskStatus.GENERATING_TTS
    assert task.requires_host_approval is False


@pytest.mark.parametrize(
    "changed_host",
    [
        HostProfile(
            id="saved",
            display_name="林知遥",
            reference_image="saved-v2.png",
            is_new=False,
        ),
        HostProfile(
            id="saved",
            display_name="林知遥",
            reference_image="saved.png",
            version=2,
            is_new=False,
        ),
        HostProfile(
            id="different-identity",
            display_name="另一位主持人",
            reference_image="saved.png",
            is_new=False,
        ),
    ],
    ids=["reference", "version", "identity"],
)
def test_manual_changed_saved_host_requires_review(tmp_path, changed_host):
    service = DailyWorkflowService(DailyTaskRepository(tmp_path))
    day = date(2026, 8, 6)
    stage_manual_host_selection(service, day)
    task = service.get(day)
    task.host_profile = HostProfile(
        id="saved",
        display_name="林知遥",
        reference_image="saved.png",
        is_new=False,
    )
    task.avatar_source = AvatarSource.SAVED_HOST
    service.repository.save(task)

    changed = service.set_host(
        day,
        changed_host,
        avatar_source=AvatarSource.SAVED_HOST,
    )

    assert changed.status is TaskStatus.HOST_REVIEW
    assert changed.host_profile is not None
    assert changed.host_profile.is_new is True
    assert changed.requires_host_approval is True
