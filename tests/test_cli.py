import json
import subprocess
import sys
from datetime import date
from pathlib import Path

from avatar_pipeline.hotspot_models import (
    DirectorAction,
    HotspotCandidateReport,
    HotspotReport,
    ShortVideoAssessment,
    TrendLabel,
    ViralityBand,
    ViralityScore,
)
from avatar_pipeline.hotspot_repository import HotspotRepository
from avatar_pipeline.models import DailyTask, HostProfile, NewsPillarSlug, TaskStatus
from avatar_pipeline.repository import DailyTaskRepository


def run_cli(tmp_path, *args):
    return subprocess.run(
        [sys.executable, "-m", "avatar_pipeline.cli", "--workspace", str(tmp_path), *args],
        check=False,
        capture_output=True,
        text=True,
        env={"PYTHONPATH": "src"},
    )


def test_cli_initializes_news_day_with_explicit_mode(tmp_path):
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


def test_cli_health_reports_news_policy_and_contracts(tmp_path):
    result = run_cli(tmp_path, "health")
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["video_structure"] == "studio_anchor_plus_vertical_news_insert"
    assert payload["subtitle"] is False
    assert "opinions_crawler" in payload["skills"]
    assert "quality_control" in payload["skills"]


def test_cli_rejects_removed_old_commands(tmp_path):
    result = run_cli(
        tmp_path, "approve-topic", "--date", "2026-08-06", "--topic-id", "t1", "--actor", "owner"
    )
    assert result.returncode != 0


def test_cli_imports_snapshot_builds_report_and_shows_transparent_status(tmp_path):
    imported = run_cli(
        tmp_path,
        "hotspot-import-snapshot",
        "--date",
        "2026-08-10",
        "--format",
        "canonical",
        "--file",
        "tests/fixtures/hotspots/canonical-t0.json",
    )
    assert imported.returncode == 0
    assert json.loads(imported.stdout)["snapshot_id"] == "t0"

    built = run_cli(tmp_path, "hotspot-build-report", "--date", "2026-08-10")
    assert built.returncode == 0
    assert json.loads(built.stdout)["outcome"] == "no_qualified_hotspot"

    status = run_cli(tmp_path, "hotspot-status", "--date", "2026-08-10")
    payload = json.loads(status.stdout)
    assert payload["snapshot_ids"] == ["t0"]
    assert payload["report_outcome"] == "no_qualified_hotspot"


