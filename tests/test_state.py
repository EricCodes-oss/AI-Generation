import pytest

from avatar_pipeline.models import TaskStatus
from avatar_pipeline.state import InvalidTransitionError, approval_gate_for, ensure_transition


def test_news_workflow_transitions_cover_manual_gates():
    ensure_transition(TaskStatus.INPUT_RECEIVED, TaskStatus.RESEARCHING)
    ensure_transition(TaskStatus.RESEARCHING, TaskStatus.FACT_SCREENED)
    ensure_transition(TaskStatus.FACT_SCREENED, TaskStatus.TOPIC_SCRIPT_REVIEW)
    ensure_transition(TaskStatus.TOPIC_SCRIPT_REVIEW, TaskStatus.MEDIA_PLANNING)
    ensure_transition(TaskStatus.MEDIA_PLANNING, TaskStatus.HOST_REVIEW)
    ensure_transition(TaskStatus.HOST_REVIEW, TaskStatus.GENERATING_TTS)
    ensure_transition(TaskStatus.QUALITY_CHECK, TaskStatus.FINAL_REVIEW)
    ensure_transition(TaskStatus.FINAL_REVIEW, TaskStatus.READY_TO_PUBLISH)


def test_managed_workflow_can_skip_user_review_states():
    ensure_transition(TaskStatus.FACT_SCREENED, TaskStatus.MEDIA_PLANNING)
    ensure_transition(TaskStatus.MEDIA_PLANNING, TaskStatus.GENERATING_TTS)
    ensure_transition(TaskStatus.QUALITY_CHECK, TaskStatus.READY_TO_PUBLISH)


def test_unsafe_skip_is_rejected():
    with pytest.raises(InvalidTransitionError, match="fact_screened -> generating_tts"):
        ensure_transition(TaskStatus.FACT_SCREENED, TaskStatus.GENERATING_TTS)


def test_gate_names_are_only_the_three_user_facing_gates():
    assert approval_gate_for(TaskStatus.TOPIC_SCRIPT_REVIEW) == "topic_script"
    assert approval_gate_for(TaskStatus.HOST_REVIEW) == "host"
    assert approval_gate_for(TaskStatus.FINAL_REVIEW) == "final_video"
    assert approval_gate_for(TaskStatus.MEDIA_PLANNING) is None
