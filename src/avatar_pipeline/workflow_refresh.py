"""Safe bridge from verified hotspot reports to an unapproved production task."""

from collections.abc import Sequence

from avatar_pipeline.hotspot_models import HotspotReport
from avatar_pipeline.models import (
    ArchivedTopicPlan,
    DailyTask,
    FactStatus,
    HostProfile,
    TaskStatus,
    TopicCandidate,
)

_LOCKED_HOST_REFERENCE = "output/host-v12-c2-pro/GPT-Image-2-Pro-C2-Pro-主持人最终选定.png"
_ALLOWED_REFRESH_STATES = {
    TaskStatus.INPUT_RECEIVED,
    TaskStatus.FACT_SCREENED,
    TaskStatus.TOPIC_SCRIPT_REVIEW,
}


def topic_candidates_from_report(report: HotspotReport) -> list[TopicCandidate]:
    if report.outcome != "qualified_candidates" or not report.candidates:
        raise ValueError("report contains no qualified hotspot")
    director_ready = [item for item in report.candidates if item.director_action.value == "do_now"]
    if not director_ready:
        raise ValueError(
            "report contains no director-ready hotspot with Douyin/Xiaohongshu evidence"
        )
    return [
        TopicCandidate(
            id=item.event_id,
            title=item.click_title,
            pillar=item.pillar,
            score=item.score.total,
            fact_status=FactStatus.VERIFIED,
            target_audience=item.audience_relevance,
            recommendation_reason=item.why_click,
            opening_hook=item.opening_hook,
            trend_evidence=item.platform_evidence,
            risk_flags=item.risks,
            source_evidence=item.source_evidence,
            dedupe_key=item.event_id,
            cluster_id=item.event_id,
            verified_at=report.generated_at,
            verification_summary=item.verification_summary,
            publishable=True,
        )
        for item in director_ready
    ]


def refresh_unapproved_task(
    task: DailyTask,
    *,
    candidates: Sequence[TopicCandidate],
    archive_reason: str,
    confirmed_host: HostProfile,
) -> DailyTask:
    if confirmed_host.reference_image != _LOCKED_HOST_REFERENCE:
        raise ValueError("confirmed host does not use the locked C2-Pro image")
    if task.host_profile is not None and task.host_profile != confirmed_host:
        raise ValueError("saved host conflicts with confirmed host")
    if task.status not in _ALLOWED_REFRESH_STATES:
        raise ValueError(f"cannot refresh task in {task.status.value}")
    if task.status is TaskStatus.INPUT_RECEIVED and (
        task.approvals
        or task.artifacts
        or task.selected_topic_id is not None
        or task.news_script is not None
        or task.media_plan is not None
    ):
        raise ValueError("input_received task contains work that cannot be bypassed")
    if any(item.gate == "topic_script" for item in task.approvals):
        raise ValueError("topic and script are already approved")
    if not archive_reason.strip():
        raise ValueError("archive_reason must not be blank")
    replacement = list(candidates)
    if not replacement:
        raise ValueError("at least one verified replacement candidate is required")
    if any(
        not item.publishable or item.fact_status is not FactStatus.VERIFIED for item in replacement
    ):
        raise ValueError("replacement candidates must be verified and publishable")
    archive = ArchivedTopicPlan(
        reason=archive_reason.strip(),
        previous_status=task.status,
        candidates=task.candidates,
        skipped_candidates=task.skipped_candidates,
        selected_topic_id=task.selected_topic_id,
        news_script=task.news_script,
        media_plan=task.media_plan,
    )
    return task.model_copy(
        update={
            "status": TaskStatus.TOPIC_SCRIPT_REVIEW,
            "candidates": replacement,
            "skipped_candidates": [],
            "selected_topic_id": None,
            "news_script": None,
            "media_plan": None,
            "host_profile": confirmed_host,
            "archived_topic_plans": [*task.archived_topic_plans, archive],
            "stop_reason": None,
        }
    )
