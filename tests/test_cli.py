import json
import os
import subprocess
import sys
from datetime import date

from avatar_pipeline.models import (
    ApprovalRecord,
    AvatarSource,
    DailyTask,
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
from avatar_pipeline.repository import DailyTaskRepository


def run_cli(tmp_path, *args, env_overrides=None):
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([str(tmp_path), "src"])
    if env_overrides:
        env.update(env_overrides)
    return subprocess.run(
        [sys.executable, "-m", "avatar_pipeline.cli", "--workspace", str(tmp_path), *args],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )


def host(*, image="host.png", is_new=False):
    return HostProfile(
        id="fixed-seated-anchor",
        display_name="林知遥",
        reference_image=image,
        is_new=is_new,
    )


def review_task(day: date, *, host_profile: HostProfile, avatar_source: AvatarSource):
    evidence = [
        SourceEvidence(
            source_id="s1",
            platform="official",
            title="官方来源",
            url_or_reference="https://example.test/s1",
            evidence_type="official",
        ),
        SourceEvidence(
            source_id="s2",
            platform="media",
            title="媒体来源",
            url_or_reference="https://example.test/s2",
            evidence_type="corroboration",
        ),
    ]
    candidate = TopicCandidate(
        id="t1",
        title="已核实热点",
        pillar="social_phenomena",
        score=95,
        fact_status=FactStatus.VERIFIED,
        source_evidence=evidence,
        verification_summary="双来源核验",
        publishable=True,
    )
    script = NewsScript(
        title="热点解读",
        spoken_segments=[ScriptSegment(id="seg1", kind="fact", text="事实内容", source_ids=["s1"])],
        source_ids=["s1", "s2"],
    )
    plan = MediaPlan(
        duration_seconds=10,
        host_id=host_profile.id,
        segments=[
            MediaSegment(
                id="a1",
                kind=MediaKind.ANCHOR,
                start_seconds=0,
                end_seconds=3,
                script_segment_id="seg1",
            ),
            MediaSegment(
                id="n1",
                kind=MediaKind.ORIGINAL_NEWS,
                start_seconds=3,
                end_seconds=7,
                script_segment_id="seg1",
                source_id="s1",
                provenance="官方公开视频",
            ),
            MediaSegment(
                id="a2",
                kind=MediaKind.ANCHOR,
                start_seconds=7,
                end_seconds=10,
                script_segment_id="seg1",
            ),
        ],
    )
    return DailyTask(
        day=day,
        mode=RunMode.MANUAL,
        avatar_source=avatar_source,
        status=TaskStatus.SCRIPT_REVIEW,
        candidates=[candidate],
        selected_topic_id="t1",
        host_profile=host_profile,
        news_script=script,
        media_plan=plan,
    )


def test_cli_initializes_news_day_with_explicit_mode_and_topic_source(tmp_path):
    created = run_cli(
        tmp_path,
        "init-day",
        "--date",
        "2026-08-06",
        "--mode",
        "manual",
        "--topic-source",
        "auto_hot",
    )
    assert created.returncode == 0
    payload = json.loads(created.stdout)
    assert payload["status"] == "input_received"
    assert payload["mode"] == "manual"
    assert payload["topic_source"] == "auto_hot"
    assert payload["avatar_source"] == "saved_host"
    assert payload["host_profile"]["id"] == "fixed-seated-anchor"
    assert payload["host_profile"]["display_name"] == "林知遥"
    assert payload["host_profile"]["reference_image"] == (
        "assets/hosts/fixed-seated-anchor/master-reference.png"
    )
    assert payload["host_profile"]["voice_id"] == "宣传女生Pro:clone_20260806_114837_980375"
    assert payload["host_profile"]["is_new"] is False


def test_cli_managed_init_requires_configured_runtime_before_creating_task(tmp_path):
    created = run_cli(
        tmp_path,
        "init-day",
        "--date",
        "2026-08-06",
        "--mode",
        "managed",
        "--topic-source",
        "user_topic",
        "--input",
        "年轻人如何看待工作和生活的边界",
    )
    assert created.returncode == 2
    assert "AVATAR_PIPELINE_MANAGED_RUNTIME" in created.stderr
    assert DailyTaskRepository(tmp_path).list_days() == []


def test_cli_managed_init_executes_configured_runtime_to_final_result(tmp_path):
    runtime_module = tmp_path / "managed_runtime_fixture.py"
    runtime_module.write_text(
        """
from avatar_pipeline.managed_runtime import ManagedRunInput
from avatar_pipeline.models import (
    FactStatus, HostProfile, MediaKind, MediaPlan, MediaSegment, NewsScript,
    ScriptSegment, SourceEvidence, TopicCandidate,
)
from avatar_pipeline.orchestration import ManagedProviders

def create_runtime(task):
    host = HostProfile(
        id="fixed-seated-anchor", display_name="林知遥",
        reference_image="host.png", is_new=False,
    )
    candidate = TopicCandidate(
        id="verified", title=task.input_text or "自动热点",
        pillar="social_phenomena", score=95, fact_status=FactStatus.VERIFIED,
        source_evidence=[
            SourceEvidence(source_id="s1", platform="official", title="官方",
                url_or_reference="https://official.test/news", evidence_type="official"),
            SourceEvidence(source_id="s2", platform="media", title="媒体",
                url_or_reference="https://media.test/report", evidence_type="reputable_media"),
        ],
        verification_summary="两个独立来源交叉核验", publishable=True,
    )
    script = NewsScript(
        title="热点解读",
        spoken_segments=[ScriptSegment(id="seg", kind="fact", text="事实", source_ids=["s1"])],
        source_ids=["s1", "s2"], ai_disclosure_required=True,
    )
    plan = MediaPlan(
        duration_seconds=15, host_id=host.id,
        segments=[
            MediaSegment(id="a1", kind=MediaKind.ANCHOR, start_seconds=0, end_seconds=5,
                script_segment_id="seg", host_id=host.id),
            MediaSegment(id="demo", kind=MediaKind.AI_DEMO, start_seconds=5, end_seconds=10,
                script_segment_id="seg", disclosure="AI生成示意画面"),
            MediaSegment(id="a2", kind=MediaKind.ANCHOR, start_seconds=10, end_seconds=15,
                script_segment_id="seg", host_id=host.id),
        ],
    )
    providers = ManagedProviders(
        script=lambda selected: (script, plan), host=lambda: host,
        tts=lambda news_script, voice_id: "audio.wav",
        anchor=lambda selected_host, audio: "anchor.mp4",
        media=lambda media_plan: "insert.mp4",
        composite=lambda daily_task: "master.mp4",
        qc=lambda daily_task: (True, "qc.json"),
    )
    return ManagedRunInput(candidates=[candidate], providers=providers)
""",
        encoding="utf-8",
    )

    created = run_cli(
        tmp_path,
        "init-day",
        "--date",
        "2026-08-06",
        "--mode",
        "managed",
        "--topic-source",
        "user_topic",
        "--input",
        "年轻人如何看待工作和生活的边界",
        env_overrides={"AVATAR_PIPELINE_MANAGED_RUNTIME": "managed_runtime_fixture:create_runtime"},
    )

    assert created.returncode == 0
    payload = json.loads(created.stdout)
    assert payload["status"] == "ready_to_publish"
    assert payload["selected_topic_id"] == "verified"
    assert payload["approvals"] == []
    assert payload["input_text"] == "年轻人如何看待工作和生活的边界"


def test_cli_user_topic_requires_nonblank_input(tmp_path):
    result = run_cli(
        tmp_path,
        "init-day",
        "--date",
        "2026-08-06",
        "--mode",
        "managed",
        "--topic-source",
        "user_topic",
    )
    assert result.returncode == 2
    assert "--input" in result.stderr


def test_cli_init_day_accepts_optional_user_host_image(tmp_path):
    host_image = tmp_path / "provided-host.png"
    host_image.write_bytes(b"image")
    created = run_cli(
        tmp_path,
        "init-day",
        "--date",
        "2026-08-06",
        "--mode",
        "manual",
        "--topic-source",
        "auto_hot",
        "--host-image",
        str(host_image),
    )
    assert created.returncode == 0
    payload = json.loads(created.stdout)
    assert payload["avatar_source"] == "user_provided"
    assert payload["host_profile"]["reference_image"] == str(host_image)
    assert payload["host_profile"]["layout"] == "seated_studio_anchor"
    assert payload["host_profile"]["is_new"] is True


def test_cli_rejects_missing_host_image_without_creating_day(tmp_path):
    missing = tmp_path / "missing-host.png"
    result = run_cli(
        tmp_path,
        "init-day",
        "--date",
        "2026-08-06",
        "--mode",
        "manual",
        "--topic-source",
        "auto_hot",
        "--host-image",
        str(missing),
    )
    assert result.returncode == 2
    assert "host image not found" in result.stderr
    assert DailyTaskRepository(tmp_path).list_days() == []


def test_cli_init_day_reuses_latest_saved_seated_host(tmp_path):
    repository = DailyTaskRepository(tmp_path)
    repository.create(
        DailyTask(
            day=date(2026, 8, 5),
            mode=RunMode.MANUAL,
            status=TaskStatus.READY_TO_PUBLISH,
            host_profile=host(image="saved-host.png", is_new=False).model_copy(
                update={"voice_id": "legacy-presenter-voice"}
            ),
            avatar_source=AvatarSource.SAVED_HOST,
            approvals=[ApprovalRecord(gate="final_video", actor="owner")],
        )
    )
    created = run_cli(
        tmp_path,
        "init-day",
        "--date",
        "2026-08-06",
        "--mode",
        "manual",
        "--topic-source",
        "auto_hot",
    )
    assert created.returncode == 0
    payload = json.loads(created.stdout)
    assert payload["avatar_source"] == "saved_host"
    assert payload["host_profile"]["reference_image"] == "saved-host.png"
    assert payload["host_profile"]["voice_id"] == "宣传女生Pro:clone_20260806_114837_980375"
    assert payload["host_profile"]["is_new"] is False
    assert payload["requires_host_approval"] is False


def test_cli_does_not_reuse_unapproved_new_host_from_ready_historical_task(tmp_path):
    repository = DailyTaskRepository(tmp_path)
    repository.create(
        DailyTask(
            day=date(2026, 8, 5),
            mode=RunMode.MANUAL,
            status=TaskStatus.READY_TO_PUBLISH,
            host_profile=host(image="unapproved-host.png", is_new=True),
            avatar_source=AvatarSource.USER_PROVIDED,
        )
    )

    created = run_cli(
        tmp_path,
        "init-day",
        "--date",
        "2026-08-06",
        "--mode",
        "manual",
        "--topic-source",
        "auto_hot",
    )

    assert created.returncode == 0
    payload = json.loads(created.stdout)
    assert payload["avatar_source"] == "saved_host"
    assert payload["host_profile"]["id"] == "fixed-seated-anchor"
    assert payload["host_profile"]["reference_image"] == (
        "assets/hosts/fixed-seated-anchor/master-reference.png"
    )
    assert payload["host_profile"]["is_new"] is False


def test_cli_approve_script_starts_generation_with_fixed_host(tmp_path):
    day = date(2026, 8, 6)
    task = review_task(
        day,
        host_profile=host(is_new=False),
        avatar_source=AvatarSource.SAVED_HOST,
    )
    task.approvals.append(ApprovalRecord(gate="hotspot", actor="owner"))
    DailyTaskRepository(tmp_path).create(task)

    approved = run_cli(
        tmp_path,
        "approve-script",
        "--date",
        day.isoformat(),
        "--actor",
        "owner",
    )

    assert approved.returncode == 0
    payload = json.loads(approved.stdout)
    assert payload["status"] == "generating_tts"
    assert [item["gate"] for item in payload["approvals"]] == ["hotspot", "script"]


def test_cli_approve_hotspot_records_selection_before_script(tmp_path):
    day = date(2026, 8, 6)
    task = review_task(
        day,
        host_profile=host(is_new=False),
        avatar_source=AvatarSource.SAVED_HOST,
    ).model_copy(
        update={
            "status": TaskStatus.HOTSPOT_REVIEW,
            "selected_topic_id": None,
            "news_script": None,
            "media_plan": None,
        }
    )
    DailyTaskRepository(tmp_path).create(task)

    approved = run_cli(
        tmp_path,
        "approve-hotspot",
        "--date",
        day.isoformat(),
        "--topic-id",
        "t1",
        "--actor",
        "owner",
    )

    assert approved.returncode == 0
    payload = json.loads(approved.stdout)
    assert payload["status"] == "scripting"
    assert payload["selected_topic_id"] == "t1"
    assert [item["gate"] for item in payload["approvals"]] == ["hotspot"]


def test_cli_set_host_uses_uploaded_host_without_extra_review(tmp_path):
    day = date(2026, 8, 6)
    staged = review_task(
        day,
        host_profile=host(is_new=False),
        avatar_source=AvatarSource.SAVED_HOST,
    ).model_copy(update={"status": TaskStatus.MEDIA_PLANNING, "host_profile": None})
    DailyTaskRepository(tmp_path).create(staged)
    host_file = tmp_path / "host.json"
    host_file.write_text(
        json.dumps(host(image="uploaded-host.png", is_new=True).model_dump(mode="json")),
        encoding="utf-8",
    )

    result = run_cli(
        tmp_path,
        "set-host",
        "--date",
        day.isoformat(),
        "--file",
        str(host_file),
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "generating_tts"
    assert payload["avatar_source"] == "user_provided"
    assert payload["host_profile"]["is_new"] is False


def test_cli_manual_final_video_approval_is_the_last_user_gate(tmp_path):
    day = date(2026, 8, 6)
    repository = DailyTaskRepository(tmp_path)
    repository.create(
        DailyTask(
            day=day,
            mode=RunMode.MANUAL,
            status=TaskStatus.FINAL_REVIEW,
            host_profile=host(is_new=False),
            avatar_source=AvatarSource.SAVED_HOST,
        )
    )

    approved = run_cli(
        tmp_path,
        "approve-final-video",
        "--date",
        day.isoformat(),
        "--actor",
        "owner",
    )

    assert approved.returncode == 0
    payload = json.loads(approved.stdout)
    assert payload["status"] == "ready_to_publish"
    assert [item["gate"] for item in payload["approvals"]] == ["final_video"]


def test_cli_health_reports_dual_mode_fixed_anchor_policy_and_public_gates(tmp_path):
    result = run_cli(tmp_path, "health")
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["supported_modes"] == ["managed", "manual"]
    assert payload["topic_sources"] == ["user_topic", "auto_hot"]
    assert payload["host_layout"] == "seated_studio_anchor"
    assert payload["host_identity"] == {
        "id": "fixed-seated-anchor",
        "display_name": "林知遥",
        "reference_image": "assets/hosts/fixed-seated-anchor/master-reference.png",
        "voice_id": "宣传女生Pro:clone_20260806_114837_980375",
        "layout": "seated_studio_anchor",
        "mouth_unobstructed": True,
    }
    assert payload["tts"] == {
        "voice_id": "宣传女生Pro:clone_20260806_114837_980375",
        "emotion": "neutral",
        "speaking_rate": 1.0,
    }
    assert payload["video_structure"] == "studio_anchor_plus_vertical_news_insert"
    assert payload["subtitle"] is False
    assert payload["manual_approval_commands"] == [
        "approve-hotspot",
        "approve-script",
        "approve-final-video",
    ]
    assert "opinions_crawler" in payload["skills"]
    assert "quality_control" in payload["skills"]


def test_cli_rejects_removed_old_commands(tmp_path):
    result = run_cli(
        tmp_path, "approve-topic", "--date", "2026-08-06", "--topic-id", "t1", "--actor", "owner"
    )
    assert result.returncode != 0
