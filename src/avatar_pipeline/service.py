"""Application service for the daily hotspot news-anchor workflow."""

from collections.abc import Sequence
from datetime import date

from avatar_pipeline.media import validate_media_plan
from avatar_pipeline.models import (
    ApprovalRecord,
    ArtifactRecord,
    DailyTask,
    HostProfile,
    MediaPlan,
    NewsScript,
    RunMode,
    TaskStatus,
    TopicCandidate,
)
from avatar_pipeline.policy import screen_candidates
from avatar_pipeline.repository import DailyTaskRepository
from avatar_pipeline.state import ensure_transition
from avatar_pipeline.workflow_refresh import refresh_unapproved_task


class WorkflowPreconditionError(ValueError):
    """Raised when a production action is not valid for the current task."""


class DailyWorkflowService:
    def __init__(self, repository: DailyTaskRepository) -> None:
        self.repository = repository

    def get(self, day: date) -> DailyTask:
        return self.repository.get(day)

    def start_day(
        self, day: date, *, mode: RunMode = RunMode.MANUAL, input_text: str | None = None
    ) -> DailyTask:
        task = DailyTask(day=day, mode=mode, input_text=input_text)
        return self.repository.create(task)

    def record_research(self, day: date, candidates: Sequence[TopicCandidate]) -> DailyTask:
        task = self._require_status(day, TaskStatus.INPUT_RECEIVED)
        ensure_transition(task.status, TaskStatus.RESEARCHING)
        task.status = TaskStatus.RESEARCHING
        accepted, skipped = screen_candidates(candidates)
        task.candidates = sorted(accepted, key=lambda candidate: candidate.score, reverse=True)
        task.skipped_candidates = skipped
        if not task.candidates:
            task.status = TaskStatus.STOPPED
            task.stop_reason = "no verified hotspot"
        else:
            ensure_transition(task.status, TaskStatus.FACT_SCREENED)
            task.status = TaskStatus.FACT_SCREENED
        return self.repository.save(task)

    def record_script_and_media_plan(
        self, day: date, topic_id: str, script: NewsScript, media_plan: MediaPlan
    ) -> DailyTask:
        existing = self.repository.get(day)
        if existing.status is TaskStatus.STOPPED and not existing.candidates:
            raise WorkflowPreconditionError("no verified hotspot")
        task = self._require_status(day, TaskStatus.FACT_SCREENED, TaskStatus.TOPIC_SCRIPT_REVIEW)
        candidate = next((item for item in task.candidates if item.id == topic_id), None)
        if candidate is None or not candidate.publishable:
            raise WorkflowPreconditionError("topic is not a verified hotspot")
        validate_media_plan(media_plan, script)
        task.selected_topic_id = topic_id
        task.news_script = script
        task.media_plan = media_plan
        if task.status is TaskStatus.FACT_SCREENED:
            target = (
                TaskStatus.TOPIC_SCRIPT_REVIEW
                if task.mode is RunMode.MANUAL
                else TaskStatus.MEDIA_PLANNING
            )
            ensure_transition(task.status, target)
            task.status = target
        return self.repository.save(task)

    def approve_topic_script(self, day: date, *, actor: str) -> DailyTask:
        task = self._require_status(day, TaskStatus.TOPIC_SCRIPT_REVIEW)
        self._require_script_plan(task)
        task.approvals.append(ApprovalRecord(gate="topic_script", actor=actor))
        ensure_transition(task.status, TaskStatus.MEDIA_PLANNING)
        task.status = TaskStatus.MEDIA_PLANNING
        return self._advance_after_media_plan(task)

    def set_host(self, day: date, host: HostProfile) -> DailyTask:
        task = self._require_status(day, TaskStatus.MEDIA_PLANNING, TaskStatus.HOST_REVIEW)
        task.host_profile = host
        if task.mode is RunMode.MANAGED or not host.is_new:
            ensure_transition(task.status, TaskStatus.GENERATING_TTS)
            task.status = TaskStatus.GENERATING_TTS
        elif task.status is TaskStatus.MEDIA_PLANNING:
            ensure_transition(task.status, TaskStatus.HOST_REVIEW)
            task.status = TaskStatus.HOST_REVIEW
        return self.repository.save(task)

    def approve_host(self, day: date, *, actor: str) -> DailyTask:
        task = self._require_status(day, TaskStatus.HOST_REVIEW)
        if not task.requires_host_approval:
            raise WorkflowPreconditionError("host approval is not required")
        task.approvals.append(ApprovalRecord(gate="host", actor=actor))
        ensure_transition(task.status, TaskStatus.GENERATING_TTS)
        task.status = TaskStatus.GENERATING_TTS
        return self.repository.save(task)

    def mark_tts_ready(self, day: date, *, artifact_path: str) -> DailyTask:
        task = self._require_status(day, TaskStatus.GENERATING_TTS)
        task.artifacts.append(ArtifactRecord(kind="master_audio", path=artifact_path))
        ensure_transition(task.status, TaskStatus.GENERATING_ANCHOR)
        task.status = TaskStatus.GENERATING_ANCHOR
        return self.repository.save(task)

    def mark_anchor_ready(self, day: date, *, artifact_path: str) -> DailyTask:
        task = self._require_status(day, TaskStatus.GENERATING_ANCHOR)
        task.artifacts.append(ArtifactRecord(kind="anchor_video", path=artifact_path))
        ensure_transition(task.status, TaskStatus.ACQUIRING_OR_GENERATING_MEDIA)
        task.status = TaskStatus.ACQUIRING_OR_GENERATING_MEDIA
        return self.repository.save(task)

    def mark_media_ready(self, day: date, *, artifact_path: str) -> DailyTask:
        task = self._require_status(day, TaskStatus.ACQUIRING_OR_GENERATING_MEDIA)
        task.artifacts.append(ArtifactRecord(kind="insert_media", path=artifact_path))
        ensure_transition(task.status, TaskStatus.COMPOSITING)
        task.status = TaskStatus.COMPOSITING
        return self.repository.save(task)

    def mark_compositing(self, day: date, *, artifact_path: str) -> DailyTask:
        task = self._require_status(day, TaskStatus.COMPOSITING)
        task.artifacts.append(ArtifactRecord(kind="master_video", path=artifact_path))
        ensure_transition(task.status, TaskStatus.QUALITY_CHECK)
        task.status = TaskStatus.QUALITY_CHECK
        return self.repository.save(task)

    def record_qc(self, day: date, *, passed: bool, report_path: str) -> DailyTask:
        task = self._require_status(day, TaskStatus.QUALITY_CHECK)
        task.artifacts.append(
            ArtifactRecord(kind="qc_report", path=report_path, metadata={"passed": passed})
        )
        target = (
            TaskStatus.READY_TO_PUBLISH
            if task.mode is RunMode.MANAGED and passed
            else TaskStatus.FINAL_REVIEW
            if passed
            else TaskStatus.COMPOSITING
        )
        ensure_transition(task.status, target)
        task.status = target
        return self.repository.save(task)

    def approve_final_video(self, day: date, *, actor: str) -> DailyTask:
        task = self._require_status(day, TaskStatus.FINAL_REVIEW)
        if task.mode is RunMode.MANAGED:
            raise WorkflowPreconditionError("managed mode does not accept user final approval")
        task.approvals.append(ApprovalRecord(gate="final_video", actor=actor))
        ensure_transition(task.status, TaskStatus.READY_TO_PUBLISH)
        task.status = TaskStatus.READY_TO_PUBLISH
        return self.repository.save(task)

    def stop_task(self, day: date, *, reason: str) -> DailyTask:
        task = self.repository.get(day)
        if task.status is not TaskStatus.STOPPED:
            ensure_transition(task.status, TaskStatus.STOPPED)
            task.status = TaskStatus.STOPPED
        task.stop_reason = reason
        return self.repository.save(task)

    def _advance_after_media_plan(self, task: DailyTask) -> DailyTask:
        if (
            task.host_profile is not None and not task.host_profile.is_new
        ) or task.mode is RunMode.MANAGED:
            ensure_transition(task.status, TaskStatus.GENERATING_TTS)
            task.status = TaskStatus.GENERATING_TTS
        return self.repository.save(task)

    @staticmethod
    def _require_script_plan(task: DailyTask) -> None:
        if task.selected_topic_id is None or task.news_script is None or task.media_plan is None:
            raise WorkflowPreconditionError("topic, script, and media plan are required")

    def refresh_unapproved_hotspots(
        self,
        day: date,
        candidates: Sequence[TopicCandidate],
        archive_reason: str,
        confirmed_host: HostProfile,
    ) -> DailyTask:
        task = self.repository.get(day)
        refreshed = refresh_unapproved_task(
            task,
            candidates=candidates,
            archive_reason=archive_reason,
            confirmed_host=confirmed_host,
        )
        return self.repository.save(refreshed)

    def _require_status(self, day: date, *expected: TaskStatus) -> DailyTask:
        task = self.repository.get(day)
        if task.status not in expected:
            names = ", ".join(status.value for status in expected)
            raise WorkflowPreconditionError(
                f"task {day.isoformat()} is {task.status.value}; expected {names}"
            )
        return task
