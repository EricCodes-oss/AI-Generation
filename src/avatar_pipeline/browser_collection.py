"""Credential-free ingestion for read-only browser collection exports."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from avatar_pipeline.research_adapters import CollectionBatch, RawCollectionItem
from avatar_pipeline.research_models import (
    AwareTimestamp,
    CollectionFailure,
    CollectorMethod,
    PlatformEvidenceRecord,
    ResearchPlatform,
)

_TARGET_PLATFORMS = {
    ResearchPlatform.DOUYIN,
    ResearchPlatform.WECHAT_CHANNELS,
    ResearchPlatform.XIAOHONGSHU,
}
_CREDENTIAL_KEY_FRAGMENTS = (
    "cookie",
    "token",
    "password",
    "passwd",
    "authorization",
    "session",
    "secret",
    "csrf",
    "access_key",
    "refresh_key",
)


class BrowserCollectionModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BrowserCapability(BrowserCollectionModel):
    platform: ResearchPlatform
    status: Literal[
        "ready",
        "login_required",
        "ui_changed",
        "rate_limited",
        "manual_assist_required",
    ]
    method: CollectorMethod
    observed_at: AwareTimestamp
    failure_code: str | None = Field(default=None, min_length=1)
    detail: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def validate_capability(self) -> BrowserCapability:
        if self.platform not in _TARGET_PLATFORMS:
            raise ValueError("capability platform must be a target video platform")
        if self.status == "ready" and self.failure_code is not None:
            raise ValueError("ready capability cannot have failure_code")
        if self.status != "ready" and not self.failure_code:
            raise ValueError("failed capability requires failure_code")
        return self


class BrowserFailure(BrowserCollectionModel):
    platform: ResearchPlatform
    capability: str = Field(min_length=1)
    message: str = Field(min_length=1)
    error_code: str = Field(min_length=1)
    retryable: bool = False
    query_group_id: str | None = None


class BrowserCollectionEnvelope(BrowserCollectionModel):
    schema_version: Literal[1]
    collector_name: str = Field(min_length=1)
    started_at: AwareTimestamp
    completed_at: AwareTimestamp
    capabilities: list[BrowserCapability] = Field(default_factory=list)
    items: list[dict[str, Any]] = Field(default_factory=list)
    failures: list[BrowserFailure] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def reject_credentials(cls, value: Any) -> Any:
        _reject_credential_keys(value)
        return value

    @model_validator(mode="after")
    def validate_envelope(self) -> BrowserCollectionEnvelope:
        if self.completed_at < self.started_at:
            raise ValueError("completed_at cannot precede started_at")
        seen_capabilities: set[ResearchPlatform] = set()
        for capability in self.capabilities:
            if capability.platform in seen_capabilities:
                raise ValueError("capability platforms must be unique")
            seen_capabilities.add(capability.platform)
        for index, item in enumerate(self.items):
            if item.get("platform") == ResearchPlatform.WECHAT_OFFICIAL_ACCOUNTS.value:
                raise ValueError("Official Account cannot be reported as WeChat Channels")
            try:
                PlatformEvidenceRecord.model_validate(item)
            except ValueError as error:
                raise ValueError(f"item {index} is invalid browser evidence: {error}") from error
        for failure in self.failures:
            if failure.platform is ResearchPlatform.WECHAT_OFFICIAL_ACCOUNTS:
                raise ValueError("Official Account cannot be reported as WeChat Channels")
        return self


def load_browser_collection(path: Path) -> CollectionBatch:
    """Load a sanitized Agent browser export into the existing collector boundary."""

    path = Path(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    envelope = BrowserCollectionEnvelope.model_validate(payload)
    raw_items = [
        RawCollectionItem(
            platform=ResearchPlatform(item["platform"]),
            payload=item,
            raw_artifact_path=str(path),
            query_group_id=item.get("query_group_id"),
        )
        for item in envelope.items
    ]
    failures = [
        CollectionFailure(
            platform=failure.platform,
            capability=failure.capability,
            query_group_id=failure.query_group_id,
            message=failure.message,
            error_code=failure.error_code,
            retryable=failure.retryable,
            attempted_at=envelope.completed_at,
            raw_artifact_path=str(path),
        )
        for failure in envelope.failures
    ]
    for capability in envelope.capabilities:
        if capability.status != "ready":
            failures.append(
                CollectionFailure(
                    platform=capability.platform,
                    capability="browser_capability",
                    message=capability.detail or capability.failure_code or capability.status,
                    error_code=capability.failure_code,
                    retryable=capability.status in {"rate_limited", "ui_changed"},
                    attempted_at=capability.observed_at,
                    raw_artifact_path=str(path),
                )
            )
    return CollectionBatch(
        raw_items=raw_items,
        failures=failures,
        collector_name=envelope.collector_name,
        started_at=envelope.started_at,
        completed_at=envelope.completed_at,
        raw_artifact_paths=[str(path)],
    )


def _reject_credential_keys(value: Any, path: str = "payload") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized = str(key).casefold().replace("-", "_")
            if any(fragment in normalized for fragment in _CREDENTIAL_KEY_FRAGMENTS):
                raise ValueError(f"credential material is forbidden at {path}.{key}")
            _reject_credential_keys(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_credential_keys(child, f"{path}[{index}]")
