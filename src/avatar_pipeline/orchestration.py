"""Provider-injected managed orchestration for the news-anchor workflow."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from avatar_pipeline.models import (
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
    task = service.get(day)
    if task.status is TaskStatus.INPUT_RECEIVED:
        task = service.record_research(day, candidates)
    if task.status is TaskStatus.STOPPED:
        return task

    if task.status is TaskStatus.MEDIA_PLANNING and task.news_script and task.media_plan:
        try:
            return _complete_managed_run(
                service, day, task, task.news_script, task.media_plan, providers
            )
        except Exception as error:  # provider boundary: stop rather than publish partial output
            return service.stop_task(day, reason=f"managed generation failed: {error}")

    for attempt, selected in enumerate(task.candidates, start=1):
        if attempt > max_topic_attempts:
            break
        try:
            script, plan = providers.script(selected)
            task = service.record_script_and_media_plan(day, selected.id, script, plan)
            return _complete_managed_run(service, day, task, script, plan, providers)
        except Exception as error:  # provider boundary: stop rather than publish partial output
            return service.stop_task(day, reason=f"managed generation failed: {error}")
    return service.stop_task(day, reason="no verified hotspot could be produced")


def _complete_managed_run(
    service: DailyWorkflowService,
    day,
    task: DailyTask,
    script: NewsScript,
    plan: MediaPlan,
    providers: ManagedProviders,
) -> DailyTask:
    if task.host_profile is None:
        task = service.set_host(day, providers.host(), avatar_source=providers.host_source)
    elif task.status is TaskStatus.MEDIA_PLANNING:
        task = service.set_host(day, task.host_profile)

    host = task.host_profile
    if host is None:
        raise RuntimeError("managed generation requires a host profile")

    task = service.mark_tts_ready(day, artifact_path=providers.tts(script))
    task = service.mark_anchor_ready(
        day, artifact_path=providers.anchor(host, task.artifacts[-1].path)
    )
    task = service.mark_media_ready(day, artifact_path=providers.media(plan))
    task = service.mark_compositing(day, artifact_path=providers.composite(task))
    passed, report = providers.qc(task)
    return service.record_qc(day, passed=passed, report_path=report)
