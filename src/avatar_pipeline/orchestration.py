"""Provider-injected managed orchestration for the news-anchor workflow."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from avatar_pipeline.models import (
    DailyTask,
    HostProfile,
    MediaPlan,
    NewsScript,
    TaskStatus,
    TopicCandidate,
)
from avatar_pipeline.service import DailyWorkflowService


@dataclass(frozen=True)
class ManagedProviders:
    script: Callable[[TopicCandidate], tuple[NewsScript, MediaPlan]]
    host: Callable[[], HostProfile]
    tts: Callable[[NewsScript], str]
    anchor: Callable[[HostProfile, str], str]
    media: Callable[[MediaPlan], str]
    composite: Callable[[DailyTask], str]
    qc: Callable[[DailyTask], tuple[bool, str]]


def run_managed(
    service: DailyWorkflowService,
    day,
    candidates: Sequence[TopicCandidate],
    providers: ManagedProviders,
    *,
    max_topic_attempts: int = 5,
) -> DailyTask:
    task = service.record_research(day, candidates)
    if task.status is TaskStatus.STOPPED:
        return task
    for attempt, selected in enumerate(task.candidates, start=1):
        if attempt > max_topic_attempts:
            break
        try:
            script, plan = providers.script(selected)
            task = service.record_script_and_media_plan(day, selected.id, script, plan)
            task = service.set_host(day, providers.host())
            task = service.mark_tts_ready(day, artifact_path=providers.tts(script))
            task = service.mark_anchor_ready(
                day, artifact_path=providers.anchor(task.host_profile, task.artifacts[-1].path)
            )
            task = service.mark_media_ready(day, artifact_path=providers.media(plan))
            task = service.mark_compositing(day, artifact_path=providers.composite(task))
            passed, report = providers.qc(task)
            return service.record_qc(day, passed=passed, report_path=report)
        except (
            Exception
        ) as error:  # provider boundary: stop safely rather than publish partial output
            task = service.stop_task(day, reason=f"managed generation failed: {error}")
            return task
    return service.stop_task(day, reason="no verified hotspot could be produced")
