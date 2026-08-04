"""Explicit workflow state transitions and approval gates."""

from avatar_pipeline.models import TaskStatus


class InvalidTransitionError(ValueError):
    """Raised when a workflow attempts to skip a required state."""


_TRANSITIONS: dict[TaskStatus, frozenset[TaskStatus]] = {
    TaskStatus.CREATED: frozenset({TaskStatus.RESEARCHED}),
    TaskStatus.RESEARCHED: frozenset({TaskStatus.TOPIC_APPROVED}),
    TaskStatus.TOPIC_APPROVED: frozenset({TaskStatus.SCRIPT_DRAFT}),
    TaskStatus.SCRIPT_DRAFT: frozenset({TaskStatus.SCRIPT_APPROVED}),
    TaskStatus.SCRIPT_APPROVED: frozenset({TaskStatus.AUDIO_READY}),
    TaskStatus.AUDIO_READY: frozenset({TaskStatus.ASSETS_GENERATING}),
    TaskStatus.ASSETS_GENERATING: frozenset({TaskStatus.COMPOSITING}),
    TaskStatus.COMPOSITING: frozenset({TaskStatus.QC_FAILED, TaskStatus.QC_PASSED}),
    TaskStatus.QC_FAILED: frozenset({TaskStatus.ASSETS_GENERATING, TaskStatus.COMPOSITING}),
    TaskStatus.QC_PASSED: frozenset({TaskStatus.VIDEO_APPROVED}),
    TaskStatus.VIDEO_APPROVED: frozenset({TaskStatus.PUBLISHED}),
    TaskStatus.PUBLISHED: frozenset({TaskStatus.ANALYZED}),
    TaskStatus.ANALYZED: frozenset(),
}

_APPROVAL_GATES: dict[TaskStatus, str] = {
    TaskStatus.TOPIC_APPROVED: "topic",
    TaskStatus.SCRIPT_APPROVED: "script",
    TaskStatus.VIDEO_APPROVED: "video",
}


def allowed_targets(status: TaskStatus) -> frozenset[TaskStatus]:
    """Return legal next states."""

    return _TRANSITIONS[status]


def ensure_transition(current: TaskStatus, target: TaskStatus) -> None:
    """Raise if target is not a legal immediate successor of current."""

    if target not in allowed_targets(current):
        raise InvalidTransitionError(f"invalid transition: {current.value} -> {target.value}")


def approval_gate_for(target: TaskStatus) -> str | None:
    """Return the manual approval gate represented by a target status."""

    return _APPROVAL_GATES.get(target)
