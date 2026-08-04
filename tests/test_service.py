from datetime import date

import pytest

from avatar_pipeline.models import TaskStatus, TopicCandidate
from avatar_pipeline.repository import DailyTaskRepository
from avatar_pipeline.service import DailyWorkflowService, WorkflowPreconditionError


def candidates():
    return [
        TopicCandidate(id="t1", title="工作受挫后", pillar="career_pressure", score=94),
        TopicCandidate(
            id="t2", title="父母先稳住情绪", pillar="parent_child_communication", score=91
        ),
        TopicCandidate(id="t3", title="停止自我否定", pillar="self_growth", score=89),
    ]


def test_three_manual_approvals_are_recorded(tmp_path):
    service = DailyWorkflowService(DailyTaskRepository(tmp_path))
    day = date(2026, 8, 4)
    service.start_day(day)
    service.record_research(day, candidates())
    service.approve_topic(day, "t1", actor="owner")
    service.record_script(day, "工作不顺时，先别急着否定自己。")
    service.approve_script(day, actor="owner")
    service.mark_audio_ready(day, artifact_path="audio/main.wav")
    service.mark_assets_generating(day)
    service.mark_compositing(day)
    service.record_qc(day, passed=True, report_path="qc/report.json")
    task = service.approve_video(day, actor="owner")

    assert task.status == TaskStatus.VIDEO_APPROVED
    assert [approval.gate for approval in task.approvals] == ["topic", "script", "video"]


def test_topic_must_be_one_of_top_three(tmp_path):
    service = DailyWorkflowService(DailyTaskRepository(tmp_path))
    day = date(2026, 8, 4)
    service.start_day(day)
    service.record_research(day, candidates())
    with pytest.raises(WorkflowPreconditionError, match="not in Top 3"):
        service.approve_topic(day, "unknown", actor="owner")
