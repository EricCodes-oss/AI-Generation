from collections import Counter
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from avatar_pipeline.cli import build_parser, dispatch
from avatar_pipeline.config import load_config
from avatar_pipeline.models import (
    ArtifactRecord,
    AvatarLayout,
    AvatarSource,
    FactStatus,
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
from avatar_pipeline.orchestration import ManagedProviders, run_managed
from avatar_pipeline.publication import build_publication_package
from avatar_pipeline.repository import DailyTaskRepository
from avatar_pipeline.service import DailyWorkflowService
from avatar_pipeline.skill_contracts import SkillKind, load_contracts

DAY = date(2026, 8, 6)
HOST_ID = "fixed-seated-anchor"
SOURCE_RECORD = "audit/2026-08-06-sources.json"


def source(source_id: str, platform: str, evidence_type: str) -> SourceEvidence:
    return SourceEvidence(
        source_id=source_id,
        platform=platform,
        title=f"{platform}核验来源",
        url_or_reference=f"https://example.test/{source_id}",
        evidence_type=evidence_type,
        published_at=datetime(2026, 8, 6, 1, tzinfo=UTC),
        reliability_note="核心事实已交叉核验",
    )


def candidate(
    candidate_id: str,
    *,
    fact_status: FactStatus = FactStatus.VERIFIED,
    risk_flags: list[str] | None = None,
    score: float = 90,
) -> TopicCandidate:
    verified = fact_status is FactStatus.VERIFIED
    return TopicCandidate(
        id=candidate_id,
        title=f"热点 {candidate_id}",
        pillar="social_phenomena",
        score=score,
        fact_status=fact_status,
        risk_flags=risk_flags or [],
        source_evidence=[
            source("official-1", "official", "official"),
            source("media-1", "reputable_media", "reputable_media"),
        ],
        verification_summary="官方来源与独立媒体已交叉核验" if verified else None,
        publishable=False,
    )


def saved_host() -> HostProfile:
    return HostProfile(
        id=HOST_ID,
        display_name="固定坐播主持人",
        reference_image="assets/fixed-seated-anchor.png",
        studio_reference="assets/quiet-news-studio.png",
        voice_id="mature-news-voice",
        is_new=False,
    )


def script_and_plan(*, use_ai_fallback: bool = False) -> tuple[NewsScript, MediaPlan]:
    script = NewsScript(
        title="经核验的热点解读",
        spoken_segments=[
            ScriptSegment(
                id="opening-fact",
                kind="fact",
                text="先说明已经核验的核心事实。",
                source_ids=["official-1"],
            ),
            ScriptSegment(
                id="context",
                kind="context",
                text="再补充背景与影响。",
                source_ids=["media-1"],
            ),
            ScriptSegment(
                id="conclusion",
                kind="conclusion",
                text="最后给出克制的总结。",
                source_ids=["official-1", "media-1"],
            ),
        ],
        source_ids=["official-1", "media-1"],
        ai_disclosure_required=use_ai_fallback,
        target_duration_seconds=60,
    )
    insert = MediaSegment(
        id="insert-1",
        kind=MediaKind.AI_DEMO if use_ai_fallback else MediaKind.ORIGINAL_NEWS,
        start_seconds=18,
        end_seconds=42,
        script_segment_id="context",
        source_id=None if use_ai_fallback else "official-1",
        provenance=None if use_ai_fallback else "官方公开视频 00:10-00:34 合规截取",
        disclosure="AI生成示意画面，非新闻现场实拍" if use_ai_fallback else None,
        asset_path=None,
    )
    plan = MediaPlan(
        duration_seconds=60,
        host_id=HOST_ID,
        segments=[
            MediaSegment(
                id="anchor-open",
                kind=MediaKind.ANCHOR,
                start_seconds=0,
                end_seconds=18,
                script_segment_id="opening-fact",
                host_id=HOST_ID,
            ),
            insert,
            MediaSegment(
                id="anchor-close",
                kind=MediaKind.ANCHOR,
                start_seconds=42,
                end_seconds=60,
                script_segment_id="conclusion",
                host_id=HOST_ID,
            ),
        ],
    )
    return script, plan


def fake_crawler(
    service: DailyWorkflowService,
    day: date,
    candidates: list[TopicCandidate],
    calls: Counter,
) -> list[TopicCandidate]:
    calls["crawler"] += 1
    task = service.get(day)
    task.artifacts.append(ArtifactRecord(kind="source_record", path=SOURCE_RECORD))
    service.repository.save(task)
    return candidates


def managed_providers(
    calls: Counter,
    *,
    use_ai_fallback: bool = False,
) -> ManagedProviders:
    host = saved_host()

    def write_script(selected: TopicCandidate) -> tuple[NewsScript, MediaPlan]:
        calls["script"] += 1
        assert selected.fact_status is FactStatus.VERIFIED
        assert selected.publishable is True
        return script_and_plan(use_ai_fallback=use_ai_fallback)

    def provide_host() -> HostProfile:
        calls["host"] += 1
        return host

    def generate_tts(script: NewsScript) -> str:
        calls["tts"] += 1
        assert script.target_duration_seconds == 60
        return "audio/master.wav"

    def generate_avatar(selected_host: HostProfile, audio_path: str) -> str:
        calls["avatar"] += 1
        assert selected_host.id == HOST_ID
        assert selected_host.layout is AvatarLayout.SEATED_STUDIO_ANCHOR
        assert audio_path == "audio/master.wav"
        return "video/anchor.mp4"

    def acquire_media(plan: MediaPlan) -> str:
        calls["media"] += 1
        inserts = [segment for segment in plan.segments if segment.kind is not MediaKind.ANCHOR]
        assert len(inserts) == 1
        if inserts[0].kind is MediaKind.ORIGINAL_NEWS:
            calls["footage_clipper"] += 1
            assert inserts[0].provenance
            return "media/original-news-clip.mp4"
        calls["seedance"] += 1
        assert "AI生成" in (inserts[0].disclosure or "")
        return "media/ai-demo.mp4"

    def composite(task) -> str:
        calls["composite"] += 1
        assert task.subtitle_enabled is False
        assert task.media_plan.subtitle_enabled is False
        assert {artifact.kind for artifact in task.artifacts} >= {
            "source_record",
            "master_audio",
            "anchor_video",
            "insert_media",
        }
        return "video/final-master.mp4"

    def quality_control(task) -> tuple[bool, str]:
        calls["qc"] += 1
        assert task.artifacts[-1].kind == "master_video"
        return True, "qc/final-passed.json"

    return ManagedProviders(
        script=write_script,
        host=provide_host,
        tts=generate_tts,
        anchor=generate_avatar,
        media=acquire_media,
        composite=composite,
        qc=quality_control,
        host_source=AvatarSource.SAVED_HOST,
    )


def test_managed_end_to_end_prefers_verified_original_news_and_builds_one_package(tmp_path):
    repository = DailyTaskRepository(tmp_path)
    service = DailyWorkflowService(repository)
    service.start_day(DAY, mode=RunMode.MANAGED, input_text="自动抓取今日可靠热点")
    calls = Counter()
    crawled = fake_crawler(
        service,
        DAY,
        [
            candidate("unverified", fact_status=FactStatus.UNVERIFIED, score=99),
            candidate("malicious", risk_flags=["malicious_claim"], score=98),
            candidate("verified", score=95),
        ],
        calls,
    )

    result = run_managed(service, DAY, crawled, managed_providers(calls))
    persisted = repository.get(DAY)
    package = build_publication_package(persisted)

    assert result == persisted
    assert persisted.status is TaskStatus.READY_TO_PUBLISH
    assert [item.id for item in persisted.candidates] == ["verified"]
    assert {item.id for item in persisted.skipped_candidates} == {"unverified", "malicious"}
    assert persisted.host_profile == saved_host()
    assert persisted.media_plan.anchor_layout is AvatarLayout.SEATED_STUDIO_ANCHOR
    assert [segment.kind for segment in persisted.media_plan.segments] == [
        MediaKind.ANCHOR,
        MediaKind.ORIGINAL_NEWS,
        MediaKind.ANCHOR,
    ]
    assert persisted.subtitle_enabled is False
    assert persisted.media_plan.subtitle_enabled is False
    assert persisted.approvals == []
    assert calls == Counter(
        crawler=1,
        script=1,
        host=1,
        tts=1,
        avatar=1,
        media=1,
        footage_clipper=1,
        composite=1,
        qc=1,
    )
    assert package.master_video_path == "video/final-master.mp4"
    assert package.ai_disclosures == []
    assert set(package.platforms) == {"douyin", "wechat_channels", "xiaohongshu"}
    assert {item.master_video_path for item in package.platforms.values()} == {
        package.master_video_path
    }


def test_managed_end_to_end_ai_fallback_is_disclosed_and_publishable(tmp_path):
    repository = DailyTaskRepository(tmp_path)
    service = DailyWorkflowService(repository)
    service.start_day(DAY, mode=RunMode.MANAGED)
    calls = Counter()
    crawled = fake_crawler(service, DAY, [candidate("verified")], calls)

    result = run_managed(
        service,
        DAY,
        crawled,
        managed_providers(calls, use_ai_fallback=True),
    )
    package = build_publication_package(repository.get(DAY))

    assert result.status is TaskStatus.READY_TO_PUBLISH
    assert calls["footage_clipper"] == 0
    assert calls["seedance"] == 1
    assert [item.disclosure for item in package.ai_disclosures] == [
        "AI生成示意画面，非新闻现场实拍"
    ]
    assert all(
        platform.ai_demo_note == "AI生成示意画面，非新闻现场实拍"
        for platform in package.platforms.values()
    )


def test_manual_saved_host_reuse_has_only_topic_and_final_approvals(tmp_path):
    repository = DailyTaskRepository(tmp_path)
    service = DailyWorkflowService(repository)
    task = service.start_day(DAY, mode=RunMode.MANUAL)
    task.host_profile = saved_host()
    task.avatar_source = AvatarSource.SAVED_HOST
    task.artifacts.append(ArtifactRecord(kind="source_record", path=SOURCE_RECORD))
    repository.save(task)
    script, plan = script_and_plan()

    service.record_research(DAY, [candidate("verified")])
    planned = service.record_script_and_media_plan(DAY, "verified", script, plan)
    assert planned.status is TaskStatus.TOPIC_SCRIPT_REVIEW

    topic_approved = service.approve_topic_script(DAY, actor="owner")
    assert topic_approved.status is TaskStatus.GENERATING_TTS
    assert topic_approved.requires_host_approval is False

    service.mark_tts_ready(DAY, artifact_path="audio/master.wav")
    service.mark_anchor_ready(DAY, artifact_path="video/anchor.mp4")
    service.mark_media_ready(DAY, artifact_path="media/original-news-clip.mp4")
    service.mark_compositing(DAY, artifact_path="video/final-master.mp4")
    final_review = service.record_qc(DAY, passed=True, report_path="qc/final-passed.json")
    assert final_review.status is TaskStatus.FINAL_REVIEW

    completed = service.approve_final_video(DAY, actor="owner")
    persisted = repository.get(DAY)
    package = build_publication_package(persisted)

    assert completed == persisted
    assert [approval.gate for approval in persisted.approvals] == [
        "topic_script",
        "final_video",
    ]
    assert "host" not in {approval.gate for approval in persisted.approvals}
    assert len({approval.gate for approval in persisted.approvals}) <= 3
    assert package.master_video_path == "video/final-master.mp4"


@pytest.mark.parametrize(
    "candidates",
    [
        [],
        [candidate("unverified", fact_status=FactStatus.UNVERIFIED)],
        [candidate("unsafe", risk_flags=["malicious_claim"])],
    ],
)
def test_managed_unsafe_or_empty_candidates_stop_without_generation_or_publication(
    tmp_path, candidates
):
    repository = DailyTaskRepository(tmp_path)
    service = DailyWorkflowService(repository)
    service.start_day(DAY, mode=RunMode.MANAGED)
    calls = Counter()
    crawled = fake_crawler(service, DAY, candidates, calls)

    result = run_managed(service, DAY, crawled, managed_providers(calls))

    assert result.status is TaskStatus.STOPPED
    assert result.stop_reason == "no verified hotspot"
    assert calls == Counter(crawler=1)
    with pytest.raises(ValueError, match="ready_to_publish"):
        build_publication_package(repository.get(DAY))


def test_managed_checkpoint_resume_does_not_repeat_completed_providers(tmp_path):
    repository = DailyTaskRepository(tmp_path)
    service = DailyWorkflowService(repository)
    task = service.start_day(DAY, mode=RunMode.MANAGED)
    task.host_profile = saved_host()
    task.avatar_source = AvatarSource.SAVED_HOST
    task.artifacts.append(ArtifactRecord(kind="source_record", path=SOURCE_RECORD))
    repository.save(task)
    script, plan = script_and_plan()
    service.record_research(DAY, [candidate("verified")])
    service.record_script_and_media_plan(DAY, "verified", script, plan)
    service.set_host(DAY, saved_host(), avatar_source=AvatarSource.SAVED_HOST)
    service.mark_tts_ready(DAY, artifact_path="audio/master.wav")
    assert repository.get(DAY).status is TaskStatus.GENERATING_ANCHOR

    calls = Counter()
    providers = managed_providers(calls)
    result = run_managed(service, DAY, [candidate("must-not-be-recrawled")], providers)

    assert result.status is TaskStatus.READY_TO_PUBLISH
    assert calls["script"] == 0
    assert calls["host"] == 0
    assert calls["tts"] == 0
    assert calls["avatar"] == 1
    assert calls["media"] == 1
    assert calls["composite"] == 1
    assert calls["qc"] == 1
    assert [artifact.kind for artifact in result.artifacts].count("master_audio") == 1


def test_health_config_and_skill_contracts_match_dual_mode_seated_news_design(tmp_path):
    config = load_config(Path("configs/default.yaml"))
    contracts = load_contracts(Path("skills/contracts"))
    args = build_parser().parse_args(["--workspace", str(tmp_path), "health"])
    health = dispatch(args)

    assert health["supported_modes"] == ["managed", "manual"]
    assert health["topic_sources"] == ["user_topic", "auto_hot"]
    assert health["host_layout"] == "seated_studio_anchor"
    assert health["video_structure"] == "studio_anchor_plus_vertical_news_insert"
    assert health["subtitle"] is False
    assert health["manual_approval_commands"] == [
        "approve-topic-script",
        "approve-host",
        "approve-final-video",
    ]
    assert config.avatar_layout == "seated_studio_anchor"
    assert config.host_visual.shot == "waist_up_seated"
    assert config.host_visual.subtitle_default is False
    assert config.approval_policy.managed.topic_script == "auto"
    assert config.approval_policy.manual.avatar == "confirm_if_new_or_changed"
    assert contracts[SkillKind.AVATAR].provider == "giggle-generation-tv-avatar-video"
    assert contracts[SkillKind.AVATAR].primary_mode == "image_plus_audio"
    assert contracts[SkillKind.AVATAR].required_inputs["layout"] == "seated_studio_anchor"
    assert contracts[SkillKind.FOOTAGE_CLIPPER].real_generation_enabled is False
    assert contracts[SkillKind.SEEDANCE].real_generation_enabled is False
    assert "默认不添加逐字口播字幕" in contracts[SkillKind.COMPOSITOR].safety_constraints
    assert (
        "检查标题安全区和默认无逐字字幕规则"
        in contracts[SkillKind.QUALITY_CONTROL].safety_constraints
    )
