"""JSON persistence for daily workflow tasks."""

import json
import tempfile
from datetime import date
from pathlib import Path

from avatar_pipeline.models import DailyTask, utc_now


class DailyTaskAlreadyExists(FileExistsError):
    """Raised when creating a task for an existing day."""


class DailyTaskNotFound(FileNotFoundError):
    """Raised when a requested daily task does not exist."""


class DailyTaskRepository:
    """Persist one validated ``DailyTask`` JSON document per calendar day."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    def create(self, task: DailyTask) -> DailyTask:
        """Create a new daily task, rejecting duplicate dates."""

        path = self._task_path(task.day)
        if path.exists():
            raise DailyTaskAlreadyExists(f"daily task already exists: {task.day.isoformat()}")
        self._write(path, task)
        return task

    def get(self, day: date) -> DailyTask:
        """Load and validate the task for ``day``."""

        path = self._task_path(day)
        if not path.exists():
            raise DailyTaskNotFound(f"daily task not found: {day.isoformat()}")
        with path.open("r", encoding="utf-8") as handle:
            return DailyTask.model_validate(json.load(handle))

    def save(self, task: DailyTask) -> DailyTask:
        """Update an existing task and refresh its modification timestamp."""

        path = self._task_path(task.day)
        if not path.exists():
            raise DailyTaskNotFound(f"daily task not found: {task.day.isoformat()}")
        task.updated_at = utc_now()
        self._write(path, task)
        return task

    def list_days(self) -> list[date]:
        """Return all persisted task dates in ascending order."""

        days_root = self.root / "days"
        if not days_root.exists():
            return []
        result: list[date] = []
        for path in days_root.glob("*/task.json"):
            try:
                result.append(date.fromisoformat(path.parent.name))
            except ValueError:
                continue
        return sorted(result)

    def _task_path(self, day: date) -> Path:
        return self.root / "days" / day.isoformat() / "task.json"

    @staticmethod
    def _write(path: Path, task: DailyTask) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = task.model_dump(mode="json")
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=path.parent,
                prefix=f".{path.name}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
                temporary_path = Path(handle.name)
            temporary_path.replace(path)
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()
