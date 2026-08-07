"""Atomic persistence and immutable revisions for daily research runs."""

from __future__ import annotations

import json
import tempfile
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from avatar_pipeline.models import utc_now
from avatar_pipeline.research_models import DailyResearchPlan, ResearchRun


class ResearchRunAlreadyExists(FileExistsError):
    """Raised when creating a research run for an existing day."""


class ResearchRunNotFound(FileNotFoundError):
    """Raised when a requested research run does not exist."""


class ResearchRevisionAlreadyExists(FileExistsError):
    """Raised when an immutable numbered revision already exists."""


class ResearchRunRepository:
    """Persist one research run and its immutable revisions per calendar day."""

    def __init__(self, workspace: Path) -> None:
        self.workspace = Path(workspace)

    def create(self, day: date) -> ResearchRun:
        """Create an empty run and the standard research artifact directories."""

        path = self._run_path(day)
        if path.exists():
            raise ResearchRunAlreadyExists(f"research run already exists: {day.isoformat()}")
        self._ensure_directories(day)
        run = ResearchRun(day=day)
        self._write_json(path, run.model_dump(mode="json"))
        return run

    def get(self, day: date) -> ResearchRun:
        """Load and validate the current run for ``day``."""

        path = self._run_path(day)
        if not path.is_file():
            raise ResearchRunNotFound(f"research run not found: {day.isoformat()}")
        with path.open("r", encoding="utf-8") as handle:
            return ResearchRun.model_validate(json.load(handle))

    def save(self, run: ResearchRun) -> ResearchRun:
        """Atomically replace an existing current run."""

        path = self._run_path(run.day)
        if not path.is_file():
            raise ResearchRunNotFound(f"research run not found: {run.day.isoformat()}")
        run.updated_at = utc_now()
        self._write_json(path, run.model_dump(mode="json"))
        return run

    def save_revision(self, run: ResearchRun) -> Path:
        """Write an immutable revision snapshot using the run's revision number."""

        if not self._run_path(run.day).is_file():
            raise ResearchRunNotFound(f"research run not found: {run.day.isoformat()}")
        path = self._research_root(run.day) / "revisions" / f"revision-{run.revision}.json"
        if path.exists():
            raise ResearchRevisionAlreadyExists(
                f"research revision already exists: {run.day.isoformat()} #{run.revision}"
            )
        self._write_json(path, run.model_dump(mode="json"))
        return path

    def write_artifact(self, day: date, relative_path: Path, payload: Any) -> Path:
        """Write an artifact below the day's research directory only."""

        if not self._run_path(day).is_file():
            raise ResearchRunNotFound(f"research run not found: {day.isoformat()}")
        path = self._safe_artifact_path(day, relative_path)
        if isinstance(payload, bytes):
            self._write_bytes(path, payload)
        elif isinstance(payload, str):
            self._write_text(path, payload)
        else:
            self._write_json(path, payload)
        return path

    def read_artifact(self, day: date, relative_path: Path) -> Any:
        """Read a JSON artifact from the safe research directory."""

        if not self._run_path(day).is_file():
            raise ResearchRunNotFound(f"research run not found: {day.isoformat()}")
        path = self._safe_artifact_path(day, relative_path)
        if not path.is_file():
            raise FileNotFoundError(f"research artifact not found: {relative_path}")
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def list_recent_plans(self, before_day: date, days: int = 30) -> list[DailyResearchPlan]:
        """Return plans before ``before_day`` within the lookback, newest first."""

        if days < 1:
            raise ValueError("days must be positive")
        lower_bound = before_day - timedelta(days=days)
        plans: list[DailyResearchPlan] = []
        days_root = self.workspace / "days"
        if not days_root.exists():
            return plans

        for path in days_root.glob("*/research/run.json"):
            try:
                run_day = date.fromisoformat(path.parents[1].name)
            except ValueError:
                continue
            if not lower_bound <= run_day < before_day:
                continue
            try:
                with path.open("r", encoding="utf-8") as handle:
                    run = ResearchRun.model_validate(json.load(handle))
            except (OSError, json.JSONDecodeError, ValueError):
                continue
            if run.plan is not None:
                plans.append(run.plan)
        return sorted(plans, key=lambda plan: plan.day, reverse=True)

    def _research_root(self, day: date) -> Path:
        return self.workspace / "days" / day.isoformat() / "research"

    def _run_path(self, day: date) -> Path:
        return self._research_root(day) / "run.json"

    def _ensure_directories(self, day: date) -> None:
        root = self._research_root(day)
        for directory in (root, root / "raw", root / "reports", root / "revisions"):
            directory.mkdir(parents=True, exist_ok=True)

    def _safe_artifact_path(self, day: date, relative_path: Path) -> Path:
        relative = Path(relative_path)
        root = self._research_root(day).resolve()
        if relative.is_absolute():
            raise ValueError("artifact path must remain inside the day's research directory")
        candidate = (root / relative).resolve()
        if candidate == root or root not in candidate.parents:
            raise ValueError("artifact path must remain inside the day's research directory")
        return candidate

    @staticmethod
    def _atomic_write(path: Path, writer: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=path.parent,
                prefix=f".{path.name}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                temporary_path = Path(handle.name)
                writer(handle)
                handle.flush()
            temporary_path.replace(path)
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()

    @classmethod
    def _write_json(cls, path: Path, payload: Any) -> None:
        def write(handle: Any) -> None:
            with open(handle.fileno(), mode="w", encoding="utf-8", closefd=False) as text_handle:
                json.dump(payload, text_handle, ensure_ascii=False, indent=2)
                text_handle.write("\n")
                text_handle.flush()

        cls._atomic_write(path, write)

    @classmethod
    def _write_text(cls, path: Path, payload: str) -> None:
        cls._atomic_write(path, lambda handle: handle.write(payload.encode("utf-8")))

    @classmethod
    def _write_bytes(cls, path: Path, payload: bytes) -> None:
        cls._atomic_write(path, lambda handle: handle.write(payload))
