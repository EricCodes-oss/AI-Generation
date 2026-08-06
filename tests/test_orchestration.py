from datetime import date

from avatar_pipeline.models import (
    AvatarSource,
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


def providers(*, host=None, host_source=None, anchor=None):
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
    provider_kwargs = {} if host_source is None else {"host_source": host_source}
    return ManagedProviders(
        script=lambda selected: (script, plan),
        host=host
        or (
            lambda: HostProfile(
                id="host", display_name="主持人", reference_image="host.png", is_new=True
            )
        ),
        tts=lambda script: "audio.wav",
        anchor=anchor or (lambda host, audio: "anchor.mp4"),
        media=lambda plan: "demo.mp4",
        composite=lambda task: "master.mp4",
        qc=lambda task: (True, "qc.json"),
        **provider_kwargs,
    )


def test_managed_run_completes_without_user_confirmation_records(tmp_path):
    service = DailyWorkflowService(DailyTaskRepository(tmp_path))
    task = service.start_day(date(2026, 8, 6), mode=RunMode.MANAGED)
    result = run_managed(
        service, task.day, [topic("pending", "pending"), topic("verified")], providers()
    )
    assert result.status is TaskStatus.READY_TO_PUBLISH
    assert result.approvals == []
    assert result.avatar_source is AvatarSource.SAVED_HOST
    assert any(item.path == "master.mp4" for item in result.artifacts)


def test_managed_run_stops_when_no_verified_topic_exists(tmp_path):
    service = DailyWorkflowService(DailyTaskRepository(tmp_path))
    task = service.start_day(date(2026, 8, 6), mode=RunMode.MANAGED)
    result = run_managed(service, task.day, [topic("pending", "pending")], providers())
    assert result.status is TaskStatus.STOPPED
    assert "verified" in (result.stop_reason or "")


def test_managed_run_marks_provider_host_source_and_calls_provider_once(tmp_path):
    service = DailyWorkflowService(DailyTaskRepository(tmp_path))
    task = service.start_day(date(2026, 8, 6), mode=RunMode.MANAGED)
    host = HostProfile(
        id="designed-host",
        display_name="主持人",
        reference_image="designed-host.png",
        is_new=True,
    )
    host_calls = []
    anchor_hosts = []

    result = run_managed(
        service,
        task.day,
        [topic("verified")],
        providers(
            host=lambda: host_calls.append("host") or host,
            host_source=AvatarSource.AGENT_DESIGNED,
            anchor=lambda selected_host, audio: anchor_hosts.append(selected_host) or "anchor.mp4",
        ),
    )

    assert host_calls == ["host"]
    assert result.avatar_source is AvatarSource.AGENT_DESIGNED
    assert result.host_profile == host
    assert anchor_hosts == [host]
    assert anchor_hosts[0] is host
    assert anchor_hosts[0].reference_image == "designed-host.png"
    assert result.approvals == []


def test_managed_run_reuses_preset_saved_host_without_provider_call(tmp_path):
    service = DailyWorkflowService(DailyTaskRepository(tmp_path))
    day = date(2026, 8, 6)
    saved_host = HostProfile(
        id="saved-host",
        display_name="林知遥",
        reference_image="hosts/saved.png",
        is_new=False,
    )
    service.start_day(day, mode=RunMode.MANAGED)
    service.record_research(day, [topic("verified")])
    staged_providers = providers()
    script, plan = staged_providers.script(topic("verified"))
    service.record_script_and_media_plan(day, "verified", script, plan)
    preset = service.get(day)
    preset.host_profile = saved_host
    preset.avatar_source = AvatarSource.SAVED_HOST
    service.repository.save(preset)
    host_calls = []
    anchor_hosts = []

    result = run_managed(
        service,
        day,
        [topic("verified")],
        providers(
            host=lambda: (
                host_calls.append("host")
                or HostProfile(
                    id="unexpected",
                    display_name="不应创建",
                    reference_image="unexpected.png",
                    is_new=True,
                )
            ),
            host_source=AvatarSource.AGENT_DESIGNED,
            anchor=lambda selected_host, audio: anchor_hosts.append(selected_host) or "anchor.mp4",
        ),
    )

    assert host_calls == []
    assert result.avatar_source is AvatarSource.SAVED_HOST
    assert result.host_profile == saved_host
    assert anchor_hosts == [saved_host]
    assert result.approvals == []


def test_managed_run_marks_user_provided_host_source(tmp_path):
    service = DailyWorkflowService(DailyTaskRepository(tmp_path))
    task = service.start_day(date(2026, 8, 6), mode=RunMode.MANAGED)

    result = run_managed(
        service,
        task.day,
        [topic("verified")],
        providers(host_source=AvatarSource.USER_PROVIDED),
    )

    assert result.avatar_source is AvatarSource.USER_PROVIDED
    assert result.approvals == []
