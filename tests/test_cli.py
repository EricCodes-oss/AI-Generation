import json
import subprocess
import sys


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
