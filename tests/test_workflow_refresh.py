from datetime import date

import pytest

from avatar_pipeline.hotspot_models import HotspotReport
from avatar_pipeline.models import (
    ApprovalRecord,
    ArtifactRecord,
    DailyTask,
    FactStatus,
    HostProfile,
    MediaKind,
    MediaPlan,
    MediaSegment,
    NewsPillarSlug,
    NewsScript,
    ScriptSegment,
    TaskStatus,
    TopicCandidate,
)
from avatar_pipeline.workflow_refresh import (
    refresh_unapproved_task,
    topic_candidates_from_report,
)


def _topic(topic_id):
    return TopicCandidate(
        id=topic_id,
        title=topic_id,
        pillar=NewsPillarSlug.SOCIAL_PHENOMENA,
        score=90,
        fact_status=FactStatus.VERIFIED,
        publishable=True,
    )


def _confirmed_host() -> HostProfile:
    return HostProfile(
        id="host-c2-pro-candidate-2-final",
        display_name="C2-Pro 新闻主持人",
        reference_image=("output/host-v12-c2-pro/GPT-Image-2-Pro-C2-Pro-主持人最终选定.png"),
        studio_reference="蓝色演播室、近景胸像、白衬衣、深藏青西装、无桌、避免手臂入镜",
        visual_style="知性亲和、专业克制、低AI感、五官清晰稳定",
        is_new=False,
        version=12,
    )


def test_refresh_archives_old_plan_reconciles_host_and_never_enters_generation():
    host = _confirmed_host()
    old = _topic("old")
    skipped = _topic("old-skipped")
    script = NewsScript(
        title="大学新生电脑涨价",
        spoken_segments=[
            ScriptSegment(
                id="s1",
                kind="fact",
                text="这是已经被否决但必须留档的旧脚本。",
                source_ids=["source-old"],
            )
        ],
        source_ids=["source-old"],
        target_duration_seconds=60,
    )
    media_plan = MediaPlan(
        duration_seconds=60,
        segments=[
            MediaSegment(
                id="m1",
                kind=MediaKind.ORIGINAL_NEWS,
                start_seconds=0,
                end_seconds=8,
                script_segment_id="s1",
                source_id="source-old",
                provenance="旧方案事实画面",
            )
        ],
    )
    approvals = [ApprovalRecord(gate="host", actor="owner")]
    artifacts = [ArtifactRecord(kind="research", path="workspace/research/old.json")]
    task = DailyTask(
        day=date(2026, 8, 10),
        status=TaskStatus.TOPIC_SCRIPT_REVIEW,
        candidates=[old],
        skipped_candidates=[skipped],
        selected_topic_id="old",
        host_profile=None,
        news_script=script,
        media_plan=media_plan,
        approvals=approvals,
        artifacts=artifacts,
    )
    refreshed = refresh_unapproved_task(
        task,
        candidates=[_topic("new")],
        archive_reason="旧候选传播性不足",
        confirmed_host=host,
    )
    assert refreshed.status is TaskStatus.TOPIC_SCRIPT_REVIEW
    assert refreshed.host_profile == host
    assert refreshed.selected_topic_id is None
    assert refreshed.news_script is None
    assert refreshed.media_plan is None
    assert refreshed.candidates[0].id == "new"
    archive = refreshed.archived_topic_plans[-1]
    assert archive.candidates == [old]
    assert archive.skipped_candidates == [skipped]
    assert archive.selected_topic_id == "old"
    assert archive.news_script == script
    assert archive.media_plan == media_plan
    assert archive.reason == "旧候选传播性不足"
    assert refreshed.approvals == approvals
    assert refreshed.artifacts == artifacts


def test_refresh_rejects_a_conflicting_non_null_host():
    task = DailyTask(
        day=date(2026, 8, 10),
        status=TaskStatus.TOPIC_SCRIPT_REVIEW,
        host_profile=_confirmed_host().model_copy(update={"id": "different-host"}),
    )
    with pytest.raises(ValueError, match="conflicts with confirmed host"):
        refresh_unapproved_task(
            task,
            candidates=[_topic("new")],
            archive_reason="replace",
            confirmed_host=_confirmed_host(),
        )


def test_refresh_rejects_topic_approval_and_late_states():
    approved = DailyTask(
        day=date(2026, 8, 10),
        status=TaskStatus.TOPIC_SCRIPT_REVIEW,
        approvals=[ApprovalRecord(gate="topic_script", actor="owner")],
    )
    with pytest.raises(ValueError, match="already approved"):
        refresh_unapproved_task(
            approved,
            candidates=[_topic("new")],
            archive_reason="replace",
            confirmed_host=_confirmed_host(),
        )
    late = DailyTask(day=date(2026, 8, 10), status=TaskStatus.GENERATING_TTS)
    with pytest.raises(ValueError, match="cannot refresh"):
        refresh_unapproved_task(
            late,
            candidates=[_topic("new")],
            archive_reason="replace",
            confirmed_host=_confirmed_host(),
        )


def test_no_qualified_report_cannot_be_converted_to_production_candidates():
    report = HotspotReport(
        day="2026-08-10",
        rule_version="viral-v1.0",
        snapshot_ids=["t0"],
        collection_failures=[],
        candidates=[],
        outcome="no_qualified_hotspot",
    )
    with pytest.raises(ValueError, match="no qualified"):
        topic_candidates_from_report(report)
