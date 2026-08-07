import json
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from avatar_pipeline.browser_collection import (
    BrowserCapability,
    BrowserCollectionEnvelope,
    load_browser_collection,
)
from avatar_pipeline.research_models import (
    CollectorMethod,
    ResearchPlatform,
)

NOW = datetime(2026, 8, 7, 10, 0, tzinfo=UTC)


def item(platform: str = "douyin") -> dict:
    return {
        "source_id": f"{platform}-source-1",
        "platform": platform,
        "event_key": "event-1",
        "content_id": f"{platform}-1",
        "canonical_url": f"https://example.test/{platform}/1",
        "account_name": "公开账号",
        "title_or_caption": "公开热点内容",
        "published_at": NOW.isoformat(),
        "collected_at": NOW.isoformat(),
        "query": "热点",
        "visible_metrics": {"likes": 1200, "comments": 80},
        "metric_visibility": {
            "likes": "visible_exact",
            "comments": "visible_exact",
            "views": "not_visible",
        },
        "collector_method": "chrome_authenticated",
        "raw_evidence_reference": f"browser/{platform}/event-1.json",
    }


def test_browser_envelope_loads_target_platforms_into_collection_batch(tmp_path):
    path = tmp_path / "browser-export.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "collector_name": "chrome-browser-readonly",
                "started_at": NOW.isoformat(),
                "completed_at": NOW.isoformat(),
                "capabilities": [
                    {
                        "platform": "douyin",
                        "status": "ready",
                        "method": "chrome_authenticated",
                        "observed_at": NOW.isoformat(),
                    }
                ],
                "items": [item()],
                "failures": [],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    batch = load_browser_collection(path)

    assert batch.collector_name == "chrome-browser-readonly"
    assert len(batch.raw_items) == 1
    assert batch.raw_items[0].platform is ResearchPlatform.DOUYIN
    assert batch.raw_items[0].payload["event_key"] == "event-1"
    assert batch.raw_artifact_paths == [str(path)]


def test_browser_capability_requires_explicit_failure_status_details():
    with pytest.raises(ValidationError, match="failure_code"):
        BrowserCapability(
            platform=ResearchPlatform.XIAOHONGSHU,
            status="login_required",
            method=CollectorMethod.CHROME_AUTHENTICATED,
            observed_at=NOW,
        )


def test_browser_envelope_rejects_wechat_official_account_as_channels():
    with pytest.raises(ValidationError, match="Official Account"):
        BrowserCollectionEnvelope(
            schema_version=1,
            collector_name="chrome-browser-readonly",
            started_at=NOW,
            completed_at=NOW,
            capabilities=[],
            items=[item("wechat_official_accounts")],
            failures=[],
        )


def test_browser_envelope_rejects_credential_material_recursively():
    payload = {
        "schema_version": 1,
        "collector_name": "chrome-browser-readonly",
        "started_at": NOW,
        "completed_at": NOW,
        "capabilities": [],
        "items": [item()],
        "failures": [],
        "debug": {"nested": {"cookie": "secret"}},
    }

    with pytest.raises(ValidationError, match="credential"):
        BrowserCollectionEnvelope.model_validate(payload)


def test_browser_envelope_preserves_explicit_platform_failure(tmp_path):
    path = tmp_path / "failure.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "collector_name": "chrome-browser-readonly",
                "started_at": NOW.isoformat(),
                "completed_at": NOW.isoformat(),
                "capabilities": [
                    {
                        "platform": "wechat_channels",
                        "status": "manual_assist_required",
                        "method": "browser_assisted",
                        "observed_at": NOW.isoformat(),
                        "failure_code": "ui_changed",
                        "detail": "页面结构变化，需要人工导出结构化记录。",
                    }
                ],
                "items": [],
                "failures": [],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    batch = load_browser_collection(path)

    assert batch.raw_items == []
    assert batch.failures[0].platform is ResearchPlatform.WECHAT_CHANNELS
    assert batch.failures[0].error_code == "ui_changed"
    assert batch.failures[0].message.startswith("页面结构变化")


def test_browser_envelope_rejects_unavailable_metric_with_value():
    bad = item()
    bad["visible_metrics"]["views"] = 10
    with pytest.raises(ValidationError, match="unavailable metric"):
        BrowserCollectionEnvelope(
            schema_version=1,
            collector_name="chrome-browser-readonly",
            started_at=NOW,
            completed_at=NOW,
            capabilities=[],
            items=[bad],
            failures=[],
        )
