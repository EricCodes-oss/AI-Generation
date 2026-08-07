from datetime import date

import pytest
from pydantic import ValidationError

from avatar_pipeline.models import (
    ApprovalRecord,
    AvatarSource,
    DailyTask,
    HostProfile,
    MediaKind,
    MediaPlan,
    MediaSegment,
    NewsScript,
    RunMode,
    ScriptSegment,
    SourceEvidence,
    TaskStatus,
    TopicCandidate,
)


def verified_topic() -> TopicCandidate:
    return TopicCandidate(
        id="topic-1",
        title="多地推出灵活就业服务",
        pillar="workplace_life",
        score=92,
        fact_status="verified",
        source_evidence=[
            SourceEvidence(
                source_id="source-1",
                platform="official",
                title="官方发布服务信息",
                url_or_reference="https://example.test/news",
                evidence_type="primary",
            ),
            SourceEvidence(
                source_id="source-2",
                platform="reputable_media",
                title="媒体报道服务变化",
                url_or_reference="https://example.test/report",
                evidence_type="corroboration",
            ),
        ],
        publishable=True,
    )


def test_daily_task_models_news_run_with_default_no_subtitles():
    task = DailyTask(
        day=date(2026, 8, 6),
        mode=RunMode.MANUAL,
        status=TaskStatus.INPUT_RECEIVED,
        candidates=[verified_topic()],
    )
    assert task.subtitle_enabled is False
    assert task.video_structure == "studio_anchor_plus_vertical_news_insert"
    assert task.schema_version == 3
    assert task.avatar_source is AvatarSource.SAVED_HOST


def test_topic_candidate_requires_verified_evidence_for_publishable_flag():
    with pytest.raises(ValidationError, match="publishable candidate must be verified"):
        TopicCandidate(
            id="unsafe",
            title="待核实爆料",
            pillar="social_phenomena",
            score=99,
            fact_status="pending",
            publishable=True,
        )


def test_legacy_pillars_are_not_valid_news_pillars():
    with pytest.raises(ValidationError):
        TopicCandidate(id="bad", title="旧内容", pillar="unsupported_legacy_pillar", score=90)


def test_news_script_and_media_plan_keep_claims_and_disclosures():
    script = NewsScript(
        title="这项服务变化，影响哪些人？",
        spoken_segments=[
            ScriptSegment(
                id="s1", kind="fact", text="官方公布了新的服务安排。", source_ids=["source-1"]
            ),
            ScriptSegment(
                id="s2", kind="context", text="这意味着办理路径更加清晰。", source_ids=["source-1"]
            ),
        ],
        source_ids=["source-1", "source-2"],
    )
    host = HostProfile(
        id="host-main",
        display_name="林知遥",
        reference_image="hosts/main.png",
        is_new=False,
    )
    plan = MediaPlan(
        duration_seconds=55,
        host_id=host.id,
        segments=[
            MediaSegment(
                id="m1",
                kind=MediaKind.ANCHOR,
                start_seconds=0,
                end_seconds=12,
                script_segment_id="s1",
                host_id=host.id,
            ),
            MediaSegment(
                id="m2",
                kind=MediaKind.ORIGINAL_NEWS,
                start_seconds=12,
                end_seconds=25,
                script_segment_id="s1",
                source_id="source-1",
                provenance="clip 00:10-00:23",
            ),
            MediaSegment(
                id="m3",
                kind=MediaKind.ANCHOR,
                start_seconds=25,
                end_seconds=43,
                script_segment_id="s2",
                host_id=host.id,
            ),
            MediaSegment(
                id="m4",
                kind=MediaKind.AI_DEMO,
                start_seconds=43,
                end_seconds=55,
                script_segment_id="s2",
                disclosure="AI生成示意画面",
            ),
        ],
    )
    task = DailyTask(day=date(2026, 8, 6), host_profile=host, news_script=script, media_plan=plan)
    assert task.media_plan.segments[-1].disclosure == "AI生成示意画面"


def test_host_profile_can_be_reused_without_new_host_approval():
    host = HostProfile(
        id="host-main", display_name="林知遥", reference_image="hosts/main.png", is_new=False
    )
    task = DailyTask(day=date(2026, 8, 6), host_profile=host)
    assert task.requires_host_approval is False
    task.host_profile.is_new = True
    assert task.requires_host_approval is True


def test_approval_records_use_only_three_user_facing_gate_names():
    assert ApprovalRecord(gate="hotspot", actor="owner")
    assert ApprovalRecord(gate="script", actor="owner")
    assert ApprovalRecord(gate="final_video", actor="owner")
    with pytest.raises(ValidationError):
        ApprovalRecord(gate="host", actor="owner")
