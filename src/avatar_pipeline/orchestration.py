"""Provider-injected managed orchestration for the news-anchor workflow."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from avatar_pipeline.models import (
    ArtifactRecord,
    AvatarSource,
    DailyTask,
    HostProfile,
    MediaPlan,
    NewsScript,
    TaskStatus,
    TopicCandidate,
)
from avatar_pipeline.service import DailyWorkflowService

HostProvider = Callable[[], HostProfile]


@dataclass(frozen=True)
class ManagedProviders:
    script: Callable[[TopicCandidate], tuple[NewsScript, MediaPlan]]
    host: HostProvider
    tts: Callable[[NewsScript], str]
    anchor: Callable[[HostProfile, str], str]
    media: Callable[[MediaPlan], str]
    composite: Callable[[DailyTask], str]
    qc: Callable[[DailyTask], tuple[bool, str]]
    host_source: AvatarSource = AvatarSource.SAVED_HOST


def run_managed(
    service: DailyWorkflowService,
    day,
    candidates: Sequence[TopicCandidate],
    providers: ManagedProviders,
    *,
    max_topic_attempts: int = 5,
) -> DailyTask:
    if max_topic_attempts < 1:
        raise ValueError("max_topic_attempts must be at least 1")

    task = service.get(day)
    if task.status in {TaskStatus.READY_TO_PUBLISH, TaskStatus.STOPPED}:
        return task
    if task.status is TaskStatus.INPUT_RECEIVED:
        task = service.record_research(day, candidates)
    if task.status is TaskStatus.STOPPED:
        return task

    failures: list[str] = []
    if task.status in _ACTIVE_GENERATION_STATUSES:
        selected_id = task.selected_topic_id
        if selected_id is None:
            return _stop_active_task(
                service, day, RuntimeError("managed checkpoint has no selected topic")
            )
        baseline = _attempt_baseline(task)
        try:
            return _resume_managed_run(service, day, task, providers)
        except Exception as error:  # provider boundary: retry a different verified candidate
            failures.append(f"{selected_id}: {error}")
            task = _reset_failed_attempt(service, day, selected_id, error, baseline)

    attempts = len(failures)
    for selected in list(task.candidates):
        if attempts >= max_topic_attempts:
            break
        attempts += 1
        task = service.get(day)
        baseline = _attempt_baseline(task)
        try:
            script, plan = providers.script(selected)
            task = service.record_script_and_media_plan(day, selected.id, script, plan)
            return _resume_managed_run(service, day, task, providers)
        except Exception as error:  # provider boundary: discard partial output and try next topic
            failures.append(f"{selected.id}: {error}")
            task = _reset_failed_attempt(service, day, selected.id, error, baseline)

    if failures:
        if len(failures) == 1:
            reason = f"managed generation failed: {failures[0].split(': ', 1)[-1]}"
        else:
            reason = f"{len(failures)} managed topic attempts failed: {'; '.join(failures)}"
        return service.stop_task(day, reason=reason)
    return service.stop_task(day, reason="no verified hotspot could be produced")


_ACTIVE_GENERATION_STATUSES = {
    TaskStatus.MEDIA_PLANNING,
    TaskStatus.GENERATING_TTS,
    TaskStatus.GENERATING_ANCHOR,
    TaskStatus.ACQUIRING_OR_GENERATING_MEDIA,
    TaskStatus.COMPOSITING,
    TaskStatus.QUALITY_CHECK,
}


_MANAGED_PRODUCTION_ARTIFACT_KINDS = {
    "master_audio",
    "anchor_video",
    "insert_media",
    "master_video",
    "qc_report",
}


def _attempt_baseline(
    task: DailyTask,
) -> tuple[HostProfile | None, AvatarSource, list[ArtifactRecord]]:
    audit_artifacts = [
        artifact
        for artifact in task.artifacts
        if artifact.kind not in _MANAGED_PRODUCTION_ARTIFACT_KINDS
    ]
    return task.host_profile, task.avatar_source, audit_artifacts


def _reset_failed_attempt(
    service: DailyWorkflowService,
    day,
    topic_id: str,
    error: Exception,
    baseline: tuple[HostProfile | None, AvatarSource, list[ArtifactRecord]],
) -> DailyTask:
    baseline_host, baseline_source, baseline_artifacts = baseline
    return service.reset_managed_attempt(
        day,
        topic_id=topic_id,
        reason=str(error),
        baseline_host=baseline_host,
        baseline_avatar_source=baseline_source,
        baseline_artifacts=baseline_artifacts,
    )


def _resume_managed_run(
    service: DailyWorkflowService,
    day,
    task: DailyTask,
    providers: ManagedProviders,
) -> DailyTask:
    script = task.news_script
    plan = task.media_plan
    if script is None or plan is None:
        raise RuntimeError("managed checkpoint requires a script and media plan")

    if task.status is TaskStatus.MEDIA_PLANNING:
        if task.host_profile is None:
            task = service.set_host(day, providers.host(), avatar_source=providers.host_source)
        else:
            task = service.set_host(day, task.host_profile)

    host = task.host_profile
    if host is None:
        raise RuntimeError("managed generation requires a host profile")

    if task.status is TaskStatus.GENERATING_TTS:
        task = service.mark_tts_ready(day, artifact_path=providers.tts(script))

    if task.status is TaskStatus.GENERATING_ANCHOR:
        audio_path = _artifact_path(task, "master_audio")
        task = service.mark_anchor_ready(day, artifact_path=providers.anchor(host, audio_path))

    if task.status is TaskStatus.ACQUIRING_OR_GENERATING_MEDIA:
        task = service.mark_media_ready(day, artifact_path=providers.media(plan))

    if task.status is TaskStatus.COMPOSITING:
        task = service.mark_compositing(day, artifact_path=providers.composite(task))

    if task.status is TaskStatus.QUALITY_CHECK:
        passed, report = providers.qc(task)
        task = service.record_qc(day, passed=passed, report_path=report)
        if not passed:
            raise RuntimeError(f"quality check failed: {report}")

    return task


def _artifact_path(task: DailyTask, kind: str) -> str:
    for artifact in reversed(task.artifacts):
        if artifact.kind == kind:
            return artifact.path
    raise RuntimeError(f"managed checkpoint is missing {kind} artifact")


def _stop_active_task(service: DailyWorkflowService, day, error: Exception) -> DailyTask:
    task = service.get(day)
    if task.status in {TaskStatus.READY_TO_PUBLISH, TaskStatus.STOPPED}:
        return task
    return service.stop_task(day, reason=f"managed generation failed: {error}")
