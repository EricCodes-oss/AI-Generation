import json
from datetime import date

import pytest

from avatar_pipeline.models import DailyTask
from avatar_pipeline.repository import (
    DailyTaskAlreadyExists,
    DailyTaskNotFound,
    DailyTaskRepository,
)


def test_repository_round_trips_utf8_json(tmp_path):
    repo = DailyTaskRepository(tmp_path)
    task = DailyTask(day=date(2026, 8, 6))
    repo.create(task)
    loaded = repo.get(date(2026, 8, 6))
    assert loaded.day == task.day
    assert loaded.schema_version == 2
    assert (tmp_path / "days" / "2026-08-06" / "task.json").exists()


def test_repository_rejects_duplicate_day(tmp_path):
    repo = DailyTaskRepository(tmp_path)
    repo.create(DailyTask(day=date(2026, 8, 6)))
    with pytest.raises(DailyTaskAlreadyExists):
        repo.create(DailyTask(day=date(2026, 8, 6)))


def test_repository_reports_missing_day(tmp_path):
    with pytest.raises(DailyTaskNotFound):
        DailyTaskRepository(tmp_path).get(date(2026, 8, 6))


def test_repository_migrates_legacy_task_without_fabricating_verification(tmp_path):
    path = tmp_path / "days" / "2026-08-04" / "task.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps({"day": "2026-08-04", "status": "created", "candidates": []}), encoding="utf-8"
    )
    task = DailyTaskRepository(tmp_path).get(date(2026, 8, 4))
    assert task.schema_version == 2
    assert task.status.value == "input_received"
    assert task.candidates == []
