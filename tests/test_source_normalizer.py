from datetime import UTC, datetime
from pathlib import Path

import pytest

from avatar_pipeline.models import ContentPillarSlug
from avatar_pipeline.research_adapters import CollectionBatch, RawCollectionItem
from avatar_pipeline.research_models import ConfidenceLevel, ResearchGrade, ResearchPlatform
from avatar_pipeline.source_normalizer import (
    NormalizationContext,
    SourceNormalizationError,
    normalize_batch,
    normalize_source,
)

NOW = datetime(2026, 8, 4, 1, 0, tzinfo=UTC)
CONTEXT = NormalizationContext(
    collector_name="fixture",
    collector_version="fixture-v1",
    collected_at=NOW,
    query_pillars={"q-career": ContentPillarSlug.CAREER_PRESSURE},
    default_query_group_id="q-career",
)


def raw_item(tmp_path: Path, payload: dict, *, platform=ResearchPlatform.OTHER):
    path = tmp_path / "raw.json"
    path.write_text('{"原始":"内容"}', encoding="utf-8")
    return RawCollectionItem(
        platform=platform,
        payload=payload,
        raw_artifact_path=str(path),
        query_group_id="q-career",
    )


def test_normalizes_platform_alias_metrics_and_preserves_unknown_views(tmp_path):
    source = normalize_source(
        raw_item(
            tmp_path,
            {
                "platform": "小红书",
                "title": "停止内耗，不是让你假装坚强",
                "url": "https://www.xiaohongshu.com/explore/note-1?utm_source=test",
                "content_id": "note-1",
                "likes": "1.2万",
                "comments": "3千",
                "saves": "856",
                "published_at": "2026-08-04T08:00:00+08:00",
                "grade": "A",
            },
        ),
        CONTEXT,
    )

    assert source.platform is ResearchPlatform.XIAOHONGSHU
    assert source.metrics.likes == 12000
    assert source.metrics.comments == 3000
    assert source.metrics.saves == 856
    assert source.metrics.views is None
    assert source.published_at is not None and source.published_at.utcoffset() is not None
    assert source.grade is ResearchGrade.A


def test_source_id_is_stable_and_provenance_is_complete(tmp_path):
    raw = raw_item(
        tmp_path,
        {
            "平台": "抖音",
            "标题": "下班后还在回消息的人为什么越来越累",
            "链接": "https://www.douyin.com/video/123?share_token=abc",
            "作品ID": "123",
        },
    )

    first = normalize_source(raw, CONTEXT)
    second = normalize_source(raw, CONTEXT)

    assert first.id == second.id
    assert first.platform is ResearchPlatform.DOUYIN
    assert first.query_group_id == "q-career"
    assert first.pillar is ContentPillarSlug.CAREER_PRESSURE
    assert first.collector == "fixture"
    assert first.collector_version == "fixture-v1"
    assert first.collected_at == NOW
    assert first.raw_artifact_path == raw.raw_artifact_path
    assert len(first.raw_artifact_sha256) == 64
    assert first.confidence is ConfidenceLevel.HIGH


def test_naive_published_time_is_made_aware_and_warned(tmp_path):
    source = normalize_source(
        raw_item(
            tmp_path,
            {
                "platform": "微博",
                "title": "允许自己慢一点",
                "url": "https://weibo.com/1/2",
                "published_at": "2026-08-04 08:00:00",
            },
        ),
        CONTEXT,
    )

    assert source.published_at is not None
    assert source.published_at.tzinfo is UTC
    assert "published_at had no timezone; assumed UTC" in source.warnings


def test_batch_separates_duplicates_rejections_warnings_and_missing_metrics(tmp_path):
    valid = raw_item(
        tmp_path,
        {
            "platform": "小红书",
            "title": "别急着否定自己",
            "url": "https://www.xiaohongshu.com/explore/note-2",
            "content_id": "note-2",
            "likes": "2万+",
        },
    )
    duplicate = valid.model_copy()
    blank = raw_item(
        tmp_path,
        {"platform": "知乎", "title": "   ", "url": "https://zhihu.com/question/1"},
    )
    untraceable = raw_item(
        tmp_path,
        {"platform": "B站", "title": "有标题但没有链接或内容ID"},
    )
    batch = CollectionBatch(
        raw_items=[valid, duplicate, blank, untraceable],
        collector_name="fixture",
        started_at=NOW,
        completed_at=NOW,
        raw_artifact_paths=[valid.raw_artifact_path],
    )

    result = normalize_batch(batch, CONTEXT)

    assert len(result.sources) == 1
    assert len(result.rejected_items) == 2
    assert {item.error_code for item in result.rejected_items} == {
        "blank_title",
        "untraceable_source",
    }
    assert any("duplicate source id" in warning for warning in result.warnings)
    source_id = result.sources[0].id
    assert set(result.missing_metric_fields[source_id]) == {
        "views",
        "comments",
        "shares",
        "saves",
        "followers",
        "platform_heat",
    }


def test_rejects_unknown_query_provenance_and_does_not_invent_identity(tmp_path):
    raw = RawCollectionItem(
        platform=ResearchPlatform.XIAOHONGSHU,
        payload={"title": "无法归属的内容", "content_id": "note-3"},
        raw_artifact_path=str(tmp_path / "missing.json"),
        query_group_id="unknown-query",
    )

    with pytest.raises(SourceNormalizationError, match="unknown_query_group"):
        normalize_source(raw, CONTEXT)

    no_identity = raw.model_copy(
        update={
            "query_group_id": "q-career",
            "payload": {"title": "不能凭空生成平台身份"},
        }
    )
    with pytest.raises(SourceNormalizationError, match="untraceable_source"):
        normalize_source(no_identity, CONTEXT)
