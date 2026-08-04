"""Normalize heterogeneous collector output into traceable research sources."""

from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import BaseModel, ConfigDict, Field

from avatar_pipeline.models import ContentPillarSlug
from avatar_pipeline.research_adapters import CollectionBatch, RawCollectionItem
from avatar_pipeline.research_models import (
    AwareTimestamp,
    ConfidenceLevel,
    EngagementMetrics,
    ResearchGrade,
    ResearchPlatform,
    ResearchSource,
)

_PLATFORM_ALIASES = {
    "douyin": ResearchPlatform.DOUYIN,
    "抖音": ResearchPlatform.DOUYIN,
    "wechat_channels": ResearchPlatform.WECHAT_CHANNELS,
    "wechat channels": ResearchPlatform.WECHAT_CHANNELS,
    "视频号": ResearchPlatform.WECHAT_CHANNELS,
    "微信视频号": ResearchPlatform.WECHAT_CHANNELS,
    "xiaohongshu": ResearchPlatform.XIAOHONGSHU,
    "小红书": ResearchPlatform.XIAOHONGSHU,
    "rednote": ResearchPlatform.XIAOHONGSHU,
    "zhihu": ResearchPlatform.ZHIHU,
    "知乎": ResearchPlatform.ZHIHU,
    "weibo": ResearchPlatform.WEIBO,
    "微博": ResearchPlatform.WEIBO,
    "bilibili": ResearchPlatform.BILIBILI,
    "b站": ResearchPlatform.BILIBILI,
    "哔哩哔哩": ResearchPlatform.BILIBILI,
    "toutiao": ResearchPlatform.TOUTIAO,
    "今日头条": ResearchPlatform.TOUTIAO,
    "jike": ResearchPlatform.JIKE,
    "即刻": ResearchPlatform.JIKE,
    "wechat_official_accounts": ResearchPlatform.WECHAT_OFFICIAL_ACCOUNTS,
    "微信公众号": ResearchPlatform.WECHAT_OFFICIAL_ACCOUNTS,
    "youtube": ResearchPlatform.YOUTUBE,
    "reddit": ResearchPlatform.REDDIT,
}

_FIELD_ALIASES = {
    "title": ("title", "标题", "文案", "name"),
    "excerpt": ("excerpt", "摘要", "简介", "description", "content"),
    "url": ("url", "链接", "地址", "share_url"),
    "content_id": ("content_id", "platform_content_id", "作品ID", "内容ID", "id"),
    "author": ("author", "author_label", "作者", "博主", "昵称"),
    "platform": ("platform", "平台", "source_platform"),
    "published_at": ("published_at", "发布时间", "publish_time", "created_at"),
    "grade": ("grade", "等级", "research_grade"),
}

_METRIC_ALIASES = {
    "views": ("views", "view_count", "播放量", "浏览量", "阅读量"),
    "likes": ("likes", "like_count", "点赞", "点赞数"),
    "comments": ("comments", "comment_count", "评论", "评论数"),
    "shares": ("shares", "share_count", "分享", "转发", "转发数"),
    "saves": ("saves", "save_count", "收藏", "收藏数"),
    "followers": ("followers", "follower_count", "粉丝", "粉丝数"),
    "platform_heat": ("platform_heat", "heat", "热度"),
}

_TRACKING_QUERY_PREFIXES = ("utm_",)
_TRACKING_QUERY_KEYS = {"share_token", "source", "from", "spm"}


class NormalizerModel(BaseModel):
    """Strict base model for normalization inputs and outputs."""

    model_config = ConfigDict(extra="forbid")


class NormalizationContext(NormalizerModel):
    """Trusted collection and query provenance supplied by orchestration."""

    collector_name: str = Field(min_length=1)
    collector_version: str = Field(min_length=1)
    collected_at: AwareTimestamp
    query_pillars: dict[str, ContentPillarSlug] = Field(min_length=1)
    default_query_group_id: str | None = None


