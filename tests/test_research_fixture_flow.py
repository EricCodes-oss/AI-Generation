import json
import subprocess
import sys
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures" / "research"
DAY = "2026-08-04"


def run_cli(workspace, *args):
    return subprocess.run(
        [sys.executable, "-m", "avatar_pipeline.cli", "--workspace", str(workspace), *args],
        check=False,
        capture_output=True,
        text=True,
    )


def run_ok(workspace, *args):
    result = run_cli(workspace, *args)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_fixture_research_flow_stops_at_approval_without_touching_top3_or_daily_task(
    tmp_path,
):
    run_ok(tmp_path, "init-day", "--date", DAY)
    run_ok(tmp_path, "research-init", "--date", DAY)

    planned = run_ok(tmp_path, "research-plan", "--date", DAY)
    assert planned["status"] == "collecting"
    assert len(planned["plan"]["core_groups"]) == 9

    collected = run_ok(
        tmp_path,
        "research-import",
        "--date",
        DAY,
        "--collector",
        "fixture",
        "--file",
        str(FIXTURES / "manual_sources.json"),
    )
    assert len(collected["sources"]) == 30
    assert len(collected["failures"]) == 1

    ready = run_ok(
        tmp_path,
        "research-import-insights",
        "--date",
        DAY,
        "--file",
        str(FIXTURES / "comment_insights.json"),
    )
    assert ready["status"] == "ready_for_review"
    assert len(ready["insight_cards"]) == 5

    first_report = run_ok(tmp_path, "research-report", "--date", DAY)
    assert Path(first_report["report_path"]).is_file()
    assert first_report["run"]["status"] == "ready_for_review"

    revised = run_ok(
        tmp_path,
        "research-revise",
        "--date",
        DAY,
        "--action",
        "recollect_comments",
        "--feedback",
        "复核评论洞察后再批准",
    )
    assert revised["status"] == "revision_requested"

    run_ok(
        tmp_path,
        "research-import-insights",
        "--date",
        DAY,
        "--file",
        str(FIXTURES / "comment_insights.json"),
    )
    second_report = run_ok(tmp_path, "research-report", "--date", DAY)
    assert Path(second_report["report_path"]).is_file()

    approved = run_ok(
        tmp_path,
        "research-approve",
        "--date",
        DAY,
        "--actor",
        "项目负责人",
    )
    assert approved["status"] == "approved"
    assert approved["approvals"][-1]["actor"] == "项目负责人"

    research_status = run_ok(tmp_path, "research-status", "--date", DAY)
    serialized = json.dumps(research_status, ensure_ascii=False)
    assert "topic_candidates" not in serialized
    assert "script_text" not in serialized
    assert "Top 3" not in serialized

    daily_status = run_ok(tmp_path, "status", "--date", DAY)
    assert daily_status["status"] == "created"
    assert daily_status["candidates"] == []
