from datetime import date

import pytest
from pydantic import ValidationError

from avatar_pipeline.models import DailyTask, TaskStatus, TopicCandidate


def test_daily_task_accepts_exactly_three_ranked_candidates():
    candidates = [
        TopicCandidate(
            id=f"topic-{index}", title=f"候选 {index}", pillar="self_growth", score=90 - index
        )
        for index in range(1, 4)
    ]
    task = DailyTask(day=date(2026, 8, 4), status=TaskStatus.RESEARCHED, candidates=candidates)
    assert len(task.candidates) == 3


def test_daily_task_rejects_duplicate_candidate_ids():
    candidates = [
        TopicCandidate(id="same", title="A", pillar="self_growth", score=90),
        TopicCandidate(id="same", title="B", pillar="career_pressure", score=89),
        TopicCandidate(
            id="third", title="C", pillar="parent_child_communication", score=88
        ),
    ]
    with pytest.raises(ValidationError, match="candidate ids must be unique"):
        DailyTask(day=date(2026, 8, 4), status=TaskStatus.RESEARCHED, candidates=candidates)


def test_retirement_care_is_not_a_valid_v1_pillar():
    with pytest.raises(ValidationError):
        TopicCandidate(id="bad", title="养老", pillar="eldercare", score=90)