class RejectedSource(NormalizerModel):
    """A raw item that could not be normalized without inventing facts."""

    index: int = Field(ge=0)
    platform: ResearchPlatform
    error_code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    raw_artifact_path: str = Field(min_length=1)


class NormalizationResult(NormalizerModel):
    """Normalized sources plus explicit rejects, warnings, and missing metrics."""

    sources: list[ResearchSource] = Field(default_factory=list)
    rejected_items: list[RejectedSource] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    missing_metric_fields: dict[str, list[str]] = Field(default_factory=dict)


class SourceNormalizationError(ValueError):
    """A structured, expected rejection of one raw source."""

    def __init__(self, error_code: str, message: str) -> None:
        self.error_code = error_code
        self.detail = message
        super().__init__(f"{error_code}: {message}")


def normalize_source(raw: RawCollectionItem, context: NormalizationContext) -> ResearchSource:
    """Normalize one raw record while preserving all available provenance."""

    payload = raw.payload
    query_group_id = raw.query_group_id or context.default_query_group_id
    if not query_group_id or query_group_id not in context.query_pillars:
        raise SourceNormalizationError(
            "unknown_query_group", "raw source does not reference a known query group"
        )

    title = _string_value(payload, _FIELD_ALIASES["title"])
    if not title:
        raise SourceNormalizationError("blank_title", "source title is blank")

    url = _string_value(payload, _FIELD_ALIASES["url"])
    content_id = _string_value(payload, _FIELD_ALIASES["content_id"])
    if not url and not content_id:
        raise SourceNormalizationError(
            "untraceable_source", "source requires a URL or platform content id"
        )

    platform = _resolve_platform(raw.platform, payload)
    canonical_url = _canonicalize_url(url) if url else None
    source_id = _stable_source_id(platform, content_id, canonical_url)
    warnings: list[str] = []
    published_at = _parse_published_at(
        _value(payload, _FIELD_ALIASES["published_at"]), warnings
    )
    metrics, metric_notes = _normalize_metrics(payload, warnings)
    raw_path = Path(raw.raw_artifact_path)
    if not raw_path.is_file():
        raise SourceNormalizationError(
            "missing_raw_artifact", f"raw artifact does not exist: {raw.raw_artifact_path}"
        )

    return ResearchSource(
        id=source_id,
        platform=platform,
        query_group_id=query_group_id,
        title=title,
        excerpt=_string_value(payload, _FIELD_ALIASES["excerpt"]),
        url=canonical_url,
        platform_content_id=content_id,
        author_label=_string_value(payload, _FIELD_ALIASES["author"]),
        pillar=context.query_pillars[query_group_id],
        grade=_parse_grade(_value(payload, _FIELD_ALIASES["grade"]), warnings),
        metrics=metrics,
        metric_notes=metric_notes,
        published_at=published_at,
        collector=context.collector_name,
        collector_version=context.collector_version,
        raw_artifact_path=raw.raw_artifact_path,
        raw_artifact_sha256=_sha256_file(raw_path),
        collected_at=context.collected_at,
        confidence=_confidence_for_source(content_id, canonical_url),
        warnings=warnings,
    )


def normalize_batch(
    batch: CollectionBatch, context: NormalizationContext
) -> NormalizationResult:
    """Normalize a batch without allowing one invalid record to abort the rest."""

    sources: list[ResearchSource] = []
    rejected: list[RejectedSource] = []
    warnings: list[str] = []
    missing_metrics: dict[str, list[str]] = {}
    seen_ids: set[str] = set()

    for index, raw in enumerate(batch.raw_items):
        try:
            source = normalize_source(raw, context)
        except SourceNormalizationError as error:
            rejected.append(
                RejectedSource(
                    index=index,
                    platform=raw.platform,
                    error_code=error.error_code,
                    message=error.detail,
                    raw_artifact_path=raw.raw_artifact_path,
                )
            )
            continue

        if source.id in seen_ids:
            warnings.append(f"duplicate source id ignored: {source.id}")
            continue
        seen_ids.add(source.id)
        sources.append(source)
        missing = [
            field
            for field in EngagementMetrics.model_fields
            if getattr(source.metrics, field) is None
        ]
        if missing:
            missing_metrics[source.id] = missing

    warnings.extend(
        f"collector failure preserved: {failure.platform.value}/{failure.error_code or 'unknown'}"
        for failure in batch.failures
    )
    return NormalizationResult(
        sources=sources,
        rejected_items=rejected,
        warnings=warnings,
        missing_metric_fields=missing_metrics,
    )


