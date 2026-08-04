import json
import subprocess
import sys


def run_cli(tmp_path, *args):
    return subprocess.run(
        [sys.executable, "-m", "avatar_pipeline.cli", "--workspace", str(tmp_path), *args],
        check=False,
        capture_output=True,
        text=True,
    )


def test_cli_initializes_and_reports_day(tmp_path):
    created = run_cli(tmp_path, "init-day", "--date", "2026-08-04")
    assert created.returncode == 0
    status = run_cli(tmp_path, "status", "--date", "2026-08-04")
    assert status.returncode == 0
    payload = json.loads(status.stdout)
    assert payload["day"] == "2026-08-04"
    assert payload["status"] == "created"


def test_cli_health_reports_ffmpeg_and_disabled_real_generators(tmp_path):
    result = run_cli(tmp_path, "health")
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["ffmpeg"]["available"] is True
    assert payload["skills"]["avatar"]["real_generation_enabled"] is False
    assert payload["skills"]["seedance"]["real_generation_enabled"] is False
