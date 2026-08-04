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
    task = DailyTask(day=date(2026, 8, 4))
    repo.create(task)
    loaded = repo.get(date(2026, 8, 4))
    assert loaded.day == task.day
    assert (tmp_path / "days" / "2026-08-04" / "task.json").exists()


def test_repository_rejects_duplicate_day(tmp_path):
    repo = DailyTaskRepository(tmp_path)
    repo.create(DailyTask(day=date(2026, 8, 4)))
    with pytest.raises(DailyTaskAlreadyExists):
        repo.create(DailyTask(day=date(2026, 8, 4)))


def test_repository_reports_missing_day(tmp_path):
    with pytest.raises(DailyTaskNotFound):
        DailyTaskRepository(tmp_path).get(date(2026, 8, 4))
