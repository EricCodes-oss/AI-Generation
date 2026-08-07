"""Application service for the daily hotspot news-anchor workflow."""

from collections.abc import Sequence
from datetime import date

from avatar_pipeline.media import validate_media_plan
from avatar_pipeline.models import (
    ApprovalRecord,
    ArtifactRecord,
    AvatarSource,
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
from avatar_pipeline.voice import DEFAULT_TTS_VOICE_ID


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
        ranked = sorted(accepted, key=lambda candidate: candidate.score, reverse=True)
        if task.mode is RunMode.MANUAL:
            task.candidates = ranked[:3]
            task.skipped_candidates = [*skipped, *ranked[3:]]
        else:
            task.candidates = ranked
            task.skipped_candidates = skipped
        if not task.candidates:
            task.status = TaskStatus.STOPPED
            task.stop_reason = "no verified hotspot"
        else:
            target = (
                TaskStatus.HOTSPOT_REVIEW if task.mode is RunMode.MANUAL else TaskStatus.SCRIPTING
            )
            ensure_transition(task.status, target)
            task.status = target
        return self.repository.save(task)

    def approve_hotspot(self, day: date, *, topic_id: str, actor: str) -> DailyTask:
        task = self._require_status(day, TaskStatus.HOTSPOT_REVIEW)
        candidate = next((item for item in task.candidates if item.id == topic_id), None)
        if candidate is None or not candidate.publishable:
            raise WorkflowPreconditionError("topic is not a verified hotspot candidate")
        task.selected_topic_id = topic_id
        task.approvals.append(ApprovalRecord(gate="hotspot", actor=actor))
        ensure_transition(task.status, TaskStatus.SCRIPTING)
        task.status = TaskStatus.SCRIPTING
        return self.repository.save(task)

    def record_script_and_media_plan(
        self, day: date, topic_id: str, script: NewsScript, media_plan: MediaPlan
    ) -> DailyTask:
        existing = self.repository.get(day)
        if existing.status is TaskStatus.STOPPED and not existing.candidates:
            raise WorkflowPreconditionError("no verified hotspot")
        task = self._require_status(day, TaskStatus.SCRIPTING, TaskStatus.SCRIPT_REVIEW)
        candidate = next((item for item in task.candidates if item.id == topic_id), None)
        if candidate is None or not candidate.publishable:
            raise WorkflowPreconditionError("topic is not a verified hotspot")
        if task.mode is RunMode.MANUAL and task.selected_topic_id != topic_id:
            raise WorkflowPreconditionError("script topic must match the approved hotspot")
        validate_media_plan(media_plan, script)
        if task.host_profile is not None:
            self._require_media_host_identity(media_plan, task.host_profile)
        task.selected_topic_id = topic_id
        task.news_script = script
        task.media_plan = media_plan
        if task.status is TaskStatus.SCRIPTING:
            target = (
                TaskStatus.SCRIPT_REVIEW
                if task.mode is RunMode.MANUAL
                else TaskStatus.MEDIA_PLANNING
            )
            ensure_transition(task.status, target)
            task.status = target
        return self.repository.save(task)

    def approve_script(self, day: date, *, actor: str) -> DailyTask:
        task = self._require_status(day, TaskStatus.SCRIPT_REVIEW)
        self._require_script_plan(task)
        task.approvals.append(ApprovalRecord(gate="script", actor=actor))
        ensure_transition(task.status, TaskStatus.MEDIA_PLANNING)
        task.status = TaskStatus.MEDIA_PLANNING
        return self._advance_after_media_plan(task)

    def set_host(
        self, day: date, host: HostProfile, *, avatar_source: AvatarSource | None = None
    ) -> DailyTask:
        task = self._require_status(day, TaskStatus.MEDIA_PLANNING)
        self._require_media_host_identity(task.media_plan, host)
        effective_source = avatar_source or task.avatar_source
        task.avatar_source = effective_source
        if host.voice_id != DEFAULT_TTS_VOICE_ID:
            host = host.model_copy(update={"voice_id": DEFAULT_TTS_VOICE_ID})
        task.host_profile = host.model_copy(update={"is_new": False})
        ensure_transition(task.status, TaskStatus.GENERATING_TTS)
        task.status = TaskStatus.GENERATING_TTS
        return self.repository.save(task)

    def mark_tts_ready(self, day: date, *, artifact_path: str) -> DailyTask:
        task = self._require_status(day, TaskStatus.GENERATING_TTS)
        if task.host_profile is None:
            raise WorkflowPreconditionError("host profile is required before TTS generation")
        task.artifacts.append(
            ArtifactRecord(
                kind="master_audio",
                path=artifact_path,
                metadata={"voice_id": task.host_profile.voice_id},
            )
        )
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

    def reset_managed_attempt(
        self,
        day: date,
        *,
        topic_id: str,
        reason: str,
        baseline_host: HostProfile | None,
        baseline_avatar_source: AvatarSource,
        baseline_artifacts: Sequence[ArtifactRecord],
    ) -> DailyTask:
        """Discard partial output for one failed managed topic and return to scripting."""

        task = self.repository.get(day)
        if task.mode is not RunMode.MANAGED:
            raise WorkflowPreconditionError("managed attempt reset requires managed mode")
        if task.status in {TaskStatus.READY_TO_PUBLISH, TaskStatus.STOPPED}:
            raise WorkflowPreconditionError("completed task cannot reset a managed attempt")
        failed = next((item for item in task.candidates if item.id == topic_id), None)
        if failed is None:
            raise WorkflowPreconditionError("managed attempt topic is not available")
        task.selected_topic_id = None
        task.candidates = [item for item in task.candidates if item.id != topic_id]
        task.skipped_candidates.append(
            failed.model_copy(
                update={
                    "publishable": False,
                    "risk_flags": [*failed.risk_flags, "managed_generation_failed"],
                }
            )
        )
        task.news_script = None
        task.media_plan = None
        task.host_profile = baseline_host
        task.avatar_source = baseline_avatar_source
        task.artifacts = list(baseline_artifacts)
        task.artifacts.append(
            ArtifactRecord(
                kind="managed_attempt_failure",
                path=f"managed-attempts/{topic_id}.json",
                metadata={"topic_id": topic_id, "reason": reason},
            )
        )
        task.status = TaskStatus.SCRIPTING
        task.stop_reason = None
        return self.repository.save(task)

    def stop_task(self, day: date, *, reason: str) -> DailyTask:
        task = self.repository.get(day)
        if task.status is not TaskStatus.STOPPED:
            ensure_transition(task.status, TaskStatus.STOPPED)
            task.status = TaskStatus.STOPPED
        task.stop_reason = reason
        return self.repository.save(task)

    def _advance_after_media_plan(self, task: DailyTask) -> DailyTask:
        if task.host_profile is not None:
            self._require_media_host_identity(task.media_plan, task.host_profile)
            task.host_profile = task.host_profile.model_copy(update={"is_new": False})
            ensure_transition(task.status, TaskStatus.GENERATING_TTS)
            task.status = TaskStatus.GENERATING_TTS
        return self.repository.save(task)

    @staticmethod
    def _require_media_host_identity(media_plan: MediaPlan | None, host: HostProfile) -> None:
        if media_plan is None or media_plan.host_id != host.id:
            raise WorkflowPreconditionError("media plan host_id must match the fixed host profile")

    @staticmethod
    def _require_script_plan(task: DailyTask) -> None:
        if task.selected_topic_id is None or task.news_script is None or task.media_plan is None:
            raise WorkflowPreconditionError("topic, script, and media plan are required")

    def _require_status(self, day: date, *expected: TaskStatus) -> DailyTask:
        task = self.repository.get(day)
        if task.status not in expected:
            names = ", ".join(status.value for status in expected)
            raise WorkflowPreconditionError(
                f"task {day.isoformat()} is {task.status.value}; expected {names}"
            )
        return task
