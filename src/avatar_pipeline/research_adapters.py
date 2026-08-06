"""Failure-tolerant collection seams for daily hotspot research."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

from avatar_pipeline.models import utc_now
from avatar_pipeline.research_models import (
    AwareTimestamp,
    CollectionFailure,
    DailyResearchPlan,
    ResearchPlatform,
)

Clock = Callable[[], datetime]
Runner = Callable[..., Any]


class AdapterModel(BaseModel):
    """Strict base model for data crossing a collector boundary."""

    model_config = ConfigDict(extra="forbid")


class RawCollectionItem(AdapterModel):
    """Unnormalized collector output with its minimum provenance."""

    platform: ResearchPlatform
    payload: dict[str, Any]
    raw_artifact_path: str = Field(min_length=1)
    query_group_id: str | None = None
    rate_delay_seconds: float | None = Field(default=None, ge=0)


class CollectionBatch(AdapterModel):
    """One collector execution, including partial successes and failures."""

    raw_items: list[RawCollectionItem] = Field(default_factory=list)
    failures: list[CollectionFailure] = Field(default_factory=list)
    collector_name: str = Field(min_length=1)
    started_at: AwareTimestamp
    completed_at: AwareTimestamp
    raw_artifact_paths: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_timing_and_paths(self) -> CollectionBatch:
        if self.completed_at < self.started_at:
            raise ValueError("completed_at cannot precede started_at")
        if len(self.raw_artifact_paths) != len(set(self.raw_artifact_paths)):
            raise ValueError("raw artifact paths must be unique")
        return self


class ResearchCollector(Protocol):
    """Collector interface used by the research orchestration stage."""

    def collect(self, plan: DailyResearchPlan) -> CollectionBatch:
        """Collect raw items without aborting other platform attempts."""


class FixtureCollector:
    """Read deterministic local JSON fixtures with per-file failure isolation."""

    collector_name = "fixture"

    def __init__(
        self,
        sources: Mapping[ResearchPlatform, Sequence[Path | str]],
        *,
        clock: Clock = utc_now,
    ) -> None:
        self._sources = {
            platform: [Path(path) for path in paths] for platform, paths in sources.items()
        }
        self._clock = clock

    def collect(self, plan: DailyResearchPlan) -> CollectionBatch:
        del plan  # Fixtures carry their own platform provenance; query attribution happens later.
        started_at = self._clock()
        raw_items: list[RawCollectionItem] = []
        failures: list[CollectionFailure] = []
        artifact_paths: list[str] = []

        for platform, paths in self._sources.items():
            for path in paths:
                path_text = str(path)
                artifact_paths.append(path_text)
                try:
                    payload = json.loads(path.read_text(encoding="utf-8"))
                    items = _extract_json_items(payload)
                except FileNotFoundError as error:
                    failures.append(
                        self._failure(
                            platform,
                            path_text,
                            "file_not_found",
                            str(error),
                            retryable=False,
                        )
                    )
                    continue
                except json.JSONDecodeError as error:
                    failures.append(
                        self._failure(
                            platform,
                            path_text,
                            "invalid_json",
                            f"invalid JSON: {error.msg}",
                            retryable=False,
                        )
                    )
                    continue
                except ValueError as error:
                    failures.append(
                        self._failure(
                            platform,
                            path_text,
                            "invalid_payload",
                            str(error),
                            retryable=False,
                        )
                    )
                    continue

                raw_items.extend(
                    RawCollectionItem(
                        platform=platform,
                        payload=item,
                        raw_artifact_path=path_text,
                    )
                    for item in items
                )

        return CollectionBatch(
            raw_items=raw_items,
            failures=failures,
            collector_name=self.collector_name,
            started_at=started_at,
            completed_at=self._clock(),
            raw_artifact_paths=list(dict.fromkeys(artifact_paths)),
        )

    def _failure(
        self,
        platform: ResearchPlatform,
        path: str,
        error_code: str,
        message: str,
        *,
        retryable: bool,
    ) -> CollectionFailure:
        return CollectionFailure(
            platform=platform,
            capability="local_json_import",
            message=message,
            error_code=error_code,
            retryable=retryable,
            attempted_at=self._clock(),
            raw_artifact_path=path,
        )


class ManualImportCollector(FixtureCollector):
    """Import operator-exported JSON while marking the collection method explicitly."""

    collector_name = "manual_import"


class CommandSpec(AdapterModel):
    """An audited command invocation; argv is always passed without a shell."""

    platform: ResearchPlatform
    argv: list[str] = Field(min_length=1)
    raw_output_path: Path
    timeout_seconds: float = Field(gt=0)
    rate_delay_seconds: float = Field(default=0, ge=0)
    query_group_id: str | None = None
    capability: str = "search"

    @model_validator(mode="after")
    def validate_argv(self) -> CommandSpec:
        if any(not argument for argument in self.argv):
            raise ValueError("command arguments must not be blank")
        return self


class CommandCollector:
    """Execute injected audited argv commands and preserve partial results."""

    collector_name = "command"

    def __init__(
        self,
        commands: Sequence[CommandSpec],
        *,
        runner: Runner = subprocess.run,
        clock: Clock = utc_now,
    ) -> None:
        self._commands = list(commands)
        self._runner = runner
        self._clock = clock

    def collect(self, plan: DailyResearchPlan) -> CollectionBatch:
        del plan  # The command specs already record optional query-group attribution.
        started_at = self._clock()
        raw_items: list[RawCollectionItem] = []
        failures: list[CollectionFailure] = []
        artifact_paths: list[str] = []

        for spec in self._commands:
            attempted_at = self._clock()
            try:
                completed = self._runner(
                    list(spec.argv),
                    capture_output=True,
                    text=True,
                    timeout=float(spec.timeout_seconds),
                    check=False,
                )
            except subprocess.TimeoutExpired:
                failures.append(
                    self._failure(
                        spec,
                        attempted_at,
                        "timeout",
                        f"command timed out after {spec.timeout_seconds:g} seconds",
                        retryable=True,
                    )
                )
                continue
            except OSError as error:
                failures.append(
                    self._failure(
                        spec,
                        attempted_at,
                        "command_error",
                        str(error),
                        retryable=True,
                    )
                )
                continue

            stdout = completed.stdout or ""
            artifact_path = self._write_raw_output(spec.raw_output_path, stdout)
            artifact_paths.append(artifact_path)

            if completed.returncode != 0:
                message = (completed.stderr or "").strip() or (
                    f"command exited with status {completed.returncode}"
                )
                failures.append(
                    self._failure(
                        spec,
                        attempted_at,
                        "non_zero_exit",
                        message,
                        retryable=True,
                        raw_artifact_path=artifact_path,
                    )
                )
                continue

            try:
                items = _extract_json_items(json.loads(stdout))
            except json.JSONDecodeError as error:
                failures.append(
                    self._failure(
                        spec,
                        attempted_at,
                        "invalid_json",
                        f"invalid JSON: {error.msg}",
                        retryable=False,
                        raw_artifact_path=artifact_path,
                    )
                )
                continue
            except ValueError as error:
                failures.append(
                    self._failure(
                        spec,
                        attempted_at,
                        "invalid_payload",
                        str(error),
                        retryable=False,
                        raw_artifact_path=artifact_path,
                    )
                )
                continue

            raw_items.extend(
                RawCollectionItem(
                    platform=spec.platform,
                    payload=item,
                    raw_artifact_path=artifact_path,
                    query_group_id=spec.query_group_id,
                    rate_delay_seconds=spec.rate_delay_seconds,
                )
                for item in items
            )

        return CollectionBatch(
            raw_items=raw_items,
            failures=failures,
            collector_name=self.collector_name,
            started_at=started_at,
            completed_at=self._clock(),
            raw_artifact_paths=list(dict.fromkeys(artifact_paths)),
        )

    @staticmethod
    def _write_raw_output(path: Path, stdout: str) -> str:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(stdout, encoding="utf-8")
        return str(path)

    @staticmethod
    def _failure(
        spec: CommandSpec,
        attempted_at: datetime,
        error_code: str,
        message: str,
        *,
        retryable: bool,
        raw_artifact_path: str | None = None,
    ) -> CollectionFailure:
        return CollectionFailure(
            platform=spec.platform,
            capability=spec.capability,
            query_group_id=spec.query_group_id,
            message=message,
            error_code=error_code,
            retryable=retryable,
            attempted_at=attempted_at,
            raw_artifact_path=raw_artifact_path,
        )


def _extract_json_items(payload: Any) -> list[dict[str, Any]]:
    """Accept a JSON object, object with ``items``, or a list of objects."""

    if isinstance(payload, dict) and "items" in payload:
        payload = payload["items"]
    if isinstance(payload, dict):
        return [payload]
    if isinstance(payload, list) and all(isinstance(item, dict) for item in payload):
        return payload
    raise ValueError("collector JSON must be an object, an object with items, or a list of objects")