def test_cli_refresh_preserves_confirmed_host_and_creates_no_assets(tmp_path):
    day = date(2026, 8, 10)
    host = HostProfile(
        id="host-c2-pro-candidate-2-final",
        display_name="C2-Pro 新闻主持人",
        reference_image="output/host-v12-c2-pro/GPT-Image-2-Pro-C2-Pro-主持人最终选定.png",
        studio_reference="蓝色演播室、近景胸像、白衬衣、深藏青西装、无桌、避免手臂入镜",
        visual_style="知性亲和、专业克制、低AI感、五官清晰稳定",
        is_new=False,
        version=12,
    )
    confirmed_host_path = tmp_path / "confirmed-host.json"
    confirmed_host_path.write_text(
        host.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
    DailyTaskRepository(tmp_path).create(
        DailyTask(day=day, host_profile=None, status=TaskStatus.TOPIC_SCRIPT_REVIEW)
    )
    score = ViralityScore(
        event_id="event-1",
        rule_version="viral-v1.0",
        cross_platform_resonance=25,
        trend_velocity=20,
        conflict_suspense=15,
        public_interest=10,
        curiosity_gap=10,
        visual_impact=8,
        explanatory_depth=4,
        fact_safety=5,
        total=97,
    )
    candidate = HotspotCandidateReport(
        event_id="event-1",
        representative_title="事件",
        click_title="事件为什么突然引发关注？",
        collected_from="2026-08-10T19:40:00+08:00",
        collected_to="2026-08-10T20:00:00+08:00",
        platform_evidence=["weibo rank=1", "baidu rank=2", "zhihu rank=3"],
        trend_label=TrendLabel.RISING,
        score=score,
        score_band=ViralityBand.DIRECTOR_FIRST,
        why_click="存在明确认知缺口",
        opening_hook="变化发生得比预期更快。",
        audience_relevance="影响普通人的安全与出行",
        visual_assets=["official-map.png"],
        copyright_notes=["引用时标注官方来源"],
        expected_lifetime="12-24小时",
        risks=[],
        wording_to_avoid=[],
        director_action=DirectorAction.DO_NOW,
        pillar=NewsPillarSlug.SOCIAL_PHENOMENA,
        source_evidence=[],
        verification_summary="核心事实已核验",
        short_video_assessment=ShortVideoAssessment(
            event_id="event-1",
            passed=True,
            required_platforms=["douyin", "xiaohongshu"],
            strong_platforms=["douyin", "xiaohongshu"],
            platform_scores={"douyin": 0.9, "xiaohongshu": 0.85},
            checks={
                "short_video_evidence:douyin": True,
                "short_video_evidence:xiaohongshu": True,
            },
        ),
    )
    report = HotspotReport(
        day=day.isoformat(),
        rule_version="viral-v1.0",
        snapshot_ids=["t0", "t1", "t2"],
        collection_failures=[],
        candidates=[candidate],
        director_recommendation_event_id="event-1",
        outcome="qualified_candidates",
    )
    HotspotRepository(tmp_path).save_report(day, report, "# report\n")

    result = run_cli(
        tmp_path,
        "hotspot-refresh",
        "--date",
        "2026-08-10",
        "--archive-reason",
        "旧候选传播性不足",
        "--confirmed-host-profile",
        str(confirmed_host_path),
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "topic_script_review"
    assert payload["host_profile"] == host.model_dump(mode="json")
    assert payload["selected_topic_id"] is None
    assert payload["news_script"] is None
    assert payload["media_plan"] is None
    assert payload["artifacts"] == []


def test_cli_imports_short_video_evidence_with_review_inputs(tmp_path):
    verification_path = tmp_path / "verification.json"
    editorial_path = tmp_path / "editorial.json"
    short_video_path = tmp_path / "short-video.json"
    verification_path.write_text("[]\n", encoding="utf-8")
    editorial_path.write_text("[]\n", encoding="utf-8")
    short_video_path.write_text(
        json.dumps(
            [
                {
                    "event_id": "event-1",
                    "captured_at": "2026-08-11T11:30:00+08:00",
                    "platforms": {
                        "douyin": {
                            "platform": "douyin",
                            "collection_status": "success",
                            "source_count": 2,
                            "comment_sample_count": 10,
                            "views": 100000,
                            "likes": 5000,
                            "comments": 300,
                            "shares": 200,
                            "saves": 100,
                            "suitability_score": 0.8,
                            "raw_evidence_paths": ["tmp/douyin.json"],
                        },
                        "xiaohongshu": {
                            "platform": "xiaohongshu",
                            "collection_status": "restricted",
                            "failure_reason": "login verification required",
                            "raw_evidence_paths": ["tmp/xiaohongshu-error.json"],
                        },
                    },
                }
            ],
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    result = run_cli(
        tmp_path,
        "hotspot-import-review",
        "--date",
        "2026-08-11",
        "--verification",
        str(verification_path),
        "--editorial-signals",
        str(editorial_path),
        "--short-video-evidence",
        str(short_video_path),
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["short_video_event_ids"] == ["event-1"]
    loaded = HotspotRepository(tmp_path).load_short_video_evidence(date(2026, 8, 11))
    assert loaded["event-1"].platforms["xiaohongshu"].collection_status.value == "restricted"


def test_news_v5_guidance_reports_v5_rhythm_for_52_seconds():
    from avatar_pipeline.cli import build_parser, dispatch

    args = build_parser().parse_args(["news-v5-guidance", "--duration", "52.128"])
    payload = dispatch(args)
    assert payload["recommended_count"] == 3
    assert payload["minimum_count"] == 2
    assert payload["maximum_count"] == 3
    assert payload["minimum_clip_seconds"] == 4.5
    assert payload["maximum_clip_seconds"] == 6.5


def test_news_v5_init_and_status_are_non_interactive_json_commands(tmp_path):
    output_root = tmp_path / "output"
    created = run_cli(
        tmp_path,
        "news-v5-init",
        "--output-root",
        str(output_root),
        "--date",
        "2026-08-12",
        "--slug",
        "台风暴雨",
        "--topic",
        "台风及城市积水影响",
        "--version",
        "1",
    )
    assert created.returncode == 0, created.stderr
    payload = json.loads(created.stdout)
    run_dir = output_root / "manual-news-2026-08-12-台风暴雨-v01"
    assert payload["run_dir"] == str(run_dir)
    assert payload["manifest"]["status"] == "initialized"

    status = run_cli(tmp_path, "news-v5-status", "--run-dir", str(run_dir))
    assert status.returncode == 0, status.stderr
    status_payload = json.loads(status.stdout)
    assert status_payload["run_id"] == run_dir.name
    assert status_payload["status"] == "initialized"
    assert status_payload["records"]["manifest"] is True
    assert status_payload["records"]["final_qc_report"] is False

    duplicate = run_cli(
        tmp_path,
        "news-v5-init",
        "--output-root",
        str(output_root),
        "--date",
        "2026-08-12",
        "--slug",
        "台风暴雨",
        "--topic",
        "台风及城市积水影响",
        "--version",
        "1",
    )
    assert duplicate.returncode != 0


def test_news_v5_stage_commands_dispatch_to_quality_gates(monkeypatch, tmp_path):
    from avatar_pipeline import cli
    from avatar_pipeline.news_production import StageValidationResult
    from avatar_pipeline.news_production_models import (
        DirectorCheck,
        DirectorReview,
        NewsRunManifest,
        NewsRunStatus,
    )
    from avatar_pipeline.news_qc import FinalQualityReport

    run_dir = tmp_path / "run"
    run_dir.mkdir()
    calls = []

    def fake_preflight(path):
        calls.append(("preflight", Path(path)))
        return StageValidationResult(
            stage="timeline",
            status=NewsRunStatus.TIMELINE_READY,
            hard_failures=[],
            advisories=["broll_count:2 outside director target"],
        )

    def fake_mark(path):
        calls.append(("mark", Path(path)))
        return NewsRunManifest(
            run_id="run",
            quality_profile="v5",
            quality_profile_version="1.0",
            topic="topic",
            target_duration_seconds=60,
            host_id="host",
            host_reference_image="host.png",
            host_sha256="a" * 64,
            voice_id="voice",
            status=NewsRunStatus.RENDERED_PENDING_QC,
            final_video_path="video/final-clean.mp4",
            created_at="2026-08-12T00:00:00Z",
        )

    def fake_qc(path):
        calls.append(("qc", Path(path)))
        return FinalQualityReport(
            run_id="run",
            overall_passed=False,
            checks=[],
            director_review=None,
            final_video_sha256="b" * 64,
        )

    def fake_review(path):
        calls.append(("review", Path(path)))
        return FinalQualityReport(
            run_id="run",
            overall_passed=True,
            checks=[],
            director_review=DirectorReview(
                run_id="run",
                approved=True,
                checks=[
                    DirectorCheck(
                        id="overall_news_effect",
                        description="overall_news_effect",
                        passed=True,
                    )
                ],
                reviewed_at="2026-08-12T00:00:00Z",
                actor="director",
            ),
            final_video_sha256="b" * 64,
        )

    monkeypatch.setattr(cli, "validate_timeline_preflight", fake_preflight)
    monkeypatch.setattr(cli, "mark_rendered", fake_mark)
    monkeypatch.setattr(cli, "build_automatic_qc_report", fake_qc)
    monkeypatch.setattr(cli, "apply_director_review", fake_review)

    preflight = cli.dispatch(
        cli.build_parser().parse_args(
            ["news-v5-preflight", "--run-dir", str(run_dir), "--stage", "timeline"]
        )
    )
    assert preflight == {
        "stage": "timeline",
        "status": "timeline_ready",
        "hard_failures": [],
        "advisories": ["broll_count:2 outside director target"],
    }
    rendered = cli.dispatch(
        cli.build_parser().parse_args(["news-v5-mark-rendered", "--run-dir", str(run_dir)])
    )
    assert rendered["status"] == "rendered_pending_qc"
    automatic = cli.dispatch(
        cli.build_parser().parse_args(["news-v5-build-qc", "--run-dir", str(run_dir)])
    )
    assert automatic["overall_passed"] is False
    reviewed = cli.dispatch(
        cli.build_parser().parse_args(["news-v5-apply-director-review", "--run-dir", str(run_dir)])
    )
    assert reviewed["overall_passed"] is True
    assert calls == [
        ("preflight", run_dir),
        ("mark", run_dir),
        ("qc", run_dir),
        ("review", run_dir),
    ]
