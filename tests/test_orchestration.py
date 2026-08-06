from datetime import date

from avatar_pipeline.models import (
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
from avatar_pipeline.repository import DailyTaskRepository
from avatar_pipeline.service import DailyWorkflowService


def topic(topic_id, status="verified"):
    return TopicCandidate(
        id=topic_id,
        title=topic_id,
        pillar="social_phenomena",
        score=90,
        fact_status=status,
        source_evidence=[
            SourceEvidence(
                source_id="s1",
                platform="official",
                title="官方",
                url_or_reference="s1",
                evidence_type="primary",
            ),
            SourceEvidence(
                source_id="s2",
                platform="media",
                title="媒体",
                url_or_reference="s2",
                evidence_type="corroboration",
            ),
        ],
        verification_summary="双源确认" if status == "verified" else None,
        publishable=status == "verified",
    )


def providers():
    script = NewsScript(
        title="标题",
        spoken_segments=[ScriptSegment(id="s1", kind="fact", text="事实", source_ids=["s1"])],
        source_ids=["s1", "s2"],
    )
    plan = MediaPlan(
        duration_seconds=15,
        segments=[
            MediaSegment(
                id="a",
                kind=MediaKind.ANCHOR,
                start_seconds=0,
                end_seconds=5,
                script_segment_id="s1",
            ),
            MediaSegment(
                id="d",
                kind=MediaKind.AI_DEMO,
                start_seconds=5,
                end_seconds=10,
                script_segment_id="s1",
                disclosure="AI生成示意画面",
            ),
            MediaSegment(
                id="b",
                kind=MediaKind.ANCHOR,
                start_seconds=10,
                end_seconds=15,
                script_segment_id="s1",
            ),
        ],
    )
    return ManagedProviders(
        script=lambda selected: (script, plan),
        host=lambda: HostProfile(
            id="host", display_name="主持人", reference_image="host.png", is_new=True
        ),
        tts=lambda script: "audio.wav",
        anchor=lambda host, audio: "anchor.mp4",
        media=lambda plan: "demo.mp4",
        composite=lambda task: "master.mp4",
        qc=lambda task: (True, "qc.json"),
    )


def test_managed_run_completes_without_user_confirmation_records(tmp_path):
    service = DailyWorkflowService(DailyTaskRepository(tmp_path))
    task = service.start_day(date(2026, 8, 6), mode=RunMode.MANAGED)
    result = run_managed(
        service, task.day, [topic("pending", "pending"), topic("verified")], providers()
    )
    assert result.status is TaskStatus.READY_TO_PUBLISH
    assert result.approvals == []
    assert any(item.path == "master.mp4" for item in result.artifacts)


def test_managed_run_stops_when_no_verified_topic_exists(tmp_path):
    service = DailyWorkflowService(DailyTaskRepository(tmp_path))
    task = service.start_day(date(2026, 8, 6), mode=RunMode.MANAGED)
    result = run_managed(service, task.day, [topic("pending", "pending")], providers())
    assert result.status is TaskStatus.STOPPED
    assert "verified" in (result.stop_reason or "")
