"""Application service for the approval-gated daily workflow."""

from datetime import date

from avatar_pipeline.models import (
    ApprovalRecord,
    ArtifactRecord,
    DailyTask,
    TaskStatus,
    TopicCandidate,
)
from avatar_pipeline.repository import DailyTaskRepository
from avatar_pipeline.state import ensure_transition


class WorkflowPreconditionError(ValueError):
    """Raised when workflow data or state does not satisfy an operation."""


class DailyWorkflowService:
    """Coordinate persistence, state changes, artifacts, and manual approvals."""

    def __init__(self, repository: DailyTaskRepository) -> None:
        self.repository = repository

    def start_day(self, day: date) -> DailyTask:
        """Create the single production task for a calendar day."""

        return self.repository.create(DailyTask(day=day))

    def record_research(self, day: date, candidates: list[TopicCandidate]) -> DailyTask:
        """Store the ranked Top 3 topic candidates."""

        task = self._require_status(day, TaskStatus.CREATED)
        if len(candidates) != 3:
            raise WorkflowPreconditionError("research must contain exactly three Top 3 candidates")
        ensure_transition(task.status, TaskStatus.RESEARCHED)
        task.candidates = candidates
        task.status = TaskStatus.RESEARCHED
        self._validate(task)
        return self.repository.save(task)

    def approve_topic(self, day: date, topic_id: str, *, actor: str) -> DailyTask:
        """Record manual selection of one candidate from the Top 3."""

        task = self._require_status(day, TaskStatus.RESEARCHED)
        if topic_id not in {candidate.id for candidate in task.candidates}:
            raise WorkflowPreconditionError(f"topic {topic_id!r} is not in Top 3")
        ensure_transition(task.status, TaskStatus.TOPIC_APPROVED)
        task.selected_topic_id = topic_id
        task.approvals.append(ApprovalRecord(gate="topic", actor=actor))
        task.status = TaskStatus.TOPIC_APPROVED
        self._validate(task)
        return self.repository.save(task)

    def record_script(self, day: date, script_text: str) -> DailyTask:
        """Store the original script draft for the approved topic."""

        task = self._require_status(day, TaskStatus.TOPIC_APPROVED)
        normalized = script_text.strip()
        if not normalized:
            raise WorkflowPreconditionError("script text must not be blank")
        ensure_transition(task.status, TaskStatus.SCRIPT_DRAFT)
        task.script_text = normalized
        task.status = TaskStatus.SCRIPT_DRAFT
        return self.repository.save(task)

    def approve_script(self, day: date, *, actor: str) -> DailyTask:
        """Record the manual script approval gate."""

        task = self._require_status(day, TaskStatus.SCRIPT_DRAFT)
        if not task.script_text:
            raise WorkflowPreconditionError("script must exist before approval")
        ensure_transition(task.status, TaskStatus.SCRIPT_APPROVED)
        task.approvals.append(ApprovalRecord(gate="script", actor=actor))
        task.status = TaskStatus.SCRIPT_APPROVED
        return self.repository.save(task)

    def mark_audio_ready(self, day: date, *, artifact_path: str) -> DailyTask:
        """Record the independent TTS master audio artifact."""

        task = self._require_status(day, TaskStatus.SCRIPT_APPROVED)
        ensure_transition(task.status, TaskStatus.AUDIO_READY)
        task.artifacts.append(ArtifactRecord(kind="master_audio", path=artifact_path))
        task.status = TaskStatus.AUDIO_READY
        return self.repository.save(task)

    def mark_assets_generating(self, day: date) -> DailyTask:
        """Enter or retry external avatar and Seedance asset generation."""

        task = self.repository.get(day)
        if task.status not in {TaskStatus.AUDIO_READY, TaskStatus.QC_FAILED}:
            self._raise_expected(task, TaskStatus.AUDIO_READY, TaskStatus.QC_FAILED)
        ensure_transition(task.status, TaskStatus.ASSETS_GENERATING)
        task.status = TaskStatus.ASSETS_GENERATING
        return self.repository.save(task)

    def mark_compositing(self, day: date) -> DailyTask:
        """Enter compositing after asset generation, or retry it after failed QC."""

        task = self.repository.get(day)
        if task.status not in {TaskStatus.ASSETS_GENERATING, TaskStatus.QC_FAILED}:
            self._raise_expected(task, TaskStatus.ASSETS_GENERATING, TaskStatus.QC_FAILED)
        ensure_transition(task.status, TaskStatus.COMPOSITING)
        task.status = TaskStatus.COMPOSITING
        return self.repository.save(task)

    def record_qc(self, day: date, *, passed: bool, report_path: str) -> DailyTask:
        """Store a QC report and branch to passed or retry-required state."""

        task = self._require_status(day, TaskStatus.COMPOSITING)
        target = TaskStatus.QC_PASSED if passed else TaskStatus.QC_FAILED
        ensure_transition(task.status, target)
        task.artifacts.append(
            ArtifactRecord(kind="qc_report", path=report_path, metadata={"passed": passed})
        )
        task.status = target
        return self.repository.save(task)

    def approve_video(self, day: date, *, actor: str) -> DailyTask:
        """Record the final manual finished-video approval gate."""

        task = self._require_status(day, TaskStatus.QC_PASSED)
        ensure_transition(task.status, TaskStatus.VIDEO_APPROVED)
        task.approvals.append(ApprovalRecord(gate="video", actor=actor))
        task.status = TaskStatus.VIDEO_APPROVED
        return self.repository.save(task)

    def _require_status(self, day: date, expected: TaskStatus) -> DailyTask:
        task = self.repository.get(day)
        if task.status is not expected:
            self._raise_expected(task, expected)
        return task

    @staticmethod
    def _raise_expected(task: DailyTask, *expected: TaskStatus) -> None:
        names = ", ".join(status.value for status in expected)
        raise WorkflowPreconditionError(
            f"task {task.day.isoformat()} is {task.status.value}; expected {names}"
        )

    @staticmethod
    def _validate(task: DailyTask) -> None:
        DailyTask.model_validate(task.model_dump())
