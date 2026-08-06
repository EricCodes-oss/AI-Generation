from datetime import date

import pytest

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


def providers(*, host_profile=None, host_provider=None, host_source=None, anchor=None):
    selected_host = host_profile or HostProfile(
        id="host",
        display_name="主持人",
        reference_image="host.png",
        is_new=True,
    )
    script = NewsScript(
        title="标题",
        spoken_segments=[ScriptSegment(id="s1", kind="fact", text="事实", source_ids=["s1"])],
        source_ids=["s1", "s2"],
    )
    plan = MediaPlan(
        duration_seconds=15,
        host_id=selected_host.id,
        segments=[
            MediaSegment(
                id="a",
                kind=MediaKind.ANCHOR,
                start_seconds=0,
                end_seconds=5,
                script_segment_id="s1",
                host_id=selected_host.id,
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
                host_id=selected_host.id,
            ),
        ],
    )
    provider_kwargs = {} if host_source is None else {"host_source": host_source}
    return ManagedProviders(
        script=lambda selected: (script, plan),
        host=host_provider or (lambda: selected_host),
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


def test_managed_run_retries_next_verified_candidate_after_script_provider_failure(tmp_path):
    service = DailyWorkflowService(DailyTaskRepository(tmp_path))
    day = date(2026, 8, 6)
    service.start_day(day, mode=RunMode.MANAGED)
    calls = []
    base = providers()

    def script_provider(selected):
        calls.append(selected.id)
        if selected.id == "first":
            raise RuntimeError("script provider unavailable for first topic")
        return base.script(selected)

    managed_providers = ManagedProviders(
        script=script_provider,
        host=base.host,
        tts=base.tts,
        anchor=base.anchor,
        media=base.media,
        composite=base.composite,
        qc=base.qc,
    )

    result = run_managed(service, day, [topic("first"), topic("second")], managed_providers)

    assert result.status is TaskStatus.READY_TO_PUBLISH
    assert result.selected_topic_id == "second"
    assert calls == ["first", "second"]
    assert [item.id for item in result.skipped_candidates] == ["first"]
    assert any(item.kind == "managed_attempt_failure" for item in result.artifacts)


def test_managed_run_retries_next_verified_candidate_after_downstream_provider_failure(tmp_path):
    service = DailyWorkflowService(DailyTaskRepository(tmp_path))
    day = date(2026, 8, 6)
    service.start_day(day, mode=RunMode.MANAGED)
    base = providers()
    tts_calls = []

    def tts_provider(script):
        tts_calls.append(script.title)
        if len(tts_calls) == 1:
            raise RuntimeError("tts failed for first topic")
        return "audio-second.wav"

    managed_providers = ManagedProviders(
        script=lambda selected: (
            base.script(selected)[0].model_copy(update={"title": selected.id}),
            base.script(selected)[1],
        ),
        host=base.host,
        tts=tts_provider,
        anchor=base.anchor,
        media=base.media,
        composite=base.composite,
        qc=base.qc,
    )

    result = run_managed(service, day, [topic("first"), topic("second")], managed_providers)

    assert result.status is TaskStatus.READY_TO_PUBLISH
    assert result.selected_topic_id == "second"
    assert tts_calls == ["first", "second"]
    assert not any(
        item.kind == "master_audio" and item.path != "audio-second.wav" for item in result.artifacts
    )


def test_managed_run_stops_only_after_bounded_candidate_attempts_are_exhausted(tmp_path):
    service = DailyWorkflowService(DailyTaskRepository(tmp_path))
    day = date(2026, 8, 6)
    service.start_day(day, mode=RunMode.MANAGED)
    calls = []
    base = providers()

    def failing_script(selected):
        calls.append(selected.id)
        raise RuntimeError("no script")

    managed_providers = ManagedProviders(
        script=failing_script,
        host=base.host,
        tts=base.tts,
        anchor=base.anchor,
        media=base.media,
        composite=base.composite,
        qc=base.qc,
    )

    result = run_managed(
        service,
        day,
        [topic("first"), topic("second"), topic("third")],
        managed_providers,
        max_topic_attempts=2,
    )

    assert result.status is TaskStatus.STOPPED
    assert calls == ["first", "second"]
    assert "2 managed topic attempts failed" in (result.stop_reason or "")


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
            host_profile=host,
            host_provider=lambda: host_calls.append("host") or host,
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
    staged_providers = providers(host_profile=saved_host)
    script, plan = staged_providers.script(topic("verified"))
    service.record_script_and_media_plan(day, "verified", script, plan)
    preset = service.get(day)
    preset.host_profile = saved_host
    preset.avatar_source = AvatarSource.SAVED_HOST
    service.repository.save(preset)
    host_calls = []
    anchor_hosts = []

    unexpected_host = HostProfile(
        id="unexpected",
        display_name="不应创建",
        reference_image="unexpected.png",
        is_new=True,
    )
    result = run_managed(
        service,
        day,
        [topic("verified")],
        providers(
            host_profile=unexpected_host,
            host_provider=lambda: host_calls.append("host") or unexpected_host,
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


def stage_managed_checkpoint(service, day, checkpoint):
    service.start_day(day, mode=RunMode.MANAGED)
    if checkpoint is TaskStatus.STOPPED:
        return service.record_research(day, [topic("pending", "pending")])

    service.record_research(day, [topic("verified")])
    checkpoint_host = HostProfile(
        id="host",
        display_name="林知遥",
        reference_image="hosts/saved.png",
        is_new=False,
    )
    staged_providers = providers(host_profile=checkpoint_host)
    script, plan = staged_providers.script(topic("verified"))
    service.record_script_and_media_plan(day, "verified", script, plan)
    if checkpoint is TaskStatus.MEDIA_PLANNING:
        return service.get(day)

    service.set_host(
        day,
        checkpoint_host,
        avatar_source=AvatarSource.SAVED_HOST,
    )
    if checkpoint is TaskStatus.GENERATING_TTS:
        return service.get(day)

    service.mark_tts_ready(day, artifact_path="audio.wav")
    if checkpoint is TaskStatus.GENERATING_ANCHOR:
        return service.get(day)

    service.mark_anchor_ready(day, artifact_path="anchor.mp4")
    if checkpoint is TaskStatus.ACQUIRING_OR_GENERATING_MEDIA:
        return service.get(day)

    service.mark_media_ready(day, artifact_path="demo.mp4")
    if checkpoint is TaskStatus.COMPOSITING:
        return service.get(day)

    service.mark_compositing(day, artifact_path="master.mp4")
    if checkpoint is TaskStatus.QUALITY_CHECK:
        return service.get(day)

    return service.record_qc(day, passed=True, report_path="qc.json")


def recording_providers(calls, *, qc_result=(True, "qc-resumed.json")):
    base = providers()
    return ManagedProviders(
        script=lambda selected: calls.append("script") or base.script(selected),
        host=lambda: calls.append("host") or base.host(),
        tts=lambda script: calls.append("tts") or "audio-resumed.wav",
        anchor=lambda host, audio: calls.append("anchor") or "anchor-resumed.mp4",
        media=lambda plan: calls.append("media") or "demo-resumed.mp4",
        composite=lambda task: calls.append("composite") or "master-resumed.mp4",
        qc=lambda task: calls.append("qc") or qc_result,
    )


@pytest.mark.parametrize(
    ("checkpoint", "expected_calls", "expected_status"),
    [
        (
            TaskStatus.MEDIA_PLANNING,
            ["host", "tts", "anchor", "media", "composite", "qc"],
            TaskStatus.READY_TO_PUBLISH,
        ),
        (
            TaskStatus.GENERATING_TTS,
            ["tts", "anchor", "media", "composite", "qc"],
            TaskStatus.READY_TO_PUBLISH,
        ),
        (
            TaskStatus.GENERATING_ANCHOR,
            ["anchor", "media", "composite", "qc"],
            TaskStatus.READY_TO_PUBLISH,
        ),
        (
            TaskStatus.ACQUIRING_OR_GENERATING_MEDIA,
            ["media", "composite", "qc"],
            TaskStatus.READY_TO_PUBLISH,
        ),
        (
            TaskStatus.COMPOSITING,
            ["composite", "qc"],
            TaskStatus.READY_TO_PUBLISH,
        ),
        (TaskStatus.QUALITY_CHECK, ["qc"], TaskStatus.READY_TO_PUBLISH),
        (TaskStatus.READY_TO_PUBLISH, [], TaskStatus.READY_TO_PUBLISH),
        (TaskStatus.STOPPED, [], TaskStatus.STOPPED),
    ],
)
def test_managed_run_resumes_from_checkpoint_without_repeating_completed_providers(
    tmp_path, checkpoint, expected_calls, expected_status
):
    service = DailyWorkflowService(DailyTaskRepository(tmp_path))
    day = date(2026, 8, 6)
    staged = stage_managed_checkpoint(service, day, checkpoint)
    original_script = staged.news_script
    original_plan = staged.media_plan
    calls = []

    result = run_managed(
        service,
        day,
        [topic("replacement-that-must-not-be-researched")],
        recording_providers(calls),
    )

    assert result.status is expected_status
    assert calls == expected_calls
    assert result.news_script == original_script
    assert result.media_plan == original_plan


def test_managed_run_safely_stops_when_checkpoint_qc_fails_without_replacement(tmp_path):
    service = DailyWorkflowService(DailyTaskRepository(tmp_path))
    day = date(2026, 8, 6)
    stage_managed_checkpoint(service, day, TaskStatus.COMPOSITING)
    calls = []

    result = run_managed(
        service,
        day,
        [topic("replacement-that-must-not-research-active-checkpoint")],
        recording_providers(calls, qc_result=(False, "qc-failed.json")),
    )

    assert result.status is TaskStatus.STOPPED
    assert calls == ["composite", "qc"]
    assert result.selected_topic_id is None
    assert [item.id for item in result.skipped_candidates] == ["verified"]
    assert result.stop_reason == "managed generation failed: quality check failed: qc-failed.json"
    assert not any(
        item.kind in {"master_audio", "anchor_video", "insert_media", "master_video", "qc_report"}
        for item in result.artifacts
    )
    assert any(
        item.kind == "managed_attempt_failure"
        and item.metadata["reason"] == "quality check failed: qc-failed.json"
        for item in result.artifacts
    )


def test_managed_run_safely_stops_when_resumed_provider_fails(tmp_path):
    service = DailyWorkflowService(DailyTaskRepository(tmp_path))
    day = date(2026, 8, 6)
    stage_managed_checkpoint(service, day, TaskStatus.QUALITY_CHECK)
    calls = []
    managed_providers = recording_providers(calls)
    managed_providers = ManagedProviders(
        script=managed_providers.script,
        host=managed_providers.host,
        tts=managed_providers.tts,
        anchor=managed_providers.anchor,
        media=managed_providers.media,
        composite=managed_providers.composite,
        qc=lambda task: (_ for _ in ()).throw(RuntimeError("qc unavailable")),
    )

    result = run_managed(service, day, [topic("verified")], managed_providers)

    assert result.status is TaskStatus.STOPPED
    assert result.stop_reason == "managed generation failed: qc unavailable"


def test_managed_run_safely_stops_when_host_provider_does_not_match_media_plan(tmp_path):
    service = DailyWorkflowService(DailyTaskRepository(tmp_path))
    day = date(2026, 8, 6)
    service.start_day(day, mode=RunMode.MANAGED)
    planned_host = HostProfile(
        id="planned-host",
        display_name="林知遥",
        reference_image="planned-host.png",
        is_new=False,
    )
    mismatched_host = HostProfile(
        id="different-host",
        display_name="另一位主持人",
        reference_image="different-host.png",
        is_new=True,
    )

    result = run_managed(
        service,
        day,
        [topic("verified")],
        providers(
            host_profile=planned_host,
            host_provider=lambda: mismatched_host,
            host_source=AvatarSource.AGENT_DESIGNED,
        ),
    )

    assert result.status is TaskStatus.STOPPED
    assert result.host_profile is None
    assert result.stop_reason == (
        "managed generation failed: media plan host_id must match the fixed host profile"
    )


def test_managed_run_retries_next_verified_candidate_after_failed_qc(tmp_path):
    service = DailyWorkflowService(DailyTaskRepository(tmp_path))
    day = date(2026, 8, 6)
    service.start_day(day, mode=RunMode.MANAGED)
    base = providers()
    qc_calls = []

    def script_provider(selected):
        script, plan = base.script(selected)
        return script.model_copy(update={"title": selected.id}), plan

    def qc_provider(task):
        qc_calls.append(task.news_script.title)
        if len(qc_calls) == 1:
            return False, "qc-first-failed.json"
        return True, "qc-second-passed.json"

    managed_providers = ManagedProviders(
        script=script_provider,
        host=base.host,
        tts=base.tts,
        anchor=base.anchor,
        media=base.media,
        composite=base.composite,
        qc=qc_provider,
    )

    result = run_managed(service, day, [topic("first"), topic("second")], managed_providers)

    assert result.status is TaskStatus.READY_TO_PUBLISH
    assert result.selected_topic_id == "second"
    assert qc_calls == ["first", "second"]
    assert [item.id for item in result.skipped_candidates] == ["first"]
    assert any(
        item.kind == "managed_attempt_failure"
        and item.metadata["reason"] == "quality check failed: qc-first-failed.json"
        for item in result.artifacts
    )
