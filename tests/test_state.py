import pytest

from avatar_pipeline.models import TaskStatus
from avatar_pipeline.state import InvalidTransitionError, approval_gate_for, ensure_transition


def test_happy_path_transitions_are_allowed():
    ensure_transition(TaskStatus.RESEARCHED, TaskStatus.TOPIC_APPROVED)
    ensure_transition(TaskStatus.SCRIPT_DRAFT, TaskStatus.SCRIPT_APPROVED)
    ensure_transition(TaskStatus.QC_PASSED, TaskStatus.VIDEO_APPROVED)


def test_skipping_script_approval_is_rejected():
    with pytest.raises(InvalidTransitionError, match="script_draft -> audio_ready"):
        ensure_transition(TaskStatus.SCRIPT_DRAFT, TaskStatus.AUDIO_READY)


def test_manual_gate_names_are_explicit():
    assert approval_gate_for(TaskStatus.TOPIC_APPROVED) == "topic"
    assert approval_gate_for(TaskStatus.SCRIPT_APPROVED) == "script"
    assert approval_gate_for(TaskStatus.VIDEO_APPROVED) == "video"
