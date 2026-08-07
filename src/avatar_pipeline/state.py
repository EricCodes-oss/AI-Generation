"""Explicit state transitions for managed and manual news production."""

from avatar_pipeline.models import TaskStatus


class InvalidTransitionError(ValueError):
    """Raised when a workflow attempts to skip a required production state."""


_TRANSITIONS: dict[TaskStatus, frozenset[TaskStatus]] = {
    TaskStatus.INPUT_RECEIVED: frozenset({TaskStatus.RESEARCHING}),
    TaskStatus.RESEARCHING: frozenset(
        {TaskStatus.HOTSPOT_REVIEW, TaskStatus.SCRIPTING, TaskStatus.STOPPED}
    ),
    TaskStatus.FACT_SCREENED: frozenset(
        {TaskStatus.HOTSPOT_REVIEW, TaskStatus.SCRIPTING, TaskStatus.STOPPED}
    ),
    TaskStatus.HOTSPOT_REVIEW: frozenset({TaskStatus.SCRIPTING, TaskStatus.STOPPED}),
    TaskStatus.SCRIPTING: frozenset(
        {TaskStatus.SCRIPT_REVIEW, TaskStatus.MEDIA_PLANNING, TaskStatus.STOPPED}
    ),
    TaskStatus.SCRIPT_REVIEW: frozenset({TaskStatus.MEDIA_PLANNING, TaskStatus.STOPPED}),
    TaskStatus.MEDIA_PLANNING: frozenset({TaskStatus.GENERATING_TTS, TaskStatus.STOPPED}),
    TaskStatus.GENERATING_TTS: frozenset({TaskStatus.GENERATING_ANCHOR, TaskStatus.STOPPED}),
    TaskStatus.GENERATING_ANCHOR: frozenset(
        {TaskStatus.ACQUIRING_OR_GENERATING_MEDIA, TaskStatus.STOPPED}
    ),
    TaskStatus.ACQUIRING_OR_GENERATING_MEDIA: frozenset(
        {TaskStatus.COMPOSITING, TaskStatus.STOPPED}
    ),
    TaskStatus.COMPOSITING: frozenset({TaskStatus.QUALITY_CHECK, TaskStatus.STOPPED}),
    TaskStatus.QUALITY_CHECK: frozenset(
        {
            TaskStatus.FINAL_REVIEW,
            TaskStatus.READY_TO_PUBLISH,
            TaskStatus.COMPOSITING,
            TaskStatus.STOPPED,
        }
    ),
    TaskStatus.FINAL_REVIEW: frozenset(
        {TaskStatus.READY_TO_PUBLISH, TaskStatus.COMPOSITING, TaskStatus.STOPPED}
    ),
    TaskStatus.READY_TO_PUBLISH: frozenset(),
    TaskStatus.STOPPED: frozenset(),
}

_APPROVAL_GATES: dict[TaskStatus, str] = {
    TaskStatus.HOTSPOT_REVIEW: "hotspot",
    TaskStatus.SCRIPT_REVIEW: "script",
    TaskStatus.FINAL_REVIEW: "final_video",
}


def allowed_targets(status: TaskStatus) -> frozenset[TaskStatus]:
    return _TRANSITIONS[status]


def ensure_transition(current: TaskStatus, target: TaskStatus) -> None:
    if target not in allowed_targets(current):
        raise InvalidTransitionError(f"invalid transition: {current.value} -> {target.value}")


def approval_gate_for(target: TaskStatus) -> str | None:
    return _APPROVAL_GATES.get(target)
