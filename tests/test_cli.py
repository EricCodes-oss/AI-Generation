import json
import subprocess
import sys
from datetime import date

from avatar_pipeline.hotspot_models import (
    DirectorAction,
    HotspotCandidateReport,
    HotspotReport,
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
        "--date", "2026-08-10",
        "--format", "canonical",
        "--file", "tests/fixtures/hotspots/canonical-t0.json",
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
        "--date", "2026-08-10",
        "--archive-reason", "旧候选传播性不足",
        "--confirmed-host-profile", str(confirmed_host_path),
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "topic_script_review"
    assert payload["host_profile"] == host.model_dump(mode="json")
    assert payload["selected_topic_id"] is None
    assert payload["news_script"] is None
    assert payload["media_plan"] is None
    assert payload["artifacts"] == []