def _resolve_platform(
    fallback: ResearchPlatform, payload: dict[str, Any]
) -> ResearchPlatform:
    raw_value = _string_value(payload, _FIELD_ALIASES["platform"])
    if not raw_value:
        return fallback
    return _PLATFORM_ALIASES.get(raw_value.casefold(), fallback)


def _value(payload: dict[str, Any], aliases: tuple[str, ...]) -> Any:
    for alias in aliases:
        if alias in payload and payload[alias] is not None:
            return payload[alias]
    return None


def _string_value(payload: dict[str, Any], aliases: tuple[str, ...]) -> str | None:
    value = _value(payload, aliases)
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _parse_count(value: Any) -> int | float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return max(value, 0)
    text = str(value).strip().replace(",", "").replace("+", "")
    if not text or text in {"-", "--", "未知", "暂无"}:
        return None
    multiplier = 1
    if text.endswith("万"):
        multiplier = 10_000
        text = text[:-1]
    elif text.endswith("千"):
        multiplier = 1_000
        text = text[:-1]
    elif text.endswith("亿"):
        multiplier = 100_000_000
        text = text[:-1]
    try:
        return float(text) * multiplier
    except ValueError:
        return None


def _normalize_metrics(
    payload: dict[str, Any], warnings: list[str]
) -> tuple[EngagementMetrics, dict[str, str]]:
    values: dict[str, int | float | None] = {}
    notes: dict[str, str] = {}
    for field, aliases in _METRIC_ALIASES.items():
        raw_value = _value(payload, aliases)
        parsed = _parse_count(raw_value)
        if field == "platform_heat":
            values[field] = float(parsed) if parsed is not None else None
        else:
            values[field] = int(parsed) if parsed is not None else None
        if raw_value is not None:
            notes[field] = f"raw={raw_value}"
            if parsed is None:
                warnings.append(f"could not parse metric {field}: {raw_value}")
    return EngagementMetrics(**values), notes


def _parse_grade(value: Any, warnings: list[str]) -> ResearchGrade:
    if value is None:
        return ResearchGrade.B
    normalized = str(value).strip().upper()
    try:
        return ResearchGrade(normalized)
    except ValueError:
        warnings.append(f"unknown grade {value}; defaulted to B")
        return ResearchGrade.B


def _parse_published_at(value: Any, warnings: list[str]) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        text = str(value).strip().replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            warnings.append(f"could not parse published_at: {value}")
            return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        warnings.append("published_at had no timezone; assumed UTC")
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def _canonicalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key.casefold() not in _TRACKING_QUERY_KEYS
        and not key.casefold().startswith(_TRACKING_QUERY_PREFIXES)
    ]
    path = re.sub(r"/{2,}", "/", parts.path)
    return urlunsplit(
        (parts.scheme.casefold(), parts.netloc.casefold(), path, urlencode(query), "")
    )


def _stable_source_id(
    platform: ResearchPlatform, content_id: str | None, canonical_url: str | None
) -> str:
    identity = content_id or canonical_url
    if identity is None:
        raise SourceNormalizationError("untraceable_source", "source identity is missing")
    digest = hashlib.sha256(f"{platform.value}\0{identity}".encode()).hexdigest()[:20]
    return f"{platform.value}-{digest}"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _confidence_for_source(
    content_id: str | None, canonical_url: str | None
) -> ConfidenceLevel:
    if content_id and canonical_url:
        return ConfidenceLevel.HIGH
    return ConfidenceLevel.MEDIUM
